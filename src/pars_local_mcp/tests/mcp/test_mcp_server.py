"""Tests for server.py - verify MCP server initialization and entry point."""

import pytest
from fastmcp import Client

from pars_local_mcp.mcp.server import create_server, main


@pytest.fixture
def isolated_database(tmp_path, monkeypatch):
    """Point DATABASE_PATH at a temp file, keeping the repo DB out of tests."""
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "pars.duckdb"))


WBS_TOOLS = {
    "validate_wbs_inputs",
    "clean_wbs_data",
    "tune_and_train_wbs",
    "predict_wbs",
    "write_back_wbs",
    "run_wbs_pipeline",
    "get_wbs_run_status",
    "get_wbs_project_descriptions",
    "get_wbs_rows",
}
PARS_TOOLS = {
    "list_projects",
    "search_wbs",
    "get_wbs_hierarchy",
    "get_wbs_lineage",
    "get_project_info",
    "get_leaf_nodes",
    "get_wbs_by_level",
}


@pytest.mark.usefixtures("isolated_database")
def test_create_server_returns_fastmcp():
    """Test that create_server returns a FastMCP instance."""
    server = create_server()
    assert server is not None
    assert hasattr(server, "run")


def test_main_callable():
    """Test that main function exists and is callable."""
    assert callable(main)


@pytest.mark.asyncio
@pytest.mark.usefixtures("isolated_database")
async def test_server_exposes_every_wbs_and_pars_tool():
    async with Client(create_server()) as client:
        names = {tool.name for tool in await client.list_tools()}
    assert WBS_TOOLS <= names, WBS_TOOLS - names
    assert PARS_TOOLS <= names, PARS_TOOLS - names


@pytest.mark.asyncio
@pytest.mark.usefixtures("isolated_database")
async def test_real_server_validates_the_bundled_mock_through_the_transport():
    async with Client(create_server()) as client:
        result = await client.call_tool("validate_wbs_inputs", {})
    report = result.structured_content
    assert report["ok"] is True, report["problems"]
    assert report["data_origin"] == "synthetic_mock"


@pytest.mark.asyncio
async def test_pyproject_entry_creates_its_database_before_serving(
    tmp_path, monkeypatch
):
    """The pars-mcp-server script must create its database before serving."""
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "pars.duckdb"))
    async with Client(create_server()) as client:
        result = await client.call_tool("list_projects", {})
    assert "error" not in result.structured_content
