"""Native DuckDB tests for published, read-only series search and normalization."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import pytest

duckdb = pytest.importorskip("duckdb")

from bls_mcp.storage.connection import (  # noqa: E402
    SnapshotNotPublishedError,
    build_connection,
)
from bls_mcp.storage.models import SnapshotInfo, SourceFileReceipt  # noqa: E402
from bls_mcp.storage.query_models import (  # noqa: E402
    CUClassification,
    PCClassification,
    QueryStatus,
    SeriesSearchFilters,
)
from bls_mcp.storage.schema import initialize_schema  # noqa: E402
from bls_mcp.storage.snapshots import (  # noqa: E402
    SnapshotMetadataError,
    write_snapshot_info,
    write_source_file,
)
from bls_mcp.storage.store import BLSStore, QueryResultLimitError  # noqa: E402

PC_A = "PCU100000000000"
PC_B = "PCU200000000000"
PC_ZERO = "PCU300000000000"
PC_EMPTY = "PCU400000000000"
CU_A = "CUUR0000SA0"
CU_SEMI = "CUUS0000SA0"

SERIES = [
    (
        PC_A,
        "pc",
        "Shared index",
        None,
        False,
        2024,
        "M12",
        2025,
        "M13",
        "index",
        "202412",
        True,
    ),
    (
        PC_B,
        "pc",
        "Shared index",
        None,
        True,
        2024,
        "M11",
        2025,
        "M01",
        "index",
        "202411",
        False,
    ),
    (
        PC_ZERO,
        "pc",
        "Zero base",
        None,
        False,
        2024,
        "M12",
        2025,
        "M01",
        "index",
        "202412",
        True,
    ),
    (
        PC_EMPTY,
        "pc",
        "No output window",
        None,
        False,
        2024,
        "M12",
        2024,
        "M12",
        "index",
        "202412",
        False,
    ),
    (
        CU_A,
        "cu",
        "All items CPI-U",
        None,
        False,
        2024,
        "M12",
        2025,
        "M13",
        "index",
        "1982-84=100",
        True,
    ),
    (
        CU_SEMI,
        "cu",
        "All items CPI-U semiannual",
        None,
        False,
        2024,
        "S01",
        2025,
        "S03",
        "index",
        "1982-84=100",
        True,
    ),
]

OBS = [
    (PC_A, 2024, "M12", 200.0, None, 1),
    (PC_A, 2025, "M01", 220.0, "P", 1),
    (PC_A, 2025, "M12", 224.0, None, 1),
    (PC_A, 2025, "M13", 223.0, None, 1),
    (PC_B, 2024, "M11", 300.0, None, 1),
    (PC_B, 2025, "M01", 310.0, None, 1),
    (PC_ZERO, 2024, "M12", 0.0, None, 1),
    (PC_ZERO, 2025, "M01", 10.0, None, 1),
    (PC_EMPTY, 2024, "M12", 50.0, None, 1),
    (CU_A, 2024, "M12", 330.0, None, 2),
    (CU_A, 2025, "M01", 333.0, None, 2),
    (CU_A, 2025, "M13", 340.0, None, 2),
    (CU_SEMI, 2024, "S01", 140.0, None, 2),
    (CU_SEMI, 2025, "S01", 150.0, None, 2),
    (CU_SEMI, 2025, "S03", 154.0, None, 2),
]


def _builder(path: Path):
    """Initialize a test-only file. Tests simulate publication explicitly."""
    return build_connection(path, threads=1)


@pytest.fixture
def published_path(tmp_path: Path) -> Path:
    path = tmp_path / "published.duckdb"
    with _builder(path) as conn:
        initialize_schema(conn)
        write_snapshot_info(
            conn,
            SnapshotInfo("query_fixture_20261105", datetime.now(UTC), ("pc", "cu")),
        )
        for file_id, program in ((1, "pc"), (2, "cu")):
            write_source_file(
                conn,
                SourceFileReceipt(file_id, program, "fixture", "a" * 64, 1, "test"),
            )
        conn.execute("INSERT INTO pc_industry VALUES ('100', 'Manufacturing')")
        conn.execute("INSERT INTO pc_product VALUES ('100', 'ABC', 'Widgets')")
        conn.execute(
            "INSERT INTO cu_area VALUES ('0000', 'U.S. city average', 0, TRUE, 1)"
        )
        conn.execute("INSERT INTO cu_item VALUES ('SA0', 'All items', 0, TRUE, 1)")
        conn.executemany(
            "INSERT INTO series_catalog VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            SERIES,
        )
        conn.executemany(
            "INSERT INTO pc_series VALUES (?, '100', 'ABC', ?, '202412')",
            [
                (sid, "S" if sid == PC_B else "U")
                for sid in (PC_A, PC_B, PC_ZERO, PC_EMPTY)
            ],
        )
        conn.executemany(
            "INSERT INTO cu_series VALUES "
            "(?, '0000', 'SA0', 'U', ?, 'S', '1982-84=100')",
            [(CU_A, "R"), (CU_SEMI, "S")],
        )
        conn.executemany("INSERT INTO observations VALUES (?, ?, ?, ?, ?, ?)", OBS)
        conn.execute(
            "CREATE INDEX observations_series_id_art ON observations(series_id)"
        )
        # Simulation only: publication is implemented in Milestone 6.
        conn.execute(
            "UPDATE snapshot_info SET lifecycle_state='PUBLISHED', "
            "validation_status='PASSED'"
        )
    return path


def test_search_literal_text_classifications_and_pagination(published_path):
    store = BLSStore(published_path)
    page = store.search_series(SeriesSearchFilters(query="shared INDEX", limit=1))
    assert page.snapshot_id == "query_fixture_20261105"
    assert (page.total_matches, len(page.matches), page.offset) == (2, 1, 0)
    assert page.matches[0].series.series_id == PC_A
    next_page = store.search_series(
        SeriesSearchFilters(query="shared INDEX", limit=1, offset=1)
    )
    assert next_page.matches[0].series.series_id == PC_B
    assert store.search_series(SeriesSearchFilters(query="%_")).total_matches == 0
    assert (
        store.search_series(
            SeriesSearchFilters(query="ABC", programs=("pc",))
        ).total_matches
        == 4
    )
    assert (
        store.search_series(SeriesSearchFilters(query="' OR 1=1 --")).total_matches == 0
    )
    pc = store.search_series(
        SeriesSearchFilters(
            programs=("pc",),
            industry_code="100",
            product_code="ABC",
            active_only=True,
        )
    )
    assert {hit.series.series_id for hit in pc.matches} == {PC_A, PC_ZERO}
    assert all(isinstance(hit.classification, PCClassification) for hit in pc.matches)
    assert pc.matches[0].classification.industry_name == "Manufacturing"
    cu = store.search_series(
        SeriesSearchFilters(
            programs=("cu",),
            area_code="0000",
            item_code="SA0",
            periodicity_code="S",
        )
    )
    assert [hit.series.series_id for hit in cu.matches] == [CU_SEMI]
    assert isinstance(cu.matches[0].classification, CUClassification)
    assert cu.matches[0].classification.area_name == "U.S. city average"
    assert [
        hit.series.series_id
        for hit in store.search_series(
            SeriesSearchFilters(seasonal_adjustment=True)
        ).matches
    ] == [PC_B]


def test_search_hyphen_and_space_equivalence(published_path):
    store = BLSStore(published_path)
    # Existing catalog title uses "CPI-U"; both spellings should find it.
    hyphenated = store.search_series(SeriesSearchFilters(query="CPI-U"))
    spaced = store.search_series(SeriesSearchFilters(query="CPI U"))
    assert hyphenated.total_matches == spaced.total_matches == 2
    assert {h.series.series_id for h in spaced.matches} == {CU_A, CU_SEMI}
    assert (
        store.search_series(
            SeriesSearchFilters(query="not-a-real-series")
        ).total_matches
        == 0
    )


def test_multi_series_raw_values_order_and_statuses(published_path):
    result = BLSStore(published_path).get_observations(
        [CU_A, PC_A, PC_EMPTY, "unknown", CU_SEMI], start_year=2025, end_year=2025
    )
    assert result.snapshot_id == "query_fixture_20261105"
    assert [s.status for s in result.statuses] == [
        QueryStatus.SUCCESS,
        QueryStatus.SUCCESS,
        QueryStatus.NO_ROWS_IN_WINDOW,
        QueryStatus.UNKNOWN_SERIES,
        QueryStatus.SUCCESS,
    ]
    assert [(o.series_id, o.period) for o in result.observations] == [
        (CU_A, "M01"),
        (CU_A, "M13"),
        (CU_SEMI, "S01"),
        (CU_SEMI, "S03"),
        (PC_A, "M01"),
        (PC_A, "M12"),
        (PC_A, "M13"),
    ]
    assert result.observations[-3].footnote_codes == "P"
    assert result.observations[-3].value == 220.0
    assert {o.source_file_id for o in result.observations} == {1, 2}


def test_exact_base_outside_window_and_per_series_failures(published_path):
    result = BLSStore(published_path).normalize_series(
        [PC_A, PC_B, PC_ZERO, PC_EMPTY, "not-a-series", CU_A],
        base_year=2024,
        base_period="M12",
        start_year=2025,
        end_year=2025,
    )
    assert [out.status for out in result.statuses] == [
        QueryStatus.SUCCESS,
        QueryStatus.MISSING_BASE,
        QueryStatus.ZERO_BASE,
        QueryStatus.NO_ROWS_IN_WINDOW,
        QueryStatus.UNKNOWN_SERIES,
        QueryStatus.SUCCESS,
    ]
    assert [out.base_value for out in result.statuses] == [
        200.0,
        None,
        0.0,
        50.0,
        None,
        330.0,
    ]
    pc_rows = [r for r in result.observations if r.series_id == PC_A]
    assert [r.period for r in pc_rows] == ["M01", "M12", "M13"]
    assert [r.normalized_value for r in pc_rows] == pytest.approx([110.0, 112.0, 111.5])
    assert pc_rows[0].raw_value == 220.0
    assert pc_rows[0].base_value == 200.0
    assert pc_rows[0].footnote_codes == "P"
    assert [r.series_id for r in result.observations].count(PC_B) == 0
    assert result.statuses[0].observation_count == 3
    cu_rows = [r for r in result.observations if r.series_id == CU_A]
    assert [r.normalized_value for r in cu_rows] == pytest.approx(
        [100.9090909091, 103.0303030303]
    )


def test_semiannual_normalization_and_custom_target(published_path):
    result = BLSStore(published_path).normalize_series(
        [CU_SEMI],
        base_year=2024,
        base_period="S01",
        start_year=2025,
        target_base=1.0,
    )
    assert result.statuses[0].status is QueryStatus.SUCCESS
    assert [r.period for r in result.observations] == ["S01", "S03"]
    assert [r.normalized_value for r in result.observations] == pytest.approx(
        [150 / 140, 154 / 140]
    )


def test_requested_ids_cannot_inject_sql(published_path):
    malicious = "PCU9999' OR 1=1 --"
    result = BLSStore(published_path).get_observations(
        [PC_A, malicious], start_year=2025, end_year=2025
    )
    assert len(result.observations) == 3
    assert [status.status for status in result.statuses] == [
        QueryStatus.SUCCESS,
        QueryStatus.UNKNOWN_SERIES,
    ]


def test_duplicate_base_row_is_not_accepted(published_path):
    # The publication milestone must reject duplicates before reaching this
    # API; also fail closed if a malformed snapshot somehow slips through.
    with duckdb.connect(str(published_path)) as conn:
        conn.execute(
            "INSERT INTO observations VALUES (?, 2024, 'M12', 200.0, NULL, 1)",
            [PC_A],
        )
    with pytest.raises(SnapshotMetadataError, match="Multiple base"):
        BLSStore(published_path).normalize_series(
            [PC_A], base_year=2024, base_period="M12"
        )


def test_hard_output_budget_does_not_silently_truncate(published_path):
    store = BLSStore(published_path)
    with pytest.raises(QueryResultLimitError, match="max_rows=1"):
        store.get_observations([PC_A], max_rows=1)
    with pytest.raises(QueryResultLimitError, match="max_rows=1"):
        store.normalize_series([PC_A], base_year=2024, base_period="M12", max_rows=1)


def test_unpublished_and_failed_validation_are_not_queryable(tmp_path):
    path = tmp_path / "candidate.duckdb"
    with _builder(path) as conn:
        initialize_schema(conn)
        write_snapshot_info(conn, SnapshotInfo("not_ready", datetime.now(UTC), ("pc",)))
    with pytest.raises(SnapshotNotPublishedError):
        BLSStore(path).search_series()
    with duckdb.connect(str(path)) as conn:
        conn.execute("UPDATE snapshot_info SET lifecycle_state='PUBLISHED'")
    with pytest.raises(SnapshotMetadataError, match="PASSED"):
        BLSStore(path).get_observations([PC_A])
    with duckdb.connect(str(path)) as conn:
        conn.execute("UPDATE snapshot_info SET schema_version=1")
    with pytest.raises(SnapshotMetadataError, match="Unsupported"):
        BLSStore(path).search_series()
    nonexistent = tmp_path / "no" / "file.duckdb"
    with pytest.raises(FileNotFoundError):
        BLSStore(nonexistent).search_series()
    assert not nonexistent.parent.exists()


def test_reads_are_independent_and_do_not_change_the_art_index(published_path):
    store = BLSStore(published_path, threads=1)

    def query(_: int):
        result = store.get_observations([PC_A, CU_A])
        return result.snapshot_id, len(result.observations)

    with ThreadPoolExecutor(max_workers=4) as executor:
        assert (
            list(executor.map(query, range(8))) == [("query_fixture_20261105", 7)] * 8
        )
    with duckdb.connect(str(published_path), read_only=True) as conn:
        assert conn.execute(
            "SELECT index_name FROM duckdb_indexes() WHERE table_name='observations'"
        ).fetchall() == [("observations_series_id_art",)]
        with pytest.raises(duckdb.Error):
            conn.execute("CREATE TABLE cannot_write(i INTEGER)")


def test_thousand_series_batch_uses_one_bound_list(tmp_path):
    path = tmp_path / "thousand.duckdb"
    ids = [f"PCU{num:012d}" for num in range(1_000)]
    with _builder(path) as conn:
        initialize_schema(conn)
        write_snapshot_info(
            conn, SnapshotInfo("batch_1000", datetime.now(UTC), ("pc",))
        )
        write_source_file(
            conn, SourceFileReceipt(1, "pc", "batch.fixture", "b" * 64, 1, "test")
        )
        conn.executemany(
            "INSERT INTO series_catalog(series_id,program_code,title) "
            "VALUES (?, 'pc', ?)",
            [(sid, f"Series {number:04d}") for number, sid in enumerate(ids)],
        )
        conn.executemany(
            "INSERT INTO observations VALUES (?, ?, ?, ?, ?, ?)",
            [
                (sid, year, "M12", value, None, 1)
                for sid in ids
                for year, value in ((2024, 100.0), (2025, 110.0))
            ],
        )
        conn.execute(
            "CREATE INDEX observations_series_id_art ON observations(series_id)"
        )
        conn.execute(
            "UPDATE snapshot_info SET lifecycle_state='PUBLISHED', "
            "validation_status='PASSED'"
        )
    store = BLSStore(path)
    for batch_size in (1, 10, 100, 500, 1_000):
        selection = ids[:batch_size]
        raw = store.get_observations(
            selection, start_year=2025, end_year=2025, max_rows=2_000
        )
        assert (len(raw.observations), len(raw.statuses)) == (batch_size, batch_size)
        assert all(out.status is QueryStatus.SUCCESS for out in raw.statuses)
        rebased = store.normalize_series(
            selection,
            base_year=2024,
            base_period="M12",
            start_year=2025,
            end_year=2025,
            max_rows=2_000,
        )
        assert (len(rebased.observations), len(rebased.statuses)) == (
            batch_size,
            batch_size,
        )
        assert all(
            row.normalized_value == pytest.approx(110) for row in rebased.observations
        )
        assert all(out.status is QueryStatus.SUCCESS for out in rebased.statuses)


OEWS_SERIES = (
    "OEUN000000000000000000001",
    "oe",
    "Employment for All Occupations in All Industries, National",
    None,
    False,
    2024,
    "A01",
    2024,
    "A01",
    "number",
    None,
    True,
)


def test_search_series_surfaces_cpi_series_through_the_catalog_service(
    published_path,
):
    """search_series's ``cu`` filter returns the snapshot's CPI-U series."""
    from bls_mcp.models.series import SeriesSearchRequest
    from bls_mcp.services.series_catalog import SeriesCatalogService

    service = SeriesCatalogService(BLSStore(published_path))
    results = service.search(SeriesSearchRequest(programs=["cu"]))

    assert {r.series.series_id for r in results} == {CU_A, CU_SEMI}
    assert {r.series.program for r in results} == {"cu"}
    assert {r.series.geography for r in results} == {"U.S. city average"}


def test_search_series_accepts_oews_before_and_after_oews_data_exists(
    published_path,
):
    """``oe`` is accepted now and returns OEWS series once a snapshot holds them.

    OEWS has no ingestion yet, so the filter finds nothing; it must not be a
    validation error. A catalog row with no OEWS classification table must still
    come back, so the filter keeps working when OEWS ingestion lands.
    """
    from bls_mcp.models.series import SeriesSearchRequest
    from bls_mcp.services.series_catalog import SeriesCatalogService

    request = SeriesSearchRequest(programs=["oe"])
    assert SeriesCatalogService(BLSStore(published_path)).search(request) == []

    conn = duckdb.connect(str(published_path))
    try:
        conn.execute(
            "INSERT INTO series_catalog VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            OEWS_SERIES,
        )
    finally:
        conn.close()

    results = SeriesCatalogService(BLSStore(published_path)).search(request)
    assert [r.series.series_id for r in results] == [OEWS_SERIES[0]]
    assert results[0].series.program == "oe"
    mixed = SeriesCatalogService(BLSStore(published_path)).search(
        SeriesSearchRequest(programs=["cu", "oe"])
    )
    assert {r.series.program for r in mixed} == {"cu", "oe"}
