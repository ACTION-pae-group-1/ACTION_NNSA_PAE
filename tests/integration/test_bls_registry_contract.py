"""Guard the portable client's BLS allowlist against drift from the server.

The bundled agent can call only the tools listed for ``bls_server`` in
``src/mcp_servers.json``. If the allowlist omits a step of the source-backed
workflow, the agent can describe a basket but never calculate it from the
snapshot, which is the path the conversation evals grade.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bls_mcp.tests.harness_duckdb import duckdb_server_env

pytest.importorskip("duckdb")

ROOT = Path(__file__).resolve().parents[2]
SOURCE_BACKED_WORKFLOW = {
    "search_series",
    "create_index_spec",
    "validate_index_spec",
    "save_index_spec",
    "calculate_index_from_bls",
}


def _allowed_tools() -> list[str]:
    config = json.loads((ROOT / "src/mcp_servers.json").read_text(encoding="utf-8"))
    return config["servers"]["bls_server"]["allowed_tools"]


def test_bls_allowlist_includes_the_source_backed_workflow() -> None:
    missing = SOURCE_BACKED_WORKFLOW - set(_allowed_tools())
    assert not missing, f"bls_server allowlist is missing {sorted(missing)}"


def test_bls_allowlist_has_no_duplicates() -> None:
    allowed = _allowed_tools()
    assert len(allowed) == len(set(allowed))


@pytest.mark.asyncio
async def test_bls_allowlist_names_only_registered_tools(tmp_path: Path) -> None:
    async with duckdb_server_env(tmp_path) as env:
        registered = {tool.name for tool in await env.client.list_tools()}

    unknown = set(_allowed_tools()) - registered
    assert not unknown, f"bls_server allowlist names unknown tools {sorted(unknown)}"
