"""Tests for the PARS panel state builders, using a fake PARS client."""

import pytest

from cost_intel_app import pars_panels as pp


class FakeClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def call(self, tool, arguments):
        self.calls.append((tool, arguments))
        response = self.responses[tool]
        if isinstance(response, Exception):
            raise response
        return response


def guarded(responses):
    fake = FakeClient(responses)
    return pp.GuardedClient(fake), fake


def test_guard_refuses_write_and_run_tools():
    client, fake = guarded({})
    for tool in (
        "write_back_wbs",
        "clean_wbs_data",
        "tune_and_train_wbs",
        "predict_wbs",
        "run_wbs_pipeline",
    ):
        with pytest.raises(pp.ToolNotAllowed):
            client.call(tool, {})
    assert fake.calls == []


def test_read_only_allowlist_has_the_eleven_read_tools():
    assert len(pp.READ_ONLY_TOOLS) == 11
    assert "get_wbs_lineage" in pp.READ_ONLY_TOOLS
    assert "validate_wbs_inputs" in pp.READ_ONLY_TOOLS
    assert "write_back_wbs" not in pp.READ_ONLY_TOOLS


def test_builders_refuse_a_client_without_the_guard():
    raw = FakeClient({"get_project_info": {}})
    with pytest.raises(TypeError):
        pp.project_header(raw, "100")
    with pytest.raises(TypeError):
        pp.evidence(raw)
    assert raw.calls == []


PROJECT = {
    "parsid": "100",
    "project_name": "Demo",
    "total_elements": 42,
    "hierarchy_depth": 4,
}


def test_project_header_loaded():
    client, fake = guarded({"get_project_info": PROJECT})
    panel = pp.project_header(client, "100")
    assert panel["state"] == "loaded"
    assert panel["name"] == "Demo"
    assert panel["total_elements"] == 42
    assert fake.calls == [("get_project_info", {"project_id": "100"})]


def test_project_id_is_sent_stripped():
    client, fake = guarded({"get_project_info": PROJECT})
    pp.project_header(client, "  100 ")
    assert fake.calls == [("get_project_info", {"project_id": "100"})]


def test_pars_error_text_is_replaced_by_a_fixed_message():
    client, _ = guarded({"get_project_info": {"error": "Project 999 not found"}})
    panel = pp.project_header(client, "999")
    assert panel["state"] == "error"
    assert panel["message"] == pp.FAILED_PROJECT
    assert "999" not in panel["message"]


def test_transport_exception_becomes_the_error_state_without_its_text():
    client, _ = guarded({"get_project_info": RuntimeError("socket closed at /secret")})
    panel = pp.project_header(client, "100")
    assert panel["state"] == "error"
    assert panel["message"] == pp.FAILED_PROJECT
    assert "secret" not in panel["message"]


def test_response_missing_a_key_is_an_error_not_a_crash():
    client, _ = guarded({"get_project_info": {"parsid": "100"}})
    assert pp.project_header(client, "100")["state"] == "error"


def test_blank_project_id_is_refused_before_calling_pars():
    client, fake = guarded({})
    assert pp.project_header(client, "   ")["state"] == "error"
    assert fake.calls == []


def test_lineage_keeps_the_element_first_then_ancestors():
    client, _ = guarded(
        {
            "get_wbs_lineage": {
                "lineage": [
                    {"wbs_code": "1.2.3", "title": "Element", "level": 3},
                    {"wbs_code": "1.2", "title": "Parent", "level": 2},
                    {"wbs_code": "1", "title": "Root", "level": 1},
                ]
            }
        }
    )
    panel = pp.lineage(client, "100", "1.2.3")
    assert panel["state"] == "loaded"
    assert [r["wbs_code"] for r in panel["rows"]] == ["1.2.3", "1.2", "1"]


def test_empty_lineage_is_the_empty_state():
    client, _ = guarded({"get_wbs_lineage": {"lineage": []}})
    assert pp.lineage(client, "100", "1.2.3")["state"] == "empty"


def test_lineage_error_response_is_the_error_state():
    client, _ = guarded({"get_wbs_lineage": {"error": "Element not found"}})
    panel = pp.lineage(client, "100", "9.9")
    assert panel["state"] == "error"
    assert panel["message"] == pp.FAILED_LINEAGE


