"""Tests for the JSON-safe basket state used by the MCP app."""

from decimal import Decimal

import pytest

from cost_intel_app.basket_state import (
    approve_basket,
    choose_preset,
    initial_basket,
    normalize_basket,
    update_basket,
    weight_text,
)
from cost_intel_ui.fake_data import InMemoryDataSource

NOW = "2026-11-13T00:00:00+00:00"


@pytest.fixture
def source():
    return InMemoryDataSource()


@pytest.fixture
def basket(source):
    return initial_basket(source, "y12")


def _rows(basket, **changes):
    """Rows as the UI sends them back, with per-index overrides."""
    rows = [dict(r) for r in basket["rows"]]
    for key, value in changes.items():
        field, index = key.rsplit("_", 1)
        rows[int(index)][field] = value
    return rows


def _visible(slots):
    """The filled entries of a fixed-slot list, in order."""
    return [slot for slot in slots if slot["visible"]]


def test_initial_rows_match_the_recommended_y12_basket(basket):
    assert [r["title"] for r in basket["rows"]] == [
        "Structural steel",
        "Concrete",
        "Electrical systems",
        "Mechanical / equipment",
    ]
    assert [r["weight"] for r in basket["rows"]] == ["15", "15", "45", "25"]
    assert [r["enabled"] for r in basket["rows"]] == [True] * 4
    assert [r["sample_label"] for r in basket["rows"]] == [
        "+18.80%",
        "+10.40%",
        "+11.60%",
        "+12.10%",
    ]
    first = basket["rows"][0]
    assert first["series_line"] == "Steel mill products · DEMO-WPU1017"
    assert first["type_label"] == "PPI"
    assert first["checkbox_label"] == "Include Structural steel"
    assert first["weight_label"] == "Allocation percent for Structural steel"


def test_initial_header_totals_and_actions(basket):
    assert basket["title"] == "Recommended PPI escalation basket"
    assert basket["project_key"] == "y12"
    assert basket["phase"] == "review"
    assert basket["locked"] is False
    assert (basket["badge_label"], basket["badge_tone"]) == (
        "Requires approval",
        "amber",
    )
    assert basket["columns"] == [
        "Use",
        "Component / mock series",
        "Type",
        "2023→2026 sample",
        "Weight %",
    ]
    assert basket["total_label"] == "100.00%"
    assert (basket["status_label"], basket["status_tone"]) == (
        "✓ Precomputed result ready",
        "valid",
    )
    assert basket["normalize_enabled"] is True
    assert basket["approve_enabled"] is True
    assert basket["approve_label"] == "Approve & view result →"
    assert basket["toast"] is None
    assert [(p["key"], p["label"], p["current"]) for p in basket["presets"]] == [
        ("recommended", "Recommended", True),
        ("materials", "Materials-heavy", False),
        ("equipment", "Equipment-heavy", False),
    ]


def test_other_projects_use_their_own_preset_weights(source):
    assert [r["weight"] for r in initial_basket(source, "pantex")["rows"]] == [
        "30",
        "25",
        "15",
        "30",
    ]


def test_unknown_project_returns_an_error_state(source):
    state = initial_basket(source, "nope")
    assert state["state"] == "error"
    assert state["error"] == "This project has no basket."
    assert "nope" not in state["error"]
    assert state["rows"] == []
    assert state["locked"] is False
    # Same keys as a normal basket, so the view can bind either one.
    assert set(state) == set(initial_basket(source, "y12"))


def test_unchecking_a_row_drops_it_from_the_total(source, basket):
    updated = update_basket(source, "y12", _rows(basket, enabled_0=False), "review")
    assert updated["rows"][0]["enabled"] is False
    assert updated["rows"][0]["weight"] == "0"
    assert updated["rows"][0]["weight_disabled"] is True
    assert updated["rows"][0]["checkbox_disabled"] is False
    assert updated["total_label"] == "85.00%"
    assert (updated["status_label"], updated["status_tone"]) == (
        "Weights must equal 100%",
        "invalid",
    )
    assert updated["approve_enabled"] is False
    assert [p["current"] for p in updated["presets"]] == [False, False, False]


