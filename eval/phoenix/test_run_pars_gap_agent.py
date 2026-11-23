"""Tests for the pure helper logic in the PARS gap tool-call-order agent eval.

The full main() flow (launching the isolated stdio server, driving a local
Ollama agent through it) is exercised end-to-end by actually running it —
see eval/caef/results/release-2026-11-19/FINAL_EVALUATION_REPORT.md section
4.1 (13/13 cases pass). These tests cover the standalone, pure helper logic:
the Ollama pin, the qualified tool-name parser, and the deterministic
tool-call-order/argument checks.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_pars_gap_agent as rpga  # noqa: E402


def test_ollama_pin_refuses_any_other_provider_or_host():
    assert rpga.OLLAMA["LLM_PROVIDER"] == "ollama"
    assert rpga.OLLAMA["LLM_BASE_URL"] == "http://localhost:11434/v1"


def test_tool_name_strips_the_server_prefix():
    assert rpga._tool_name("pars_mcp__get_wbs_by_level") == "get_wbs_by_level"
    assert rpga._tool_name("list_projects") == "list_projects"


def test_check_calls_flags_an_agent_error():
    checks = rpga._check_calls({"expect_tools": []}, [], "boom")
    no_error_check = next(c for c in checks if c["name"] == "no_agent_error")
    assert no_error_check["pass"] is False
    assert no_error_check["detail"] == "boom"


def test_check_calls_passes_when_expected_tools_appear_in_order():
    case = {"expect_tools": ["list_projects", "get_wbs_by_level"]}
    calls = [
        {"tool": "list_projects", "args": {}, "result": "{}"},
        {"tool": "get_wbs_by_level", "args": {}, "result": "{}"},
    ]
    checks = rpga._check_calls(case, calls, "")
    ordered = next(c for c in checks if c["name"] == "expected_tools_in_order")
    assert ordered["pass"] is True


def test_check_calls_fails_when_expected_tools_are_out_of_order():
    case = {"expect_tools": ["list_projects", "get_wbs_by_level"]}
    calls = [
        {"tool": "get_wbs_by_level", "args": {}, "result": "{}"},
        {"tool": "list_projects", "args": {}, "result": "{}"},
    ]
    checks = rpga._check_calls(case, calls, "")
    ordered = next(c for c in checks if c["name"] == "expected_tools_in_order")
    assert ordered["pass"] is False


def test_check_calls_flags_an_unregistered_tool():
    case = {"expect_tools": []}
    calls = [{"tool": "not_a_real_tool", "args": {}, "result": "{}"}]
    checks = rpga._check_calls(case, calls, "")
    registered = next(c for c in checks if c["name"] == "only_registered_tools")
    assert registered["pass"] is False


def test_check_calls_verifies_required_arguments():
    case = {
        "expect_tools": ["get_wbs_by_level"],
        "required_args": {"get_wbs_by_level": {"project_id": "proj_001"}},
    }
    calls = [
        {
            "tool": "get_wbs_by_level",
            "args": {"project_id": "proj_001", "level": 2},
            "result": "{}",
        }
    ]
    checks = rpga._check_calls(case, calls, "")
    args_check = next(c for c in checks if c["name"] == "args_get_wbs_by_level")
    assert args_check["pass"] is True


def test_check_calls_fails_when_required_arguments_do_not_match():
    case = {
        "expect_tools": ["get_wbs_by_level"],
        "required_args": {"get_wbs_by_level": {"project_id": "proj_002"}},
    }
    calls = [
        {
            "tool": "get_wbs_by_level",
            "args": {"project_id": "proj_001", "level": 2},
            "result": "{}",
        }
    ]
    checks = rpga._check_calls(case, calls, "")
    args_check = next(c for c in checks if c["name"] == "args_get_wbs_by_level")
    assert args_check["pass"] is False
