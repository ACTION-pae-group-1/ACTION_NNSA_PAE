"""Native DuckDB CU ingest, cross-program behavior and ART persistence tests."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

duckdb = pytest.importorskip("duckdb")

from bls_mcp.ingestion.cu import CUIngestError, ingest_cu  # noqa: E402
from bls_mcp.ingestion.cu_manifest import CUInputError  # noqa: E402
from bls_mcp.ingestion.pc import ingest_pc  # noqa: E402
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

MONTHLY = "CUUR0000SA0"
SEMIANNUAL = "CUUS0000SA0"
ALTERNATE = "CUSR0400AA0"
DATA_HEADER = "series_id\tyear\tperiod\tvalue\tfootnote_codes\n"
SERIES_HEADER = (
    "series_id\tarea_code\titem_code\tseasonal\tperiodicity_code\tbase_code\t"
    "base_period\tseries_title\tfootnote_codes\tbegin_year\tbegin_period\t"
    "end_year\tend_period\n"
)
SOURCE_FILES = {
    "cu.area": (
        "area_mapping",
        "area_code\tarea_name\tdisplay_level\tselectable\tsort_sequence\n"
        "0000\tU.S. city average\t0\tT\t1\n"
        "0400\tWest\t0\tF\t2\n",
    ),
    "cu.item": (
        "item_mapping",
        "item_code\titem_name\tdisplay_level\tselectable\tsort_sequence\n"
        "SA0\tAll items\t0\tT\t1\t\n"
        "AA0\tAll items - old base\t0\tF\t2\t\n",
    ),
    "cu.series": (
        "series_metadata",
        SERIES_HEADER
        + f"{MONTHLY}\t0000\tSA0\tU\tR\tS\t1982-84=100\tAll items (monthly)\t\t"
        "1913\tM01\t2026\tM12\t\n"
        f"{SEMIANNUAL}\t0000\tSA0\tU\tS\tS\t1982-84=100\tAll items (semiannual)\t\t"
        "1990\tS01\t2026\tS03\t\n"
        f"{ALTERNATE}\t0400\tAA0\tS\tR\tA\t1967=100\tWest old-base all items\t\t"
        "2000\tM01\t2020\tM12\t\n",
    ),
}


def make_manifest(
    root: Path,
    *,
    historical: str | None = None,
    current: str | None = None,
    corrupt_series: str | None = None,
) -> Path:
    files = dict(SOURCE_FILES)
    if corrupt_series is not None:
        files["cu.series"] = ("series_metadata", corrupt_series)
    if historical is not None:
        files["cu.data.1.AllItems"] = ("historical", DATA_HEADER + historical)
    if current is not None:
        files["cu.data.0.Current"] = ("current", DATA_HEADER + current)
    entries = []
    for filename, (role, text) in files.items():
        raw = text.encode()
        (root / filename).write_bytes(raw)
        entries.append(
            {
                "path": filename,
                "role": role,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size_bytes": len(raw),
            }
        )
    manifest = root / "cu-input.json"
    manifest.write_text(
        json.dumps({"schema_version": 1, "program": "cu", "files": entries}),
        encoding="utf-8",
    )
    return manifest


@pytest.fixture
def writer(tmp_path: Path):
    path = tmp_path / "candidate.duckdb"
    with build_connection(path) as conn:
        initialize_schema(conn)
        write_snapshot_info(conn, SnapshotInfo("cu_test", datetime.now(UTC), ("cu",)))
        yield conn, path


def test_monthly_semiannual_dedup_classifications_and_art(writer, tmp_path):
    conn, _ = writer
    manifest = make_manifest(
        tmp_path,
        historical=(
            f"{MONTHLY}\t2025\tM12\t321.000\t\n"
            f"{MONTHLY}\t2025\tM13\t318.2\t\n"
            f"{SEMIANNUAL}\t2025\tS03\t310.2\t\n"
        ),
        current=(
            f"{MONTHLY}\t2025\tM12\t321\t\n"
            f"{MONTHLY}\t2026\tM01\t322.5\tP\n"
            f"{SEMIANNUAL}\t2026\tS01\t-\tA\n"
            f"{ALTERNATE}\t2020\tM12\t158.6\t\n"
        ),
    )
    report = ingest_cu(conn, manifest)
    assert report.snapshot_id == "cu_test"
    assert (report.source_files, report.areas, report.items, report.series) == (
        5,
        2,
        2,
        3,
    )
    assert (report.rows_read, report.missing_rows, report.identical_duplicates) == (
        7,
        1,
        1,
    )
    assert report.observations == 5
    assert report.art_index == "observations_series_id_art"
    assert conn.execute(
        "SELECT year, period, value, footnote_codes FROM observations "
        "WHERE series_id=? ORDER BY year, period",
        [MONTHLY],
    ).fetchall() == [
        (2025, "M12", 321.0, None),
        (2025, "M13", 318.2, None),
        (2026, "M01", 322.5, "P"),
    ]
    assert conn.execute(
        "SELECT periodicity_code, base_code, base_period "
        "FROM cu_series WHERE series_id=?",
        [SEMIANNUAL],
    ).fetchone() == ("S", "S", "1982-84=100")
    assert conn.execute(
        "SELECT original_reference_base, seasonal_adjustment "
        "FROM series_catalog WHERE series_id=?",
        [ALTERNATE],
    ).fetchone() == ("1967=100", True)
    assert conn.execute(
        "SELECT display_level, selectable, sort_sequence FROM cu_area "
        "WHERE area_code='0400'"
    ).fetchone() == (0, False, 2)
    assert conn.execute(
        "SELECT display_level, selectable, sort_sequence FROM cu_area "
        "WHERE area_code='0000'"
    ).fetchone() == (0, True, 1)
    assert conn.execute(
        "SELECT display_level, selectable, sort_sequence FROM cu_item "
        "WHERE item_code='AA0'"
    ).fetchone() == (0, False, 2)
    assert [r.selection_role for r in read_source_files(conn)] == [
        "area_mapping",
        "item_mapping",
        "series_metadata",
        "historical",
        "current",
    ]
    assert conn.execute(
        """SELECT filename FROM source_files s JOIN observations o
        USING (source_file_id) WHERE o.series_id=? AND o.year=2025
        AND o.period='M12'""",
        [MONTHLY],
    ).fetchone() == ("cu.data.1.AllItems",)
    assert conn.execute(
        "SELECT is_unique FROM duckdb_indexes() WHERE index_name=?",
        [report.art_index],
    ).fetchone() == (False,)


def test_art_survives_reopening_and_candidate_is_not_published(tmp_path):
    db = tmp_path / "cu.duckdb"
    manifest = make_manifest(tmp_path, current=f"{MONTHLY}\t2026\tM01\t321\t\n")
    with build_connection(db) as conn:
        initialize_schema(conn)
        write_snapshot_info(
            conn, SnapshotInfo("persist_cu", datetime.now(UTC), ("cu",))
        )
        ingest_cu(conn, manifest)
    with pytest.raises(SnapshotNotPublishedError):
        with snapshot_reader(db):
            pass
    with snapshot_reader(db, require_published=False) as reader:
        assert reader.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 1
        assert (
            reader.execute(
                "SELECT COUNT(*) FROM duckdb_indexes() "
                "WHERE index_name='observations_series_id_art'"
            ).fetchone()[0]
            == 1
        )


@pytest.mark.parametrize(
    "bad_data, expected",
    [
        (f"{MONTHLY}\t2025\tM14\t101\t\n", "Malformed"),
        (f"{MONTHLY}\t2025\tQ01\t101\t\n", "Malformed"),
        (f"{MONTHLY}\t2025\tS01\t101\t\n", "periodicity"),
        (f"{SEMIANNUAL}\t2025\tM01\t101\t\n", "periodicity"),
        (f"{MONTHLY}\tbad\tM01\t101\t\n", "Malformed"),
        (f"{MONTHLY}\t2025\tM01\tNaN\t\n", "Malformed"),
        (f"{MONTHLY}\t2025\tM01\tInfinity\t\n", "Malformed"),
        (f"{MONTHLY}\t2025\tM01\tINVALID\t\n", "Malformed"),
        ("CUUR9999SA0\t2025\tM01\t101\t\n", "unknown CU series"),
    ],
)
def test_bad_data_rolls_back_entire_cu_import(tmp_path, writer, bad_data, expected):
    conn, _ = writer
    manifest = make_manifest(tmp_path, current=bad_data)
    with pytest.raises(CUIngestError, match=expected):
        ingest_cu(conn, manifest)
    for table in (
        "series_catalog",
        "cu_series",
        "cu_area",
        "cu_item",
        "observations",
        "source_files",
    ):
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
        f"{MONTHLY}\t2025\tM12\t321.5\t\n",
        f"{MONTHLY}\t2025\tM12\t321\tP\n",
    ],
)
def test_current_historical_conflict_rolls_back(tmp_path, writer, current):
    conn, _ = writer
    manifest = make_manifest(
        tmp_path, historical=f"{MONTHLY}\t2025\tM12\t321\t\n", current=current
    )
    with pytest.raises(CUIngestError, match="Conflicting"):
        ingest_cu(conn, manifest)
    assert conn.execute("SELECT COUNT(*) FROM source_files").fetchone()[0] == 0


def test_cu_area_selectable_must_be_boolean_flag(tmp_path, writer):
    conn, _ = writer
    manifest = make_manifest(tmp_path, current=f"{MONTHLY}\t2025\tM12\t321\t\n")
    area = tmp_path / "cu.area"
    raw = area.read_bytes().replace(
        b"0000\tU.S. city average\t0\tT\t1",
        b"0000\tU.S. city average\t0\tX\t1",
    )
    area.write_bytes(raw)
    entries = json.loads(manifest.read_text(encoding="utf-8"))
    for item in entries["files"]:
        if item["path"] == "cu.area":
            item["sha256"] = hashlib.sha256(raw).hexdigest()
            item["size_bytes"] = len(raw)
    manifest.write_text(json.dumps(entries), encoding="utf-8")
    with pytest.raises(CUIngestError, match="area selectable"):
        ingest_cu(conn, manifest)
    assert conn.execute("SELECT COUNT(*) FROM cu_area").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 0


def test_reingestion_refused(tmp_path, writer):
    conn, _ = writer
    manifest = make_manifest(tmp_path, current=f"{MONTHLY}\t2025\tM12\t321\t\n")
    ingest_cu(conn, manifest)
    with pytest.raises(CUIngestError, match="already contains"):
        ingest_cu(conn, manifest)
    assert conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 1


def test_checksum_failure_occurs_before_database_writes(tmp_path, writer):
    conn, _ = writer
    manifest = make_manifest(tmp_path, current=f"{MONTHLY}\t2025\tM12\t321\t\n")
    (tmp_path / "cu.series").write_bytes(b"tampered\n")
    with pytest.raises(CUInputError, match="header"):
        ingest_cu(conn, manifest)
    assert conn.execute("SELECT COUNT(*) FROM series_catalog").fetchone()[0] == 0


def test_classification_mismatch_is_rejected(tmp_path, writer):
    conn, _ = writer
    corrupt = SOURCE_FILES["cu.series"][1].replace(
        f"{MONTHLY}\t0000\tSA0", f"{MONTHLY}\tXXXX\tSA0"
    )
    manifest = make_manifest(
        tmp_path,
        current=f"{MONTHLY}\t2025\tM12\t321\t\n",
        corrupt_series=corrupt,
    )
    with pytest.raises(CUIngestError, match="Unknown CU area/item"):
        ingest_cu(conn, manifest)
    assert conn.execute("SELECT COUNT(*) FROM cu_series").fetchone()[0] == 0


def _make_pc_manifest(root: Path) -> Path:
    sample = {
        "pc.industry": (
            "industry_mapping",
            "industry_code\tindustry_name\n334---\tMachinery\n",
        ),
        "pc.product": (
            "product_mapping",
            "industry_code\tproduct_code\tproduct_name\n334---\t334---\tMachinery\n",
        ),
        "pc.series": (
            "series_metadata",
            "series_id\tindustry_code\tproduct_code\tseasonal\t"
            "base_date\tseries_title\tfootnote_codes\tbegin_year\tbegin_period\t"
            "end_year\tend_period\n"
            "PCU334---334---\t334---\t334---\tU\t200012\tMachinery PPI\t\t"
            "2000\tM01\t2026\tM12\n",
        ),
        "pc.data.0.Current": (
            "current",
            "series_id\tyear\tperiod\tvalue\tfootnote_codes\n"
            "PCU334---334---\t2025\tM01\t100.25\t\n",
        ),
    }
    files = []
    for filename, (role, data) in sample.items():
        raw = data.encode()
        (root / filename).write_bytes(raw)
        files.append(
            {
                "path": filename,
                "role": role,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size_bytes": len(raw),
            }
        )
    manifest = root / "pc-input.json"
    manifest.write_text(
        json.dumps({"schema_version": 1, "program": "pc", "files": files})
    )
    return manifest


@pytest.mark.parametrize("order", [("pc", "cu"), ("cu", "pc")])
def test_pc_cu_coexist_without_collisions_and_keep_art(tmp_path, order):
    cu = make_manifest(tmp_path, current=f"{MONTHLY}\t2025\tM01\t301.125\t\n")
    pc = _make_pc_manifest(tmp_path)
    with build_connection(tmp_path / "mixed.duckdb") as conn:
        initialize_schema(conn)
        write_snapshot_info(
            conn, SnapshotInfo("mixed_pc_cu", datetime.now(UTC), ("pc", "cu"))
        )
        for program in order:
            if program == "pc":
                ingest_pc(conn, pc)
            else:
                ingest_cu(conn, cu)
        assert conn.execute(
            "SELECT program_code, COUNT(*) FROM series_catalog "
            "GROUP BY program_code ORDER BY program_code"
        ).fetchall() == [("cu", 3), ("pc", 1)]
        assert conn.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 2
        assert (
            conn.execute(
                "SELECT COUNT(DISTINCT source_file_id) FROM source_files"
            ).fetchone()[0]
            == 8
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM duckdb_indexes() "
                "WHERE index_name='observations_series_id_art'"
            ).fetchone()[0]
            == 1
        )
        assert conn.execute("SELECT COUNT(*) FROM pc_industry").fetchone()[0] == 1