def test_reenabled_row_starts_at_zero_until_a_new_weight_is_entered(source, basket):
    excluded = update_basket(source, "y12", _rows(basket, enabled_0=False), "review")
    rows = [dict(row) for row in excluded["rows"]]
    rows[0]["enabled"] = True
    enabled = update_basket(source, "y12", rows, "review")
    assert enabled["rows"][0]["weight"] == "0"
    assert enabled["total_label"] == "85.00%"
    assert enabled["approve_enabled"] is False


def test_editing_a_weight_accepts_text_and_numbers(source, basket):
    as_text = update_basket(source, "y12", _rows(basket, weight_2="40"), "review")
    as_number = update_basket(source, "y12", _rows(basket, weight_2=40), "review")
    assert as_text["total_label"] == as_number["total_label"] == "95.00%"
    assert as_text["rows"][2]["weight"] == "40"


def test_blank_or_invalid_weight_is_treated_as_missing(source, basket):
    for bad in ("", None, "abc", "nan"):
        updated = update_basket(source, "y12", _rows(basket, weight_1=bad), "review")
        assert updated["rows"][1]["weight"] == ""
        assert updated["total_label"] == "85.00%"
        assert updated["approve_enabled"] is False


def test_switching_to_another_preset_weighting_is_recognized(source, basket):
    rows = _rows(basket, weight_0="35", weight_1="30", weight_2="20", weight_3="15")
    updated = update_basket(source, "y12", rows, "review")
    assert [p["current"] for p in updated["presets"]] == [False, True, False]
    assert updated["approve_enabled"] is True


def test_normalize_rescales_enabled_rows_to_100(source, basket):
    updated = normalize_basket(source, "y12", _rows(basket, enabled_0=False), "review")
    weights = [Decimal(r["weight"]) for r in updated["rows"]]
    assert updated["rows"][0]["weight"] == "0"  # visibly excluded
    assert weights[1:] == [
        Decimal("17.647059"),
        Decimal("52.941176"),
        Decimal("29.411765"),
    ]
    assert updated["total_label"] == "100.00%"
    assert updated["status_label"] == "✓ Custom calculation ready"
    assert updated["approve_enabled"] is True
    assert updated["toast"] == (
        "Allocation normalized. Review the weights, then approve to calculate locally."
    )


def test_normalized_weights_survive_a_round_trip(source, basket):
    normalized = normalize_basket(
        source, "y12", _rows(basket, enabled_0=False), "review"
    )
    again = update_basket(source, "y12", normalized["rows"], "review")
    assert again["status_label"] == "✓ Custom calculation ready"


def test_normalize_with_nothing_selected_explains_why(source, basket):
    rows = _rows(basket, enabled_0=False, enabled_1=False, enabled_2=False)
    rows[3]["enabled"] = False
    updated = normalize_basket(source, "y12", rows, "review")
    assert updated["toast"] == "Include at least one component"


def test_approve_locks_the_basket(source, basket):
    approved = approve_basket(source, "y12", basket["rows"], "review", NOW)
    assert approved["phase"] == "approved"
    assert approved["locked"] is True
    assert approved["approved_at"] == NOW
    assert approved["scenario"] == "recommended"
    assert (approved["badge_label"], approved["badge_tone"]) == (
        "✓ Approved fixture",
        "green",
    )
    assert approved["approve_label"] == "✓ Approved"
    assert approved["approve_enabled"] is False
    assert approved["normalize_enabled"] is False
    assert all(
        r["checkbox_disabled"] and r["weight_disabled"] for r in approved["rows"]
    )
    assert approved["toast"] == "Validated sample result displayed."


def test_approve_refuses_invalid_weights(source, basket):
    refused = approve_basket(
        source, "y12", _rows(basket, enabled_0=False), "review", NOW
    )
    assert refused["phase"] == "review"
    assert refused["locked"] is False
    assert refused["toast"] == "Selected weights must total 100%."


