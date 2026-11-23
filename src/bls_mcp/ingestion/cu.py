"""Offline CPI-U (CU) classification and observation ingestion into DuckDB.

Loads explicitly verified BLS ``cu.*`` files into a BUILDING snapshot. Python
parses the comparatively small metadata files; DuckDB streams large ``cu.data``
partitions into an on-disk staging table. No network or MCP operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bls_mcp.ingestion.cu_manifest import (
    CUInputManifest,
    CUSourceFile,
    load_cu_manifest,
    verify_cu_source,
)
from bls_mcp.storage.models import SnapshotState, SourceFileReceipt, ValidationStatus
from bls_mcp.storage.snapshots import read_snapshot_info, write_source_file

if TYPE_CHECKING:
    from duckdb import DuckDBPyConnection


class CUIngestError(ValueError):
    """A CU classification, observation or cross-file overlap is invalid."""


@dataclass(frozen=True, slots=True)
class CUIngestReport:
    snapshot_id: str
    source_files: int
    areas: int
    items: int
    series: int
    rows_read: int
    missing_rows: int
    identical_duplicates: int
    observations: int
    art_index: str


@dataclass(frozen=True, slots=True)
class _CUSeries:
    series_id: str
    area_code: str
    item_code: str
    seasonal: str
    periodicity: str
    base_code: str
    base_period: str
    title: str
    begin_year: int
    begin_period: str
    end_year: int
    end_period: str


_ART_INDEX = "observations_series_id_art"
_MONTHLY = {f"M{i:02d}" for i in range(1, 14)}
_SEMIANNUAL = {"S01", "S02", "S03"}

_STAGE_FROM_FILE = """
    INSERT INTO _cu_raw
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
    """Strict CU metadata TSV with optional empty trailing BLS tab fields."""
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise CUIngestError(f"Cannot read CU metadata: {path.name}") from exc
    if not lines:
        raise CUIngestError(f"Empty CU metadata: {path.name}")
    header = [part.strip() for part in lines[0].split("\t")]
    while len(header) > len(names) and not header[-1]:
        header.pop()
    if tuple(header) != names:
        raise CUIngestError(f"Unexpected CU metadata header: {path.name}")
    records: list[tuple[str, ...]] = []
    for lineno, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        fields = [part.strip() for part in line.split("\t")]
        while len(fields) > len(names) and not fields[-1]:
            fields.pop()
        if len(fields) != len(names):
            raise CUIngestError(f"{path.name}:{lineno}: incorrect column count")
        records.append(tuple(fields))
    if not records:
        raise CUIngestError(f"CU metadata has no records: {path.name}")
    return records


