"""Tests for the basket MCP App, exercised through FastMCP's in-memory Client."""

import asyncio
import json
from typing import Any

import pytest
from fastmcp import Client
from starlette.testclient import TestClient

from cost_intel_app.server import APP_NAME, ENTRY_TOOL, mcp
from cost_intel_ui.fake_data import InMemoryDataSource

MCP_APP_MIME = "text/html;profile=mcp-app"
# The basket is built from fixed lists, so the view binds each row and preset
# by a literal state path rather than by a ForEach variable.
_PRESET_KEYS = ("recommended", "materials", "equipment")
_ROW_COUNT = len(InMemoryDataSource().list_sources())


def run(coro):
    return asyncio.run(coro)


async def _with_client(fn):
    async with Client(mcp) as client:
        return await fn(client)


def _open(project_key: str | None = None) -> dict[str, Any]:
    args = {} if project_key is None else {"project_key": project_key}

    async def call(client):
        result = await client.call_tool(ENTRY_TOOL, args)
        return {
            "text": [c.text for c in result.content],
            "structured": result.structured_content,
        }

    return run(_with_client(call))


def _nodes(tree: Any):
    """Yield every dict in a serialized Prefab tree (components and actions)."""
    if isinstance(tree, dict):
        yield tree
        for value in tree.values():
            yield from _nodes(value)
    elif isinstance(tree, list):
        for item in tree:
            yield from _nodes(item)


def _tool_calls(view: Any) -> dict[str, dict[str, Any]]:
    """Backend tool calls in the view, keyed by their unhashed local name."""
    calls = {}
    for node in _nodes(view):
        if node.get("action") == "toolCall":
            calls[node["tool"].split("_", 1)[1]] = node
    return calls


@pytest.fixture(scope="module")
def opened():
    return _open()


@pytest.fixture(scope="module")
def basket(opened):
    return opened["structured"]["state"]["basket"]


@pytest.fixture(scope="module")
def view(opened):
    return opened["structured"]["view"]


def test_entry_tool_is_registered_with_app_metadata():
    tools = run(_with_client(lambda c: c.list_tools()))
    by_name = {t.name: t for t in tools}
    assert ENTRY_TOOL in by_name
    meta = by_name[ENTRY_TOOL].meta
    assert meta["ui"]["resourceUri"].startswith("ui://prefab/")
    assert meta["ui"]["visibility"] == ["model"]
    assert meta["fastmcp"]["app"] == APP_NAME


def test_backend_tools_are_hidden_from_the_model_listing():
    # The basket is the only model-visible entry point. The PARS panel, draft,
    # and context tools are backend tools; the removed pars_workspace stays gone.
    names = {t.name for t in run(_with_client(lambda c: c.list_tools()))}
    assert names == {ENTRY_TOOL}


def test_ui_resource_is_listed_and_serves_the_renderer():
    async def probe(client):
        tools = await client.list_tools()
        uri = next(t for t in tools if t.name == ENTRY_TOOL).meta["ui"]["resourceUri"]
        resources = {str(r.uri): r for r in await client.list_resources()}
        contents = await client.read_resource(uri)
        return uri, resources, contents

    uri, resources, contents = run(_with_client(probe))
    assert uri in resources
    assert resources[uri].mimeType == MCP_APP_MIME
    assert "<html" in contents[0].text.lower()


def test_output_has_the_basket_rows_and_totals(basket):
    assert basket["title"] == "Recommended PPI escalation basket"
    assert [(r["title"], r["weight"], r["sample_label"]) for r in basket["rows"]] == [
        ("Structural steel", "15", "+18.80%"),
        ("Concrete", "15", "+10.40%"),
        ("Electrical systems", "45", "+11.60%"),
        ("Mechanical / equipment", "25", "+12.10%"),
    ]
    assert basket["total_label"] == "100.00%"
    assert basket["status_label"] == "✓ Precomputed result ready"
    assert basket["approve_enabled"] is True


def test_project_argument_selects_that_projects_basket():
    basket = _open("lanl")["structured"]["state"]["basket"]
    assert [r["weight"] for r in basket["rows"]] == ["25", "25", "25", "25"]


