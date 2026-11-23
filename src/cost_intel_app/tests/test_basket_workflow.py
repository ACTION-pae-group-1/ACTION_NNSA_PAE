"""Workflow steps and the collapsible evidence panel of the basket app.

Every test here replaces the live PARS session with an unavailable one, so
nothing in this file starts the PARS MCP server. The ``pars_calls`` fixture
counts attempts; tests assert that approval never opens a PARS session.
"""

import asyncio
import json
from contextlib import contextmanager
from typing import Any

import pytest
from fastmcp import Client

from cost_intel_app import pars_live
from cost_intel_app import server as app_module
from cost_intel_app.server import ENTRY_TOOL, mcp, workflow_steps

_RECOMMENDED = ("15", "15", "45", "25")  # Matches the recommended preset.


@pytest.fixture
def pars_calls(monkeypatch):
    """PARS reports unavailable; each attempt to open a session is recorded."""
    calls: list[object] = []

    @contextmanager
    def unavailable(repo, client_factory=None):
        calls.append(repo)
        yield pars_live.LiveParsSession.unavailable(pars_live.NOT_SET)

    monkeypatch.setattr(pars_live, "live_session", unavailable)
    return calls


def _rows(weights, enabled=None):
    flags = enabled or [True] * len(weights)
    return [
        {"enabled": flag, "weight": weight}
        for flag, weight in zip(flags, weights, strict=True)
    ]


def _basket(**changes: Any) -> dict[str, Any]:
    """A basket state with the fields ``workflow_steps`` reads, valid by default."""
    base: dict[str, Any] = {
        "state": "ready",
        "error": "",
        "rows": _rows(_RECOMMENDED),
        "locked": False,
        "total_label": "100.00%",
        "status_tone": "valid",
        "status_label": "✓ Precomputed result ready",
        "approve_enabled": True,
        "results": None,
    }
    base.update(changes)
    return base


def _approved(blocked: bool = False) -> dict[str, Any]:
    results = {"explorer": {"blocked": blocked, "body": "", "title": ""}}
    return _basket(
        locked=True,
        approve_enabled=False,
        status_tone="valid",
        results=results,
    )


def _active(steps: dict[str, Any]) -> list[str]:
    return [
        key for key in ("step1", "step2", "step3") if steps[key]["state"] == "active"
    ]


# --- Step derivation (pure, from basket state) ----------------------------


def test_unavailable_basket_blocks_every_step():
    steps = workflow_steps(_basket(rows=[], error="The allocation is unavailable."))
    assert steps["step1"] == {
        "state": "blocked",
        "available": False,
        "reason": "The allocation is unavailable.",
    }
    assert steps["step2"]["state"] == "blocked"
    assert steps["step3"]["state"] == "blocked"
    assert _active(steps) == []


def test_weights_not_totaling_100_keep_review_current_and_block_approval():
    steps = workflow_steps(
        _basket(
            rows=_rows(("15", "15", "45", "20")),
            total_label="95.00%",
            status_tone="invalid",
            approve_enabled=False,
            status_label="Weights must equal 100%",
        )
    )
    assert _active(steps) == ["step1"]
    assert steps["step1"]["available"] is True
    assert "95.00%" in steps["step1"]["reason"]
    assert steps["step2"]["state"] == "upcoming"
    assert steps["step2"]["available"] is False
    assert steps["step2"]["reason"] == steps["step1"]["reason"]


def test_blank_included_weight_is_named_in_the_reason():
    steps = workflow_steps(
        _basket(rows=_rows(("15", "", "45", "25")), status_tone="invalid")
    )
    assert steps["step1"]["reason"] == "Enter a weight for every included component."


def test_no_included_component_is_named_in_the_reason():
    steps = workflow_steps(
        _basket(
            rows=_rows(("0", "0", "0", "0"), enabled=[False] * 4),
            status_tone="invalid",
            approve_enabled=False,
        )
    )
    assert steps["step1"]["reason"] == "Include at least one component."


def test_valid_weights_without_a_calculator_are_not_approvable():
    steps = workflow_steps(
        _basket(status_tone="invalid", approve_enabled=False, status_label="No calc")
    )
    assert _active(steps) == ["step1"]
    assert steps["step2"]["available"] is False
    assert "calculator" in steps["step2"]["reason"]


def test_valid_review_keeps_step_one_current_until_approval():
    """Step 1 stays the current step through approval; valid weights alone
    don't complete it. The Approve control is still available, independent
    of which step is shown as current."""
    steps = workflow_steps(_basket())
    assert steps["step1"]["state"] == "active"
    assert steps["step1"]["available"] is True
    assert steps["step2"] == {
        "state": "upcoming",
        "available": True,
        "reason": "Approve to calculate the result from these weights.",
    }
    assert steps["step3"]["state"] == "upcoming"
    assert steps["step3"]["available"] is False
    assert steps["badge_label"] == "Not approved"


