"""Offline registration contract for validate_wbs_inputs."""

import pytest
from fastmcp import Client, FastMCP

from pars_local_mcp.config import Settings
from pars_local_mcp.mcp.tools import validate_wbs_inputs


@pytest.mark.asyncio
async def test_validate_wbs_inputs_registers_exact_tool(tmp_path):
    settings = Settings(
        database_path=tmp_path / "pars.duckdb",
        model_dir=tmp_path / "models",
        model_signing_key_path=tmp_path / "keys" / "model_signing.key",
    )
    server = FastMCP("registration-test")
    validate_wbs_inputs.register(server, settings)
    async with Client(server) as client:
        tools = await client.list_tools()
    assert [tool.name for tool in tools] == ["validate_wbs_inputs"]