def test_view_renders_rows_from_state(view):
    # Rows are unrolled with literal paths, one per source, not a ForEach.
    dumped = json.dumps(view)
    for i in range(_ROW_COUNT):
        assert f"basket.rows.{i}.title" in dumped
    loops = [n for n in _nodes(view) if n.get("type") == "ForEach"]
    assert not any(n["key"] == "basket.rows" for n in loops)


def test_include_checkboxes_and_weight_inputs_are_bound_to_row_state(view):
    checkboxes = [n for n in _nodes(view) if n.get("type") == "Checkbox"]
    inputs = [
        n
        for n in _nodes(view)
        if n.get("type") == "Input" and n.get("value", "").startswith("{{ basket.rows.")
    ]
    assert checkboxes and inputs
    # A checkbox reads and writes its row through `name`; see the schema test.
    assert {n["name"] for n in checkboxes} == {
        f"basket.rows.{i}.enabled" for i in range(_ROW_COUNT)
    }
    assert {n["value"] for n in inputs} == {
        "{{ basket.rows.%d.weight }}" % i for i in range(_ROW_COUNT)
    }
    assert all(n["inputType"] == "number" for n in inputs)
    editable = [n for n in checkboxes if not n["disabled"]]
    assert editable, "an editable include checkbox is rendered for review"
    change = editable[0]["onChange"]
    assert change[0]["action"] == "setState"
    assert change[0]["key"] == editable[0]["name"]
    assert change[1]["action"] == "setState"
    assert change[1]["key"] == change[0]["key"].replace(".enabled", ".weight")
    assert change[1]["value"] == "0"
    assert change[2]["action"] == "toolCall"
    assert change[2]["tool"].endswith("_update_basket")
    weight_change = next(n for n in inputs if not n["disabled"])["onChange"]
    assert weight_change[0]["action"] == "setState"
    weight_key = weight_change[0]["key"]
    assert weight_key in {f"basket.rows.{i}.weight" for i in range(_ROW_COUNT)}


def test_basket_actions_and_table_bindings_have_no_loop_scoped_templates(view):
    """No action key or argument carries a ForEach variable or an index marker.

    Those resolve per loop in the browser, so the basket binds literal paths.
    """
    for node in _nodes(view):
        if node.get("action") in ("setState", "toolCall"):
            scoped = json.dumps({k: node[k] for k in ("key", "arguments") if k in node})
            assert "_loop" not in scoped and "_idx" not in scoped, scoped
    basket_table = next(n for n in _nodes(view) if n.get("type") == "Table")
    table_text = json.dumps(basket_table)
    assert "_loop" not in table_text and "_idx" not in table_text


def test_basket_view_has_no_loop_scoped_bindings(view):
    """Only PARS project choices may loop; basket controls use literal paths.

    Loop-scoped state/action bindings previously made every basket row show
    the same weight. The independent PARS project options are read-only labels.
    """
    # Project choices now use fixed paths; WBS still uses a separate loop.
    # Basket controls must not share loop-scoped state bindings.
    loops = [n for n in _nodes(view) if n.get("type") == "ForEach"]
    assert all(n.get("key") == "chat_reply.tools" for n in loops)
    for loop in loops:
        assert all(child.get("type") == "Small" for child in loop.get("children", []))
        assert not any("action" in node for node in _nodes(loop))
    # Basket controls are checked separately.


def test_explorer_stats_and_ribbon_are_literal_slots(view):
    dumped = json.dumps(view)
    for i in range(3):
        assert "basket.results.explorer.stats.%d.value" % i in dumped
    for i in range(_ROW_COUNT):
        assert "basket.results.explorer.ribbon.%d.name" % i in dumped


def test_adjustment_math_rows_are_literal_slots(view):
    dumped = json.dumps(view)
    for i in range(_ROW_COUNT):
        assert "basket.results.adjustment.math_rows.%d.label" % i in dumped