def test_lineage_refuses_a_blank_element_or_project_before_calling():
    client, fake = guarded({})
    assert pp.lineage(client, "100", " ")["message"] == pp.CHOOSE_ELEMENT
    assert pp.lineage(client, " ", "1.2")["message"] == pp.CHOOSE_PROJECT
    assert fake.calls == []


def test_synthetic_origin_shows_the_synthetic_label_and_read_only_views():
    client, _ = guarded(
        {
            "validate_wbs_inputs": {
                "source_db_name": "pars",
                "ok": True,
                "problems": [],
                "tables": ["silver_spae_data"],
                "data_origin": "synthetic_mock",
            }
        }
    )
    panel = pp.evidence(client)
    assert panel["state"] == "loaded"
    assert panel["label"] == "synthetic"
    assert panel["read_only_views"] is True


def test_non_synthetic_origin_hides_the_read_only_views():
    client, _ = guarded(
        {
            "validate_wbs_inputs": {
                "source_db_name": "pars",
                "ok": True,
                "problems": [],
                "tables": ["silver_spae_data"],
                "data_origin": "labeled_test_fixture",
            }
        }
    )
    panel = pp.evidence(client)
    assert panel["label"] == "labeled_test_fixture"
    assert panel["read_only_views"] is False


def test_evidence_error_is_the_error_state_with_views_hidden():
    client, _ = guarded({"validate_wbs_inputs": RuntimeError("boom")})
    panel = pp.evidence(client)
    assert panel["state"] == "error"
    assert panel["message"] == pp.FAILED_EVIDENCE
    assert panel["read_only_views"] is False


def test_hierarchy_returns_the_element_and_one_child_level():
    client, fake = guarded(
        {
            "get_wbs_hierarchy": {
                "element": {
                    "wbs_code": "1.2",
                    "title": "Parent",
                    "level": 2,
                    "parent_wbs": "1",
                    "leaf_node": False,
                },
                "children": [
                    {
                        "element": {
                            "wbs_code": "1.2.1",
                            "title": "Child",
                            "level": 3,
                            "leaf_node": True,
                        },
                        "children": [],
                    }
                ],
            }
        }
    )
    panel = pp.hierarchy(client, "100", "1.2")
    assert panel["state"] == "loaded"
    assert panel["element"]["wbs_code"] == "1.2"
    assert [c["wbs_code"] for c in panel["children"]] == ["1.2.1"]
    assert fake.calls == [
        ("get_wbs_hierarchy", {"project_id": "100", "wbs_code": "1.2"})
    ]


def test_hierarchy_refuses_blank_inputs_before_calling():
    client, fake = guarded({})
    assert pp.hierarchy(client, " ", "1.2")["message"] == pp.CHOOSE_PROJECT
    assert pp.hierarchy(client, "100", " ")["message"] == pp.CHOOSE_ELEMENT
    assert fake.calls == []


def test_hierarchy_error_is_the_error_state():
    client, _ = guarded({"get_wbs_hierarchy": {"error": "WBS code 9 not found"}})
    panel = pp.hierarchy(client, "100", "9")
    assert panel["state"] == "error"
    assert panel["message"] == pp.FAILED_HIERARCHY


def test_hierarchy_missing_key_is_an_error():
    client, _ = guarded(
        {"get_wbs_hierarchy": {"element": {"wbs_code": "1"}, "children": []}}
    )
    assert pp.hierarchy(client, "100", "1")["state"] == "error"


def test_search_passes_only_the_filters_given():
    client, fake = guarded(
        {
            "search_wbs": {
                "elements": [
                    {
                        "wbs_code": "1.2",
                        "title": "Pump",
                        "level": 2,
                        "parent_wbs": "1",
                        "leaf_node": False,
                    }
                ]
            }
        }
    )
    panel = pp.search(client, "100", "  1.2 ", min_level=2)
    assert panel["state"] == "loaded"
    assert panel["rows"][0]["wbs_code"] == "1.2"
    assert fake.calls == [
        ("search_wbs", {"project_id": "100", "wbs_pattern": "1.2%", "min_level": 2})
    ]


def test_search_with_no_matches_is_the_empty_state():
    client, _ = guarded({"search_wbs": {"elements": []}})
    assert pp.search(client, "100", "zzz")["state"] == "empty"


def test_search_refuses_a_blank_project_before_calling():
    client, fake = guarded({})
    panel = pp.search(client, "  ", "pump")
    assert panel["state"] == "error"
    assert panel["message"] == pp.CHOOSE_PROJECT
    assert fake.calls == []


