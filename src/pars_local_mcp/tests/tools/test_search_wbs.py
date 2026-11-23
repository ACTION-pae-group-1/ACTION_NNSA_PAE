"""Offline registration contract for search_wbs."""

import pytest
from fastmcp import Client, FastMCP

from pars_local_mcp.config import Settings
from pars_local_mcp.mcp.tools import search_wbs


@pytest.mark.asyncio
async def test_search_wbs_registers_exact_tool(tmp_path):
    settings = Settings(
        database_path=tmp_path / "pars.duckdb",
        model_dir=tmp_path / "models",
        model_signing_key_path=tmp_path / "keys" / "model_signing.key",
    )
    server = FastMCP("registration-test")
    search_wbs.register(server, settings)
    async with Client(server) as client:
        tools = await client.list_tools()
    assert [tool.name for tool in tools] == ["search_wbs"]
