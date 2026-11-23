"""Offline Employment Cost Index (CI) ingestion into a BUILDING DuckDB snapshot.

Only **current-dollar index** series (``periodicity_code = 'I'``, December
2005 = 100) are loaded. Every other CI family is a percent change, a
constant-dollar index or a response rate; none is a ratio-scale escalation
input, so those series and their observations are counted and left out.

Python parses the small metadata files; DuckDB streams the ``ci.data`` files
into an on-disk staging table. No network or MCP operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bls_mcp.ingestion.ci_manifest import (
    CI_DATA_ROLES,
    CI_DIMENSIONS,
    CI_SERIES_HEADER,
    CIInputManifest,
    CISourceFile,
    load_ci_manifest,
    verify_ci_source,
)
from bls_mcp.storage.models import SnapshotState, SourceFileReceipt, ValidationStatus
from bls_mcp.storage.snapshots import read_snapshot_info, write_source_file

if TYPE_CHECKING:
    from duckdb import DuckDBPyConnection


class CIIngestError(ValueError):
    """A CI classification, observation or cross-file overlap is invalid."""


@dataclass(frozen=True, slots=True)
class CIIngestReport:
    snapshot_id: str
    source_files: int
    dimension_codes: int
    series: int
    excluded_series: int
    rows_read: int
    excluded_rows: int
    missing_rows: int
    identical_duplicates: int
    observations: int
    art_index: str


@dataclass(frozen=True, slots=True)
class _CISeries:
    series_id: str
    seasonal: str
    owner_code: str
    industry_code: str
    occupation_code: str
    subcell_code: str
    area_code: str
    estimate_code: str
    title: str
    begin_year: int
    begin_period: str
    end_year: int
    end_period: str


#: The only CI family that is a ratio-scale index level.
INDEX_PERIODICITY = "I"
REFERENCE_BASE = "December 2005=100"
_ART_INDEX = "observations_series_id_art"
_QUARTERS = {"Q01", "Q02", "Q03", "Q04"}
_SERIES_ID_LENGTH = 17
_DIMENSION_FIELDS = (
    ("owner", "owner_code"),
    ("industry", "industry_code"),
    ("occupation", "occupation_code"),
    ("subcell", "subcell_code"),
    ("area", "area_code"),
    ("estimate", "estimate_code"),
)

_STAGE_FROM_FILE = """
    INSERT INTO _ci_raw
    SELECT ?, TRIM(series_id), TRIM(year), TRIM(period), TRIM(value),
           COALESCE(TRIM(footnote_codes), '')
    FROM read_csv(
        ?, delim = '\t', header = true, auto_detect = false,
        columns = {
            'series_id': 'VARCHAR', 'year': 'VARCHAR', 'period': 'VARCHAR',
            'value': 'VARCHAR', 'footnote_codes': 'VARCHAR'
        },
        quote = '', escape = '', null_padding = false, ignore_errors = false
    )