def test_blocked_issue_list_has_a_literal_slot_per_listed_issue(view):
    from cost_intel_ui.results_view import MAX_LISTED_ISSUES

    dumped = json.dumps(view)
    for i in range(MAX_LISTED_ISSUES):
        assert "basket.results.explorer.issues.%d" % i in dumped


@pytest.mark.parametrize("project_key", ["y12", "pantex", "lanl"])
def test_preset_and_row_counts_match_what_the_view_binds(project_key):
    basket = _open(project_key)["structured"]["state"]["basket"]
    assert [p["key"] for p in basket["presets"]] == list(_PRESET_KEYS)
    assert len(basket["rows"]) == _ROW_COUNT
    assert len(basket["columns"]) == 5


def test_include_checkbox_value_is_a_boolean_for_the_browser_schema(view):
    """The renderer's Checkbox schema is z.boolean() for `value`.

    prefab_ui 0.21.1 (renderer/app.html) validates each raw node before it
    resolves `{{ }}` templates, so a template string in `value` fails with
    "Invalid <Checkbox> props" on every row. State binding goes through `name`.
    """
    checkboxes = [n for n in _nodes(view) if n.get("type") == "Checkbox"]
    assert checkboxes
    assert all(isinstance(n.get("value", False), bool) for n in checkboxes)


def test_normalize_and_approve_are_present_as_actions(view):
    calls = _tool_calls(view)
    assert {"normalize_basket", "approve_basket", "update_basket"} <= set(calls)
    for name in ("normalize_basket", "approve_basket"):
        assert calls[name]["arguments"] == {
            "project_key": "{{ basket.project_key }}",
            "rows": "{{ basket.rows }}",
            "phase": "{{ basket.phase }}",
            "scenario": "{{ basket.scenario }}",
        }
        assert calls[name]["onSuccess"] == [
            {"action": "setState", "key": "basket", "value": "{{ $result }}"},
            {
                "action": "setState",
                "key": "csv_export",
                "value": {"state": "idle", "message": "", "filename": "", "url": ""},
            },
        ]
    labels = {n.get("label") for n in _nodes(view) if n.get("type") == "Button"}
    assert "Normalize" in labels
    assert "{{ basket.approve_label }}" in labels


def test_presets_are_actions_too(view):
    assert "choose_preset" in _tool_calls(view)
    keys = {
        n["arguments"]["preset_key"]
        for n in _nodes(view)
        if n.get("action") == "toolCall"
        and n.get("tool", "").endswith("_choose_preset")
    }
    assert keys == set(_PRESET_KEYS)


def test_ui_actions_round_trip_through_the_hashed_backend_tools(view, basket):
    calls = _tool_calls(view)
    rows = [dict(r) for r in basket["rows"]]
    rows[0]["enabled"] = False

    async def act(client):
        args = {"project_key": "y12", "rows": rows, "phase": "review"}
        updated = await client.call_tool(calls["update_basket"]["tool"], args)
        normalized = await client.call_tool(calls["normalize_basket"]["tool"], args)
        approve_args = {**args, "rows": basket["rows"]}
        approved = await client.call_tool(calls["approve_basket"]["tool"], approve_args)
        return updated.data, normalized.data, approved.data

    updated, normalized, approved = run(_with_client(act))
    assert updated["total_label"] == "85.00%"
    assert updated["approve_enabled"] is False
    assert normalized["total_label"] == "100.00%"
    assert [r["weight"] for r in normalized["rows"]][1:] == [
        "17.647059",
        "52.941176",
        "29.411765",
    ]
    assert approved["locked"] is True
    assert approved["badge_label"] == "✓ Approved fixture"


def _without_chart_labels(tree: Any) -> Any:
    """Exclude fixed source-catalog labels, not basket state bindings."""
    if isinstance(tree, dict):
        is_chart = tree.get("type") == "AreaChart"
        is_option = tree.get("type") == "SelectOption"
        return {
            k: _without_chart_labels(v)
            for k, v in tree.items()
            if not ((is_chart and k == "series") or (is_option and k == "label"))
        }
    if isinstance(tree, list):
        return [_without_chart_labels(item) for item in tree]
    return tree


