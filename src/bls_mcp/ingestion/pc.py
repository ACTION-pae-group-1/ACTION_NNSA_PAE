"""Bulk PC (PPI industry) ingestion into an unpublished DuckDB candidate.

A caller owns the offline builder connection and initializes the v1 schema and
snapshot identity. This loader never fetches, publishes, or updates a
live MCP server. Large observation partitions are staged directly by
DuckDB, not materialized as Python objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bls_mcp.data.flat_file import (
    FlatFileFormatError,
    ParsedSeries,
    parse_code_mapping,
    parse_series_file,
)
from bls_mcp.ingestion.manifest import (
    PCInputManifest,
    PCSourceFile,
    load_pc_manifest,
    verify_pc_source,
)
from bls_mcp.storage.models import SnapshotState, SourceFileReceipt, ValidationStatus
from bls_mcp.storage.snapshots import read_snapshot_info, write_source_file

if TYPE_CHECKING:
    from duckdb import DuckDBPyConnection


class PCIngestError(ValueError):
    """A PC input has invalid classifications, observations, or overlap."""


@dataclass(frozen=True, slots=True)
class PCIngestReport:
    """Reconciled counts for a PC build; a successful result is not publication."""

    snapshot_id: str
    source_files: int
    industries: int
    products: int
    series: int
    rows_read: int
    missing_rows: int
    identical_duplicates: int
    observations: int
    art_index: str


_ART_INDEX = "observations_series_id_art"

# Keep original data text in an on-disk DuckDB temporary table. Explicit CSV
# columns bypass padded BLS header names and disable numeric auto-detection.
_STAGE_FROM_FILE = """
    INSERT INTO _pc_raw
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


def _read_mapping(path: Path, *, columns: int) -> dict[str, str]:
    """Require complete, unique PC lookup keys (no silent setdefault)."""
    try:
        mapping, count = parse_code_mapping(
            path.read_text(encoding="utf-8-sig"),
            file_label=str(path),
            key_columns=columns,
        )
    except (OSError, UnicodeDecodeError, FlatFileFormatError) as exc:
        raise PCIngestError(f"Invalid PC mapping {path.name}: {exc}") from exc
    if not mapping or len(mapping) != count:
        raise PCIngestError(f"PC mapping {path.name} has empty or duplicate keys/names")
    return mapping


def _read_series(
    path: Path, industries: dict[str, str], products: dict[str, str]
) -> list[ParsedSeries]:
    try:
        series, _ = parse_series_file(
            path.read_text(encoding="utf-8-sig"), "pc", file_label=str(path)
        )
    except (OSError, UnicodeDecodeError, FlatFileFormatError) as exc:
        raise PCIngestError(f"Invalid PC series metadata: {exc}") from exc
    if not series or len({s.series_id for s in series}) != len(series):
        raise PCIngestError("PC series metadata is empty or duplicates series IDs")
    valid_periods = {f"M{i:02d}" for i in range(1, 14)}
    for record in series:
        if not record.series_id or not record.title:
            raise PCIngestError("PC series must have a nonempty ID and title")
        if record.industry_code not in industries:
            raise PCIngestError(
                f"Unknown industry {record.industry_code} for {record.series_id}"
            )
        if f"{record.industry_code}\t{record.product_code}" not in products:
            raise PCIngestError(
                f"Unknown industry/product for {record.series_id}: "
                f"{record.industry_code}/{record.product_code}"
            )
        if record.seasonal_code not in ("U", "S"):
            raise PCIngestError(f"Unknown seasonal code for {record.series_id}")
        for period in (record.begin_period, record.end_period):
            if period not in valid_periods:
                raise PCIngestError(
                    f"Invalid PC metadata period {period!r} for {record.series_id}"
                )
        if (record.begin_year, record.begin_period) > (
            record.end_year,
            record.end_period,
        ):
            raise PCIngestError(f"PC series has inverted dates: {record.series_id}")
    return series


