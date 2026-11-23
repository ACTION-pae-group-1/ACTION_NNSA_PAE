"""Startup wiring of the PARS server assembled in pars_local_mcp/server.py."""

import json
from pathlib import Path

import duckdb
import pytest
from fastmcp import Client

import pars_local_mcp.mcp.server as mcp_server_mod
import pars_local_mcp.server as server_mod
from pars_local_mcp.config import Settings
from pars_local_mcp.mcp.errors import PublicError

READ_TOOLS = {
    "list_projects",
    "search_wbs",
    "get_wbs_hierarchy",
    "get_wbs_lineage",
    "get_project_info",
    "get_leaf_nodes",
    "get_wbs_by_level",
}
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
REPO_ROOT = Path(__file__).resolve().parents[3]


def _settings(tmp_path):
    return Settings(
        database_path=tmp_path / "pars.duckdb",
        model_dir=tmp_path / "models",
        model_signing_key_path=tmp_path / "keys" / "model_signing.key",
    )


def _pars_allowlist():
    path = REPO_ROOT / "src" / "mcp_servers.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    return set(config["servers"]["pars_mcp"]["allowed_tools"])


def test_create_server_initializes_the_database_before_serving(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    monkeypatch.setattr(server_mod, "get_settings", lambda: settings)

    server_mod.create_server()

    con = duckdb.connect(str(settings.database_path), read_only=True)
    try:
        tables = {row[0] for row in con.execute("SHOW TABLES").fetchall()}
    finally:
        con.close()
    assert "projects" in tables
    assert "labeled_wbs" in tables


@pytest.mark.asyncio
async def test_create_server_exposes_every_read_and_wbs_tool(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    monkeypatch.setattr(server_mod, "get_settings", lambda: settings)

    async with Client(server_mod.create_server()) as client:
        names = {tool.name for tool in await client.list_tools()}

    assert READ_TOOLS <= names, READ_TOOLS - names
    assert WBS_TOOLS <= names, WBS_TOOLS - names


@pytest.mark.asyncio
async def test_pars_allowlist_matches_registered_tools(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    monkeypatch.setattr(mcp_server_mod, "get_settings", lambda: settings)

    allowed = _pars_allowlist()
    async with Client(mcp_server_mod.create_server()) as client:
        registered = {tool.name for tool in await client.list_tools()}

    # Every registered PARS tool must be explicitly allowlisted.
    assert registered == allowed, {
        "not_registered": allowed - registered,
        "not_allowlisted": registered - allowed,
    }


def test_server_instructions_describe_only_what_the_server_does(tmp_path, monkeypatch):
    settings = _settings(tmp_path)
    monkeypatch.setattr(mcp_server_mod, "get_settings", lambda: settings)

    instructions = mcp_server_mod.create_server().instructions or ""

    assert "MLflow" not in instructions
    assert "chunking" not in instructions.lower()
    assert "WBS" in instructions
    assert "synthetic" in instructions


@pytest.mark.parametrize(
    "server_module",
    [server_mod, mcp_server_mod],
    ids=["main_server", "mcp_server"],
)
def test_server_startup_preserves_non_synthetic_database(
    tmp_path, monkeypatch, server_module
):
    """Server startup must refuse to overwrite an existing unmarked database."""
    settings = _settings(tmp_path)

    # Create an existing, unmarked database outside the synthetic data directory.
    con = duckdb.connect(str(settings.database_path))
    try:
        con.execute("CREATE TABLE projects (id INTEGER, name VARCHAR)")
        con.execute("INSERT INTO projects VALUES (42, 'preserve-me')")
    finally:
        con.close()

    monkeypatch.setattr(server_module, "get_settings", lambda: settings)

    # Startup must fail before any synthetic data replaces existing tables.
    with pytest.raises(PublicError, match="not marked as synthetic"):
        server_module.create_server()

    # The original database and its data must remain intact.
    con = duckdb.connect(str(settings.database_path), read_only=True)
    try:
        rows = con.execute("SELECT id, name FROM projects").fetchall()
        tables = {row[0] for row in con.execute("SHOW TABLES").fetchall()}
    finally:
        con.close()

    assert rows == [(42, "preserve-me")]
    assert tables == {"projects"}