def test_search_error_is_the_error_state():
    client, _ = guarded({"search_wbs": {"error": "min_level must be 1-8"}})
    panel = pp.search(client, "100", "pump", min_level=9)
    assert panel["state"] == "error"
    assert panel["message"] == pp.FAILED_SEARCH


PROJECTS = {
    "projects": [
        {
            "parsid": "100",
            "project_name": "Demo",
            "total_elements": 42,
            "hierarchy_depth": 4,
        }
    ]
}


def test_project_list_is_the_picker_source():
    client, fake = guarded({"list_projects": PROJECTS})
    panel = pp.project_list(client)
    assert panel["state"] == "loaded"
    assert panel["rows"][0]["parsid"] == "100"
    assert fake.calls == [("list_projects", {})]


def test_project_list_with_no_projects_is_the_empty_state():
    client, _ = guarded({"list_projects": {"projects": []}})
    assert pp.project_list(client)["state"] == "empty"


def test_project_list_error_is_the_error_state():
    client, _ = guarded({"list_projects": {"error": "database locked"}})
    panel = pp.project_list(client)
    assert panel["state"] == "error"
    assert panel["message"] == pp.FAILED_PROJECTS


RUN = {
    "run_id": "r1",
    "created_at": "2026-11-15T10:00:00",
    "data_origin": "synthetic_mock",
    "stages": {
        "clean": {"status": "ok", "finished_at": "2026-11-15T10:01:00"},
        "predict": {"status": "stale", "reason": "clean re-run"},
    },
}


def test_run_status_lists_stages_and_labels_synthetic_origin():
    client, fake = guarded({"get_wbs_run_status": RUN})
    panel = pp.run_status(client, "r1")
    assert panel["state"] == "loaded"
    assert panel["label"] == "synthetic"
    assert panel["stages"] == [
        {"stage": "clean", "status": "ok"},
        {"stage": "predict", "status": "stale"},
    ]
    assert fake.calls == [("get_wbs_run_status", {"run_id": "r1"})]


def test_run_status_refuses_a_blank_run_before_calling():
    client, fake = guarded({})
    assert pp.run_status(client, "  ")["message"] == pp.CHOOSE_RUN
    assert fake.calls == []


def test_run_status_error_is_the_error_state():
    client, _ = guarded({"get_wbs_run_status": {"error": "run not found"}})
    panel = pp.run_status(client, "missing")
    assert panel["state"] == "error"
    assert panel["message"] == pp.FAILED_RUN


def test_read_only_data_is_hidden_without_calling_pars():
    client, fake = guarded({})
    panel = pp.read_only_data(client, "descriptions", read_only_views=False)
    assert panel["state"] == "hidden"
    assert fake.calls == []


def test_read_only_data_loads_rows_keyed_by_column_when_allowed():
    client, fake = guarded(
        {
            "get_wbs_project_descriptions": {
                "table": "silver_project_descriptions",
                "columns": ["parsid", "project_name"],
                "total_rows": 1,
                "returned": 1,
                "rows": [{"parsid": "100", "project_name": "Demo"}],
            }
        }
    )
    panel = pp.read_only_data(client, "descriptions", read_only_views=True)
    assert panel["state"] == "loaded"
    assert panel["columns"] == ["parsid", "project_name"]
    assert panel["rows"] == [{"parsid": "100", "project_name": "Demo"}]
    assert fake.calls == [("get_wbs_project_descriptions", {"limit": 20})]


def test_read_only_data_refuses_an_out_of_range_limit_before_calling():
    client, fake = guarded({})
    panel = pp.read_only_data(client, "rows", read_only_views=True, limit=0)
    assert panel["state"] == "error"
    assert fake.calls == []


def test_read_only_data_with_no_rows_is_the_empty_state():
    client, _ = guarded(
        {
            "get_wbs_rows": {
                "table": "silver_spae_data",
                "columns": ["a"],
                "total_rows": 0,
                "returned": 0,
                "rows": [],
            }
        }
    )
    assert pp.read_only_data(client, "rows", read_only_views=True)["state"] == "empty"


def test_read_only_data_error_is_the_error_state():
    client, _ = guarded({"get_wbs_rows": {"error": "source missing"}})
    panel = pp.read_only_data(client, "rows", read_only_views=True)
    assert panel["state"] == "error"
    assert panel["message"] == pp.FAILED_DATA


