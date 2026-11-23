"""PARS explore panels and the basket's PARS context, on the current interface.

The removed ``pars_workspace`` view is no longer a tool. The explore panels run
through the backend tool ``pars_panel``, which the basket does not bind, so these
tests call the tool function directly with the same arguments the panel sends.
Tests that only asserted the removed Prefab layout were dropped; the basket layout
is covered by the basket tests at the end of this file and by
test_pars_third_panel.py.
"""

import asyncio
import contextlib
import json

import pytest
from fastmcp import Client

from cost_intel_app import server as server_module
from cost_intel_app.server import CallRow, mcp
from cost_intel_app.tests.fake_pars import FakeParsMock


@pytest.fixture(autouse=True)
def synthetic_fake(monkeypatch):
    """Panel tests read the synthetic fake; test_pars_live covers the live session."""

    @contextlib.contextmanager
    def session():
        yield FakeParsMock()

    monkeypatch.setattr(server_module, "_pars_session", session)


def _panel_response(panel, value, project_id="100", log=()):
    """The whole pars_panel response, for one request from the explore panel."""
    return server_module.pars_panel(
        project_id=project_id,
        panel=panel,
        value=value,
        log=[CallRow(**row) for row in log],
    )


def _panel_call(panel, value, project_id="100"):
    """The panel state that the request loads."""
    return _panel_response(panel, value, project_id)["panel"]


def test_search_panel_lists_matching_elements():
    state = _panel_call("search", "1")
    assert state["state"] == "loaded"
    assert state["rows"] and all("wbs_code" in row for row in state["rows"])


def test_the_search_rows_carry_each_elements_level():
    state = _panel_call("search", "1")
    assert all(isinstance(row.get("level"), int) for row in state["rows"])


def test_a_blank_search_is_refused_with_a_fixed_message():
    state = _panel_call("search", "  ")
    assert state["state"] == "error"
    assert state["message"] == "Choose a search term."
    assert state["rows"] == []


def test_search_panel_refuses_wildcards_because_the_tool_adds_them():
    for value in ("1%", "a_b"):
        state = _panel_call("search", value)
        assert state["state"] == "error", value
        assert "not allowed" in state["message"], value


def test_lineage_panel_needs_an_element():
    state = _panel_call("lineage", "")
    assert state["state"] == "error"
    assert state["message"] == "Choose an element."


def test_level_panel_needs_a_whole_number():
    state = _panel_call("level", "two")
    assert state["state"] == "error"
    assert state["message"] == "Choose a level from 1 to 8."


def test_run_panel_needs_a_run_id():
    state = _panel_call("run", "  ")
    assert state["state"] == "error"
    assert state["message"] == "Choose a run."


def test_an_unknown_panel_is_refused():
    state = _panel_call("write_back", "")
    assert state["state"] == "error"
    assert state["message"] == "Choose a panel."


def test_levels_outside_one_to_eight_are_refused():
    for value in ("0", "9", "-1", "2.5"):
        state = _panel_call("level", value)
        assert state["message"] == "Choose a level from 1 to 8.", value


def test_refused_requests_never_open_a_pars_session(monkeypatch):
    opened = []

    @contextlib.contextmanager
    def counting_session():
        opened.append(True)
        yield FakeParsMock()

    monkeypatch.setattr(server_module, "_pars_session", counting_session)
    refusals = [
        ("search", "1", ""),
        ("search", "1%", "100"),
        ("search", "a_b", "100"),
        ("search", "  ", "100"),
        ("level", "two", "100"),
        ("level", "0", "100"),
        ("level", "9", "100"),
        ("lineage", "  ", "100"),
        ("run", "", "100"),
        ("nope", "", "100"),
    ]
    for panel, value, project_id in refusals:
        state = _panel_call(panel, value, project_id=project_id)
        assert state["state"] == "error", (panel, value)
    assert opened == []
    # Positive control: a valid request does open a session, so the count is real.
    assert _panel_call("search", "1", project_id="100")["state"] == "loaded"
    assert opened == [True]


def test_a_panel_request_adds_its_calls_to_the_log():
    prior = [{"tool": "get_project_info", "status": "ok"}]
    response = _panel_response("search", "1", log=prior)
    assert response["log"]["state"] == "loaded"
    rows = response["log"]["rows"]
    assert rows[: len(prior)] == prior
    assert {"tool": "search_wbs", "status": "ok"} in rows[len(prior) :]


def test_a_failed_panel_call_is_logged_as_an_error(monkeypatch):
    @contextlib.contextmanager
    def failing_session():
        yield FakeParsMock(fail={"search_wbs"})

    monkeypatch.setattr(server_module, "_pars_session", failing_session)
    response = _panel_response("search", "1")
    assert response["panel"]["state"] == "error"
    assert {"tool": "search_wbs", "status": "error"} in response["log"]["rows"]


def _basket(project_key: str | None = None) -> dict:
    async def open_basket():
        async with Client(mcp) as client:
            args = {} if project_key is None else {"project_key": project_key}
            return (await client.call_tool("ppi_basket", args)).structured_content

    return asyncio.run(open_basket())


def test_basket_context_starts_unlinked_and_has_manual_pars_control():
    opened = _basket()
    assert opened["state"]["pars_context_input"] == ""
    assert opened["state"]["pars_context"]["state"] == "idle"
    dump = json.dumps(opened["view"])
    assert "pars_context_input" in dump
    assert "load_pars_context" in dump
    assert "Suggested indexes are for review, not automatic choices." in dump
    assert "No actual PARS project costs are changed or recalculated." in dump