def test_an_approved_non_default_preset_keeps_its_weights(source):
    materials = choose_preset(source, "y12", "materials", "review")
    approved = approve_basket(source, "y12", materials["rows"], "review", NOW)
    assert approved["scenario"] == "materials"
    refreshed = update_basket(source, "y12", approved["rows"], approved["phase"])
    assert [r["weight"] for r in refreshed["rows"]] == ["35", "30", "20", "15"]
    assert refreshed["locked"] is True
    assert all(r["checkbox_disabled"] for r in refreshed["rows"])


def test_choose_preset_loads_weights_and_reopens_review(source, basket):
    approved = approve_basket(source, "y12", basket["rows"], "review", NOW)
    chosen = choose_preset(source, "y12", "equipment", approved["phase"])
    assert [r["weight"] for r in chosen["rows"]] == ["10", "10", "55", "25"]
    assert chosen["phase"] == "review"
    assert chosen["locked"] is False
    assert [p["current"] for p in chosen["presets"]] == [False, False, True]
    assert chosen["toast"] == "Precomputed equipment scenario loaded for review."


def test_wrong_row_count_returns_an_error_state_with_the_recommended_basket(
    source, basket
):
    state = update_basket(source, "y12", basket["rows"][:2], "review")
    assert state["state"] == "error"
    assert state["error"] == (
        "The basket rows do not match this project; showing the recommended basket."
    )
    assert [r["weight"] for r in state["rows"]] == ["15", "15", "45", "25"]


def test_weight_text_is_plain_and_bounded():
    assert weight_text(Decimal("15")) == "15"
    assert weight_text(Decimal("100")) == "100"
    assert weight_text(Decimal(100) / 3) == "33.333333"
    assert weight_text(None) == ""


def test_state_is_json_safe_and_contains_no_markup_or_templates(basket):
    import json

    text = json.dumps(basket, ensure_ascii=False)
    assert "<" not in text and ">" not in text
    assert "{{" not in text and "}}" not in text


def test_current_preset_is_marked_in_text(basket):
    assert [p["display_label"] for p in basket["presets"]] == [
        "✓ Recommended (current)",
        "Materials-heavy",
        "Equipment-heavy",
    ]


def test_state_has_no_chat_fields(basket):
    # The host's model owns the conversation: no chat transcript, no assistant
    # narration ("I reviewed the ... scope"), and no ask-why chat link.
    assert not {"messages", "chat", "intent", "role", "intro", "why_link"} & set(basket)


def test_review_basket_has_no_results(basket):
    assert basket["results"] is None


def test_approved_basket_shows_the_recommended_result(source, basket):
    approved = approve_basket(source, "y12", _rows(basket), "review", NOW)
    results = approved["results"]
    assert results["explorer"]["blocked"] is False
    labels = [s["label"] for s in results["explorer"]["stats"]]
    assert labels[:2] == ["Base factor", "2026 composite factor"]
    assert results["comparison"]["boxes"][0]["approved"] is True
    assert [b["approved"] for b in results["comparison"]["boxes"]] == [
        True,
        False,
        False,
    ]


def test_chart_heights_sum_to_the_composite_factor(source, basket):
    approved = approve_basket(source, "y12", _rows(basket), "review", NOW)
    chart = approved["results"]["chart"]
    assert len(chart) == 6
    for row in chart:
        total = sum(v for k, v in row.items() if k not in ("period", "composite"))
        assert total == pytest.approx(row["composite"], abs=1e-4)


def test_every_project_result_uses_only_listed_sources(source):
    source_ids = {s.component_id for s in source.list_sources()}
    for project in source.list_projects():
        for key in source.scenario_weights(project.key):
            packet = source.get_result(project.key, key)
            ids = {c["component_id"] for c in packet.result["components"]}
            assert ids <= source_ids, (project.key, key)


def test_update_in_approved_phase_finds_the_matching_scenario(source):
    materials = source.scenario_weights("y12")["materials"]
    rows = [{"enabled": True, "weight": str(w)} for w in materials]
    state = update_basket(source, "y12", rows, "approved")
    assert state["scenario"] == "materials"
    approved = [b["approved"] for b in state["results"]["comparison"]["boxes"]]
    assert approved == [False, True, False]


