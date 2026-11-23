"""Tests for chat/quick-prompt routing (ports the HTML's submitQuery)."""

import pytest

from cost_intel_ui.fake_data import InMemoryDataSource
from cost_intel_ui.intents import QUICK_PROMPTS, submit_query
from cost_intel_ui.session import AppState, approve

NOW = "2026-11-13T00:00:00+00:00"


@pytest.fixture
def source():
    return InMemoryDataSource()


def _state(source, approved=False):
    state = AppState().start(source, "y12", now=NOW)
    if approved:
        state = state.replace_active(approve(state.active, source, NOW).session)
    return state


def test_quick_prompts_match_html_labels_and_queries():
    assert [(p.label, p.query) for p in QUICK_PROMPTS] == [
        ("Find PPI indices", "Find relevant cost indices"),
        ("Explain the weights", "Why these weights?"),
        ("Compare scenarios", "Compare cost scenarios"),
        ("View source trail", "Show the audit trail"),
    ]


def test_blank_query_is_ignored(source):
    state = AppState()
    out = submit_query("   ", state, source, now=NOW)
    assert out.state is state


def test_first_query_starts_a_custom_session(source):
    out = submit_query("Escalate my scope", AppState(), source, now=NOW)
    assert out.state.active.project_key == "custom"
    assert out.state.active.scope == "Escalate my scope"


def test_why_routes_to_explanation(source):
    out = submit_query("Why these weights?", _state(source), source, now=NOW)
    assert out.state.active.messages[-2].text == "Why these PPI indices?"


def test_compare_routes_to_comparison_when_approved(source):
    out = submit_query("Compare cost scenarios", _state(source, True), source, NOW)
    assert out.state.active.messages[-1].kind == "compare"


def test_audit_routes_open_the_audit_modal(source):
    out = submit_query("Show the audit trail", _state(source), source, now=NOW)
    assert out.modal == "audit"
    assert out.state.active.messages[-1].text.startswith("The full calculation")


def test_waterfall_switches_tab_only_when_approved(source):
    out = submit_query("show the waterfall", _state(source, True), source, NOW)
    assert out.state.active.detail_tab == "adjustment"
    blocked = submit_query("show the waterfall", _state(source), source, NOW)
    assert blocked.state.active.messages[-1].text.startswith("Approve a basket first")


def test_csv_switches_to_table_tab_when_approved(source):
    out = submit_query("export table", _state(source, True), source, NOW)
    assert out.state.active.detail_tab == "table"


def test_calculate_approves_a_valid_preset(source):
    out = submit_query("calculate the index", _state(source), source, NOW)
    assert out.state.active.phase == "approved"


def test_pars_routes_open_the_pars_modal(source):
    out = submit_query("save to PARS", _state(source), source, now=NOW)
    assert out.modal == "pars"


def test_history_routes_to_previous(source):
    out = submit_query("past projects", _state(source), source, now=NOW)
    assert out.state.active.messages[-1].kind == "previous"


def test_find_indices_with_active_session_falls_back_to_capabilities(source):
    out = submit_query("Find relevant cost indices", _state(source), source, NOW)
    assert out.state.active.messages[-1].text.startswith(
        "In this offline prototype I can demonstrate"
    )
