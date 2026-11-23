"""Tests for the Recommended PPI escalation basket view model."""

from dataclasses import replace
from decimal import Decimal

import pytest

from cost_intel_ui.basket_view import SCENARIO_LABELS, basket_view
from cost_intel_ui.fake_data import InMemoryDataSource
from cost_intel_ui.session import approve, set_weight, start_session

NOW = "2026-11-13T00:00:00+00:00"


@pytest.fixture
def source():
    return InMemoryDataSource()


@pytest.fixture
def session(source):
    return start_session(source, "y12", session_id=1, now=NOW)


def test_header_badge_and_presets_for_a_fresh_basket(source, session):
    view = basket_view(session, source)
    assert view.title == "Recommended PPI escalation basket"
    assert (view.badge_label, view.badge_tone) == ("Requires approval", "amber")
    assert [(p.label, p.current) for p in view.presets] == [
        ("Recommended", True),
        ("Materials-heavy", False),
        ("Equipment-heavy", False),
    ]


def test_rows_show_series_metadata_type_sample_and_weight(source, session):
    row = basket_view(session, source).rows[0]
    assert row.title == "Structural steel"
    assert row.series_line == "Steel mill products · DEMO-WPU1017"
    assert row.type_label == "PPI"
    assert row.sample_label == "+18.80%"
    assert row.weight == Decimal(15)
    assert not row.checkbox_disabled and not row.weight_disabled


def test_columns_match_the_html_table_header(source, session):
    assert basket_view(session, source).columns == (
        "Use",
        "Component / mock series",
        "Type",
        "2023→2026 sample",
        "Weight %",
    )


def test_valid_preset_enables_approve(source, session):
    view = basket_view(session, source)
    assert view.total_label == "100.00%"
    assert (view.status_label, view.status_tone) == (
        "✓ Precomputed result ready",
        "valid",
    )
    assert view.approve_enabled and view.normalize_enabled
    assert view.approve_label == "Approve & view result →"
    assert view.notice == "Precomputed result available for this basket."


def test_custom_valid_weights_enable_local_approval(source, session):
    custom = set_weight(set_weight(session, 0, Decimal(16)), 1, Decimal(14))
    view = basket_view(custom, source)
    assert (view.status_label, view.status_tone) == (
        "✓ Custom calculation ready",
        "valid",
    )
    assert view.approve_enabled
    assert view.notice.startswith(
        "Custom weights use the local synthetic PPI calculator"
    )


def test_invalid_total_reports_the_100_percent_rule(source, session):
    view = basket_view(set_weight(session, 0, Decimal(10)), source)
    assert view.total_label == "95.00%"
    assert view.status_label == "Weights must equal 100%"
    assert not view.approve_enabled


def test_disabled_row_locks_its_weight_input(source, session):
    view = basket_view(
        replace(
            session, rows=(replace(session.rows[0], enabled=False), *session.rows[1:])
        ),
        source,
    )
    assert view.rows[0].weight_disabled


def test_approved_basket_is_locked(source, session):
    approved = approve(session, source, NOW).session
    view = basket_view(approved, source)
    assert (view.badge_label, view.badge_tone) == ("✓ Approved fixture", "green")
    assert view.approve_label == "✓ Approved"
    assert not view.approve_enabled and not view.normalize_enabled
    assert all(r.checkbox_disabled and r.weight_disabled for r in view.rows)


def test_intro_names_the_project_and_counts_drivers(source, session):
    view = basket_view(session, source)
    assert "Y-12 Site Utility Resilience Upgrade" in view.intro
    assert "four PPI cost drivers" in view.intro


def test_unknown_scenario_key_falls_back_to_the_key_itself():
    assert SCENARIO_LABELS.get("recommended") == "Recommended"


# --- Accessibility and interaction logic for the Streamlit basket screen ---


def test_every_row_input_has_an_accessible_label(source, session):
    row = basket_view(session, source).rows[0]
    assert row.checkbox_label == "Include Structural steel"
    assert row.weight_label == "Allocation percent for Structural steel"


def test_current_preset_is_marked_in_text_not_only_by_color(source, session):
    presets = basket_view(session, source).presets
    assert [p.display_label for p in presets] == [
        "✓ Recommended (current)",
        "Materials-heavy",
        "Equipment-heavy",
    ]


def test_status_carries_a_text_marker_for_each_tone(source, session):
    ready = basket_view(session, source)
    invalid = basket_view(set_weight(session, 0, Decimal(10)), source)
    assert ready.status_label.startswith("✓")
    assert invalid.status_label == "Weights must equal 100%"


def test_weight_widget_values_mirror_session_rows(source, session):
    from cost_intel_ui.basket_view import weight_widget_key, weight_widget_values

    values = weight_widget_values(set_weight(session, 3, None))
    assert values[weight_widget_key(session.id, 0)] == 15.0
    assert values[weight_widget_key(session.id, 3)] is None
    assert weight_widget_key(7, 2) == "basket-7-weight-2"


def test_apply_set_weight_converts_floats_and_blanks(source, session):
    from cost_intel_ui.basket_view import SetWeight, apply_basket_action

    out = apply_basket_action(session, SetWeight(0, 20.0), source, NOW)
    assert out.session.rows[0].weight == Decimal("20.0")
    blank = apply_basket_action(session, SetWeight(0, None), source, NOW)
    assert blank.session.rows[0].weight is None
    nan = apply_basket_action(session, SetWeight(0, float("nan")), source, NOW)
    assert nan.session.rows[0].weight is None


def test_apply_toggle_preset_normalize_approve_and_why(source, session):
    from cost_intel_ui.basket_view import (
        Approve,
        AskWhy,
        ChoosePreset,
        Normalize,
        Toggle,
        apply_basket_action,
    )

    toggled = apply_basket_action(session, Toggle(1, False), source, NOW).session
    assert not toggled.rows[1].enabled
    preset = apply_basket_action(session, ChoosePreset("materials"), source, NOW)
    assert preset.session.scenario == "materials"
    assert preset.toast == "Precomputed materials scenario loaded for review."
    normalized = apply_basket_action(toggled, Normalize(), source, NOW).session
    assert sum(r.weight for r in normalized.rows if r.enabled) == Decimal(100)
    approved = apply_basket_action(session, Approve(), source, NOW)
    assert approved.session.phase == "approved"
    why = apply_basket_action(session, AskWhy(), source, NOW).session
    assert why.messages[-2].text == "Why these PPI indices?"
