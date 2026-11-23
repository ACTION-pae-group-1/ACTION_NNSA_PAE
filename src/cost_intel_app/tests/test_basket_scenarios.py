"""An approved basket stays on its own scenario, not the recommended one."""

import asyncio

import pytest
from fastmcp import Client

from cost_intel_app.basket_state import approve_basket, update_basket
from cost_intel_app.server import ENTRY_TOOL, mcp
from cost_intel_ui.fake_data import InMemoryDataSource

NOW = "2026-11-16T12:00:00Z"


@pytest.fixture
def source():
    return InMemoryDataSource()


def _rows_for(source, key):
    values = dict(source.scenario_weights("y12"))[key]
    return [{"enabled": True, "weight": str(w)} for w in values]


def test_approved_scenario_accepts_its_own_rows(source):
    state = update_basket(
        source, "y12", _rows_for(source, "materials"), "approved", scenario="materials"
    )
    assert state["state"] == "ready"
    assert state["scenario"] == "materials"
    assert state["locked"] is True


def test_approved_scenario_refuses_a_change_and_keeps_that_scenario(source):
    rows = _rows_for(source, "materials")
    rows[0]["weight"] = "36"
    state = update_basket(source, "y12", rows, "approved", scenario="materials")
    assert state["state"] == "error"
    assert state["scenario"] == "materials"
    assert [r["weight"] for r in state["rows"]] == ["35", "30", "20", "15"]
    assert state["locked"] is True


def test_approved_scenario_refuses_another_scenarios_rows(source):
    rows = _rows_for(source, "recommended")
    state = update_basket(source, "y12", rows, "approved", scenario="materials")
    assert state["state"] == "error"
    assert state["scenario"] == "materials"
    assert [r["weight"] for r in state["rows"]] == ["35", "30", "20", "15"]


def test_custom_weights_approve_and_remain_locked(source):
    rows = _rows_for(source, "recommended")
    rows[0]["weight"], rows[1]["weight"] = "16", "14"
    approved = approve_basket(source, "y12", rows, "review", NOW)
    assert approved["state"] == "ready"
    assert approved["locked"] is True
    assert approved["scenario"] == "custom:1:16,1:14,1:45,1:25"
    assert approved["results"]["explorer"]["blocked"] is False
    same = update_basket(source, "y12", rows, "approved", scenario=approved["scenario"])
    assert same["state"] == "ready"
    assert same["results"]["chart"] == approved["results"]["chart"]
    changed = [dict(row) for row in rows]
    changed[0]["weight"] = "17"
    refused = update_basket(
        source, "y12", changed, "approved", scenario=approved["scenario"]
    )
    assert refused["state"] == "error"
    assert refused["rows"][0]["weight"] == "16"
    assert refused["scenario"] == approved["scenario"]


def test_invalid_custom_token_is_refused(source):
    rows = _rows_for(source, "recommended")
    rejected = update_basket(
        source, "y12", rows, "approved", scenario="custom:1:16,1:14,1:45,1:26"
    )
    assert rejected["state"] == "error"


def test_an_unknown_approved_scenario_is_refused(source):
    state = update_basket(
        source, "y12", _rows_for(source, "materials"), "approved", scenario="nope"
    )
    assert state["state"] == "error"
    assert "not available" in state["error"]


def test_approving_a_scenario_records_that_scenario(source):
    state = approve_basket(source, "y12", _rows_for(source, "equipment"), "review", NOW)
    assert state["locked"] is True
    assert state["scenario"] == "equipment"


def test_the_recommended_scenario_still_locks_without_a_scenario_argument(source):
    rows = _rows_for(source, "recommended")
    state = update_basket(source, "y12", rows, "approved")
    assert state["state"] == "ready"
    assert state["scenario"] == "recommended"


def _view_update_tool(view):
    stack = [view]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            if node.get("action") == "toolCall" and node["tool"].endswith(
                "_update_basket"
            ):
                return node["tool"]
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    raise AssertionError("the view has no update_basket call")


def test_the_view_tool_locks_to_the_scenario_it_is_sent(source):
    rows = _rows_for(source, "materials")

    async def call(changed):
        async with Client(mcp) as client:
            opened = await client.call_tool(ENTRY_TOOL, {"project_key": "y12"})
            tool = _view_update_tool(opened.structured_content["view"])
            sent = [dict(r) for r in rows]
            sent[0]["weight"] = "36" if changed else sent[0]["weight"]
            result = await client.call_tool(
                tool,
                {
                    "project_key": "y12",
                    "rows": sent,
                    "phase": "approved",
                    "scenario": "materials",
                },
            )
            return result.data

    same = asyncio.run(call(changed=False))
    assert same["state"] == "ready"
    assert same["scenario"] == "materials"
    refused = asyncio.run(call(changed=True))
    assert refused["state"] == "error"
    assert refused["scenario"] == "materials"
