"""Snapshot identity and file lineage persist across connection boundaries."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

duckdb = pytest.importorskip("duckdb")

from bls_mcp.storage.connection import build_connection, snapshot_reader  # noqa: E402
from bls_mcp.storage.models import (  # noqa: E402
    SnapshotInfo,
    SnapshotState,
    SourceFileReceipt,
    ValidationStatus,
)
from bls_mcp.storage.schema import initialize_schema  # noqa: E402
from bls_mcp.storage.snapshots import (  # noqa: E402
    SnapshotMetadataError,
    read_snapshot_info,
    read_source_files,
    write_snapshot_info,
    write_source_file,
)

NOW = datetime(2026, 11, 5, 13, 45, tzinfo=timezone.utc)


def test_snapshot_info_round_trip_and_singleton(tmp_path: Path):
    path = tmp_path / "test.duckdb"
    with build_connection(path) as writer:
        initialize_schema(writer)
        original = SnapshotInfo(
            "snapshot_20261105_1", NOW, ("pc", "cu"), build_commit="abcdef12"
        )
        write_snapshot_info(writer, original)
        with pytest.raises(Exception, match="Duplicate|duplicate|PRIMARY KEY"):
            write_snapshot_info(writer, original)
    with snapshot_reader(path, require_published=False) as reader:
        restored = read_snapshot_info(reader)
    assert restored == original


def test_missing_and_wrong_schema_version_raise_metadata_error(tmp_path: Path):
    path = tmp_path / "schema.duckdb"
    with build_connection(path) as writer:
        initialize_schema(writer)
    with pytest.raises(SnapshotMetadataError, match="exactly one"):
        with snapshot_reader(path, require_published=False):
            pass
    with duckdb.connect(str(path)) as writer:
        write_snapshot_info(writer, SnapshotInfo("bad_version", NOW, ("pc",)))
        writer.execute("UPDATE snapshot_info SET schema_version=999")
    with pytest.raises(SnapshotMetadataError, match="Unsupported"):
        with snapshot_reader(path, require_published=False):
            pass


def test_v1_scratch_snapshots_require_rebuilding(tmp_path: Path):
    path = tmp_path / "old_version.duckdb"
    with build_connection(path) as writer:
        initialize_schema(writer)
        write_snapshot_info(writer, SnapshotInfo("old_v1", NOW, ("cu",)))
        writer.execute("UPDATE snapshot_info SET schema_version=1")
    with pytest.raises(SnapshotMetadataError, match="Unsupported"):
        with snapshot_reader(path, require_published=False):
            pass


def test_file_receipts_round_trip_and_stable_order(tmp_path: Path):
    path = tmp_path / "source.duckdb"
    with build_connection(path) as writer:
        initialize_schema(writer)
        write_snapshot_info(
            writer,
            SnapshotInfo(
                "snap_reproducible",
                NOW,
                ("pc",),
                lifecycle_state=SnapshotState.READY,
                validation_status=ValidationStatus.PASSED,
            ),
        )
        later = SourceFileReceipt(
            2,
            "pc",
            "pc.data.0.Current",
            "a" * 64,
            27,
            "current",
            "https://download.bls.gov/pub/time.series/pc/pc.data.0.Current",
            NOW,
            '"v1"',
            "Thu, 05 Nov 2026 13:00:00 GMT",
        )
        earlier = SourceFileReceipt(
            1, "pc", "pc.series", "b" * 64, 72, "series_metadata"
        )
        write_source_file(writer, later)
        write_source_file(writer, earlier)
    with snapshot_reader(path, require_published=False) as reader:
        assert read_snapshot_info(reader).validation_status is ValidationStatus.PASSED
        stored = read_source_files(reader)
        assert stored == (earlier, later)
        assert stored[1].retrieved_at == NOW
