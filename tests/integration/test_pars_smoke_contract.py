"""Dependency-free checks for the local PARS protocol smoke script."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "verify_pars_mcp.py"


def test_pars_smoke_script_compiles():
    ast.parse(SCRIPT.read_text(encoding="utf-8"))


def test_pars_smoke_never_invokes_mutating_tools():
    source = SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(source)
    called = {
        node.args[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "call"
        and node.args
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    }
    assert called == {
        "list_projects",
        "get_project_info",
        "search_wbs",
        "get_wbs_hierarchy",
        "get_wbs_lineage",
        "get_leaf_nodes",
        "get_wbs_by_level",
    }