def test_blocked_result_keeps_the_same_fields_and_lists_issues(source):
    from cost_intel_ui.data_access import ResultPacket

    class BrokenSource(type(source)):
        def get_result(self, project_key, scenario_key):
            packet = super().get_result(project_key, scenario_key)
            result = {k: v for k, v in packet.result.items() if k != "composite_points"}
            return ResultPacket(result=result, presentation=packet.presentation)

    recommended = source.scenario_weights("y12")["recommended"]
    rows = [{"enabled": True, "weight": str(w)} for w in recommended]
    state = update_basket(BrokenSource(), "y12", rows, "approved")
    explorer = state["results"]["explorer"]
    assert explorer["blocked"] is True
    assert [issue for issue in explorer["issues"] if issue]
    assert explorer["subtitle"] == ""
    assert _visible(explorer["stats"]) == []
    assert _visible(explorer["ribbon"]) == []
    assert state["results"]["chart"] == []


def _approved_y12(source, basket):
    return approve_basket(source, "y12", _rows(basket), "review", NOW)["results"]


def test_approved_results_include_the_selected_component_history(source, basket):
    component = _approved_y12(source, basket)["component"]
    assert component["component_id"] == "electric"
    assert component["title"].startswith("Electrical equipment")
    assert len(component["rows"]) == 6
    assert component["rows"][0]["period"] == "2021"
    assert all(isinstance(r["value"], float) for r in component["rows"])


def test_approved_results_include_the_latest_adjustment_to_base(source, basket):
    from cost_intel_ui.results_view import eligible_adjustment_years

    packet = source.get_result("y12", "recommended")
    adjustment = _approved_y12(source, basket)["adjustment"]
    assert adjustment["year"] == eligible_adjustment_years(packet)[-1]
    assert adjustment["source_year"] == adjustment["year"]
    assert adjustment["math_rows"]
    assert adjustment["message"] == ""


def test_approved_results_include_the_observation_table(source, basket):
    packet = source.get_result("y12", "recommended")
    table = _approved_y12(source, basket)["table"]
    assert table["columns"][0] == "period"
    assert len(table["rows"]) == len(packet.presentation["table_rows"])


def test_blocked_results_have_no_tab_content(source):
    from cost_intel_ui.data_access import ResultPacket

    class BrokenSource(type(source)):
        def get_result(self, project_key, scenario_key):
            packet = super().get_result(project_key, scenario_key)
            result = {k: v for k, v in packet.result.items() if k != "composite_points"}
            return ResultPacket(result=result, presentation=packet.presentation)

    recommended = source.scenario_weights("y12")["recommended"]
    rows = [{"enabled": True, "weight": str(w)} for w in recommended]
    results = update_basket(BrokenSource(), "y12", rows, "approved")["results"]
    assert results["component"] is None
    assert results["adjustment"] is None
    assert results["table"] is None


def _packet_with_presentation(source, edit):
    """A fixture packet whose presentation is changed by ``edit``."""
    from cost_intel_ui.data_access import ResultPacket

    class EditedSource(type(source)):
        def get_result(self, project_key, scenario_key):
            packet = super().get_result(project_key, scenario_key)
            presentation = edit(dict(packet.presentation))
            return ResultPacket(result=packet.result, presentation=presentation)

    recommended = source.scenario_weights("y12")["recommended"]
    rows = [{"enabled": True, "weight": str(w)} for w in recommended]
    return update_basket(EditedSource(), "y12", rows, "approved")["results"]


def test_malformed_table_row_fails_only_the_table_tab(source):
    def drop_display_order(presentation):
        presentation["table_rows"] = [
            {k: v for k, v in r.items() if k != "display_order"}
            for r in presentation["table_rows"]
        ]
        return presentation

    results = _packet_with_presentation(source, drop_display_order)
    assert results["explorer"]["blocked"] is False
    assert results["table"]["rows"] == []
    assert results["table"]["message"] != ""
    assert _visible(results["adjustment"]["math_rows"])