def test_data_strings_live_in_state_not_in_the_view(view, basket):
    view_text = json.dumps(_without_chart_labels(view), ensure_ascii=False)
    for row in basket["rows"]:
        assert row["title"] not in view_text
        assert row["series_line"] not in view_text
    assert basket["notice"] not in view_text


def test_output_is_escaped_and_has_no_chat_markup(opened):
    assert opened["text"] == ["[Rendered Prefab UI]"]
    state_text = json.dumps(opened["structured"]["state"], ensure_ascii=False)
    assert "<" not in state_text and ">" not in state_text
    assert "{{" not in state_text
    actions = {n.get("action") for n in _nodes(opened["structured"]["view"])}
    assert "sendMessage" not in actions
    whole = json.dumps(opened["structured"], ensure_ascii=False).lower()
    for marker in ('"messages"', '"role"', '"intent"'):
        assert marker not in whole
    assert opened["structured"]["state"]["show_chat"] is False


def test_results_chart_is_stacked_over_the_listed_sources(view):
    from cost_intel_ui.fake_data import InMemoryDataSource

    charts = [n for n in _nodes(view) if n.get("type") == "AreaChart"]
    assert len(charts) == 1
    keys = [s["dataKey"] for s in charts[0]["series"]]
    expected = [s.component_id for s in InMemoryDataSource().list_sources()]
    assert keys == expected
    assert charts[0]["stacked"] is True


def test_chart_legend_names_each_layer_from_the_source_catalog(view):
    from cost_intel_ui.fake_data import InMemoryDataSource

    chart = [n for n in _nodes(view) if n.get("type") == "AreaChart"][0]
    assert chart["showLegend"] is True
    # Same names the results ribbon shows, so the legend and ribbon agree.
    expected = [
        (s.component_id, s.name, s.color_hex)
        for s in InMemoryDataSource().list_sources()
    ]
    actual = [(s["dataKey"], s["label"], s["color"]) for s in chart["series"]]
    assert actual == expected


def test_results_title_is_bound_once(view):
    dumped = json.dumps(view)
    assert dumped.count("basket.results.explorer.title") == 1


def test_results_subtitle_is_only_bound_when_unblocked(view):
    dumped = json.dumps(view)
    assert dumped.count("basket.results.explorer.subtitle") == 1


def test_blocked_results_list_their_issues(view):
    assert "basket.results.explorer.issues" in json.dumps(view)


def test_results_have_five_tabs_in_order(view):
    titles = [n.get("title") for n in _nodes(view) if n.get("type") == "Tab"]
    assert titles == [
        "Component detail",
        "Adjustment to base",
        "Data & CSV",
        "Evidence & audit",
        "Scenario comparison",
    ]


def test_audit_is_bound_to_current_approval_and_independent_pars_evidence(view):
    dumped = json.dumps(view)
    for key in (
        "basket.project_key",
        "basket.scenario",
        "basket.total_label",
        "pars_context.evidence_label",
        "pars_context.project_id",
        "mapping_review.wbs_code",
        "mapping_review.series_id",
        "mapping_review.rationale",
    ):
        assert key in dumped
    assert "not live BLS observations" in dumped
    assert "no PARS write-back is performed" in dumped


def test_workflow_strip_follows_reference_context_approval_results(view):
    dumped = json.dumps(view)
    for text in ("Review allocation", "Approve allocation", "Explore results"):
        assert text in dumped
    assert "basket.workflow.step1.state" in dumped
    assert "basket.workflow.step3.reason" in dumped


def test_component_history_is_an_unlabeled_line_chart_over_state_rows(view):
    lines = [n for n in _nodes(view) if n.get("type") == "LineChart"]
    assert len(lines) == 1
    assert [s["dataKey"] for s in lines[0]["series"]] == ["value"]
    assert "label" not in lines[0]["series"][0]
    assert "basket.results.component.rows" in json.dumps(lines[0])


def test_data_tab_binds_table_rows_from_state(view):
    dumped = json.dumps(view)
    assert "basket.results.table.rows" in dumped
    assert "basket.results.adjustment.math_rows" in dumped