def test_read_only_data_rejects_an_unknown_source():
    client, _ = guarded({})
    with pytest.raises(ValueError):
        pp.read_only_data(client, "write_back", read_only_views=True)


def test_leaf_nodes_lists_the_leaves_of_a_project():
    client, fake = guarded(
        {
            "get_leaf_nodes": {
                "leaf_nodes": [{"wbs_code": "1.2.1", "title": "Pump", "level": 3}]
            }
        }
    )
    panel = pp.leaf_nodes(client, "100")
    assert panel["state"] == "loaded"
    assert panel["rows"] == [{"wbs_code": "1.2.1", "title": "Pump", "level": 3}]
    assert fake.calls == [("get_leaf_nodes", {"project_id": "100"})]


def test_leaf_nodes_empty_and_error_states():
    client, _ = guarded({"get_leaf_nodes": {"leaf_nodes": []}})
    assert pp.leaf_nodes(client, "100")["state"] == "empty"
    client, _ = guarded({"get_leaf_nodes": {"error": "boom"}})
    panel = pp.leaf_nodes(client, "100")
    assert panel["state"] == "error"
    assert panel["message"] == pp.FAILED_LEAVES


def test_leaf_nodes_refuses_a_blank_project_before_calling():
    client, fake = guarded({})
    assert pp.leaf_nodes(client, " ")["message"] == pp.CHOOSE_PROJECT
    assert fake.calls == []


def test_by_level_passes_the_level_and_rejects_levels_outside_1_to_8():
    client, fake = guarded(
        {
            "get_wbs_by_level": {
                "elements": [{"wbs_code": "1", "title": "Root", "parent_wbs": None}]
            }
        }
    )
    panel = pp.by_level(client, "100", 1)
    assert panel["state"] == "loaded"
    assert panel["rows"][0]["wbs_code"] == "1"
    assert fake.calls == [("get_wbs_by_level", {"project_id": "100", "level": 1})]
    for bad in (0, 9):
        with pytest.raises(ValueError):
            pp.by_level(client, "100", bad)
    with pytest.raises(ValueError):
        pp.by_level(client, "100", "2")  # a string level is a caller error


def test_by_level_error_and_empty_states():
    client, _ = guarded({"get_wbs_by_level": {"elements": []}})
    assert pp.by_level(client, "100", 2)["state"] == "empty"
    client, _ = guarded({"get_wbs_by_level": {"error": "boom"}})
    assert pp.by_level(client, "100", 2)["message"] == pp.FAILED_LEVEL


def test_tool_log_records_each_call_with_its_status():
    fake = FakeClient(
        {
            "list_projects": PROJECTS,
            "get_project_info": RuntimeError("down"),
        }
    )
    log = pp.LoggedClient(pp.GuardedClient(fake))
    log.call("list_projects", {})
    with pytest.raises(RuntimeError):
        log.call("get_project_info", {"project_id": "100"})
    with pytest.raises(pp.ToolNotAllowed):
        log.call("write_back_wbs", {})
    panel = pp.chat_log(log.entries)
    assert panel["state"] == "loaded"
    assert [(r["tool"], r["status"]) for r in panel["rows"]] == [
        ("list_projects", "ok"),
        ("get_project_info", "error"),
        ("write_back_wbs", "refused"),
    ]


def test_chat_log_is_the_empty_state_before_any_call():
    assert pp.chat_log([])["state"] == "empty"


def test_write_back_preview_is_a_draft_and_calls_nothing():
    lines = [{"wbs_code": "1.2.1", "title": "Pump", "proposed_weight": "42.5"}]
    preview = pp.write_back_preview(lines)
    assert preview["state"] == "draft"
    assert preview["rows"] == lines
    assert "Nothing is written" in preview["note"]
    assert pp.write_back_preview([])["state"] == "empty"


def test_run_with_no_stages_is_the_empty_state():
    client, _ = guarded({"get_wbs_run_status": {**RUN, "stages": {}}})
    assert pp.run_status(client, "r1")["state"] == "empty"


def test_run_status_labels_a_non_synthetic_origin_by_its_origin():
    origin = {**RUN, "data_origin": "labeled_test_fixture"}
    client, _ = guarded({"get_wbs_run_status": origin})
    assert pp.run_status(client, "r1")["label"] == "labeled_test_fixture"


