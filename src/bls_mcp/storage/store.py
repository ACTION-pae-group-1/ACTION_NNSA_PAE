"""Read-only, MCP-independent query facade over a published DuckDB snapshot.

All input values are bound parameters (including the list of up to 1,000
series IDs). The connection is opened afresh for each operation; no reader is
shared across threads. Ingestion, publication, and user state live elsewhere.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from bls_mcp.storage.connection import snapshot_reader
from bls_mcp.storage.hierarchy import (
    display_order_problem,
    industry_parents,
    level_parents,
    product_parents,
)
from bls_mcp.storage.models import ObservationRecord, SeriesRecord, ValidationStatus
from bls_mcp.storage.query_models import (
    DEFAULT_RESULT_ROWS,
    CIClassification,
    CUClassification,
    HierarchyEntry,
    NormalizationResult,
    NormalizedObservation,
    ObservationsPage,
    PCClassification,
    QueryStatus,
    SeriesHierarchy,
    SeriesOutcome,
    SeriesSearchFilters,
    SeriesSearchHit,
    SeriesSearchPage,
    validate_max_rows,
    validate_normalization,
    validate_series_ids,
    validate_window,
)
from bls_mcp.storage.snapshots import SnapshotMetadataError, read_snapshot_info

if TYPE_CHECKING:
    from duckdb import DuckDBPyConnection


class QueryResultLimitError(ValueError):
    """The requested output exceeds the hard per-call row budget."""


# Left joins expose classification names without denormalizing the snapshot.
# All query text is fixed by the package, never taken from the caller.
_CATALOG_JOINS = """
FROM series_catalog c
LEFT JOIN pc_series ps ON ps.series_id = c.series_id AND c.program_code = 'pc'
LEFT JOIN pc_industry pi ON pi.industry_code = ps.industry_code
LEFT JOIN pc_product pp ON pp.industry_code = ps.industry_code
                       AND pp.product_code = ps.product_code
LEFT JOIN cu_series cs ON cs.series_id = c.series_id AND c.program_code = 'cu'
LEFT JOIN cu_area ca ON ca.area_code = cs.area_code
LEFT JOIN cu_item ci ON ci.item_code = cs.item_code
LEFT JOIN ci_series es ON es.series_id = c.series_id AND c.program_code = 'ci'
LEFT JOIN ci_dimension eow ON eow.dimension = 'owner' AND eow.code = es.owner_code
LEFT JOIN ci_dimension ein ON ein.dimension = 'industry'
                          AND ein.code = es.industry_code
LEFT JOIN ci_dimension eoc ON eoc.dimension = 'occupation'
                          AND eoc.code = es.occupation_code
LEFT JOIN ci_dimension esu ON esu.dimension = 'subcell'
                          AND esu.code = es.subcell_code
LEFT JOIN ci_dimension ear ON ear.dimension = 'area' AND ear.code = es.area_code
LEFT JOIN ci_dimension ees ON ees.dimension = 'estimate'
                          AND ees.code = es.estimate_code
"""

_CATALOG_COLUMNS = """
c.series_id, c.program_code, c.title, c.description, c.seasonal_adjustment,
c.first_year, c.first_period, c.last_year, c.last_period, c.units,
c.original_reference_base, c.active,
ps.industry_code, pi.industry_name, ps.product_code, pp.product_name,
ps.seasonal_code, ps.base_date,
cs.area_code, ca.area_name, cs.item_code, ci.item_name,
cs.seasonal_code, cs.periodicity_code, cs.base_code, cs.base_period,
es.owner_code, eow.name, es.industry_code, ein.name,
es.occupation_code, eoc.name, es.subcell_code, esu.name,
es.area_code, ear.name, es.estimate_code, ees.name,
es.seasonal_code, es.periodicity_code
"""


# Normalize punctuation and common inflections consistently on both sides.
# These scores rank textual relevance, not economic suitability.
def _search_normalized(column: str) -> str:
    return (
        "trim(regexp_replace(replace(lower(coalesce("
        + column
        + ", '')), 'mixed', 'mix'), '[^a-z0-9]+', ' ', 'g'))"
    )


_SEARCH_METADATA = (
    "concat_ws(' ', c.title, c.description, pi.industry_name, "
    "pp.product_name, ca.area_name, ci.item_name, ein.name, eoc.name, ees.name)"
)
_SEARCH_JOIN = f"""
CROSS JOIN (SELECT ?::VARCHAR AS q, ?::VARCHAR[] AS tokens,
                   ?::VARCHAR AS exact_id) search_query