def test_data_table_binds_its_rows_to_state_without_a_loop(view):
    # One DataTable reads every observation row from state, so the row count
    # is not capped and no ForEach variable is needed.
    tables = [n for n in _nodes(view) if n.get("type") == "DataTable"]
    assert len(tables) == 1
    assert tables[0]["rows"] == "{{ basket.results.table.rows }}"
    assert [c["key"] for c in tables[0]["columns"]] == [
        "period",
        "component_name",
        "allocation_weight",
        "normalized_factor",
        "composite_factor",
    ]
    assert [c["header"] for c in tables[0]["columns"]] == [
        "Period",
        "Component",
        "Weight",
        "Normalized factor",
        "Composite factor",
    ]


def test_table_shows_count_not_the_export_status(view):
    dumped = json.dumps(view)
    assert "basket.results.table.count_label" in dumped
    assert "basket.results.table.status" not in dumped


def test_component_chart_has_no_legend_and_no_unbacked_footnote(view):
    dumped = json.dumps(view)
    chart = [n for n in _nodes(view) if n.get("type") == "LineChart"][0]
    assert chart["showLegend"] is False
    assert "basket.results.component.footnote" not in dumped


def test_adjustment_tab_shows_the_skipped_year_note(view):
    assert "basket.results.adjustment.note" in json.dumps(view)


def test_results_header_shows_the_approved_demo_badge(view):
    labels = [n.get("label") for n in _nodes(view) if n.get("type") == "Badge"]
    assert labels.count("{{ basket.results.explorer.badge_label }}") == 1


def test_results_header_lists_the_meta_chips_from_state(view):
    # Five literal slots, one per chip, so no ForEach variable reaches the view.
    chips = [
        n["label"]
        for n in _nodes(view)
        if n.get("type") == "Badge"
        and str(n.get("label", "")).startswith("{{ basket.results.explorer.meta_chips.")
    ]
    expected = ["{{ basket.results.explorer.meta_chips.%d }}" % i for i in range(5)]
    assert chips == expected


def test_results_have_the_allocation_and_chart_subheads(view):
    dumped = json.dumps(view)
    assert "Allocation basis" in dumped
    assert "Weighted component levels and composite factor" in dumped


def test_adjustment_tab_shows_the_base_year_overview(view):
    dumped = json.dumps(view)
    assert "basket.results.adjustment.source_composite" in dumped
    assert "basket.results.adjustment.adjustment_factor" in dumped


def test_adjustment_tab_draws_the_waterfall_from_state(view):
    charts = [n for n in _nodes(view) if n.get("type") == "WaterfallChart"]
    assert len(charts) == 1
    assert charts[0]["data"] == "{{ basket.results.adjustment.waterfall }}"
    assert charts[0]["dataKey"] == "value"
    assert charts[0]["nameKey"] == "label"
    assert charts[0]["totalKey"] == "total"


def test_comparison_boxes_offer_review_of_their_allocation(view):
    reviews = [
        n
        for n in _nodes(view)
        if n.get("type") == "Button" and n.get("label") == "Review this allocation"
    ]
    assert len(reviews) == len(_PRESET_KEYS)
    assert all(n["onClick"]["tool"].endswith("_choose_preset") for n in reviews)
    assert {n["onClick"]["arguments"]["preset_key"] for n in reviews} == set(
        _PRESET_KEYS
    )


def _select(view, name):
    matches = [
        n for n in _nodes(view) if n.get("type") == "Select" and n.get("name") == name
    ]
    assert len(matches) == 1, name
    return matches[0]


def _assert_explores_on_change(select):
    change = select["onChange"]
    assert change[0]["action"] == "setState"
    assert change[0]["key"] == select["name"]
    assert change[1]["action"] == "setState"
    assert change[1]["key"] == "csv_export"
    assert change[2]["action"] == "toolCall"
    assert change[2]["tool"].endswith("_explore_basket")


def test_explore_is_a_backend_tool_the_view_calls(view):
    assert "explore_basket" in _tool_calls(view)


