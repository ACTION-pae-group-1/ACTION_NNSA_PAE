"""ingest_ci fails closed on a manifest it cannot load, before any write."""

import duckdb
import pytest

from bls_mcp.ingestion.ci import ingest_ci
from bls_mcp.ingestion.ci_manifest import CIInputError


def test_missing_manifest_is_refused_and_creates_nothing(tmp_path):
    conn = duckdb.connect(":memory:")
    try:
        with pytest.raises(CIInputError, match="Cannot load CI manifest"):
            ingest_ci(conn, tmp_path / "missing_manifest.json")

        assert conn.execute("SHOW TABLES").fetchall() == []
    finally:
        conn.close()
