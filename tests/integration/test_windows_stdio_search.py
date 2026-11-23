"""Windows stdio regression: the first snapshot-backed MCP search must reply.

This test covers subprocess/pipe behavior that in-process FastMCP tests cannot.
The fixture snapshot contains one known series and never contacts BLS or Ask Sage.
"""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

import pytest

from bls_mcp.tests.harness_duckdb import FIXTURE_PC_SERIES, build_registry
from portable_llm_mcp import MCPHub, ServerConfig


@pytest.mark.asyncio
@pytest.mark.skipif(
    sys.platform != "win32", reason="Windows stdio loader-lock regression"
)
async def test_first_stdio_catalog_search_completes(tmp_path: Path) -> None:
    registry = build_registry(tmp_path)
    servers = {
        "bls_server": ServerConfig(
            transport="stdio",
            allowed_tools=("search_series", "get_bls_access_status"),
            command=sys.executable,
            args=("-m", "bls_mcp.app"),
            env={
                "MCP_TRANSPORT": "stdio",
                "BLS_SNAPSHOT_REGISTRY_DIR": str(registry),
                "BLS_SPECS_DB_PATH": str(tmp_path / "specs.duckdb"),
            },
        )
    }
    async with MCPHub(servers) as hub:
        session = hub._sessions["bls_server"]
        status = await session.call_tool(
            "get_bls_access_status",
            arguments={},
            read_timeout_seconds=timedelta(seconds=15),
        )
        assert not status.isError

        result = await session.call_tool(
            "search_series",
            arguments={"request": {"query": "Machinery", "limit": 10}},
            read_timeout_seconds=timedelta(seconds=20),
        )
        assert not result.isError
        hits = result.structuredContent["result"]
        assert FIXTURE_PC_SERIES in {hit["series"]["series_id"] for hit in hits}