CROSS JOIN LATERAL (
    SELECT {_search_normalized("c.title")} AS title_text,
           {_search_normalized(_SEARCH_METADATA)} AS metadata_text
) search_text
CROSS JOIN LATERAL (
    SELECT CASE
      WHEN lower(c.series_id) = search_query.exact_id THEN 1.00
      WHEN search_text.title_text = search_query.q THEN 0.95
      WHEN lower(pp.product_code) = search_query.q THEN 0.90
      WHEN strpos(' ' || search_text.title_text || ' ',
                  ' ' || search_query.q || ' ') > 0 THEN 0.85
      WHEN list_has_all(string_split(search_text.title_text, ' '),
                        search_query.tokens) THEN 0.75
      WHEN list_has_all(string_split(search_text.metadata_text, ' '),
                        search_query.tokens) THEN 0.50
      WHEN len(search_query.tokens) >= 3 AND
           len(list_filter(search_query.tokens, t ->
               list_contains(string_split(search_text.metadata_text, ' '), t)))
               >= len(search_query.tokens) - 1 THEN 0.35
      ELSE 0.0 END AS relevance
) search_rank
"""


def _normalize_query(query: str) -> str:
    import re

    return " ".join(re.findall(r"[a-z0-9]+", query.casefold().replace("mixed", "mix")))


_REQUESTED = "WITH requested AS (SELECT unnest(?::VARCHAR[]) AS series_id)"


def _catalog_filters(filters: SeriesSearchFilters) -> tuple[str, list[object]]:
    clauses: list[str] = []
    params: list[object] = []
    if filters.query and _normalize_query(filters.query):
        clauses.append("search_rank.relevance > 0")
    if filters.programs is not None:
        clauses.append("c.program_code IN (SELECT unnest(?::VARCHAR[]))")
        params.append(list(filters.programs))
    if filters.active_only:
        clauses.append("c.active IS TRUE")
    if filters.seasonal_adjustment is not None:
        clauses.append("c.seasonal_adjustment = ?")
        params.append(filters.seasonal_adjustment)
    # A code filter matches whichever program defines that dimension.
    for columns, value in (
        (("ps.industry_code", "es.industry_code"), filters.industry_code),
        (("ps.product_code",), filters.product_code),
        (("cs.area_code", "es.area_code"), filters.area_code),
        (("cs.item_code",), filters.item_code),
        (("cs.periodicity_code", "es.periodicity_code"), filters.periodicity_code),
    ):
        if value is not None:
            clauses.append("(" + " OR ".join(f"{c} = ?" for c in columns) + ")")
            params.extend([value] * len(columns))
    return " AND ".join(clauses) if clauses else "TRUE", params


def _year_conditions(
    start_year: int | None, end_year: int | None
) -> tuple[str, list[object]]:
    clauses: list[str] = []
    params: list[object] = []
    if start_year is not None:
        clauses.append("o.year >= ?")
        params.append(start_year)
    if end_year is not None:
        clauses.append("o.year <= ?")
        params.append(end_year)
    return " AND ".join(clauses) if clauses else "TRUE", params


def _known_series(conn: DuckDBPyConnection, ids: tuple[str, ...]) -> set[str]:
    return {
        row[0]
        for row in conn.execute(
            f"""{_REQUESTED}
            SELECT c.series_id FROM series_catalog c
            JOIN requested r ON r.series_id = c.series_id""",
            [list(ids)],
        ).fetchall()
    }


def _base_values(
    conn: DuckDBPyConnection,
    ids: tuple[str, ...],
    year: int,
    period: str,
) -> dict[str, float]:
    rows = conn.execute(
        f"""{_REQUESTED}
        SELECT o.series_id, o.value FROM observations o
        JOIN requested r ON r.series_id = o.series_id
        WHERE o.year = ? AND o.period = ?""",
        [list(ids), year, period],
    ).fetchall()
    result: dict[str, float] = {}
    for series_id, value in rows:
        if series_id in result:
            raise SnapshotMetadataError(
                f"Multiple base observations for {series_id} at {year} {period}"
            )
        result[series_id] = float(value)
    return result


def _outcomes(
    ids: tuple[str, ...],
    known: set[str],
    counts: Counter[str],
    bases: dict[str, float] | None = None,
) -> tuple[SeriesOutcome, ...]:
    outcomes = []
    for series_id in ids:
        base_value = bases.get(series_id) if bases is not None else None
        if series_id not in known:
            status = QueryStatus.UNKNOWN_SERIES
        elif bases is not None and base_value is None:
            status = QueryStatus.MISSING_BASE
        elif bases is not None and base_value == 0:
            status = QueryStatus.ZERO_BASE
        elif counts[series_id] == 0:
            status = QueryStatus.NO_ROWS_IN_WINDOW
        else:
            status = QueryStatus.SUCCESS
        outcomes.append(SeriesOutcome(series_id, status, counts[series_id], base_value))
    return tuple(outcomes)


def _bounded_rows(rows: list[tuple[object, ...]], max_rows: int) -> None:
    if len(rows) > max_rows:
        raise QueryResultLimitError(
            f"Result exceeds max_rows={max_rows}; narrow the year range "
            "or split the series batch"
        )


#: (dimension, code, name, series_id) before observation presence is known.
_Node = tuple[str, str, str | None, str | None]
#: parents, sub-items, dimensions looked up, and (dimension, reason) unverified.
_Tree = tuple[list[_Node], list[_Node], list[str], list[tuple[str, str]]]

_CI_DIMENSIONS = ("owner", "industry", "occupation", "subcell", "area", "estimate")
#: ECI dimensions whose nesting says what an index includes. Owner is flat;
#: area is geography and subcell a worker cross-tabulation, so neither is
#: composition. Estimate is: total compensation = wages + benefits.
_CI_COMPOSITION = ("industry", "occupation", "estimate")


def _pc_tree(conn: DuckDBPyConnection, series_id: str) -> _Tree:
    row = conn.execute(
        "SELECT industry_code, product_code, seasonal_code FROM pc_series "
        "WHERE series_id = ?",
        [series_id],
    ).fetchone()
    if row is None:
        return [], [], [], []
    industry, product, seasonal = row[0], row[1] or row[0], row[2]
    family = industry[:2]  # NAICS-style nesting never crosses the first 2 chars
    industry_names = dict(
        conn.execute(
            "SELECT industry_code, industry_name FROM pc_industry "
            "WHERE left(industry_code, 2) = ?",
            [family],
        ).fetchall()
    )
    product_names = dict(
        conn.execute(
            "SELECT product_code, product_name FROM pc_product WHERE industry_code = ?",
            [industry],
        ).fetchall()
    )
    series = {
        (ind, prod or ind): sid
        for ind, prod, sid in conn.execute(
            "SELECT industry_code, product_code, series_id FROM pc_series "
            "WHERE seasonal_code = ? AND left(industry_code, 2) = ?",
            [seasonal, family],
        ).fetchall()
    }
    ind_parent = industry_parents(industry_names)
    prod_parent = product_parents(industry, product_names)

    def industry_node(code: str) -> _Node:
        return ("industry", code, industry_names.get(code), series.get((code, code)))

    def product_node(code: str) -> _Node:
        name = product_names.get(code)
        return ("product", code, name, series.get((industry, code)))

    unverified: list[tuple[str, str]] = []
    if product == industry:
        dimensions = ["product", "industry"]
        parent = ind_parent.get(industry)
        parents = [industry_node(parent)] if parent else []
        subs = [product_node(p) for p, up in prod_parent.items() if up == industry]
        subs += [industry_node(c) for c, up in ind_parent.items() if up == industry]
        if not industry.rstrip("-").isdigit():
            # e.g. OMFG-- (total manufacturing) or ATRADE: BLS aggregates whose
            # member industries are not encoded in the code itself.
            unverified.append(
                (
                    "industry",
                    f"'{industry}' is a BLS aggregate whose member industries "
                    "are not encoded in its code, so they could not be identified",
                )
            )
    else:
        dimensions = ["product"]
        up = prod_parent.get(product, industry)
        parents = [industry_node(up) if up == industry else product_node(up)]
        subs = [product_node(p) for p, pp in prod_parent.items() if pp == product]
    subs.sort(key=lambda node: (node[0], node[1]))
    return parents, subs, dimensions, unverified


def _level_tree(
    rows: list[tuple[str, str, int, int, bool]],
    target: str,
    dimension: str,
    series: dict[str, str],
) -> tuple[list[_Node], list[_Node], str | None]:
    """Parent and direct children of *target* in a display-level hierarchy.

    Rows marked not selectable are display headings, not codes: they are
    never listed, and the codes under a heading are listed under the heading's
    own parent. When the display order is not a single hierarchy, nothing is
    reported and the reason is returned instead.
    """
    headings = frozenset(row[0] for row in rows if not row[4] and row[0] != target)
    problem = display_order_problem(((r[0], r[2], r[3]) for r in rows), headings)
    if problem is not None:
        return [], [], problem
    kept = [row for row in rows if row[0] not in headings]
    names = {row[0]: row[1] for row in kept}
    parents_of = level_parents(((row[0], row[2], row[3]) for row in rows), headings)
    parent = parents_of.get(target)
    up = [(dimension, parent, names.get(parent), series.get(parent))] if parent else []
    down: list[_Node] = [
        (dimension, row[0], row[1], series.get(row[0]))
        for row in sorted(kept, key=lambda r: (r[3], r[0]))
        if parents_of.get(row[0]) == target
    ]
    return up, down, None


def _cu_tree(conn: DuckDBPyConnection, series_id: str) -> _Tree:
    row = conn.execute(
        "SELECT area_code, item_code, seasonal_code, periodicity_code, base_code "
        "FROM cu_series WHERE series_id = ?",
        [series_id],
    ).fetchone()
    if row is None:
        return [], [], [], []
    area, item, seasonal, periodicity, base = row
    rows = conn.execute(
        "SELECT item_code, item_name, display_level, sort_sequence, selectable "
        "FROM cu_item"
    ).fetchall()
    series = dict(
        conn.execute(
            "SELECT item_code, series_id FROM cu_series WHERE area_code = ? "
            "AND seasonal_code = ? AND periodicity_code = ? AND base_code = ?",
            [area, seasonal, periodicity, base],
        ).fetchall()
    )
    up, down, problem = _level_tree(rows, item, "item", series)
    return up, down, ["item"], [("item", problem)] if problem else []


def _ci_tree(conn: DuckDBPyConnection, series_id: str) -> _Tree:
    columns = ", ".join(f"{d}_code" for d in _CI_DIMENSIONS)
    row = conn.execute(
        f"SELECT seasonal_code, {columns} FROM ci_series WHERE series_id = ?",
        [series_id],
    ).fetchone()
    if row is None:
        return [], [], [], []
    seasonal, codes = row[0], dict(zip(_CI_DIMENSIONS, row[1:], strict=True))
    parents: list[_Node] = []
    subs: list[_Node] = []
    unverified: list[tuple[str, str]] = []
    for dimension in _CI_COMPOSITION:
        rows = conn.execute(
            "SELECT code, name, display_level, sort_sequence, selectable "
            "FROM ci_dimension WHERE dimension = ?",
            [dimension],
        ).fetchall()
        # Series that differ from this one only in the current dimension.
        others = [d for d in _CI_DIMENSIONS if d != dimension]
        same = " AND ".join(f"{d}_code = ?" for d in others)
        series = dict(
            conn.execute(
                f"SELECT {dimension}_code, series_id FROM ci_series "
                f"WHERE seasonal_code = ? AND {same}",
                [seasonal, *(codes[d] for d in others)],
            ).fetchall()
        )
        up, down, problem = _level_tree(rows, codes[dimension], dimension, series)
        parents += up
        subs += down
        if problem:
            unverified.append((dimension, problem))
    return parents, subs, list(_CI_COMPOSITION), unverified


class BLSStore:
    """Query a fixed, validated and PUBLISHED DuckDB file by path.

    This service does not follow an active-snapshot registry (Milestone 6).
    Readers remain independent and cannot create or modify a database. A test
    fixture may mark an offline file PUBLISHED to exercise the contract, but
    normal builds must not bypass the future validation/publication workflow.
    """

    def __init__(
        self,
        snapshot_path: str | Path,
        *,
        threads: int | None = None,
        memory_limit: str | None = None,
    ) -> None:
        self.snapshot_path = Path(snapshot_path)
        self.threads = threads
        self.memory_limit = memory_limit

    @contextmanager
    def _read(self) -> Iterator[tuple[DuckDBPyConnection, str]]:
        with snapshot_reader(
            self.snapshot_path,
            threads=self.threads,
            memory_limit=self.memory_limit,
        ) as conn:
            info = read_snapshot_info(conn)
            if info.validation_status is not ValidationStatus.PASSED:
                raise SnapshotMetadataError(
                    "A published query snapshot must have PASSED validation"
                )
            yield conn, info.snapshot_id

    def search_series(
        self, filters: SeriesSearchFilters | None = None
    ) -> SeriesSearchPage:
        """Search and rank normalized catalog matches with stable pagination."""
        filters = filters if filters is not None else SeriesSearchFilters()
        where, params = _catalog_filters(filters)
        normalized = _normalize_query(filters.query)

        # A nonblank query containing no searchable tokens is not
        # equivalent to an intentionally blank catalog-browsing query.
        if filters.query.strip() and not normalized:
            with self._read() as (_, snapshot_id):
                return SeriesSearchPage(
                    snapshot_id,
                    (),
                    0,
                    filters.limit,
                    filters.offset,
                )

        ranked = bool(normalized)
        joins = _CATALOG_JOINS + (_SEARCH_JOIN if ranked else "")
        query_params: list[object] = (
            [normalized, normalized.split(), filters.query.casefold()] if ranked else []
        )
        order = (
            "search_rank.relevance DESC, lower(c.title), c.series_id"
            if ranked
            else "lower(c.title), c.series_id"
        )
        extra = ", search_rank.relevance" if ranked else ""
        with self._read() as (conn, snapshot_id):
            total_row = conn.execute(
                f"SELECT COUNT(*) {joins} WHERE {where}",
                [*query_params, *params],
            ).fetchone()
            assert total_row is not None
            rows = conn.execute(
                f"""SELECT {_CATALOG_COLUMNS}{extra}
                {joins} WHERE {where}
                ORDER BY {order}
                LIMIT ? OFFSET ?""",
                [*query_params, *params, filters.limit, filters.offset],
            ).fetchall()
        matches = []
        for row in rows:
            series = SeriesRecord(*row[:12])
            classification: (
                PCClassification | CUClassification | CIClassification | None
            ) = None
            if series.program_code == "pc" and row[12] is not None:
                classification = PCClassification(*row[12:18])
            elif series.program_code == "cu" and row[18] is not None:
                classification = CUClassification(*row[18:26])
            elif series.program_code == "ci" and row[26] is not None:
                classification = CIClassification(*row[26:40])
            score = float(row[40]) if ranked else None
            reason = None
            if score is not None:
                reason = {
                    1.0: "exact series ID",
                    0.95: "exact normalized title",
                    0.9: "exact product classification code",
                    0.85: "title phrase",
                    0.75: "all title tokens",
                    0.5: "all catalog metadata tokens",
                    0.35: "partial catalog metadata tokens",
                }[score]
            matches.append(SeriesSearchHit(series, classification, score, reason))
        return SeriesSearchPage(
            snapshot_id,
            tuple(matches),
            int(total_row[0]),
            filters.limit,
            filters.offset,
        )

    def series_hierarchy(self, series_id: str) -> SeriesHierarchy | None:
        """The codes directly above and beneath one series' code.

        Each entry names the code and, when this snapshot has one, the series
        that differs from *series_id* only in that code, and whether that
        series has observations. Returns None for an unknown series ID.
        """
        validate_series_ids([series_id])
        with self._read() as (conn, snapshot_id):
            row = conn.execute(
                "SELECT program_code, title FROM series_catalog WHERE series_id = ?",
                [series_id],
            ).fetchone()
            if row is None:
                return None
            program, title = row
            trees = {"pc": _pc_tree, "cu": _cu_tree, "ci": _ci_tree}
            tree = trees.get(program)
            if tree is None:
                unsupported = f"program '{program}' is not supported"
                found: _Tree = ([], [], [], [("all", unsupported)])
            else:
                found = tree(conn, series_id)
            parents, subs, dimensions, unverified = found
            linked = sorted({node[3] for node in parents + subs if node[3]})
            with_data: set[str] = set()
            if linked:
                with_data = {
                    sid
                    for (sid,) in conn.execute(
                        f"""{_REQUESTED}
                        SELECT DISTINCT o.series_id FROM observations o
                        JOIN requested r ON r.series_id = o.series_id""",
                        [linked],
                    ).fetchall()
                }

        def entry(node: _Node) -> HierarchyEntry:
            dimension, code, name, sid = node
            return HierarchyEntry(dimension, code, name, sid, sid in with_data)

        return SeriesHierarchy(
            snapshot_id,
            series_id,
            program,
            title,
            tuple(entry(node) for node in parents),
            tuple(entry(node) for node in subs),
            tuple(dimensions),
            tuple(unverified),
        )

    def get_observations(
        self,
        series_ids: tuple[str, ...] | list[str],
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        max_rows: int = DEFAULT_RESULT_ROWS,
    ) -> ObservationsPage:
        """Retrieve original DOUBLE values for 1-1,000 series IDs.

        Order is by series ID, year, then original BLS period code; M13 is
        an annual average, not a thirteenth month. Exceeding max_rows raises
        instead of silently dropping observations.
        """
        ids = validate_series_ids(series_ids)
        validate_window(start_year, end_year)
        validate_max_rows(max_rows)
        where, year_params = _year_conditions(start_year, end_year)
        with self._read() as (conn, snapshot_id):
            known = _known_series(conn, ids)
            rows = conn.execute(
                f"""{_REQUESTED}
                SELECT o.series_id, o.year, o.period, o.value,
                       o.source_file_id, o.footnote_codes
                FROM observations o
                JOIN requested r ON r.series_id = o.series_id
                WHERE {where}
                ORDER BY o.series_id, o.year, o.period, o.source_file_id
                LIMIT ?""",
                [list(ids), *year_params, max_rows + 1],
            ).fetchall()
        _bounded_rows(rows, max_rows)
        observations = tuple(ObservationRecord(*row) for row in rows)
        counts = Counter(obs.series_id for obs in observations)
        return ObservationsPage(
            snapshot_id, observations, _outcomes(ids, known, counts)
        )

    def normalize_series(
        self,
        series_ids: tuple[str, ...] | list[str],
        *,
        base_year: int,
        base_period: str,
        start_year: int | None = None,
        end_year: int | None = None,
        target_base: float = 100.0,
        max_rows: int = DEFAULT_RESULT_ROWS,
    ) -> NormalizationResult:
        """Rebase each series in DuckDB SQL, using its exact base reading.

        Bases are looked up independently of the year window. There is no
        interpolation, fallback, borrowing another series' base, or division
        by zero. QueryStatus explains why any requested series has no output.
        """
        ids = validate_series_ids(series_ids)
        validate_window(start_year, end_year)
        validate_normalization(base_year, base_period, target_base)
        validate_max_rows(max_rows)
        where, year_params = _year_conditions(start_year, end_year)
        with self._read() as (conn, snapshot_id):
            known = _known_series(conn, ids)
            bases = _base_values(conn, ids, base_year, base_period)
            rows = conn.execute(
                f"""{_REQUESTED},
                base AS (
                    SELECT b.series_id, b.value AS base_value
                    FROM observations b
                    JOIN requested r ON r.series_id = b.series_id
                    WHERE b.year = ? AND b.period = ?
                )
                SELECT o.series_id, o.year, o.period, o.value,
                       (o.value / base.base_value) * ? AS normalized_value,
                       base.base_value, o.source_file_id, o.footnote_codes
                FROM observations o
                JOIN base ON base.series_id = o.series_id
                WHERE base.base_value <> 0 AND {where}
                ORDER BY o.series_id, o.year, o.period, o.source_file_id
                LIMIT ?""",
                [
                    list(ids),
                    base_year,
                    base_period,
                    target_base,
                    *year_params,
                    max_rows + 1,
                ],
            ).fetchall()
        _bounded_rows(rows, max_rows)
        observations = tuple(NormalizedObservation(*row) for row in rows)
        counts = Counter(obs.series_id for obs in observations)
        return NormalizationResult(
            snapshot_id=snapshot_id,
            base_year=base_year,
            base_period=base_period,
            target_base=target_base,
            observations=observations,
            statuses=_outcomes(ids, known, counts, bases),
        )
