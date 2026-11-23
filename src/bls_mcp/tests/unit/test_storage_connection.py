"""Offline writer isolation and read-only snapshot access."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

duckdb = pytest.importorskip("duckdb")

from bls_mcp.storage.connection import (  # noqa: E402
    SnapshotNotPublishedError,
    build_connection,
    snapshot_reader,
)
from bls_mcp.storage.models import SnapshotInfo  # noqa: E402
from bls_mcp.storage.schema import initialize_schema  # noqa: E402
from bls_mcp.storage.snapshots import write_snapshot_info  # noqa: E402


@pytest.fixture
def candidate_path(tmp_path: Path) -> Path:
    path = tmp_path / "snapshot.duckdb"
    with build_connection(path, threads=1, memory_limit="128MB") as conn:
        initialize_schema(conn)
        write_snapshot_info(
            conn,
            SnapshotInfo("candidate_20261105", datetime.now(timezone.utc), ("pc",)),
        )
    return path


def test_builder_refuses_existing_database(candidate_path):
    with pytest.raises(FileExistsError, match="Refusing"):
        with build_connection(candidate_path):
            pass


def test_reader_does_not_create_nonexistent_database(tmp_path):
    missing = tmp_path / "missing" / "snapshot.duckdb"
    with pytest.raises(FileNotFoundError):
        with snapshot_reader(missing):
            pass
    assert not missing.parent.exists()


def test_reader_rejects_incomplete_snapshot_by_default(candidate_path):
    with pytest.raises(SnapshotNotPublishedError, match="BUILDING"):
        with snapshot_reader(candidate_path):
            pass
    with snapshot_reader(candidate_path, require_published=False) as reader:
        assert reader.execute("SELECT COUNT(*) FROM observations").fetchone() == (0,)
        with pytest.raises(duckdb.Error):
            reader.execute("CREATE TABLE not_permitted (id INT)")


def test_published_reader_supports_multiple_read_only_connections(candidate_path):
    with duckdb.connect(str(candidate_path)) as conn:
        conn.execute(
            "UPDATE snapshot_info SET lifecycle_state='PUBLISHED', "
            "validation_status='PASSED'"
        )
    with snapshot_reader(candidate_path, threads=1) as first:
        with snapshot_reader(candidate_path, threads=1) as second:
            identity = first.execute("SELECT snapshot_id FROM snapshot_info").fetchone()
            assert identity == ("candidate_20261105",)
            receipts = second.execute("SELECT COUNT(*) FROM source_files").fetchone()
            assert receipts == (0,)
            with pytest.raises(duckdb.Error):
                second.execute("CREATE TABLE not_permitted (id INT)")


def test_connection_options_reject_invalid_threads(candidate_path):
    with pytest.raises(ValueError, match="threads"):
        with snapshot_reader(candidate_path, threads=0):
            pass
    with pytest.raises(ValueError, match="threads"):
        with build_connection(candidate_path.parent / "other.duckdb", threads=True):
            pass
