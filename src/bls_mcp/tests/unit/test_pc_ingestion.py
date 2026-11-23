"""Offline integration tests for DuckDB PC staging and the post-load ART index."""

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

duckdb = pytest.importorskip("duckdb")

from bls_mcp.ingestion.pc import PCIngestError, ingest_pc  # noqa: E402
from bls_mcp.storage.connection import (  # noqa: E402
    SnapshotNotPublishedError,
    build_connection,
    snapshot_reader,
)
from bls_mcp.storage.models import SnapshotInfo  # noqa: E402
from bls_mcp.storage.schema import initialize_schema  # noqa: E402
from bls_mcp.storage.snapshots import (  # noqa: E402
    read_source_files,
    write_snapshot_info,
)

SERIES_A = "PCU334---334---"
SERIES_B = "PCU334519334519S"
DATA_HEADER = "series_id\tyear\tperiod\tvalue\tfootnote_codes\n"
BASE_FILES = {
    "pc.industry.txt": (
        "industry_mapping",
        "industry_code\tindustry_name\n334---\tMachinery\n334519\tInstruments\n",
    ),
    "pc.product": (
        "product_mapping",
        "industry_code\tproduct_code\tproduct_name\n"
        "334---\t334---\tMachinery\n"
        "334519\t334519S\tSpecial instruments\n",
    ),
    "pc.series": (
        "series_metadata",
        "series_id\tindustry_code\tproduct_code\tseasonal\tbase_date\t"
        "series_title\tfootnote_codes\tbegin_year\tbegin_period\tend_year\tend_period\n"
        f"{SERIES_A}\t334---\t334---\tU\t200012\tMachinery PPI\t\t"
        "2000\tM01\t2026\tM12\n"
        f"{SERIES_B}\t334519\t334519S\tS\t201212\tInstruments PPI\t\t"
        "2012\tM01\t2025\tM12\n",
    ),
}


def make_manifest(
    tmp_path: Path,
    *,
    historical: str | None = None,
    current: str | None = None,
    all_data: str | None = None,
) -> Path:
    files = dict(BASE_FILES)
    if historical is not None:
        files["pc.data.1.Historical"] = ("historical", DATA_HEADER + historical)
    if current is not None:
        files["pc.data.0.Current"] = ("current", DATA_HEADER + current)
    if all_data is not None:
        files["pc.data.AllData"] = ("all_data", DATA_HEADER + all_data)
    entries = []
    for filename, (role, data) in files.items():
        raw = data.encode()
        (tmp_path / filename).write_bytes(raw)
        entries.append(
            {
                "path": filename,
                "role": role,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size_bytes": len(raw),
            }
        )
    path = tmp_path / "pc.json"
    path.write_text(
        json.dumps({"schema_version": 1, "program": "pc", "files": entries})
    )
    return path


@pytest.fixture
def writer(tmp_path: Path):
    path = tmp_path / "test.duckdb"
    with build_connection(path) as conn:
        initialize_schema(conn)
        write_snapshot_info(conn, SnapshotInfo("pc_test", datetime.now(UTC), ("pc",)))
        yield conn, path