"""


def _read_rows(path: Path, names: tuple[str, ...]) -> list[tuple[str, ...]]:
    """Strict CI metadata TSV with optional empty trailing BLS tab fields."""
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise CIIngestError(f"Cannot read CI metadata: {path.name}") from exc
    if not lines:
        raise CIIngestError(f"Empty CI metadata: {path.name}")
    header = [part.strip() for part in lines[0].split("\t")]
    while len(header) > len(names) and not header[-1]:
        header.pop()
    if tuple(header) != names:
        raise CIIngestError(f"Unexpected CI metadata header: {path.name}")
    records: list[tuple[str, ...]] = []
    for lineno, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        fields = [part.strip() for part in line.split("\t")]
        while len(fields) > len(names) and not fields[-1]:
            fields.pop()
        if len(fields) != len(names):
            raise CIIngestError(f"{path.name}:{lineno}: incorrect column count")
        records.append(tuple(fields))
    if not records:
        raise CIIngestError(f"CI metadata has no records: {path.name}")
    return records


def _int(value: str, label: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise CIIngestError(f"CI {label} is not an integer: {value!r}") from exc
    if parsed < 0 or parsed > 32767:
        raise CIIngestError(f"CI {label} out of range: {value!r}")
    return parsed


def _read_dimensions(
    files: dict[str, Path],
) -> dict[str, dict[str, tuple[str, int, bool, int]]]:
    """Return ``{dimension: {code: (name, display_level, selectable, order)}}``."""
    dimensions: dict[str, dict[str, tuple[str, int, bool, int]]] = {}
    for role, (dimension, code_column, text_column, _name) in CI_DIMENSIONS.items():
        codes: dict[str, tuple[str, int, bool, int]] = {}
        for code, name, level, selectable, order in _read_rows(
            files[role],
            (code_column, text_column, "display_level", "selectable", "sort_sequence"),
        ):
            if not code or not name or code in codes:
                raise CIIngestError(
                    f"Missing or duplicate CI {dimension} code/name: {code!r}"
                )
            if selectable not in ("T", "F"):
                raise CIIngestError(
                    f"Invalid CI {dimension} selectable for {code}: {selectable!r}"
                )
            codes[code] = (
                name,
                _int(level, f"{dimension} display_level"),
                selectable == "T",
                _int(order, f"{dimension} sort_sequence"),
            )
        dimensions[dimension] = codes
    return dimensions


def _read_series(
    path: Path, dimensions: dict[str, dict[str, tuple[str, int, bool, int]]]
) -> tuple[list[_CISeries], set[str]]:
    """Return index-level series and the IDs of every excluded CI series."""
    included: list[_CISeries] = []
    excluded: set[str] = set()
    seen: set[str] = set()
    for (
        series_id,
        seasonal,
        owner,
        industry,
        occupation,
        subcell,
        area,
        periodicity,
        estimate,
        title,
        _footnotes,
        first_year,
        first_period,
        last_year,
        last_period,
    ) in _read_rows(path, CI_SERIES_HEADER):
        if not series_id or series_id in seen or not title:
            raise CIIngestError(f"Missing or duplicate CI series/title: {series_id!r}")
        seen.add(series_id)
        # ci.txt section 4: CI + seasonal + owner + estimate ... + periodicity.
        if (
            len(series_id) != _SERIES_ID_LENGTH
            or not series_id.startswith("CI")
            or seasonal not in ("S", "U")
            or series_id[2] != seasonal
            or series_id[3] != owner
            or series_id[4:6] != estimate
            or not periodicity
            or series_id[-1] != periodicity
        ):
            raise CIIngestError(
                f"CI series identifier contradicts metadata: {series_id}"
            )
        if periodicity != INDEX_PERIODICITY:
            excluded.add(series_id)
            continue
        codes = (owner, industry, occupation, subcell, area, estimate)
        for (dimension, _column), code in zip(_DIMENSION_FIELDS, codes, strict=True):
            if code not in dimensions[dimension]:
                raise CIIngestError(
                    f"Unknown CI {dimension} code for {series_id}: {code!r}"
                )
        begin = _int(first_year, "begin_year")
        end = _int(last_year, "end_year")
        if (
            begin < 1
            or end < 1
            or first_period not in _QUARTERS
            or last_period not in _QUARTERS
            or (begin, first_period) > (end, last_period)
        ):
            raise CIIngestError(f"Invalid CI series date range: {series_id}")
        included.append(
            _CISeries(
                series_id,
                seasonal,
                owner,
                industry,
                occupation,
                subcell,
                area,
                estimate,
                title,
                begin,
                first_period,
                end,
                last_period,
            )
        )
    if not included:
        raise CIIngestError("CI series file has no current-dollar index series")
    return included, excluded


def _insert_metadata(
    conn: DuckDBPyConnection,
    dimensions: dict[str, dict[str, tuple[str, int, bool, int]]],
    series: list[_CISeries],
) -> None:
    conn.executemany(
        "INSERT INTO ci_dimension VALUES (?, ?, ?, ?, ?, ?)",
        [
            (dimension, code, *attrs)
            for dimension, codes in dimensions.items()
            for code, attrs in codes.items()
        ],
    )
    latest = max((s.end_year, s.end_period) for s in series)
    conn.executemany(
        """INSERT INTO series_catalog (
            series_id, program_code, title, seasonal_adjustment,
            first_year, first_period, last_year, last_period,
            units, original_reference_base, active
        ) VALUES (?, 'ci', ?, ?, ?, ?, ?, ?, 'index', ?, ?)""",
        [
            (
                s.series_id,
                s.title,
                s.seasonal == "S",
                s.begin_year,
                s.begin_period,
                s.end_year,
                s.end_period,
                REFERENCE_BASE,
                (s.end_year, s.end_period) == latest,
            )
            for s in series
        ],
    )
    conn.executemany(
        """INSERT INTO ci_series (
            series_id, seasonal_code, owner_code, industry_code,
            occupation_code, subcell_code, area_code, estimate_code,
            periodicity_code
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                s.series_id,
                s.seasonal,
                s.owner_code,
                s.industry_code,
                s.occupation_code,
                s.subcell_code,
                s.area_code,
                s.estimate_code,
                INDEX_PERIODICITY,
            )
            for s in series
        ],
    )


