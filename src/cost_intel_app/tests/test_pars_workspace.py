"""Tests for the PARS workspace state: every panel gathered from one client."""

from cost_intel_app import pars_panels as pp
from cost_intel_app.pars_workspace import workspace_state
from cost_intel_app.tests.fake_pars import FakeParsMock


def test_synthetic_source_loads_every_panel_and_logs_each_call():
    client = pp.LoggedClient(FakeParsMock())
    state = workspace_state(client, "100")
    assert state["header"]["state"] == "loaded"
    assert state["evidence"]["label"] == "synthetic"
    assert state["roots"]["state"] == "loaded"
    assert state["descriptions"]["state"] == "loaded"
    assert state["rows"]["state"] == "loaded"
    tools = [e["tool"] for e in client.entries]
    assert "get_project_info" in tools
    assert "get_wbs_rows" in tools
    assert all(e["status"] == "ok" for e in client.entries)


def test_non_synthetic_source_hides_the_read_only_views():
    class Fixture(FakeParsMock):
        def call(self, tool, arguments):
            response = super().call(tool, arguments)
            if tool == "validate_wbs_inputs":
                response["data_origin"] = "labeled_test_fixture"
            return response

    client = pp.LoggedClient(Fixture())
    state = workspace_state(client, "100")
    assert state["evidence"]["read_only_views"] is False
    assert state["descriptions"]["state"] == "hidden"
    assert state["rows"]["state"] == "hidden"
    assert all(e["tool"] != "get_wbs_rows" for e in client.entries)


def test_one_failing_panel_does_not_hide_the_others():
    client = pp.LoggedClient(FakeParsMock(fail={"get_project_info"}))
    state = workspace_state(client, "100")
    assert state["header"]["state"] == "error"
    assert state["roots"]["state"] == "loaded"
    assert state["evidence"]["state"] == "loaded"


def test_the_log_has_one_entry_per_call_in_this_render():
    client = pp.LoggedClient(FakeParsMock())
    workspace_state(client, "100")
    assert {e["status"] for e in client.entries} == {"ok"}
    log = pp.chat_log(client.entries)
    assert log["state"] == "loaded"
    assert len(log["rows"]) == len(client.entries)


def _bound(state):
    """Every dotted path the Prefab view binds from pars state."""
    paths = [
        ("header", "state"),
        ("header", "message"),
        ("header", "name"),
        ("header", "summary"),
        ("evidence", "state"),
        ("evidence", "message"),
        ("evidence", "label"),
        ("evidence", "ok"),
        ("evidence", "problems"),
        ("evidence", "detail"),
        ("roots", "state"),
        ("roots", "rows"),
        ("roots", "message"),
        ("descriptions", "state"),
        ("descriptions", "rows"),
        ("descriptions", "message"),
        ("descriptions", "summary"),
        ("rows", "state"),
        ("rows", "rows"),
        ("rows", "message"),
        ("rows", "summary"),
        ("log", "state"),
        ("log", "rows"),
    ]
    missing = []
    for panel, key in paths:
        if key not in state[panel]:
            missing.append(f"{panel}.{key}")
    return missing


def test_every_bound_key_exists_in_the_synthetic_case():
    assert _bound(workspace_state(pp.LoggedClient(FakeParsMock()), "100")) == []


def test_every_bound_key_exists_when_panels_fail_or_are_hidden():
    failing = pp.LoggedClient(FakeParsMock(fail={"get_project_info", "get_wbs_rows"}))
    assert _bound(workspace_state(failing, "100")) == []

    class Fixture(FakeParsMock):
        def call(self, tool, arguments):
            response = super().call(tool, arguments)
            if tool == "validate_wbs_inputs":
                response["data_origin"] = "labeled_test_fixture"
            return response

    assert _bound(workspace_state(pp.LoggedClient(Fixture()), "100")) == []


def test_header_carries_the_evidence_label_even_when_the_header_fails():
    ok = workspace_state(pp.LoggedClient(FakeParsMock()), "100")
    failed = workspace_state(
        pp.LoggedClient(FakeParsMock(fail={"get_project_info"})), "100"
    )
    assert ok["header"]["label"] == ok["evidence"]["label"] == "synthetic"
    assert failed["header"]["label"] == "synthetic"


class EmptyList(FakeParsMock):
    def call(self, tool, arguments):
        if tool == "list_projects":
            return {"projects": []}
        return super().call(tool, arguments)


def test_a_blank_project_opens_the_first_project_from_the_list():
    state = workspace_state(pp.LoggedClient(FakeParsMock()), "")
    assert state["project_id"] == "100"
    assert state["header"]["state"] == "loaded"
    assert state["header"]["name"] == "Demo Synthetic Project"
    assert state["roots"]["state"] == "loaded"


def test_a_blank_project_with_no_projects_asks_for_one():
    state = workspace_state(pp.LoggedClient(EmptyList()), "")
    assert state["project_id"] == ""
    assert state["header"]["message"] == pp.CHOOSE_PROJECT


def test_a_blank_project_when_the_list_fails_says_the_list_failed():
    state = workspace_state(pp.LoggedClient(FakeParsMock(fail={"list_projects"})), "")
    assert state["project_id"] == ""
    assert state["header"]["state"] == "error"
    assert state["header"]["message"] == pp.FAILED_PROJECTS
    assert {"name", "summary", "label"} <= set(state["header"])


def test_explore_panels_start_idle_and_load_only_on_request():
    client = pp.LoggedClient(FakeParsMock())
    state = workspace_state(client, "100")
    assert set(state["panels"]) == {"search", "lineage", "leaves", "level", "run"}
    assert all(panel["state"] == "idle" for panel in state["panels"].values())
    assert {"search", "lineage", "level", "run"} <= set(state["inputs"])
    called = {entry["tool"] for entry in state["log"]["rows"]}
    assert not called & {
        "search_wbs",
        "get_wbs_lineage",
        "get_leaf_nodes",
        "get_wbs_run_status",
    }
    # get_wbs_by_level is also used by the roots panel on load, so it is not checked.


def test_the_load_calls_the_level_tool_only_for_the_roots_panel():
    state = workspace_state(pp.LoggedClient(FakeParsMock()), "100")
    calls = [entry["tool"] for entry in state["log"]["rows"]]
    assert calls.count("get_wbs_by_level") == 1