def test_approved_result_makes_exploration_current():
    steps = workflow_steps(_approved())
    assert steps["step1"]["state"] == "complete"
    assert steps["step1"]["available"] is False  # Edits need Edit approved allocation.
    assert steps["step2"]["state"] == "complete"
    assert steps["step3"] == {
        "state": "active",
        "available": True,
        "reason": "Explore the approved result below.",
    }
    assert steps["badge_label"] == "Approved"


def test_a_blocked_approved_result_is_not_shown_as_usable():
    steps = workflow_steps(_approved(blocked=True))
    assert steps["step2"]["state"] == "blocked"
    assert steps["step3"]["state"] == "blocked"
    assert steps["step3"]["available"] is False
    assert steps["badge_label"] == "Result blocked"
    assert "failed a data check" in steps["step2"]["reason"]


def test_an_approved_basket_without_a_result_is_blocked():
    steps = workflow_steps(_basket(locked=True, approve_enabled=False, results=None))
    assert steps["step2"]["state"] == "blocked"
    assert steps["step3"]["state"] == "blocked"
    assert steps["badge_label"] == "Result blocked"


@pytest.mark.parametrize(
    "basket",
    [
        _basket(),
        _basket(rows=_rows(("15", "15", "45", "20")), status_tone="invalid"),
        _basket(status_tone="invalid", approve_enabled=False),
        _approved(),
        _approved(blocked=True),
        _basket(rows=[], error="unavailable"),
    ],
    ids=["valid", "bad-total", "no-calculator", "approved", "blocked-result", "none"],
)
def test_at_most_one_step_is_current(basket):
    assert len(_active(workflow_steps(basket))) <= 1


def test_approve_control_is_available_while_reviewing_valid_weights():
    """``available`` tracks whether the control is usable, independent of which
    step's badge currently reads "current step" — step 1 stays current here,
    but Approve must still be clickable."""
    steps = workflow_steps(_basket())
    assert steps["step2"]["state"] == "upcoming"
    assert steps["step2"]["available"] is True


def test_approve_control_is_unavailable_once_approved():
    steps = workflow_steps(_approved())
    assert steps["step2"]["state"] == "complete"
    assert steps["step2"]["available"] is False


# --- Through the backend tools (PARS unavailable) -------------------------


def _tool_names() -> dict[str, str]:
    """Backend tool names, keyed by local name, read from the rendered view."""

    async def opened(client):
        result = await client.call_tool(ENTRY_TOOL, {})
        return result.structured_content["view"]

    view = asyncio.run(_with_client(opened))
    names: dict[str, str] = {}
    stack: list[Any] = [view]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            if node.get("action") == "toolCall":
                names[node["tool"].split("_", 1)[1]] = node["tool"]
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return names


async def _with_client(fn):
    async with Client(mcp) as client:
        return await fn(client)


