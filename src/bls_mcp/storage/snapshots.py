"""Snapshot identity and original-source receipts stored inside DuckDB.

This module does not build, validate, publish, or activate snapshots. Those
lifecycle operations are deferred until Milestone 6.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from bls_mcp.storage.models import (
    SnapshotInfo,
    SnapshotState,
    SourceFileReceipt,
    ValidationStatus,
)
from bls_mcp.storage.schema import SCHEMA_VERSION

if TYPE_CHECKING:
    from duckdb import DuckDBPyConnection


class SnapshotMetadataError(ValueError):
    """Snapshot identity is absent, unsupported, or internally inconsistent."""


def write_snapshot_info(conn: DuckDBPyConnection, info: SnapshotInfo) -> None:
    """Insert the single immutable identity record for a new build.

    A singleton PRIMARY KEY prevents two identity rows in the same database.
    Changes to build/validation/publication state belong to the lifecycle API.
    """
    if info.schema_version != SCHEMA_VERSION:
        raise SnapshotMetadataError(
            f"Cannot write schema {info.schema_version}; supported {SCHEMA_VERSION}"
        )
    conn.execute(
        """
        INSERT INTO snapshot_info (
            singleton, snapshot_id, schema_version, built_at, build_commit,
            programs, lifecycle_state, validation_status
        ) VALUES (1, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            info.snapshot_id,
            info.schema_version,
            info.built_at,
            info.build_commit,
            json.dumps(info.programs, separators=(",", ":")),
            info.lifecycle_state.value,
            info.validation_status.value,
        ],
    )


def read_snapshot_info(conn: DuckDBPyConnection) -> SnapshotInfo:
    """Read and validate the unique snapshot identity, including schema version."""
    try:
        rows = conn.execute(
            """
            SELECT snapshot_id, schema_version, built_at, build_commit,
                   programs, lifecycle_state, validation_status
            FROM snapshot_info
            """
        ).fetchall()
    except Exception as exc:
        raise SnapshotMetadataError("Snapshot has no readable snapshot_info") from exc
    if len(rows) != 1:
        raise SnapshotMetadataError("Snapshot must contain exactly one identity row")
    snapshot_id, schema_version, built_at, build_commit, raw_programs, state, status = (
        rows[0]
    )
    if schema_version not in (4, SCHEMA_VERSION):
        raise SnapshotMetadataError(
            f"Unsupported snapshot schema {schema_version}"
            "expected 4 or {SCHEMA_VERSION}"
        )
    try:
        programs = json.loads(raw_programs)
        if not isinstance(programs, list):
            raise ValueError("programs must be a JSON array")
        return SnapshotInfo(
            snapshot_id=snapshot_id,
            schema_version=schema_version,
            built_at=built_at,
            build_commit=build_commit,
            programs=tuple(programs),
            lifecycle_state=SnapshotState(state),
            validation_status=ValidationStatus(status),
        )
    except (TypeError, ValueError) as exc:
        raise SnapshotMetadataError("Malformed snapshot_info record") from exc


def write_source_file(conn: DuckDBPyConnection, receipt: SourceFileReceipt) -> None:
    """Save verified raw-file metadata; never import source bytes here."""
    conn.execute(
        """
        INSERT INTO source_files (
            source_file_id, program_code, filename, source_url, sha256,
            size_bytes, retrieved_at, etag, last_modified, selection_role
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            receipt.source_file_id,
            receipt.program_code,
            receipt.filename,
            receipt.source_url,
            receipt.sha256.lower(),
            receipt.size_bytes,
            receipt.retrieved_at,
            receipt.etag,
            receipt.last_modified,
            receipt.selection_role,
        ],
    )


def read_source_files(conn: DuckDBPyConnection) -> tuple[SourceFileReceipt, ...]:
    """Return receipts in stable source_file_id order for later validation."""
    rows = conn.execute(
        """
        SELECT source_file_id, program_code, filename, sha256, size_bytes,
               selection_role, source_url, retrieved_at, etag, last_modified
        FROM source_files
        ORDER BY source_file_id
        """
    ).fetchall()
    return tuple(SourceFileReceipt(*row) for row in rows)