def test_ribbon_segments_choose_their_component(view):
    picks = {
        n["onClick"]["arguments"]["component"]
        for n in _nodes(view)
        if n.get("type") == "Button"
        and str(n.get("label", "")).startswith("{{ basket.results.explorer.ribbon.")
    }
    expected = {
        "{{ basket.results.explorer.ribbon.%d.component_id }}" % i
        for i in range(_ROW_COUNT)
    }
    assert picks == expected


def test_component_detail_has_a_normalized_and_raw_toggle(view):
    labels = {n.get("label") for n in _nodes(view) if n.get("type") == "Button"}
    assert {"Normalized (%)", "Raw PPI"} <= labels
    modes = {
        n["onClick"]["arguments"]["mode"]
        for n in _nodes(view)
        if n.get("type") == "Button" and n.get("label") in {"Normalized (%)", "Raw PPI"}
    }
    assert modes == {"normalized", "raw"}


def test_source_year_select_offers_the_catalog_years(view, basket):
    from cost_intel_app import basket_state

    select = _select(view, "basket.results.selection.source_year")
    years = list(basket_state.catalog_adjustment_years(InMemoryDataSource()))
    assert [c["value"] for c in select["children"]] == years
    assert select["value"] == "{{ basket.results.selection.source_year }}"
    # Initial baskets are in review; results are computed only after approval.
    assert basket["phase"] == "review"
    assert basket["results"] is None
    _assert_explores_on_change(select)


def test_table_filters_are_selects_that_explore_on_change(view):
    years = ["all", *(f"202{i}" for i in range(1, 7))]
    components = ["all", *(s.component_id for s in InMemoryDataSource().list_sources())]
    expected = {
        "basket.results.selection.table_year": years,
        "basket.results.selection.table_comp": components,
        "basket.results.selection.table_sort": ["asc", "desc"],
    }
    for name, values in expected.items():
        select = _select(view, name)
        assert [c["value"] for c in select["children"]] == values
        _assert_explores_on_change(select)


def test_explore_round_trips_the_chosen_view_through_the_backend(view, basket):
    calls = _tool_calls(view)
    args = {
        "project_key": "y12",
        "rows": [dict(r) for r in basket["rows"]],
        "phase": "approved",
        "scenario": "recommended",
        "component": "steel",
        "mode": "raw",
        "source_year": "2023",
        "table_year": "2024",
        "table_comp": "all",
        "table_sort": "desc",
    }

    async def act(client):
        result = await client.call_tool(calls["explore_basket"]["tool"], args)
        return result.data

    state = run(_with_client(act))
    assert state["results"]["selection"] == {
        "component": "steel",
        "mode": "raw",
        "source_year": "2023",
        "table_year": "2024",
        "table_comp": "all",
        "table_sort": "desc",
    }
    assert state["results"]["table"]["count_label"] == "4 of 24 observations"


def test_root_page_points_to_the_mcp_endpoint():
    with TestClient(mcp.http_app()) as http:
        response = http.get("/")
    assert response.status_code == 200
    assert "/mcp" in response.text


def test_favicon_request_gets_no_content_not_a_404():
    with TestClient(mcp.http_app()) as http:
        response = http.get("/favicon.ico")
    assert response.status_code == 204


def test_the_mcp_endpoint_is_still_mounted_at_mcp():
    with TestClient(mcp.http_app()) as http:
        response = http.get("/mcp")
    assert response.status_code != 404


def test_approved_allocation_can_be_reopened_for_review(view):
    dumped = json.dumps(view)
    assert "Edit approved allocation" in dumped
    assert "reopen_allocation" in _tool_calls(view)
    assert "Prepare CSV" in dumped
    assert "export_analysis_csv" in _tool_calls(view)


def test_dark_theme_visibility_and_analysis_language(view):
    dumped = json.dumps(view)
    assert "!text-slate-100" in dumped
    assert "!text-slate-300" in dumped
    assert "Illustrative project" in dumped
    assert "Demo project" not in dumped