def _validate_stage(
    conn: DuckDBPyConnection, excluded: set[str]
) -> tuple[int, int, int, int]:
    """Type-check staged rows; return (read, excluded, missing, duplicates)."""
    bad = conn.execute(
        """SELECT source_file_id, series_id, year_text, period, value_text
        FROM _ci_raw WHERE
            series_id IS NULL OR series_id = ''
            OR TRY_CAST(year_text AS SMALLINT) IS NULL
            OR TRY_CAST(year_text AS SMALLINT) < 1
            OR period IS NULL
            OR NOT regexp_full_match(period, 'Q0[1-4]')
            OR (
                COALESCE(value_text, '') NOT IN ('', '-')
                AND (TRY_CAST(value_text AS DOUBLE) IS NULL
                     OR NOT isfinite(TRY_CAST(value_text AS DOUBLE)))
            )
        LIMIT 1"""
    ).fetchone()
    if bad is not None:
        raise CIIngestError(f"Malformed CI observation: {bad}")

    conn.execute("CREATE TEMP TABLE _ci_excluded (series_id VARCHAR PRIMARY KEY)")
    if excluded:
        conn.executemany(
            "INSERT INTO _ci_excluded VALUES (?)", [(sid,) for sid in sorted(excluded)]
        )
    unknown = conn.execute(
        """SELECT r.source_file_id, r.series_id FROM _ci_raw r
        LEFT JOIN series_catalog c ON c.series_id=r.series_id
                                 AND c.program_code='ci'
        LEFT JOIN _ci_excluded x ON x.series_id=r.series_id
        WHERE c.series_id IS NULL AND x.series_id IS NULL LIMIT 1"""
    ).fetchone()
    if unknown is not None:
        raise CIIngestError(f"Observation refers to unknown CI series: {unknown}")

    counts = conn.execute(
        """SELECT COUNT(*),
                  COUNT(*) FILTER (WHERE x.series_id IS NOT NULL),
                  COUNT(*) FILTER (
                      WHERE x.series_id IS NULL
                        AND COALESCE(r.value_text, '') IN ('', '-'))
        FROM _ci_raw r LEFT JOIN _ci_excluded x ON x.series_id=r.series_id"""
    ).fetchone()
    assert counts is not None
    raw, skipped, missing = int(counts[0]), int(counts[1]), int(counts[2])
    conn.execute(
        """CREATE TEMP TABLE _ci_typed AS
        SELECT r.source_file_id, r.series_id,
               CAST(r.year_text AS SMALLINT) AS year, r.period,
               CAST(r.value_text AS DOUBLE) AS value, r.footnote_codes
        FROM _ci_raw r
        JOIN series_catalog c ON c.series_id=r.series_id AND c.program_code='ci'
        WHERE COALESCE(r.value_text, '') NOT IN ('', '-')"""
    )
    conflict = conn.execute(
        """SELECT series_id, year, period FROM _ci_typed
        GROUP BY series_id, year, period
        HAVING MIN(value) <> MAX(value) OR COUNT(DISTINCT footnote_codes) > 1
        LIMIT 1"""
    ).fetchone()
    if conflict is not None:
        raise CIIngestError(f"Conflicting CI observations across files: {conflict}")
    duplicate = conn.execute(
        """SELECT COALESCE(SUM(c - 1), 0) FROM
        (SELECT COUNT(*) AS c FROM _ci_typed
         GROUP BY series_id, year, period HAVING COUNT(*) > 1)"""
    ).fetchone()
    assert duplicate is not None
    return raw, skipped, missing, int(duplicate[0])


def _insert_observations(conn: DuckDBPyConnection) -> int:
    conn.execute(
        """INSERT INTO observations (
            series_id, year, period, value, footnote_codes, source_file_id
        )
        SELECT series_id, year, period, value,
               NULLIF(footnote_codes, ''), source_file_id
        FROM (
            SELECT *, ROW_NUMBER() OVER (
                PARTITION BY series_id, year, period ORDER BY source_file_id
            ) AS chosen FROM _ci_typed
        ) WHERE chosen=1
        ORDER BY series_id, year, period"""
    )
    # Earlier program loaders create this ART; a CI-only build creates it here.
    existing = conn.execute(
        "SELECT sql FROM duckdb_indexes() WHERE table_name='observations' "
        "AND index_name=?",
        [_ART_INDEX],
    ).fetchone()
    if existing is None:
        conn.execute(f"CREATE INDEX {_ART_INDEX} ON observations (series_id)")
    confirmed = conn.execute(
        "SELECT sql, is_unique FROM duckdb_indexes() "
        "WHERE table_name='observations' AND index_name=?",
        [_ART_INDEX],
    ).fetchone()
    if confirmed is None or "series_id" not in confirmed[0] or confirmed[1]:
        raise CIIngestError("Required observation ART index is missing or incompatible")
    count = conn.execute(
        """SELECT COUNT(*) FROM observations o JOIN series_catalog c
        USING (series_id) WHERE c.program_code='ci'"""
    ).fetchone()
    assert count is not None
    return int(count[0])