@pytest.mark.parametrize("gate", ["yes", {"synthetic": True}, 1, None, [True]])
def test_read_only_data_gate_fails_closed_on_anything_but_true(gate):
    client, fake = guarded({})
    for which in ("descriptions", "rows"):
        panel = pp.read_only_data(client, which, read_only_views=gate)
        assert panel["state"] == "hidden"
    assert fake.calls == []


@pytest.mark.parametrize("limit", [0, 501, "5", None, 1.5, True])
def test_read_only_data_limit_must_be_an_int_from_1_to_500(limit):
    client, fake = guarded({})
    panel = pp.read_only_data(client, "rows", read_only_views=True, limit=limit)
    assert panel["state"] == "error"
    assert fake.calls == []


def test_read_only_data_accepts_the_upper_limit():
    client, fake = guarded(
        {
            "get_wbs_rows": {
                "table": "t",
                "columns": ["a"],
                "total_rows": 0,
                "returned": 0,
                "rows": [],
            }
        }
    )
    panel = pp.read_only_data(client, "rows", read_only_views=True, limit=500)
    assert panel["state"] == "empty"
    assert fake.calls == [("get_wbs_rows", {"limit": 500})]


def test_read_only_data_rejects_rows_that_are_not_mappings():
    client, _ = guarded(
        {
            "get_wbs_rows": {
                "table": "t",
                "columns": ["a", "b"],
                "total_rows": 1,
                "returned": 1,
                "rows": [["a", "b"]],
            }
        }
    )
    panel = pp.read_only_data(client, "rows", read_only_views=True)
    assert panel["state"] == "error"
    assert panel["message"] == pp.FAILED_DATA


def test_project_roots_are_the_top_wbs_level_without_an_element_code():
    client, fake = guarded(
        {
            "get_wbs_by_level": {
                "elements": [{"wbs_code": "1", "title": "Root", "parent_wbs": None}]
            }
        }
    )
    panel = pp.project_roots(client, "100")
    assert panel["state"] == "loaded"
    assert panel["rows"][0]["wbs_code"] == "1"
    assert fake.calls == [("get_wbs_by_level", {"project_id": "100", "level": 1})]


def test_logged_client_marks_a_non_dict_response_as_an_error():
    fake = FakeClient({"list_projects": None})
    log = pp.LoggedClient(pp.GuardedClient(fake))
    log.call("list_projects", {})
    assert log.entries == [{"tool": "list_projects", "status": "error"}]


def test_logged_client_marks_an_error_response_as_an_error():
    fake = FakeClient({"list_projects": {"error": "down"}})
    log = pp.LoggedClient(pp.GuardedClient(fake))
    log.call("list_projects", {})
    assert log.entries == [{"tool": "list_projects", "status": "error"}]


def test_a_refused_tool_inside_a_builder_is_not_hidden():
    class Refusing:
        def call(self, tool, arguments):
            raise pp.ToolNotAllowed("refused")

    with pytest.raises(pp.ToolNotAllowed):
        pp.project_header(pp.GuardedClient(Refusing()), "100")


def test_by_level_rejects_a_boolean_level():
    client, _ = guarded({})
    with pytest.raises(ValueError):
        pp.by_level(client, "100", True)


def test_write_back_preview_takes_no_client():
    import inspect

    assert list(inspect.signature(pp.write_back_preview).parameters) == ["lines"]


def test_project_with_no_elements_is_the_empty_state():
    client, _ = guarded(
        {"get_project_info": {**PROJECT, "total_elements": 0, "hierarchy_depth": 0}}
    )
    assert pp.project_header(client, "100")["state"] == "empty"


def test_evidence_with_no_tables_is_the_empty_state():
    client, _ = guarded(
        {
            "validate_wbs_inputs": {
                "ok": True,
                "problems": [],
                "tables": [],
                "data_origin": "synthetic_mock",
            }
        }
    )
    panel = pp.evidence(client)
    assert panel["state"] == "empty"
    assert panel["read_only_views"] is True


def test_hierarchy_element_without_children_is_the_empty_state():
    client, _ = guarded(
        {
            "get_wbs_hierarchy": {
                "element": {
                    "wbs_code": "1.2.1",
                    "title": "Pump",
                    "level": 3,
                    "parent_wbs": "1.2",
                    "leaf_node": True,
                },
                "children": [],
            }
        }
    )
    panel = pp.hierarchy(client, "100", "1.2.1")
    assert panel["state"] == "empty"
    assert panel["element"]["wbs_code"] == "1.2.1"