def test_bulk_load_deduplicates_and_creates_persistent_art_index(tmp_path, writer):
    conn, _ = writer
    manifest = make_manifest(
        tmp_path,
        historical=(f"{SERIES_A}\t2025\tM12\t100.0\t\n{SERIES_A}\t2025\tM13\t99.8\t\n"),
        current=(
            f"{SERIES_A}\t2025\tM12\t100.000\t\n"
            f"{SERIES_A}\t2026\tM01\t101.1\tP\n"
            f"{SERIES_B}\t2025\tM12\t200.0\t\n"
            f"{SERIES_B}\t2026\tM01\t-\tA\n"
        ),
    )
    report = ingest_pc(conn, manifest)
    assert report.snapshot_id == "pc_test"
    assert report.source_files == 5
    assert report.industries == 2
    assert report.products == 2
    assert report.series == 2
    assert report.rows_read == 6
    assert report.missing_rows == 1
    assert report.identical_duplicates == 1
    assert report.observations == 4
    assert report.art_index == "observations_series_id_art"
    assert conn.execute(
        "SELECT series_id, year, period FROM observations "
        "ORDER BY series_id, year, period"
    ).fetchall() == [
        (SERIES_A, 2025, "M12"),
        (SERIES_A, 2025, "M13"),
        (SERIES_A, 2026, "M01"),
        (SERIES_B, 2025, "M12"),
    ]
    assert (
        conn.execute(
            "SELECT source_file_id FROM observations "
            + "WHERE series_id=? AND period='M12'",
            [SERIES_A],
        ).fetchone()[0]
        == 4
    )  # Historical has precedence over Current.
    assert (
        conn.execute(
            "SELECT footnote_codes FROM observations WHERE period='M01'"
        ).fetchone()[0]
        == "P"
    )
    assert (
        conn.execute(
            "SELECT product_name FROM pc_product "
            "WHERE industry_code='334519' AND product_code='334519S'"
        ).fetchone()[0]
        == "Special instruments"
    )
    assert (
        conn.execute(
            "SELECT active FROM series_catalog WHERE series_id=?", [SERIES_B]
        ).fetchone()[0]
        is False
    )
    assert [r.selection_role for r in read_source_files(conn)] == [
        "industry_mapping",
        "product_mapping",
        "series_metadata",
        "historical",
        "current",
    ]
    index = conn.execute(
        """SELECT sql, is_unique FROM duckdb_indexes()
        WHERE table_name='observations'
          AND index_name='observations_series_id_art'"""
    ).fetchone()
    assert index is not None and "series_id" in index[0]
    assert index[1] is False


def test_art_index_persists_after_reopening_on_disk(tmp_path):
    path = tmp_path / "indexed.duckdb"
    manifest = make_manifest(tmp_path, current=f"{SERIES_A}\t2026\tM01\t120.0\t\n")
    with build_connection(path) as writer:
        initialize_schema(writer)
        write_snapshot_info(
            writer, SnapshotInfo("indexed_pc", datetime.now(UTC), ("pc",))
        )
        ingest_pc(writer, manifest)
    with pytest.raises(SnapshotNotPublishedError):
        with snapshot_reader(path):
            pass
    with snapshot_reader(path, require_published=False) as reader:
        assert reader.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 1
        assert (
            reader.execute(
                "SELECT COUNT(*) FROM duckdb_indexes() "
                "WHERE index_name='observations_series_id_art'"
            ).fetchone()[0]
            == 1
        )


@pytest.mark.parametrize(
    "bad_data,expected",
    [
        (f"{SERIES_A}\t2026\tM14\t100.0\t\n", "Malformed"),
        (f"{SERIES_A}\tbad\tM01\t100.0\t\n", "Malformed"),
        (f"{SERIES_A}\t2026\tQ01\t100.0\t\n", "Malformed"),
        (f"{SERIES_A}\t2026\tM01\tNaN\t\n", "Malformed"),
        (f"{SERIES_A}\t2026\tM01\tInfinity\t\n", "Malformed"),
        (f"{SERIES_A}\t2026\tM01\tnot_a_number\t\n", "Malformed"),
        ("PCU_UNKNOWN\t2026\tM01\t100.0\t\n", "unknown PC series"),
    ],
)
def test_invalid_data_rolls_back_all_pc_writes(tmp_path, writer, bad_data, expected):
    conn, _ = writer
    manifest = make_manifest(tmp_path, current=bad_data)
    with pytest.raises(PCIngestError, match=expected):
        ingest_pc(conn, manifest)
    for table in ("series_catalog", "observations", "source_files", "pc_industry"):
        assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM duckdb_indexes() WHERE table_name='observations'"
        ).fetchone()[0]
        == 0
    )