def _int(value: str, label: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise CUIngestError(f"CU {label} is not an integer: {value!r}") from exc
    if parsed < 0 or parsed > 32767:
        raise CUIngestError(f"CU {label} out of range: {value!r}")
    return parsed


def _read_classifications(
    areas_path: Path, items_path: Path, series_path: Path
) -> tuple[
    dict[str, tuple[str, int, bool, int]],
    dict[str, tuple[str, int, bool, int]],
    list[_CUSeries],
]:
    areas: dict[str, tuple[str, int, bool, int]] = {}
    for code, name, level, selectable, order in _read_rows(
        areas_path,
        ("area_code", "area_name", "display_level", "selectable", "sort_sequence"),
    ):
        if not code or not name or code in areas:
            raise CUIngestError(f"Missing or duplicate CU area code/name: {code!r}")
        if selectable not in ("T", "F"):
            raise CUIngestError(
                f"Invalid CU area selectable for {code}: {selectable!r}"
            )
        areas[code] = (
            name,
            _int(level, "area display_level"),
            selectable == "T",
            _int(order, "area sort_sequence"),
        )

    items: dict[str, tuple[str, int, bool, int]] = {}
    for code, name, level, selectable, order in _read_rows(
        items_path,
        ("item_code", "item_name", "display_level", "selectable", "sort_sequence"),
    ):
        if not code or not name or code in items:
            raise CUIngestError(f"Missing or duplicate CU item code/name: {code!r}")
        if selectable not in ("T", "F"):
            raise CUIngestError(f"Invalid CU selectable for {code}: {selectable!r}")
        items[code] = (
            name,
            _int(level, "item display_level"),
            selectable == "T",
            _int(order, "item sort_sequence"),
        )

    rows = _read_rows(
        series_path,
        (
            "series_id",
            "area_code",
            "item_code",
            "seasonal",
            "periodicity_code",
            "base_code",
            "base_period",
            "series_title",
            "footnote_codes",
            "begin_year",
            "begin_period",
            "end_year",
            "end_period",
        ),
    )
    series: list[_CUSeries] = []
    seen: set[str] = set()
    for (
        series_id,
        area,
        item,
        seasonal,
        periodicity,
        base_code,
        base_period,
        title,
        _footnotes,
        first_year,
        first_period,
        last_year,
        last_period,
    ) in rows:
        if not series_id or series_id in seen or not title:
            raise CUIngestError(f"Missing or duplicate CU series/title: {series_id!r}")
        seen.add(series_id)
        if area not in areas or item not in items:
            raise CUIngestError(f"Unknown CU area/item for {series_id}: {area}/{item}")
        if seasonal not in ("S", "U") or periodicity not in ("R", "S"):
            raise CUIngestError(f"Invalid CU seasonal/periodicity for {series_id}")
        if base_code not in ("S", "A") or not base_period:
            raise CUIngestError(f"Invalid CU reference base for {series_id}")
        # BLS's item_code INCLUDES the base-code character at position nine.
        # For example, CUUR0000SA0 -> base S and item SA0, not A0.
        if (
            not series_id.startswith("CU")
            or len(series_id) < 10
            or series_id[2] != seasonal
            or series_id[3] != periodicity
            or series_id[4:8] != area
            or series_id[8] != base_code
            or series_id[8:] != item
        ):
            raise CUIngestError(
                f"CU series identifier contradicts metadata: {series_id}"
            )
        begin = _int(first_year, "begin_year")
        end = _int(last_year, "end_year")
        valid_periods = _MONTHLY if periodicity == "R" else _SEMIANNUAL
        if (
            begin < 1
            or end < 1
            or first_period not in valid_periods
            or last_period not in valid_periods
            or (begin, first_period) > (end, last_period)
        ):
            raise CUIngestError(f"Invalid CU series date range: {series_id}")
        series.append(
            _CUSeries(
                series_id,
                area,
                item,
                seasonal,
                periodicity,
                base_code,
                base_period,
                title,
                begin,
                first_period,
                end,
                last_period,
            )
        )
    return areas, items, series


def _insert_metadata(
    conn: DuckDBPyConnection,
    areas: dict[str, tuple[str, int, bool, int]],
    items: dict[str, tuple[str, int, bool, int]],
    series: list[_CUSeries],
) -> None:
    conn.executemany(
        "INSERT INTO cu_area VALUES (?, ?, ?, ?, ?)",
        [(code, *attrs) for code, attrs in areas.items()],
    )
    conn.executemany(
        "INSERT INTO cu_item VALUES (?, ?, ?, ?, ?)",
        [(code, *attrs) for code, attrs in items.items()],
    )
    # Monthly and semiannual families have different period alphabets; active
    # is judged against the latest reported endpoint within each family.
    latest_by_frequency = {
        code: max((s.end_year, s.end_period) for s in series if s.periodicity == code)
        for code in {s.periodicity for s in series}
    }
    conn.executemany(
        """INSERT INTO series_catalog (
            series_id, program_code, title, seasonal_adjustment,
            first_year, first_period, last_year, last_period,
            units, original_reference_base, active
        ) VALUES (?, 'cu', ?, ?, ?, ?, ?, ?, 'index', ?, ?)""",
        [
            (
                s.series_id,
                s.title,
                s.seasonal == "S",
                s.begin_year,
                s.begin_period,
                s.end_year,
                s.end_period,
                s.base_period,
                (s.end_year, s.end_period) == latest_by_frequency[s.periodicity],
            )
            for s in series
        ],
    )
    conn.executemany(
        """INSERT INTO cu_series (
            series_id, area_code, item_code, seasonal_code,
            periodicity_code, base_code, base_period
        ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                s.series_id,
                s.area_code,
                s.item_code,
                s.seasonal,
                s.periodicity,
                s.base_code,
                s.base_period,
            )
            for s in series
        ],
    )


def _validate_stage(conn: DuckDBPyConnection) -> tuple[int, int, int]:
    bad = conn.execute(
        """SELECT source_file_id, series_id, year_text, period, value_text
        FROM _cu_raw WHERE
            series_id IS NULL OR series_id = ''
            OR TRY_CAST(year_text AS SMALLINT) IS NULL
            OR TRY_CAST(year_text AS SMALLINT) < 1
            OR period IS NULL
            OR NOT regexp_full_match(period, 'M(0[1-9]|1[0-3])|S0[1-3]')
            OR (
                COALESCE(value_text, '') NOT IN ('', '-')
                AND (TRY_CAST(value_text AS DOUBLE) IS NULL
                     OR NOT isfinite(TRY_CAST(value_text AS DOUBLE)))
            )
        LIMIT 1"""
    ).fetchone()
    if bad is not None:
        raise CUIngestError(f"Malformed CU observation: {bad}")
    unknown = conn.execute(
        """SELECT r.source_file_id, r.series_id FROM _cu_raw r
        LEFT JOIN series_catalog c ON c.series_id=r.series_id
                                 AND c.program_code='cu'
        WHERE c.series_id IS NULL LIMIT 1"""
    ).fetchone()
    if unknown is not None:
        raise CUIngestError(f"Observation refers to unknown CU series: {unknown}")
    wrong_period = conn.execute(
        """SELECT r.series_id, r.period, s.periodicity_code FROM _cu_raw r
        JOIN cu_series s ON s.series_id=r.series_id
        WHERE (s.periodicity_code='R' AND r.period NOT LIKE 'M%')
           OR (s.periodicity_code='S' AND r.period NOT LIKE 'S%')
        LIMIT 1"""
    ).fetchone()
    if wrong_period is not None:
        raise CUIngestError(f"CU periodicity mismatch: {wrong_period}")

    counts = conn.execute(
        """SELECT COUNT(*), COUNT(*) FILTER (
            WHERE COALESCE(value_text, '') IN ('', '-')
        ) FROM _cu_raw"""
    ).fetchone()
    assert counts is not None
    raw, missing = int(counts[0]), int(counts[1])
    conn.execute(
        """CREATE TEMP TABLE _cu_typed AS
        SELECT source_file_id, series_id, CAST(year_text AS SMALLINT) AS year,
               period, CAST(value_text AS DOUBLE) AS value, footnote_codes
        FROM _cu_raw WHERE COALESCE(value_text, '') NOT IN ('', '-')"""
    )
    conflict = conn.execute(
        """SELECT series_id, year, period FROM _cu_typed
        GROUP BY series_id, year, period
        HAVING MIN(value) <> MAX(value) OR COUNT(DISTINCT footnote_codes) > 1
        LIMIT 1"""
    ).fetchone()
    if conflict is not None:
        raise CUIngestError(
            f"Conflicting CU observations across partitions: {conflict}"
        )
    duplicate = conn.execute(
        """SELECT COALESCE(SUM(c - 1), 0) FROM
        (SELECT COUNT(*) AS c FROM _cu_typed
         GROUP BY series_id, year, period HAVING COUNT(*) > 1)"""
    ).fetchone()
    assert duplicate is not None
    return raw, missing, int(duplicate[0])


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
            ) AS chosen FROM _cu_typed
        ) WHERE chosen=1
        ORDER BY series_id, year, period"""
    )
    # M3 creates this ART on PC loads. A CU-only build creates the same ART
    # after bulk insertion; mixed builds preserve the existing index.
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
        raise CUIngestError("Required observation ART index is missing or incompatible")
    count = conn.execute(
        """SELECT COUNT(*) FROM observations o JOIN series_catalog c
        USING (series_id) WHERE c.program_code='cu'"""
    ).fetchone()
    assert count is not None
    return int(count[0])


def ingest_cu(conn: DuckDBPyConnection, manifest_path: str | Path) -> CUIngestReport:
    """Atomically import pinned CPI-U files into a BUILDING CU snapshot.

    A CU snapshot can coexist with PC in the same schema. Repeated imports,
    bad checksums, unknown classifications, revisions and malformed periods
    fail closed; successful ingestion does not publish the snapshot.
    """
    selection: CUInputManifest = load_cu_manifest(manifest_path)
    verified: list[tuple[CUSourceFile, Path, int]] = []
    for source in selection.selected():
        path = selection.resolve(source)
        verified.append((source, path, verify_cu_source(path, source)))

    identity = read_snapshot_info(conn)
    if (
        "cu" not in identity.programs
        or identity.lifecycle_state is not SnapshotState.BUILDING
        or identity.validation_status is not ValidationStatus.NOT_RUN
    ):
        raise CUIngestError("CU ingestion requires a BUILDING cu snapshot")
    existing = conn.execute(
        """SELECT
          (SELECT COUNT(*) FROM source_files WHERE program_code='cu') +
          (SELECT COUNT(*) FROM series_catalog WHERE program_code='cu') +
          (SELECT COUNT(*) FROM cu_area) + (SELECT COUNT(*) FROM cu_item) +
          (SELECT COUNT(*) FROM cu_series)"""
    ).fetchone()
    if existing is None or existing[0]:
        raise CUIngestError("This snapshot already contains CU data")

    files = {
        source.role: path
        for source, path, _ in verified
        if source.role not in ("historical", "current")
    }
    areas, items, series = _read_classifications(
        files["area_mapping"], files["item_mapping"], files["series_metadata"]
    )
    last_id = conn.execute(
        "SELECT COALESCE(MAX(source_file_id), 0) FROM source_files"
    ).fetchone()
    assert last_id is not None
    base_id = int(last_id[0])

    conn.execute("BEGIN TRANSACTION")
    try:
        _insert_metadata(conn, areas, items, series)
        conn.execute(
            """CREATE TEMP TABLE _cu_raw (
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
                    program_code="cu",
                    filename=source.path,
                    sha256=source.sha256,
                    size_bytes=size,
                    selection_role=source.role,
                    source_url=source.source_url,
                    etag=source.etag,
                    last_modified=source.last_modified,
                ),
            )
            if source.role in ("historical", "current"):
                conn.execute(_STAGE_FROM_FILE, [source_id, str(path)])
        rows, missing, duplicates = _validate_stage(conn)
        inserted = _insert_observations(conn)
        if rows != missing + duplicates + inserted:
            raise CUIngestError("CU staging counts failed reconciliation")
        for source, path, _ in verified:
            verify_cu_source(path, source)
        conn.execute("DROP TABLE _cu_typed")
        conn.execute("DROP TABLE _cu_raw")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return CUIngestReport(
        snapshot_id=identity.snapshot_id,
        source_files=len(verified),
        areas=len(areas),
        items=len(items),
        series=len(series),
        rows_read=rows,
        missing_rows=missing,
        identical_duplicates=duplicates,
        observations=inserted,
        art_index=_ART_INDEX,
    )
