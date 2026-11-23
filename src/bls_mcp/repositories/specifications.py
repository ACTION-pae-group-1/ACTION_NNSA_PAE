from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

import duckdb

from bls_mcp.models.specifications import EscalationIndexSpec

_SPECS_DDL = """
CREATE TABLE IF NOT EXISTS saved_index_specs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    spec_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


@contextmanager
def _specs_conn(database_path: str) -> Iterator[duckdb.DuckDBPyConnection]:
    """Open the specs DuckDB file for reading and writing."""
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(database=database_path, read_only=False)
    try:
        yield conn
    finally:
        conn.close()


class SpecificationRepository:
    """Repository for saved index specifications, backed by a DuckDB file."""

    def __init__(self, database_path: str) -> None:
        self.database_path = database_path
        #: Serializes save()'s read-previous-revision-then-write pair across
        #: threads. Connections in this process share one database instance,
        #: so without this two concurrent saves could both read revision n
        #: and both write n+1; across processes DuckDB's file lock already
        #: rejects the second writer outright.
        self._save_lock = threading.Lock()

    def _ensure_schema(self, conn: duckdb.DuckDBPyConnection) -> None:
        conn.execute(_SPECS_DDL)

    def save(self, spec: EscalationIndexSpec) -> EscalationIndexSpec:
        now = datetime.now(UTC).isoformat()
        spec.updated_at = datetime.fromisoformat(now)
        with (
            self._save_lock,
            _specs_conn(self.database_path) as conn,
        ):
            self._ensure_schema(conn)
            stored = conn.execute(
                "SELECT spec_json FROM saved_index_specs WHERE id = ?",
                [spec.id],
            ).fetchone()
            previous = json.loads(stored[0]).get("revision", 1) if stored else 0
            spec.revision = previous + 1
            payload = json.dumps(spec.model_dump(mode="json"))
            conn.execute(
                """
                INSERT INTO saved_index_specs
                    (id, name, spec_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    name = excluded.name,
                    spec_json = excluded.spec_json,
                    updated_at = excluded.updated_at
                """,
                [
                    spec.id,
                    spec.name,
                    payload,
                    spec.created_at.isoformat(),
                    spec.updated_at.isoformat(),
                ],
            )
        return spec

    def get(self, spec_id: str) -> EscalationIndexSpec | None:
        with _specs_conn(self.database_path) as conn:
            self._ensure_schema(conn)
            row = conn.execute(
                "SELECT spec_json FROM saved_index_specs WHERE id = ?",
                [spec_id],
            ).fetchone()
        if row is None:
            return None
        return EscalationIndexSpec.model_validate_json(row[0])

    def list(self) -> list[EscalationIndexSpec]:
        with _specs_conn(self.database_path) as conn:
            self._ensure_schema(conn)
            rows = conn.execute(
                "SELECT spec_json FROM saved_index_specs ORDER BY updated_at DESC"
            ).fetchall()
        return [EscalationIndexSpec.model_validate_json(row[0]) for row in rows]

    def delete(self, spec_id: str) -> None:
        with _specs_conn(self.database_path) as conn:
            self._ensure_schema(conn)
            conn.execute(
                "DELETE FROM saved_index_specs WHERE id = ?",
                [spec_id],
            )