def test_malformed_adjustment_step_fails_only_the_adjustment_tab(source):
    def bad_contribution(presentation):
        adjustments = {
            k: dict(v) for k, v in presentation["adjustments_by_year"].items()
        }
        latest = max(adjustments)
        steps = [dict(s) for s in adjustments[latest]["steps"]]
        steps[0]["adjustment_contribution"] = "not-a-number"
        adjustments[latest]["steps"] = steps
        presentation["adjustments_by_year"] = adjustments
        return presentation

    results = _packet_with_presentation(source, bad_contribution)
    assert results["explorer"]["blocked"] is False
    assert _visible(results["adjustment"]["math_rows"]) == []
    assert results["adjustment"]["waterfall"] == []
    assert results["adjustment"]["message"] != ""
    assert results["table"]["rows"]


def test_table_state_has_a_count_and_no_display_headers(source, basket):
    # Column headers are fixed labels in the DataTable, so the state has none.
    table = _approved_y12(source, basket)["table"]
    assert "headers" not in table
    assert table["count_label"] == "24 of 24 observations"
    assert table["message"] == ""


def test_adjustment_names_a_skipped_latest_year(source):
    def drop_latest_steps(presentation):
        adjustments = {
            k: dict(v) for k, v in presentation["adjustments_by_year"].items()
        }
        latest = max(adjustments)
        adjustments[latest]["steps"] = []
        presentation["adjustments_by_year"] = adjustments
        return presentation

    adjustment = _packet_with_presentation(source, drop_latest_steps)["adjustment"]
    assert adjustment["year"] == "2025"
    assert "2026" in adjustment["note"]
    assert "2025" in adjustment["note"]


def test_component_rows_are_the_normalized_series(source, basket):
    from cost_intel_ui.results_view import component_detail

    packet = source.get_result("y12", "recommended")
    detail = component_detail(packet, "electric", "normalized")
    component = _approved_y12(source, basket)["component"]
    expected = [
        {"period": str(y), "value": v} for y, v in zip(detail.years, detail.values)
    ]
    assert component["rows"] == expected


def test_adjustment_math_rows_match_the_shared_view(source, basket):
    from cost_intel_ui.results_view import adjustment_view, eligible_adjustment_years

    packet = source.get_result("y12", "recommended")
    year = eligible_adjustment_years(packet)[-1]
    view = adjustment_view(packet, year)
    expected = [{"label": label, "value": value} for label, value in view.math_rows]
    rows = _visible(_approved_y12(source, basket)["adjustment"]["math_rows"])
    assert [{"label": r["label"], "value": r["value"]} for r in rows] == expected


def test_table_rows_match_the_shared_view(source, basket):
    from cost_intel_ui.results_view import table_view

    packet = source.get_result("y12", "recommended")
    view = table_view(packet, "all", "all", "asc")
    table = _approved_y12(source, basket)["table"]
    assert table["rows"][0] == dict(zip(view.columns, view.rows[0], strict=True))
    assert len(table["rows"]) == len(view.rows)


def test_comparison_boxes_carry_the_preset_key_to_review(source, basket):
    boxes = _approved_y12(source, basket)["comparison"]["boxes"]
    assert {b["key"] for b in boxes} == {"recommended", "materials", "equipment"}


def test_approved_results_carry_the_badge_and_meta_chips(source, basket):
    explorer = _approved_y12(source, basket)["explorer"]
    assert explorer["badge_label"] == "✓ Analysis approved"
    assert len(explorer["meta_chips"]) == 5
    assert explorer["meta_chips"][0].startswith("Base year 2023")


def test_adjustment_waterfall_runs_from_100_to_the_adjustment_factor(source, basket):
    adjustment = _approved_y12(source, basket)["adjustment"]
    bars = adjustment["waterfall"]
    assert bars[0] == {"label": "Source year", "value": 100.0, "total": True}
    assert bars[-1]["label"] == "To base"
    assert bars[-1]["total"] is True
    assert bars[-1]["value"] == pytest.approx(
        float(adjustment["adjustment_factor"]) * 100, abs=1e-6
    )
    steps = bars[1:-1]
    assert steps and not any(b["total"] for b in steps)
    running = bars[0]["value"] + sum(b["value"] for b in steps)
    assert running == pytest.approx(bars[-1]["value"], abs=1e-6)


