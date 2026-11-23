"""Offline M6 build, validation, immutable publication and rollback tests."""

import hashlib
import json
from contextlib import closing
from pathlib import Path

import pytest

duckdb = pytest.importorskip("duckdb")

from bls_mcp.ingestion.cli import main  # noqa: E402
from bls_mcp.ingestion.lifecycle import (  # noqa: E402
    SnapshotLifecycleError,
    build_candidate,
    sha256_file,
    validate_candidate,
    validation_report_path,
)
from bls_mcp.ingestion.publish import (  # noqa: E402
    PublicationError,
    activate_snapshot,
    current_snapshot_path,
    publish_candidate,
    read_registry,
    rollback_snapshot,
)
from bls_mcp.storage.connection import snapshot_reader  # noqa: E402
from bls_mcp.storage.models import SnapshotState, ValidationStatus  # noqa: E402
from bls_mcp.storage.snapshots import read_snapshot_info  # noqa: E402
from bls_mcp.storage.store import BLSStore  # noqa: E402

PC_SERIES = "PCU334---334---"
CU_SERIES = "CUUR0000SA0"
HEADER = "series_id\tyear\tperiod\tvalue\tfootnote_codes\n"


def _manifest(root: Path, code: str, files: dict[str, tuple[str, str]]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    entries = []
    for name, (role, body) in files.items():
        raw = body.encode("utf-8")
        (root / name).write_bytes(raw)
        entries.append(
            {
                "path": name,
                "role": role,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size_bytes": len(raw),
            }
        )
    path = root / "source.json"
    path.write_text(
        json.dumps({"schema_version": 1, "program": code, "files": entries})
    )
    return path


def pc_manifest(root: Path, value: float = 100.0) -> Path:
    return _manifest(
        root,
        "pc",
        {
            "pc.industry.txt": (
                "industry_mapping",
                "industry_code\tindustry_name\n334---\tMachinery\n",
            ),
            "pc.product": (
                "product_mapping",
                "industry_code\tproduct_code\tproduct_name\n"
                "334---\t334---\tMachinery output\n",
            ),
            "pc.series": (
                "series_metadata",
                "series_id\tindustry_code\tproduct_code\tseasonal\t"
                "base_date\tseries_title\tfootnote_codes\tbegin_year\tbegin_period\t"
                "end_year\tend_period\n"
                f"{PC_SERIES}\t334---\t334---\tU\t200012\tMachinery PPI\t\t"
                "2000\tM01\t2026\tM12\n",
            ),
            "pc.data.0.Current": (
                "current",
                HEADER + f"{PC_SERIES}\t2025\tM12\t{value}\t\n",
            ),
        },
    )


def cu_manifest(root: Path) -> Path:
    return _manifest(
        root,
        "cu",
        {
            "cu.area": (
                "area_mapping",
                "area_code\tarea_name\tdisplay_level\tselectable\tsort_sequence\n"
                "0000\tUS average\t0\tT\t1\n",
            ),
            "cu.item": (
                "item_mapping",
                "item_code\titem_name\tdisplay_level\tselectable\t"
                "sort_sequence\nSA0\tAll items\t0\tT\t1\t\n",
            ),
            "cu.series": (
                "series_metadata",
                "series_id\tarea_code\titem_code\tseasonal\t"
                "periodicity_code\tbase_code\tbase_period\tseries_title\t"
                "footnote_codes\tbegin_year\tbegin_period\tend_year\tend_period\n"
                f"{CU_SERIES}\t0000\tSA0\tU\tR\tS\t1982-84=100\tAll items\t\t"
                "1913\tM01\t2026\tM12\t\n",
            ),
            "cu.data.0.Current": (
                "current",
                HEADER + f"{CU_SERIES}\t2025\tM12\t320.3\t\n",
            ),
        },
    )


def _ready(tmp_path: Path, identifier: str, *, value: float = 100.0):
    manifest = pc_manifest(tmp_path / f"raw-{identifier}", value)
    candidate = tmp_path / f"{identifier}.duckdb"
    built = build_candidate(candidate, identifier, pc_manifest=manifest)
    assert built.programs == ("pc",)
    report = validate_candidate(candidate, pc_manifest=manifest)
    assert report.passed, report.issues
    assert report.candidate_sha256 == sha256_file(candidate)
    return candidate, manifest


def test_build_validate_publish_activate_and_query(tmp_path: Path):
    candidate, manifest = _ready(tmp_path, "first")
    report = json.loads(validation_report_path(candidate).read_text())
    assert report["passed"] is True and report["counts"]["observations"] == 1
    with snapshot_reader(candidate, require_published=False) as conn:
        assert read_snapshot_info(conn).lifecycle_state is SnapshotState.READY
    with pytest.raises(ValueError, match="PUBLISHED"):
        with snapshot_reader(candidate):
            pass

    root = tmp_path / "published"
    entry = publish_candidate(candidate, root)
    assert entry.sha256 == sha256_file(root / entry.filename)
    assert read_registry(root).active_snapshot_id is None
    assert read_registry(root).snapshots == (entry,)
    published_file = root / entry.filename
    with snapshot_reader(published_file) as conn:
        assert read_snapshot_info(conn).lifecycle_state is SnapshotState.PUBLISHED
    with pytest.raises(PublicationError, match="No active"):
        current_snapshot_path(root)
    assert activate_snapshot(root, "first") == published_file
    assert current_snapshot_path(root) == published_file
    page = BLSStore(current_snapshot_path(root)).get_observations([PC_SERIES])
    assert page.snapshot_id == "first"
    assert len(page.observations) == 1 and page.observations[0].value == 100.0
    # Publishing changed only the staged copy, not the validated candidate.
    with snapshot_reader(candidate, require_published=False) as conn:
        assert read_snapshot_info(conn).lifecycle_state is SnapshotState.READY
    assert sha256_file(candidate) == report["candidate_sha256"]
    assert manifest.is_file()


def test_mixed_pc_cu_candidate_gets_globally_sorted_and_indexed(tmp_path: Path):
    pc = pc_manifest(tmp_path / "pc")
    cu = cu_manifest(tmp_path / "cu")
    candidate = tmp_path / "both.duckdb"
    build_candidate(candidate, "both", pc_manifest=pc, cu_manifest=cu)
    report = validate_candidate(candidate, pc_manifest=pc, cu_manifest=cu)
    assert report.passed, report.issues
    assert report.counts["observations"] == 2
    assert report.counts["cu_series"] == 1 and report.counts["pc_series"] == 1
    with snapshot_reader(candidate, require_published=False) as conn:
        assert conn.execute(
            "SELECT series_id FROM observations ORDER BY rowid"
        ).fetchall() == [(CU_SERIES,), (PC_SERIES,)]
        index = conn.execute(
            "SELECT is_unique FROM duckdb_indexes() "
            "WHERE index_name='observations_series_id_art'"
        ).fetchall()
        assert index == [(False,)]
    entry = publish_candidate(candidate, tmp_path / "registry")
    found = BLSStore(tmp_path / "registry" / entry.filename).get_observations(
        [CU_SERIES, PC_SERIES]
    )
    assert len(found.observations) == 2


def test_missing_manifest_fails_and_stays_unpublishable(tmp_path: Path):
    pc = pc_manifest(tmp_path / "raw")
    candidate = tmp_path / "candidate.duckdb"
    build_candidate(candidate, "rejected", pc_manifest=pc)
    report = validate_candidate(candidate)
    assert not report.passed and report.candidate_sha256 is None
    assert "manifest" in report.issues[0]
    with snapshot_reader(candidate, require_published=False) as conn:
        info = read_snapshot_info(conn)
        assert info.lifecycle_state is SnapshotState.VALIDATING
        assert info.validation_status is ValidationStatus.FAILED
    with pytest.raises(PublicationError, match="invalid READY validation report"):
        publish_candidate(candidate, tmp_path / "versions")
    with pytest.raises(SnapshotLifecycleError, match="BUILDING"):
        validate_candidate(candidate, pc_manifest=pc)


def test_tampered_source_is_rejected_and_reported(tmp_path: Path):
    pc = pc_manifest(tmp_path / "raw")
    candidate = tmp_path / "candidate.duckdb"
    build_candidate(candidate, "changed_raw", pc_manifest=pc)
    (pc.parent / "pc.data.0.Current").write_bytes(HEADER.encode())
    report = validate_candidate(candidate, pc_manifest=pc)
    assert not report.passed and any("mismatch" in x.lower() for x in report.issues)
    assert not (tmp_path / "versions").exists()


def test_missing_art_index_and_duplicate_observation_are_rejected(tmp_path: Path):
    pc = pc_manifest(tmp_path / "raw")
    candidate = tmp_path / "candidate.duckdb"
    build_candidate(candidate, "bad_index", pc_manifest=pc)
    with closing(duckdb.connect(str(candidate))) as conn:
        conn.execute("DROP INDEX observations_series_id_art")
    report = validate_candidate(candidate, pc_manifest=pc)
    assert not report.passed and "ART" in report.issues[0]

    other = tmp_path / "duplicates.duckdb"
    build_candidate(other, "bad_rows", pc_manifest=pc)
    with closing(duckdb.connect(str(other))) as conn:
        conn.execute("INSERT INTO observations SELECT * FROM observations LIMIT 1")
    report = validate_candidate(other, pc_manifest=pc)
    assert not report.passed and "duplicate" in report.issues[0].lower()


def test_candidate_checksum_mismatch_blocks_publication(tmp_path: Path):
    candidate, _ = _ready(tmp_path, "no_mutation")
    report_path = validation_report_path(candidate)
    doc = json.loads(report_path.read_text())
    doc["candidate_sha256"] = "0" * 64
    report_path.write_text(json.dumps(doc))
    with pytest.raises(PublicationError, match="changed after validation"):
        publish_candidate(candidate, tmp_path / "versions")
    assert read_registry(tmp_path / "versions").snapshots == ()


def test_rollback_preserves_previous_snapshots_and_open_readers(tmp_path: Path):
    first, _ = _ready(tmp_path, "snap_old", value=100.0)
    second, _ = _ready(tmp_path, "snap_new", value=115.0)
    root = tmp_path / "versions"
    old_entry = publish_candidate(first, root)
    new_entry = publish_candidate(second, root)
    old_file = root / old_entry.filename
    activate_snapshot(root, "snap_old")
    with snapshot_reader(old_file) as reader:
        activate_snapshot(root, "snap_new")
        assert current_snapshot_path(root) == root / new_entry.filename
        assert reader.execute("SELECT value FROM observations").fetchone()[0] == 100.0
        assert rollback_snapshot(root) == old_file
        assert current_snapshot_path(root) == old_file
    assert old_file.is_file() and (root / new_entry.filename).is_file()
    assert len(read_registry(root).history) == 3


def test_publish_refuses_id_collision_or_lock(tmp_path: Path):
    candidate, _ = _ready(tmp_path, "snap_a")
    root = tmp_path / "versions"
    publish_candidate(candidate, root)
    with pytest.raises(PublicationError, match="already registered"):
        publish_candidate(candidate, root)
    (root / ".publication.lock").write_text("12345")
    with pytest.raises(PublicationError, match="lock exists"):
        activate_snapshot(root, "snap_a")
    assert (root / ".publication.lock").is_file()


def test_corrupted_registry_and_published_hash_fail_closed(tmp_path: Path):
    candidate, _ = _ready(tmp_path, "snap_a")
    root = tmp_path / "versions"
    entry = publish_candidate(candidate, root)
    path = root / entry.filename
    # The original published file is not modified during a valid activation.
    (root / "active-snapshot.json").write_text('{"active_snapshot_id": "../bad"}')
    with pytest.raises(PublicationError, match="Invalid snapshot registry"):
        activate_snapshot(root, "snap_a")
    (root / "active-snapshot.json").unlink()
    # A mismatch in an existing version is also a hard failure.
    with pytest.raises(PublicationError, match="Unknown published"):
        activate_snapshot(root, "snap_a")
    assert path.is_file()


def test_failed_activation_does_not_change_active_pointer(tmp_path: Path):
    old, _ = _ready(tmp_path, "old")
    new, _ = _ready(tmp_path, "new")
    root = tmp_path / "versions"
    publish_candidate(old, root)
    entry = publish_candidate(new, root)
    activate_snapshot(root, "old")
    # Corrupt registry checksum, leaving the database intact.
    doc = json.loads((root / "active-snapshot.json").read_text())
    for item in doc["snapshots"]:
        if item["snapshot_id"] == "new":
            item["sha256"] = "0" * 64
    (root / "active-snapshot.json").write_text(json.dumps(doc))
    with pytest.raises(PublicationError, match="checksum changed"):
        activate_snapshot(root, "new")
    assert read_registry(root).active_snapshot_id == "old"
    assert (root / entry.filename).is_file()


def test_cli_build_validate_publish_activate_rollback(tmp_path: Path, capsys):
    pc1 = pc_manifest(tmp_path / "raw1")
    pc2 = pc_manifest(tmp_path / "raw2", 103.0)
    root = tmp_path / "registry"
    for identifier, manifest in (("a", pc1), ("b", pc2)):
        candidate = tmp_path / f"{identifier}.duckdb"
        assert (
            main(
                [
                    "build",
                    "--candidate",
                    str(candidate),
                    "--snapshot-id",
                    identifier,
                    "--pc-manifest",
                    str(manifest),
                ]
            )
            == 0
        )
        assert (
            main(
                [
                    "validate",
                    "--candidate",
                    str(candidate),
                    "--pc-manifest",
                    str(manifest),
                ]
            )
            == 0
        )
        assert (
            main(
                ["publish", "--candidate", str(candidate), "--registry-dir", str(root)]
            )
            == 0
        )
    assert main(["list", "--registry-dir", str(root)]) == 0
    assert main(["activate", "--registry-dir", str(root), "--snapshot-id", "a"]) == 0
    assert main(["activate", "--registry-dir", str(root), "--snapshot-id", "b"]) == 0
    assert main(["rollback", "--registry-dir", str(root)]) == 0
    assert main(["current", "--registry-dir", str(root)]) == 0
    assert str(root / "bls-a.duckdb") in capsys.readouterr().out


def test_registry_replace_failure_preserves_active_version(tmp_path: Path, monkeypatch):
    from bls_mcp.ingestion import publish as publisher

    old, _ = _ready(tmp_path, "old_active")
    candidate, _ = _ready(tmp_path, "new_candidate")
    root = tmp_path / "versions"
    publish_candidate(old, root)
    activate_snapshot(root, "old_active")
    previous_path = current_snapshot_path(root)
    previous_bytes = sha256_file(previous_path)

    def fail_registry_update(*_args):
        raise OSError("simulated registry write failure")

    monkeypatch.setattr(publisher, "_write_registry", fail_registry_update)
    with pytest.raises(OSError, match="simulated registry"):
        publish_candidate(candidate, root)
    # A versioned file may now be an orphan, but it is never active.
    assert read_registry(root).active_snapshot_id == "old_active"
    assert current_snapshot_path(root) == previous_path
    assert sha256_file(previous_path) == previous_bytes


def test_rollback_without_prior_active_does_not_change_registry(tmp_path: Path):
    candidate, _ = _ready(tmp_path, "only")
    root = tmp_path / "versions"
    publish_candidate(candidate, root)
    activate_snapshot(root, "only")
    with pytest.raises(PublicationError, match="No previous"):
        rollback_snapshot(root)
    assert read_registry(root).active_snapshot_id == "only"


def test_validation_rejects_observation_lineage_to_metadata_file(tmp_path: Path):
    pc = pc_manifest(tmp_path / "raw")
    candidate = tmp_path / "bad_lineage.duckdb"
    build_candidate(candidate, "bad_lineage", pc_manifest=pc)
    with closing(duckdb.connect(str(candidate))) as conn:
        conn.execute("UPDATE observations SET source_file_id=1")
    report = validate_candidate(candidate, pc_manifest=pc)
    assert not report.passed
    assert "source receipts" in report.issues[0]
