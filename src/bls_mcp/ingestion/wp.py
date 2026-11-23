"""Offline WP ingestion. Only explicitly pinned observations are loaded."""

from __future__ import annotations

from dataclasses import dataclass

from bls_mcp.data.flat_file import parse_series_file
from bls_mcp.ingestion.wp_manifest import load_wp_manifest, verify_wp_source
from bls_mcp.storage.models import SnapshotState, SourceFileReceipt, ValidationStatus
from bls_mcp.storage.snapshots import read_snapshot_info, write_source_file


@dataclass(frozen=True)
class WPIngestReport:
    snapshot_id: str
    source_files: int
    series: int
    observations: int
    missing_rows: int


def ingest_wp(conn, manifest_path):
    manifest = load_wp_manifest(manifest_path)
    verified = [
        (s, manifest.resolve(s), verify_wp_source(manifest.resolve(s), s))
        for s in manifest.selected()
    ]
    info = read_snapshot_info(conn)
    if (
        "wp" not in info.programs
        or info.lifecycle_state is not SnapshotState.BUILDING
        or info.validation_status is not ValidationStatus.NOT_RUN
    ):
        raise ValueError("WP requires BUILDING snapshot")

    if conn.execute(
        "SELECT COUNT(*) FROM series_catalog WHERE program_code='wp'"
    ).fetchone()[0]:
        raise ValueError("WP already loaded")

    sources = {s.role: path for s, path, _ in verified}

    def rows(path):
        with path.open(encoding="utf-8-sig") as f:
            f.readline()
            return [
                tuple(c.strip() for c in line.rstrip("\r\n").split("\t"))
                for line in f
                if line.strip()
            ]

    groups = rows(sources["group_mapping"])
    items = rows(sources["item_mapping"])
    series, _ = parse_series_file(
        sources["series_metadata"].read_text(encoding="utf-8-sig"), "wp"
    )

    group_codes = {r[0] for r in groups}
    item_codes = {(r[0], r[1]) for r in items}

    if (
        len(group_codes) != len(groups)
        or len(item_codes) != len(items)
        or len({s.series_id for s in series}) != len(series)
    ):
        raise ValueError("Duplicate WP classification or series")

    for s in series:
        if (
            s.industry_code not in group_codes
            or (s.industry_code, s.product_code) not in item_codes
        ):
            raise ValueError(f"Unmapped WP classification: {s.series_id}")

        if s.seasonal_code not in ("S", "U") or (
            s.begin_year,
            s.begin_period,
        ) > (
            s.end_year,
            s.end_period,
        ):
            raise ValueError(f"Invalid WP series metadata: {s.series_id}")

    latest = max((s.end_year, s.end_period) for s in series)

    start = conn.execute(
        "SELECT COALESCE(MAX(source_file_id),0) FROM source_files"
    ).fetchone()[0]

    conn.execute("BEGIN TRANSACTION")
    try:
        conn.executemany(
            "INSERT INTO wp_group VALUES (?,?)",
            groups,
        )
        conn.executemany(
            "INSERT INTO wp_item VALUES (?,?,?)",
            items,
        )
        conn.executemany(
            """
            INSERT INTO series_catalog (
                series_id,
                program_code,
                title,
                seasonal_adjustment,
                first_year,
                first_period,
                last_year,
                last_period,
                units,
                original_reference_base,
                active
            )
            VALUES (?,'wp',?,?,?,?,?,?,'index',?,?)
            """,
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
            "INSERT INTO wp_series VALUES (?,?,?,?,?)",
            [
                (
                    s.series_id,
                    s.industry_code,
                    s.product_code,
                    s.seasonal_code,
                    s.base_or_bench_date or None,
                )
                for s in series
            ],
        )

        conn.execute(
            """
            CREATE TEMP TABLE _wp_raw (
                source_file_id BIGINT,
                series_id VARCHAR,
                year_text VARCHAR,
                period VARCHAR,
                value_text VARCHAR,
                footnote_codes VARCHAR
            )
            """
        )

        for offset, (source, path, size) in enumerate(verified, 1):
            sid = start + offset
            write_source_file(
                conn,
                SourceFileReceipt(
                    source_file_id=sid,
                    program_code="wp",
                    filename=source.path,
                    sha256=source.sha256,
                    size_bytes=size,
                    selection_role=source.role,
                    source_url=source.source_url,
                ),
            )

            if source.role in ("historical", "current"):
                conn.execute(
                    """
                    INSERT INTO _wp_raw
                    SELECT
                        ?,
                        TRIM(series_id),
                        TRIM(year),
                        TRIM(period),
                        TRIM(value),
                        COALESCE(TRIM(footnote_codes), '')
                    FROM read_csv(
                        ?,
                        delim='\t',
                        header=true,
                        auto_detect=false,
                        columns={
                            'series_id':'VARCHAR',
                            'year':'VARCHAR',
                            'period':'VARCHAR',
                            'value':'VARCHAR',
                            'footnote_codes':'VARCHAR'
                        },
                        quote='',
                        escape='',
                        null_padding=false,
                        ignore_errors=false
                    )
                    """,
                    [sid, str(path)],
                )

        invalid = conn.execute(
            """
            SELECT COUNT(*)
            FROM _wp_raw r
            LEFT JOIN series_catalog c
                ON r.series_id = c.series_id
                AND c.program_code = 'wp'
            WHERE
                c.series_id IS NULL
                OR TRY_CAST(year_text AS SMALLINT) IS NULL
                OR TRY_CAST(year_text AS SMALLINT) < 1
                OR NOT regexp_full_match(
                    period,
                    'M(0[1-9]|1[0-3])'
                )
                OR (
                    COALESCE(value_text, '') NOT IN ('', '-')
                    AND (
                        TRY_CAST(value_text AS DOUBLE) IS NULL
                        OR NOT isfinite(
                            TRY_CAST(value_text AS DOUBLE)
                        )
                    )
                )
            """
        ).fetchone()[0]

        if invalid:
            raise ValueError(f"Invalid WP observations: {invalid}")

        conn.execute(
            """
            CREATE TEMP TABLE _wp_typed AS
            SELECT
                source_file_id,
                series_id,
                CAST(year_text AS SMALLINT) AS "year",
                period,
                TRY_CAST(value_text AS DOUBLE) AS "value",
                footnote_codes
            FROM _wp_raw
            WHERE COALESCE(value_text, '') NOT IN ('', '-')
            """
        )

        conflict = conn.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT
                    series_id,
                    year,
                    period
                FROM _wp_typed
                GROUP BY series_id, year, period
                HAVING
                    MIN(value) <> MAX(value)
                    OR COUNT(DISTINCT footnote_codes) > 1
            )
            """
        ).fetchone()[0]

        if conflict:
            raise ValueError(f"Conflicting WP observations: {conflict}")

        conn.execute(
            """
            INSERT INTO observations
            SELECT
                series_id,
                year,
                period,
                value,
                NULLIF(footnote_codes, ''),
                source_file_id
            FROM (
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        PARTITION BY series_id, year, period
                        ORDER BY source_file_id
                    ) AS n
                FROM _wp_typed
            )
            WHERE n = 1
            ORDER BY series_id, year, period
            """
        )

        if not conn.execute(
            """
            SELECT 1
            FROM duckdb_indexes()
            WHERE index_name = 'observations_series_id_art'
            """
        ).fetchone():
            conn.execute(
                """
                CREATE INDEX observations_series_id_art
                ON observations(series_id)
                """
            )

        count = conn.execute(
            """
            SELECT COUNT(*)
            FROM observations o
            JOIN series_catalog c USING(series_id)
            WHERE c.program_code = 'wp'
            """
        ).fetchone()[0]

        missing = conn.execute(
            """
            SELECT COUNT(*)
            FROM _wp_raw
            WHERE COALESCE(value_text, '') IN ('', '-')
            """
        ).fetchone()[0]

        for source, path, _ in verified:
            verify_wp_source(path, source)

        conn.execute("DROP TABLE _wp_typed")
        conn.execute("DROP TABLE _wp_raw")
        conn.execute("COMMIT")

    except Exception:
        conn.execute("ROLLBACK")
        raise

    return WPIngestReport(
        info.snapshot_id,
        len(verified),
        len(series),
        count,
        missing,
    )
