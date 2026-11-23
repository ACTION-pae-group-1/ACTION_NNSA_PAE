"""Dependency-free guard against PARS registry/UI launch drift."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_pars_registry_matches_existing_ui_launch_command():
    config = json.loads((ROOT / "src/mcp_servers.json").read_text(encoding="utf-8"))
    pars = config["servers"]["pars_mcp"]
    assert pars["transport"] == "stdio"
    assert pars["command"] == "uv"
    assert pars["args"] == [
        "run",
        "--no-sync",
        "python",
        "-m",
        "src.pars_local_mcp.server",
    ]


def test_pars_registry_tool_names_have_no_duplicates():
    config = json.loads((ROOT / "src/mcp_servers.json").read_text(encoding="utf-8"))
    allowed = config["servers"]["pars_mcp"]["allowed_tools"]
    assert len(allowed) == len(set(allowed))
    assert {"list_projects", "validate_wbs_inputs", "run_wbs_pipeline"} <= set(allowed)