def _insert_metadata(
    conn: DuckDBPyConnection,
    industries: dict[str, str],
    products: dict[str, str],
    series: list[ParsedSeries],
) -> None:
    conn.executemany(
        "INSERT INTO pc_industry (industry_code, industry_name) VALUES (?, ?)",
        list(industries.items()),
    )
    conn.executemany(
        """INSERT INTO pc_product (
            industry_code, product_code, product_name
        ) VALUES (?, ?, ?)""",
        [(*key.split("\t", 1), title) for key, title in products.items()],
    )
    latest = max((s.end_year, s.end_period) for s in series)
    conn.executemany(
        """INSERT INTO series_catalog (
            series_id, program_code, title, seasonal_adjustment,
            first_year, first_period, last_year, last_period,
            units, original_reference_base, active
        ) VALUES (?, 'pc', ?, ?, ?, ?, ?, ?, 'index', ?, ?)""",
        [
            (
                s.series_id,
                s.title,
                s.seasonal_code == "S",
                s.begin_year,
                s.begin_period,
                s.end_year,
                s.end_period,
                s.base_or_bench_date or None,
                (s.end_year, s.end_period) == latest,
            )
            for s in series
        ],
    )
    conn.executemany(
        """INSERT INTO pc_series (
            series_id, industry_code, product_code, seasonal_code, base_date
        ) VALUES (?, ?, ?, ?, ?)""",
        [
            (
                s.series_id,
                s.industry_code,
                s.product_code or None,
                s.seasonal_code,
                s.base_or_bench_date or None,
            )
            for s in series
        ],
    )


def _validate_stage(conn: DuckDBPyConnection) -> tuple[int, int, int]:
    """Reject bad rows and conflicts; return raw, missing and duplicate counts."""
    bad = conn.execute(
        """SELECT source_file_id, series_id, year_text, period, value_text
        FROM _pc_raw WHERE
            series_id IS NULL OR series_id = ''
            OR TRY_CAST(year_text AS SMALLINT) IS NULL
            OR TRY_CAST(year_text AS SMALLINT) < 1
            OR period IS NULL
            OR NOT regexp_full_match(period, 'M(0[1-9]|1[0-3])')
            OR (
                COALESCE(value_text, '') NOT IN ('', '-')
                AND (TRY_CAST(value_text AS DOUBLE) IS NULL
                     OR NOT isfinite(TRY_CAST(value_text AS DOUBLE)))
            )
        LIMIT 1"""
    ).fetchone()
    if bad is not None:
        raise PCIngestError(
            f"Malformed PC observation (source, id, year, period, value): {bad}"
        )

    unknown = conn.execute(
        """SELECT raw.source_file_id, raw.series_id
        FROM _pc_raw raw LEFT JOIN series_catalog catalog
          ON catalog.series_id = raw.series_id AND catalog.program_code = 'pc'
        WHERE catalog.series_id IS NULL LIMIT 1"""
    ).fetchone()
    if unknown is not None:
        raise PCIngestError(f"Observation refers to unknown PC series: {unknown}")

    counts = conn.execute(
        """SELECT COUNT(*), COUNT(*) FILTER (
             WHERE COALESCE(value_text, '') IN ('', '-')
        ) FROM _pc_raw"""
    ).fetchone()
    assert counts is not None
    raw_rows, missing_rows = counts

    conn.execute(
        """CREATE TEMP TABLE _pc_typed AS
        SELECT source_file_id, series_id,
               CAST(year_text AS SMALLINT) AS year, period,
               CAST(value_text AS DOUBLE) AS value,
               footnote_codes
        FROM _pc_raw WHERE COALESCE(value_text, '') NOT IN ('', '-')"""
    )
    conflict = conn.execute(
        """SELECT series_id, year, period, COUNT(*)
        FROM _pc_typed GROUP BY series_id, year, period
        HAVING MIN(value) <> MAX(value)
            OR COUNT(DISTINCT footnote_codes) > 1
        LIMIT 1"""
    ).fetchone()
    if conflict is not None:
        raise PCIngestError(
            f"Conflicting PC observations across partitions: {conflict}"
        )
    duplicated = conn.execute(
        """SELECT COALESCE(SUM(c - 1), 0)
        FROM (SELECT COUNT(*) AS c FROM _pc_typed
              GROUP BY series_id, year, period HAVING COUNT(*) > 1)"""
    ).fetchone()
    assert duplicated is not None
    return int(raw_rows), int(missing_rows), int(duplicated[0])


def _store_observations_and_index(conn: DuckDBPyConnection) -> int:
    # Historical partitions have lower source IDs than current. Identical
    # duplicates retain their first verified source receipt, deterministically.
    conn.execute(
        """INSERT INTO observations (
            series_id, year, period, value, footnote_codes, source_file_id
        )
        SELECT series_id, year, period, value,
               NULLIF(footnote_codes, ''), source_file_id
        FROM (
            SELECT *, ROW_NUMBER() OVER (
                PARTITION BY series_id, year, period
                ORDER BY source_file_id
            ) AS chosen FROM _pc_typed
        ) WHERE chosen = 1
        ORDER BY series_id, year, period"""
    )
    # Explicit CREATE INDEX creates an ART in DuckDB. Build only AFTER the
    # sorted bulk insert to avoid per-row index maintenance during loading.
    index = conn.execute(
        """SELECT 1 FROM duckdb_indexes()
        WHERE table_name = 'observations' AND index_name = ?""",
        [_ART_INDEX],
    ).fetchone()
    if index is None:
        conn.execute(f"CREATE INDEX {_ART_INDEX} ON observations (series_id)")
    confirmed = conn.execute(
        """SELECT sql FROM duckdb_indexes()
        WHERE table_name = 'observations' AND index_name = ?""",
        [_ART_INDEX],
    ).fetchone()
    if confirmed is None or "series_id" not in confirmed[0]:
        raise PCIngestError("DuckDB observation ART index was not created")
    count = conn.execute(
        """SELECT COUNT(*) FROM observations o
        JOIN series_catalog c USING (series_id)
        WHERE c.program_code = 'pc'"""
    ).fetchone()
    assert count is not None
    return int(count[0])