@pytest.mark.parametrize(
    "current",
    [
        f"{SERIES_A}\t2025\tM12\t100.1\t\n",  # Different index value.
        f"{SERIES_A}\t2025\tM12\t100.0\tP\n",  # Different footnotes.
    ],
)
def test_conflicting_current_and_historical_are_rejected(tmp_path, writer, current):
    conn, _ = writer
    manifest = make_manifest(
        tmp_path,
        historical=f"{SERIES_A}\t2025\tM12\t100.0\t\n",
        current=current,
    )
    with pytest.raises(PCIngestError, match="Conflicting"):
        ingest_pc(conn, manifest)
    assert conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM source_files").fetchone()[0] == 0


def test_all_data_selection_has_no_duplicate_sources(tmp_path, writer):
    conn, _ = writer
    manifest = make_manifest(
        tmp_path,
        all_data=f"{SERIES_A}\t2020\tM01\t91.25\t\n",
    )
    report = ingest_pc(conn, manifest)
    assert report.source_files == 4
    assert report.observations == 1
    assert report.identical_duplicates == 0


def test_second_ingestion_is_refused_without_changes(tmp_path, writer):
    conn, _ = writer
    manifest = make_manifest(tmp_path, current=f"{SERIES_A}\t2020\tM01\t90\t\n")
    ingest_pc(conn, manifest)
    with pytest.raises(PCIngestError, match="already contains"):
        ingest_pc(conn, manifest)
    assert conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 1


def test_integrity_failure_is_detected_before_any_writes(tmp_path, writer):
    conn, _ = writer
    manifest = make_manifest(tmp_path, current=f"{SERIES_A}\t2020\tM01\t90\t\n")
    (tmp_path / "pc.data.0.Current").write_text(DATA_HEADER + "tampered\n")
    with pytest.raises(ValueError, match="SHA-256"):
        ingest_pc(conn, manifest)
    assert conn.execute("SELECT COUNT(*) FROM source_files").fetchone()[0] == 0


def test_metadata_classification_mismatch_is_rejected(tmp_path, writer):
    conn, _ = writer
    manifest = make_manifest(tmp_path, current=f"{SERIES_A}\t2020\tM01\t90\t\n")
    path = tmp_path / "pc.product"
    raw = path.read_text().replace("334519S", "UNKNOWN")
    path.write_text(raw)
    on_disk = path.read_bytes()
    entries = json.loads(manifest.read_text())
    for item in entries["files"]:
        if item["path"] == "pc.product":
            item["sha256"] = hashlib.sha256(on_disk).hexdigest()
            item["size_bytes"] = len(on_disk)
    manifest.write_text(json.dumps(entries))
    with pytest.raises(PCIngestError, match="Unknown industry/product"):
        ingest_pc(conn, manifest)
    assert conn.execute("SELECT COUNT(*) FROM pc_series").fetchone()[0] == 0


def test_checked_in_pc_samples_load_without_invented_values(tmp_path, writer):
    """Exercise the real owner-saved metadata and 34-row data slice."""
    conn, _ = writer
    source_dir = Path(__file__).resolve().parents[4] / "src/bls_mcp/docs/sample_data"
    entries = []
    for filename, role in (
        ("pc.industry.txt", "industry_mapping"),
        ("pc.product", "product_mapping"),
        ("pc.series", "series_metadata"),
        ("pc.data.20.ComputerProduct.sample", "historical"),
    ):
        destination = tmp_path / filename
        shutil.copyfile(source_dir / filename, destination)
        raw = destination.read_bytes()
        entries.append(
            {
                "path": filename,
                "role": role,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size_bytes": len(raw),
            }
        )
    manifest = tmp_path / "pc-real-samples.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "program": "pc",
                "files": entries,
            }
        )
    )
    report = ingest_pc(conn, manifest)
    assert report.series == 4510
    assert report.industries == 998
    assert report.products == 4510
    assert report.rows_read == 34
    assert report.observations == 34
    assert report.identical_duplicates == 0
    assert (
        conn.execute("SELECT COUNT(*) FROM observations WHERE period='M13'").fetchone()[
            0
        ]
        == 1
    )
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM duckdb_indexes() "
            "WHERE index_name='observations_series_id_art'"
        ).fetchone()[0]
        == 1
    )