def test_pars_selector_exposes_search_and_name_id_options(view):
    dumped = json.dumps(view)
    assert "Search PARS project names or IDs" in dumped
    assert "pars_projects.choices.0.label" in dumped
    assert "pars_projects.choices.0.parsid" in dumped
    assert "Select a project, then load its read-only context." in dumped
    assert "search_pars_projects" in _tool_calls(view)


def test_pars_project_choices_are_fixed_state_bound_buttons(view):
    from cost_intel_app.server import PARS_PROJECT_SLOTS

    buttons = [
        n
        for n in _nodes(view)
        if n.get("type") == "Button"
        and "pars_projects.choices." in str(n.get("label", ""))
    ]
    assert len(buttons) == PARS_PROJECT_SLOTS
    for i, button in enumerate(buttons):
        assert button["label"] == f"{{{{ pars_projects.choices.{i}.label }}}}"
        assert button["onClick"][0] == {
            "action": "setState",
            "key": "pars_context_input",
            "value": f"{{{{ pars_projects.choices.{i}.parsid }}}}",
        }
    assert not any(
        n.get("type") == "ForEach" and n.get("key") == "pars_projects.rows"
        for n in _nodes(view)
    )


def test_pars_project_slot_list_is_padded_without_fake_projects():
    from cost_intel_app.server import PARS_PROJECT_SLOTS, _project_slots

    slots = _project_slots([{"parsid": "102", "label": "North Plant — 102"}])
    assert len(slots) == PARS_PROJECT_SLOTS
    assert slots[0] == {"visible": True, "parsid": "102", "label": "North Plant — 102"}
    assert all(not slot["visible"] and not slot["parsid"] for slot in slots[1:])


def test_search_pars_projects_filters_names_and_ids(monkeypatch):
    from contextlib import contextmanager

    from cost_intel_app import server as app_module

    @contextmanager
    def local_session():
        yield object()

    def projects(_client):
        return {
            "state": "loaded",
            "rows": [
                {"parsid": "102", "project_name": "North Plant"},
                {"parsid": "103", "project_name": "South Plant"},
            ],
        }

    monkeypatch.setattr(app_module, "_pars_session", local_session)
    monkeypatch.setattr(app_module.pars_panels, "project_list", projects)
    assert app_module.search_pars_projects("north")["rows"] == [
        {"parsid": "102", "label": "North Plant — 102"}
    ]
    assert app_module.search_pars_projects("103")["rows"] == [
        {"parsid": "103", "label": "South Plant — 103"}
    ]
    assert app_module.search_pars_projects("missing")["state"] == "empty"
    assert app_module.search_pars_projects("x" * 101)["state"] == "error"


def test_pars_search_handles_backend_error(monkeypatch):
    from contextlib import contextmanager

    from cost_intel_app import server as app_module

    @contextmanager
    def local_session():
        yield object()

    monkeypatch.setattr(app_module, "_pars_session", local_session)
    monkeypatch.setattr(
        app_module.pars_panels,
        "project_list",
        lambda _client: {"state": "error", "message": "PARS unavailable", "rows": []},
    )
    state = app_module.search_pars_projects()
    assert state["state"] == "error"
    assert "PARS catalog unavailable" in state["message"]


def test_project_navigation_has_visible_active_selection_and_real_calls(view):
    dumped = json.dumps(view, ensure_ascii=False)
    assert "✓" in dumped
    calls = [
        n
        for n in _nodes(view)
        if n.get("action") == "toolCall"
        and n.get("tool", "").endswith("_choose_demo_project")
    ]
    assert {c["arguments"]["project_key"] for c in calls} == {"y12", "pantex", "lanl"}


def test_basket_updates_invalidate_prepared_csv(view):
    """Changing allocation/preset must never leave an older download visible."""
    for call in _tool_calls(view).values():
        if not call["tool"].endswith(
            (
                "_update_basket",
                "_choose_demo_project",
                "_choose_preset",
                "_reopen_allocation",
                "_normalize_basket",
                "_approve_basket",
            )
        ):
            continue
        actions = call["onSuccess"]
        assert [action["key"] for action in actions] == ["basket", "csv_export"]
        assert actions[1]["value"]["state"] == "idle"