def test_basket_context_requires_a_manual_project_id():
    from cost_intel_app.server import load_pars_context

    assert load_pars_context(" ")["message"] == "Choose a project."
    assert load_pars_context("x" * 129)["state"] == "error"


def test_basket_context_loads_read_only_synthetic_pars_project():
    from cost_intel_app.server import load_pars_context

    context = load_pars_context("100")
    assert context["state"] == "loaded"
    assert context["project_id"] == "100"
    assert context["name"] == "Demo Synthetic Project"
    assert context["evidence_label"] == "synthetic"
    assert any(row["visible"] for row in context["roots"])
    assert len(context["roots"]) == 3


def test_basket_context_refuses_non_synthetic_source(monkeypatch):
    from cost_intel_app.server import load_pars_context

    class NonSynthetic(FakeParsMock):
        def call(self, tool, arguments):
            result = super().call(tool, arguments)
            if tool == "validate_wbs_inputs":
                result["data_origin"] = "labeled_test_fixture"
            return result

    @contextlib.contextmanager
    def session():
        yield NonSynthetic()

    monkeypatch.setattr(server_module, "_pars_session", session)
    result = load_pars_context("100")
    assert result["state"] == "error"
    assert all(not row["visible"] for row in result["roots"])


def test_basket_has_three_distinct_responsive_panes():
    dump = json.dumps(_basket()["view"])
    assert "Analysis workspace" in dump
    assert "Awaiting basket approval" in dump
    assert "Project context" in dump
    assert "ACTION Cost Intelligence" in dump
    assert "lg:flex-row" in dump
    assert "lg:w-[33%]" in dump
    assert "lg:flex-1" in dump


def _nodes(tree):
    if isinstance(tree, dict):
        yield tree
        for value in tree.values():
            yield from _nodes(value)
    elif isinstance(tree, list):
        for item in tree:
            yield from _nodes(item)


def test_basket_table_fits_narrow_pane_and_results_have_metric_cards():
    view = _basket()["view"]
    table = next(n for n in _nodes(view) if n.get("type") == "Table")
    table_dump = json.dumps(table)
    assert "table-fixed" in table_dump
    headers = [n for n in _nodes(table) if n.get("type") == "TableHead"]
    assert len(headers) == 5
    assert "whitespace-normal" in table_dump
    basket_inputs = [
        n
        for n in _nodes(table)
        if n.get("type") == "Input" and "basket.rows." in json.dumps(n)
    ]
    assert basket_inputs
    assert "w-full min-w-0" in table_dump
    dump = json.dumps(view)
    assert "text-2xl font-semibold tabular-nums" in dump
    assert "basket.results.explorer.stats.0.value" in dump


def test_wbs_bls_candidate_is_verified_read_only_and_never_applied():
    from cost_intel_app.server import review_wbs_bls_mapping

    candidate = review_wbs_bls_mapping(
        "100", "1", "steel", "Structural steel deserves steel-price review."
    )
    assert candidate["state"] == "reviewed"
    assert candidate["project_id"] == "100"
    assert candidate["wbs_code"] == "1"
    assert candidate["series_id"] == "DEMO-WPU1017"
    assert candidate["bls_origin"] == "synthetic_demo"
    selected_root = review_wbs_bls_mapping(
        "100", "1.1", "steel", "Structural materials merit a steel PPI review."
    )
    assert selected_root["state"] == "reviewed"
    assert selected_root["element_title"] == "Materials"
    assert "no PARS records were modified" in candidate["disclaimer"]


def test_wbs_bls_review_refuses_unknown_wbs_or_series():
    from cost_intel_app.server import review_wbs_bls_mapping

    assert (
        review_wbs_bls_mapping(
            "100", "invalid", "steel", "Sample rationale long enough"
        )["state"]
        == "error"
    )
    assert (
        review_wbs_bls_mapping("100", "1", "invalid", "Sample rationale long enough")[
            "state"
        ]
        == "error"
    )


def test_basket_binds_wbs_mapping_and_html_palette():
    opened = _basket()
    state = opened["state"]
    assert state["mapping_review"]["state"] == "idle"
    assert state["mapping_wbs_code"] == ""
    view = json.dumps(opened["view"])
    assert "review_wbs_bls_mapping" in view
    assert "mapping_component" in view
    assert "mapping_rationale" in view
    assert "#041E42" in view
    assert "#285A77" in view
    assert "#D8D5D2" in view
    assert "lg:w-[302px]" in view
    assert "No actual PARS project costs are changed or recalculated." in view
    assert "The price-index charts use sample data, not live BLS figures." in view


def _chat_inputs(view):
    return [
        n
        for n in _nodes(view)
        if n.get("type") == "Input"
        and "Ask about PARS projects" in str(n.get("placeholder", ""))
    ]


def test_chat_input_shares_its_state_key_with_the_examples():
    # Without an explicit name, typed text is kept under the input's own key, so a
    # clicked example (which sets chat_question) cannot replace it. The explicit
    # name makes the field and the examples use one key.
    inputs = _chat_inputs(_basket()["view"])
    assert len(inputs) == 1
    assert inputs[0].get("name") == "chat_question"
    assert "chat_question" in json.dumps(inputs[0].get("value", ""))


def test_chat_examples_set_the_question_without_submitting():
    view = _basket()["view"]
    examples = [
        n
        for n in _nodes(view)
        if n.get("type") == "Button"
        and n.get("label")
        in {"List PARS projects", "WBS for proj_001", "Steel price series"}
    ]
    assert len(examples) == 3
    for button in examples:
        actions = button.get("onClick") or button.get("on_click") or []
        actions = actions if isinstance(actions, list) else [actions]
        assert all(a.get("action") != "callTool" for a in actions), button.get("label")