def test_search_sends_a_code_prefix_pattern_and_refuses_sql_wildcards():
    client, fake = guarded({"search_wbs": {"elements": []}})
    pp.search(client, "100", "1.2")
    assert fake.calls[-1] == (
        "search_wbs",
        {"project_id": "100", "wbs_pattern": "1.2%"},
    )
    panel = pp.search(client, "100", "1%")
    assert panel["state"] == "error"
    assert panel["message"] == pp.SEARCH_CODES_ONLY
    assert len(fake.calls) == 1


def test_evidence_with_failed_inputs_is_loaded_so_the_problems_show():
    client, _ = guarded(
        {
            "validate_wbs_inputs": {
                "ok": False,
                "problems": ["source database missing"],
                "tables": {},
                "data_origin": "synthetic_mock",
            }
        }
    )
    panel = pp.evidence(client)
    assert panel["state"] == "loaded"
    assert panel["ok"] is False
    assert panel["problems"] == ["source database missing"]


def test_project_without_a_numeric_element_count_is_an_error():
    client, _ = guarded({"get_project_info": {**PROJECT, "total_elements": None}})
    panel = pp.project_header(client, "100")
    assert panel["state"] == "error"
    assert panel["message"] == pp.FAILED_PROJECT


def test_project_with_a_boolean_or_negative_count_is_an_error():
    for bad in (True, False, -1):
        client, _ = guarded({"get_project_info": {**PROJECT, "total_elements": bad}})
        assert pp.project_header(client, "100")["state"] == "error", bad


def test_search_refuses_an_underscore_wildcard_too():
    client, fake = guarded({})
    assert pp.search(client, "100", "1_2")["message"] == pp.SEARCH_CODES_ONLY
    assert fake.calls == []


def test_search_with_only_spaces_sends_no_code_filter():
    client, fake = guarded({"search_wbs": {"elements": []}})
    pp.search(client, "100", "   ")
    assert fake.calls == [("search_wbs", {"project_id": "100"})]


def test_search_keeps_whole_code_segments_not_neighbours():
    rows = [
        {
            "wbs_code": "1.1",
            "title": "A",
            "level": 2,
            "parent_wbs": "1",
            "leaf_node": False,
        },
        {
            "wbs_code": "1.1.2",
            "title": "B",
            "level": 3,
            "parent_wbs": "1.1",
            "leaf_node": True,
        },
        {
            "wbs_code": "1.10",
            "title": "C",
            "level": 2,
            "parent_wbs": "1",
            "leaf_node": False,
        },
    ]
    client, _ = guarded({"search_wbs": {"elements": rows}})
    panel = pp.search(client, "100", "1.1")
    assert [r["wbs_code"] for r in panel["rows"]] == ["1.1", "1.1.2"]


def test_project_header_carries_a_wbs_summary():
    client, _ = guarded({"get_project_info": PROJECT})
    assert pp.project_header(client, "100")["summary"] == "42 elements, 4 levels deep"
    assert pp.project_header(client, " ")["summary"] == ""


def test_source_rows_say_they_span_all_projects():
    client, _ = guarded(
        {
            "get_wbs_rows": {
                "table": "t",
                "columns": ["a"],
                "total_rows": 9,
                "returned": 2,
                "rows": [{"a": 1}, {"a": 2}],
            }
        }
    )
    panel = pp.read_only_data(client, "rows", read_only_views=True)
    assert panel["summary"] == "Showing 2 of 9 rows from all projects."


def test_hidden_and_error_panels_still_carry_every_bound_key():
    client, _ = guarded({"get_wbs_rows": {"error": "boom"}})
    for panel in (
        pp.read_only_data(client, "rows", read_only_views=False),
        pp.read_only_data(client, "rows", read_only_views=True),
    ):
        assert {"state", "message", "summary", "rows", "columns"} <= set(panel)


def test_evidence_with_failed_inputs_and_no_details_says_so():
    failed = {
        "validate_wbs_inputs": {
            "ok": False,
            "problems": [],
            "tables": {},
            "data_origin": "synthetic_mock",
        }
    }
    client, _ = guarded(failed)
    assert pp.evidence(client)["detail"] == "No details were returned."


def test_evidence_with_passing_inputs_has_no_detail():
    passing = {
        "validate_wbs_inputs": {
            "ok": True,
            "problems": [],
            "tables": ["t"],
            "data_origin": "synthetic_mock",
        }
    }
    client, _ = guarded(passing)
    assert pp.evidence(client)["detail"] == ""