def _call(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    async def go(client):
        return (await client.call_tool(tool_name, arguments)).data

    return asyncio.run(_with_client(go))


def test_approving_a_valid_basket_needs_no_pars_context(pars_calls):
    names = _tool_names()
    pars_calls.clear()
    approved = _call(
        names["approve_basket"],
        {"project_key": "y12", "rows": _rows(_RECOMMENDED), "phase": "review"},
    )
    assert approved["locked"] is True
    assert approved["workflow"]["step3"]["state"] == "active"
    assert pars_calls == []  # Approval never opens a PARS session.


def test_invalid_weights_are_refused_and_stay_in_review(pars_calls):
    names = _tool_names()
    pars_calls.clear()
    refused = _call(
        names["approve_basket"],
        {
            "project_key": "y12",
            "rows": _rows(("15", "15", "45", "20")),
            "phase": "review",
        },
    )
    assert refused["locked"] is False
    assert refused["toast"] == "Selected weights must total 100%."
    assert refused["workflow"]["step2"]["state"] == "upcoming"
    assert pars_calls == []


def test_normalize_totals_exactly_100_and_keeps_step_one_current(pars_calls):
    names = _tool_names()
    normalized = _call(
        names["normalize_basket"],
        {
            "project_key": "y12",
            "rows": _rows(("10", "10", "10", "10")),
            "phase": "review",
        },
    )
    assert normalized["total_label"] == "100.00%"
    assert normalized["approve_enabled"] is True
    assert normalized["workflow"]["step1"]["state"] == "active"
    assert normalized["workflow"]["step2"]["state"] == "upcoming"
    assert normalized["workflow"]["step2"]["available"] is True


def test_editing_after_approval_reopens_review_and_hides_results(pars_calls):
    names = _tool_names()
    approved = _call(
        names["approve_basket"],
        {"project_key": "y12", "rows": _rows(_RECOMMENDED), "phase": "review"},
    )
    assert approved["locked"] is True
    reopened = _call(
        names["reopen_allocation"],
        {"project_key": "y12", "rows": approved["rows"]},
    )
    assert reopened["locked"] is False
    assert reopened["results"] is None
    assert reopened["workflow"]["step1"]["state"] == "active"
    assert reopened["workflow"]["step3"]["state"] == "upcoming"
    assert reopened["workflow"]["step2"]["state"] == "upcoming"


def test_a_changed_row_cannot_slip_past_an_approval(pars_calls):
    names = _tool_names()
    approved = _call(
        names["approve_basket"],
        {"project_key": "y12", "rows": _rows(_RECOMMENDED), "phase": "review"},
    )
    changed = [dict(row) for row in approved["rows"]]
    changed[0]["weight"] = "10"
    still = _call(
        names["update_basket"],
        {
            "project_key": "y12",
            "rows": changed,
            "phase": "approved",
            "scenario": approved["scenario"],
        },
    )
    assert still["locked"] is True
    assert still["toast"] and "approved and locked" in still["toast"]
    assert still["workflow"]["step3"]["state"] == "active"


# --- Collapsible evidence panel --------------------------------------------


def _view(pars_calls) -> dict[str, Any]:
    async def opened(client):
        return (await client.call_tool(ENTRY_TOOL, {})).structured_content

    return asyncio.run(_with_client(opened))["view"]


def _conditions(view, when: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    stack: list[Any] = [view]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            if node.get("type") == "Condition" and any(
                case.get("when") == when for case in node.get("cases", [])
            ):
                found.append(node)
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return found


def _buttons(view, label: str) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    stack: list[Any] = [view]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            if node.get("type") == "Button" and node.get("label") == label:
                found.append(node)
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return found


def test_the_evidence_panel_starts_expanded(pars_calls):
    opened = app_module.ppi_basket()
    assert opened.state["evidence_open"] is True


def test_collapse_and_show_controls_only_change_panel_state(pars_calls):
    view = _view(pars_calls)
    (collapse,) = _buttons(view, "Collapse panel")
    (show,) = _buttons(view, "Show project evidence")
    assert collapse["onClick"] == {
        "action": "setState",
        "key": "evidence_open",
        "value": False,
    }
    assert show["onClick"] == {
        "action": "setState",
        "key": "evidence_open",
        "value": True,
    }
    assert collapse["ariaLabel"] == "Collapse panel: project and evidence (expanded)"
    assert show["ariaLabel"] == "Show project evidence (panel collapsed)"


def test_weight_inputs_share_the_state_key_they_edit(pars_calls):
    """Typed weights must follow server updates (Normalize, presets).

    Binding ``name`` to the row's weight key keeps the browser input in sync with
    state; a value-only binding left typed values stale after a Normalize.
    """
    view = _view(pars_calls)
    weight_inputs = [
        node
        for node in _walk(view)
        if node.get("type") == "Input" and node.get("inputType") == "number"
    ]
    assert weight_inputs
    names = {node["name"] for node in weight_inputs}
    assert names == {f"basket.rows.{i}.weight" for i in range(len(_RECOMMENDED))}


def _walk(tree: Any):
    """Yield every dict in a serialized Prefab tree."""
    stack: list[Any] = [tree]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            yield node
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)


def test_the_panel_body_is_shown_only_while_expanded(pars_calls):
    view = _view(pars_calls)
    (condition,) = _conditions(view, "{{ evidence_open }}")
    expanded = json.dumps(condition["cases"][0]["children"], ensure_ascii=False)
    collapsed = json.dumps(condition["else"], ensure_ascii=False)
    assert "Project & evidence" in expanded
    assert "Show project evidence" not in expanded
    assert "Show project evidence" in collapsed
    assert "Project & evidence" not in collapsed


def test_unselected_and_unloaded_pars_state_is_labelled_plainly(pars_calls):
    view = _view(pars_calls)
    text = json.dumps(view, ensure_ascii=False)
    assert "Not loaded yet. Choose Load PARS context" in text
    assert "Choose a PARS project above to enable loading." in text


# --- Contrast of the step badges (WCAG AA, 4.5:1 for text) -----------------


def _luminance(color: str) -> float:
    values = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    channels = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in values
    ]
    return sum(a * b for a, b in zip(channels, (0.2126, 0.7152, 0.0722), strict=True))


def _ratio(foreground: str, background: str) -> float:
    light, dark = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


@pytest.mark.parametrize(
    ("foreground", "background"),
    [
        ("#041E42", "#CBEBDD"),  # Done badge
        ("#FFFFFF", "#BF0D3E"),  # Blocked badge
        ("#FFFFFF", "#285A77"),  # Current-step badge
        ("#FFFFFF", "#142D4F"),  # Reason text on the evidence card
    ],
)
def test_step_badge_and_reason_colors_meet_wcag_aa(foreground, background):
    assert _ratio(foreground, background) >= 4.5