def test_pars_load_requires_selected_project(view):
    button = next(
        n
        for n in _nodes(view)
        if n.get("type") == "Button" and n.get("label") == "Load PARS context"
    )
    assert "pars_context_input" in json.dumps(button["disabled"])


def test_component_modes_disable_the_selected_view(view):
    buttons = {
        n["label"]: n
        for n in _nodes(view)
        if n.get("type") == "Button" and n.get("label") in ("Normalized (%)", "Raw PPI")
    }
    assert len(buttons) == 2
    for label in buttons:
        assert "basket.results.selection.mode" in json.dumps(buttons[label]["disabled"])


def test_pars_catalog_is_populated_when_entry_opens(monkeypatch):
    """Project choices must not depend exclusively on a browser tool callback."""
    from cost_intel_app import server as app_module

    monkeypatch.setattr(
        app_module,
        "search_pars_projects",
        lambda query="": {
            "state": "loaded",
            "message": "",
            "rows": [{"parsid": "102", "label": "North Plant — 102"}],
            "choices": app_module._project_slots(
                [{"parsid": "102", "label": "North Plant — 102"}]
            ),
        },
    )
    opened = app_module.ppi_basket()
    assert opened.state["pars_projects"]["choices"][0]["parsid"] == "102"


def test_wbs_choices_have_fixed_browser_bindings(view):
    from cost_intel_app.server import PARS_WBS_SLOTS, _wbs_slots

    buttons = [
        node
        for node in _nodes(view)
        if node.get("type") == "Button"
        and "pars_context.wbs_slots." in str(node.get("label", ""))
    ]
    assert len(buttons) == PARS_WBS_SLOTS
    assert buttons[0]["onClick"][0]["key"] == "mapping_wbs_code"
    assert buttons[0]["onClick"][0]["value"] == (
        "{{ pars_context.wbs_slots.0.wbs_code }}"
    )
    assert len(_wbs_slots([])) == PARS_WBS_SLOTS
    assert not any(
        node.get("type") == "ForEach" and node.get("key") == "pars_context.wbs_choices"
        for node in _nodes(view)
    )


def test_workflow_approved_step_is_explicit(view):
    view_text = json.dumps(view, ensure_ascii=False)
    assert "✓ APPROVED" in view_text


def _relative_luminance(color: str) -> float:
    """WCAG relative luminance for literal hexadecimal colors."""
    values = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    channels = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in values
    ]
    return sum(a * b for a, b in zip(channels, (0.2126, 0.7152, 0.0722)))


def _contrast_ratio(foreground: str, background: str) -> float:
    light, dark = sorted(
        (_relative_luminance(foreground), _relative_luminance(background)),
        reverse=True,
    )
    return (light + 0.05) / (dark + 0.05)


@pytest.mark.parametrize(
    ("foreground", "background"),
    [
        ("#FFFFFF", "#041E42"),  # Shell
        ("#F1F5F9", "#142D4F"),  # Card text (slate-100)
        ("#E2E8F0", "#142D4F"),  # Muted card text (slate-200)
        ("#041E42", "#F4F2F0"),  # Normal button
        ("#041E42", "#D8D5D2"),  # Inactive workflow badge
        ("#FFFFFF", "#285A77"),  # Active workflow badge
        ("#041E42", "#F4F2F0"),  # Disabled button (same pair as the normal button)
        ("#041E42", "#FFFFFF"),  # Input and select
    ],
)
def test_declared_text_background_pairs_meet_wcag_aa(foreground, background):
    assert _contrast_ratio(foreground, background) >= 4.5


def test_dark_cards_override_default_muted_text_styles():
    from cost_intel_app import server as app_module

    for css_class in (app_module.PANE_CARD_CLASS, app_module.EVIDENCE_CARD_CLASS):
        assert "[&_p]:!text-slate-100" in css_class
        assert "[&_small]:!text-slate-200" in css_class
        assert "[&_.text-muted-foreground]:!text-slate-200" in css_class