def ingest_pc(conn: DuckDBPyConnection, manifest_path: str | Path) -> PCIngestReport:
    """Atomically stage and import explicitly selected PC bulk files.

    The connection must be a fresh, writable, initialized offline snapshot
    with BUILDING state and program ``pc``. Identical current/historical
    overlaps are counted, conflicting keys (including footnotes) rejected.
    An explicit single-column observation ART index is built after loading.
    The resulting snapshot remains BUILDING, not READY or PUBLISHED.
    """
    selection: PCInputManifest = load_pc_manifest(manifest_path)
    # Hash/size/header verification precedes any write transaction.
    verified: list[tuple[PCSourceFile, Path, int]] = []
    for source in selection.selected():
        path = selection.resolve(source)
        verified.append((source, path, verify_pc_source(path, source)))

    identity = read_snapshot_info(conn)
    if (
        "pc" not in identity.programs
        or identity.lifecycle_state is not SnapshotState.BUILDING
        or identity.validation_status is not ValidationStatus.NOT_RUN
    ):
        raise PCIngestError("PC ingestion requires a BUILDING pc snapshot")
    already_loaded = conn.execute(
        """SELECT
          (SELECT COUNT(*) FROM source_files WHERE program_code = 'pc') +
          (SELECT COUNT(*) FROM series_catalog WHERE program_code = 'pc') +
          (SELECT COUNT(*) FROM pc_industry) + (SELECT COUNT(*) FROM pc_product)
        """
    ).fetchone()
    if already_loaded is None or already_loaded[0]:
        raise PCIngestError("This snapshot already contains PC data")

    sources = {source.role: path for source, path, _ in verified}
    industries = _read_mapping(sources["industry_mapping"], columns=1)
    products = _read_mapping(sources["product_mapping"], columns=2)
    series = _read_series(sources["series_metadata"], industries, products)
    latest_source = conn.execute(
        "SELECT COALESCE(MAX(source_file_id), 0) FROM source_files"
    ).fetchone()
    assert latest_source is not None
    next_source_id = int(latest_source[0])

    conn.execute("BEGIN TRANSACTION")
    try:
        _insert_metadata(conn, industries, products, series)
        conn.execute(
            """CREATE TEMP TABLE _pc_raw (
                source_file_id BIGINT, series_id VARCHAR, year_text VARCHAR,
                period VARCHAR, value_text VARCHAR, footnote_codes VARCHAR
            )"""
        )
        for offset, (source, path, size) in enumerate(verified, start=1):
            source_file_id = next_source_id + offset
            write_source_file(
                conn,
                SourceFileReceipt(
                    source_file_id=source_file_id,
                    program_code="pc",
                    filename=source.path,
                    sha256=source.sha256,
                    size_bytes=size,
                    selection_role=source.role,
                    source_url=source.source_url,
                    etag=source.etag,
                    last_modified=source.last_modified,
                ),
            )
            if source.role in ("historical", "current", "all_data"):
                conn.execute(_STAGE_FROM_FILE, [source_file_id, str(path)])

        rows_read, missing_rows, duplicates = _validate_stage(conn)
        observations = _store_observations_and_index(conn)
        if rows_read != observations + missing_rows + duplicates:
            raise PCIngestError("PC staging counts failed reconciliation")
        for source, path, _ in verified:
            # Defend against the source changing while DuckDB was reading it.
            verify_pc_source(path, source)
        conn.execute("DROP TABLE _pc_typed")
        conn.execute("DROP TABLE _pc_raw")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    return PCIngestReport(
        snapshot_id=identity.snapshot_id,
        source_files=len(verified),
        industries=len(industries),
        products=len(products),
        series=len(series),
        rows_read=rows_read,
        missing_rows=missing_rows,
        identical_duplicates=duplicates,
        observations=observations,
        art_index=_ART_INDEX,
    )