def test_adjustment_overview_carries_the_source_composite_and_factor(source, basket):
    adjustment = _approved_y12(source, basket)["adjustment"]
    assert adjustment["source_composite"] != ""
    assert adjustment["adjustment_factor"] != ""


WEIGHT_ERROR = "Weights must be from 0 to 100 with at most six decimal places."
APPROVED_ERROR = "This basket is approved and locked. Choose a preset to change it."


def _run(builder, source, rows, phase):
    if builder == "update":
        return update_basket(source, "y12", rows, phase)
    if builder == "normalize":
        return normalize_basket(source, "y12", rows, phase)
    return approve_basket(source, "y12", rows, phase, NOW)


@pytest.mark.parametrize(
    "bad", ["1e30", "-1e30", "100.5", "-0.5", "1.0000001", "1e-30"]
)
def test_out_of_range_or_over_precise_weight_is_refused(source, basket, bad):
    state = update_basket(source, "y12", _rows(basket, weight_0=bad), "review")
    assert state["state"] == "error"
    assert state["error"] == WEIGHT_ERROR
    assert state["toast"] == WEIGHT_ERROR
    assert state["rows"][0]["weight"] == ""
    # The other rows keep the user's edits.
    assert [r["weight"] for r in state["rows"][1:]] == ["15", "45", "25"]


@pytest.mark.parametrize("builder", ["update", "normalize", "approve"])
def test_every_builder_refuses_an_oversized_weight_without_raising(
    source, basket, builder
):
    state = _run(builder, source, _rows(basket, weight_0="1e30"), "review")
    assert state["state"] == "error"
    assert state["error"] == WEIGHT_ERROR


@pytest.mark.parametrize("ok", ["0", "100", "12.5", "15.000000"])
def test_weights_at_the_edges_of_the_percent_range_are_accepted(source, basket, ok):
    state = update_basket(source, "y12", _rows(basket, weight_0=ok), "review")
    assert state["state"] == "ready"
    assert state["error"] == ""
    assert state["rows"][0]["weight"] == weight_text(Decimal(ok))


def test_weight_text_is_safe_for_values_it_cannot_represent():
    assert weight_text(Decimal("1e30")) == ""
    assert weight_text(Decimal("-1e30")) == ""
    assert weight_text(Decimal("Infinity")) == ""
    assert weight_text(Decimal("NaN")) == ""


@pytest.mark.parametrize("builder", ["update", "normalize", "approve"])
def test_approved_basket_refuses_a_changed_weight(source, basket, builder):
    approved = approve_basket(source, "y12", basket["rows"], "review", NOW)
    changed = _rows(approved, weight_0="20", weight_1="20")
    state = _run(builder, source, changed, "approved")
    assert state["state"] == "error"
    assert state["error"] == APPROVED_ERROR
    assert state["phase"] == "approved"
    assert state["locked"] is True
    assert [r["weight"] for r in state["rows"]] == ["15", "15", "45", "25"]
    assert [r["enabled"] for r in state["rows"]] == [True] * 4
    assert state["results"] is not None


def test_approved_basket_refuses_an_excluded_row(source, basket):
    approved = approve_basket(source, "y12", basket["rows"], "review", NOW)
    state = update_basket(source, "y12", _rows(approved, enabled_3=False), "approved")
    assert state["state"] == "error"
    assert state["locked"] is True
    assert [r["enabled"] for r in state["rows"]] == [True] * 4


def test_unknown_preset_shows_a_toast_and_keeps_the_basket(source, basket):
    state = choose_preset(source, "y12", "nope", "review")
    assert state["toast"] == "That allocation is not available for this project."
    assert state["state"] == "ready"
    assert state["phase"] == "review"
    assert [r["weight"] for r in state["rows"]] == [r["weight"] for r in basket["rows"]]


def test_unknown_preset_keeps_an_approved_basket_locked(source, basket):
    approve_basket(source, "y12", basket["rows"], "review", NOW)
    state = choose_preset(source, "y12", "nope", "approved")
    assert state["toast"] == "That allocation is not available for this project."
    assert state["phase"] == "approved"
    assert state["locked"] is True
    assert [r["weight"] for r in state["rows"]] == ["15", "15", "45", "25"]