def ingest_ci(conn: DuckDBPyConnection, manifest_path: str | Path) -> CIIngestReport:
    """Atomically import pinned ECI files into a BUILDING CI snapshot.

    A CI snapshot can coexist with PC and CU in the same schema. Repeated
    imports, bad checksums, unknown classifications, conflicting revisions and
    malformed periods fail closed; successful ingestion does not publish.
    """
    selection: CIInputManifest = load_ci_manifest(manifest_path)
    verified: list[tuple[CISourceFile, Path, int]] = []
    for source in selection.selected():
        path = selection.resolve(source)
        verified.append((source, path, verify_ci_source(path, source)))

    identity = read_snapshot_info(conn)
    if (
        "ci" not in identity.programs
        or identity.lifecycle_state is not SnapshotState.BUILDING
        or identity.validation_status is not ValidationStatus.NOT_RUN
    ):
        raise CIIngestError("CI ingestion requires a BUILDING ci snapshot")
    existing = conn.execute(
        """SELECT
          (SELECT COUNT(*) FROM source_files WHERE program_code='ci') +
          (SELECT COUNT(*) FROM series_catalog WHERE program_code='ci') +
          (SELECT COUNT(*) FROM ci_dimension) + (SELECT COUNT(*) FROM ci_series)"""
    ).fetchone()
    if existing is None or existing[0]:
        raise CIIngestError("This snapshot already contains CI data")

    files: dict[str, Path] = {
        source.role: path
        for source, path, _ in verified
        if source.role not in CI_DATA_ROLES
    }
    dimensions = _read_dimensions(files)
    series, excluded = _read_series(files["series_metadata"], dimensions)
    last_id = conn.execute(
        "SELECT COALESCE(MAX(source_file_id), 0) FROM source_files"
    ).fetchone()
    assert last_id is not None
    base_id = int(last_id[0])

    conn.execute("BEGIN TRANSACTION")
    try:
        _insert_metadata(conn, dimensions, series)
        conn.execute(
            """CREATE TEMP TABLE _ci_raw (
                source_file_id BIGINT, series_id VARCHAR, year_text VARCHAR,
                period VARCHAR, value_text VARCHAR, footnote_codes VARCHAR
            )"""
        )
        for offset, (source, path, size) in enumerate(verified, start=1):
            source_id = base_id + offset
            write_source_file(
                conn,
                SourceFileReceipt(
                    source_file_id=source_id,
                    program_code="ci",
                    filename=source.path,
                    sha256=source.sha256,
                    size_bytes=size,
                    selection_role=source.role,
                    source_url=source.source_url,
                    etag=source.etag,
                    last_modified=source.last_modified,
                ),
            )
            if source.role in CI_DATA_ROLES:
                conn.execute(_STAGE_FROM_FILE, [source_id, str(path)])
        rows, skipped, missing, duplicates = _validate_stage(conn, excluded)
        inserted = _insert_observations(conn)
        if rows != skipped + missing + duplicates + inserted:
            raise CIIngestError("CI staging counts failed reconciliation")
        if not inserted:
            raise CIIngestError("CI data files hold no index observations")
        for source, path, _ in verified:
            verify_ci_source(path, source)
        conn.execute("DROP TABLE _ci_typed")
        conn.execute("DROP TABLE _ci_excluded")
        conn.execute("DROP TABLE _ci_raw")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return CIIngestReport(
        snapshot_id=identity.snapshot_id,
        source_files=len(verified),
        dimension_codes=sum(len(codes) for codes in dimensions.values()),
        series=len(series),
        excluded_series=len(excluded),
        rows_read=rows,
        excluded_rows=skipped,
        missing_rows=missing,
        identical_duplicates=duplicates,
        observations=inserted,
        art_index=_ART_INDEX,
    )
