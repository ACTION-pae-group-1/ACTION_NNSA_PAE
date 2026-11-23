"""Explicit offline-writer and read-only-reader DuckDB connection scopes."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import duckdb

from bls_mcp.storage.models import SnapshotState
from bls_mcp.storage.snapshots import SnapshotMetadataError, read_snapshot_info


class SnapshotNotPublishedError(SnapshotMetadataError):
    """An unfinished snapshot was requested through the production reader."""


def _config(
    *, threads: int | None, memory_limit: str | None
) -> dict[str, str | bool | int | float | list[str]]:
    config: dict[str, str | bool | int | float | list[str]] = {}
    if threads is not None:
        if not isinstance(threads, int) or isinstance(threads, bool) or threads < 1:
            raise ValueError("threads must be a positive integer")
        config["threads"] = str(threads)
    if memory_limit is not None:
        if not isinstance(memory_limit, str) or not memory_limit.strip():
            raise ValueError("memory_limit must be a nonempty DuckDB size string")
        config["memory_limit"] = memory_limit
    return config


@contextmanager
def build_connection(
    database_path: str | Path,
    *,
    threads: int | None = None,
    memory_limit: str | None = None,
) -> Iterator[duckdb.DuckDBPyConnection]:
    """Create a new scratch DB; refuse to open/overwrite existing snapshots.

    This is a single-writer context. Call ``initialize_schema`` and
    ``write_snapshot_info`` explicitly. Publication is a separate milestone.
    """
    path = Path(database_path)
    config = _config(threads=threads, memory_limit=memory_limit)
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite an existing DuckDB: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(database=str(path), read_only=False, config=config)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def snapshot_reader(
    snapshot_path: str | Path,
    *,
    threads: int | None = None,
    memory_limit: str | None = None,
    require_published: bool = True,
) -> Iterator[duckdb.DuckDBPyConnection]:
    """Open a snapshot read-only, without creating any files or directories.

    The default rejects incomplete and merely READY databases. Validation may
    pass ``require_published=False`` to inspect a finalized candidate before
    it is published; that mode must not serve production queries.
    """
    path = Path(snapshot_path)
    config = _config(threads=threads, memory_limit=memory_limit)
    if not path.is_file():
        raise FileNotFoundError(f"Snapshot file does not exist: {path}")
    conn = duckdb.connect(database=str(path), read_only=True, config=config)
    try:
        info = read_snapshot_info(conn)
        if require_published and info.lifecycle_state != SnapshotState.PUBLISHED:
            raise SnapshotNotPublishedError(
                f"Snapshot {info.snapshot_id} is {info.lifecycle_state}; "
                "only PUBLISHED snapshots may serve queries"
            )
        yield conn
    finally:
        conn.close()
