"""Tests for the app shell: left rail, top bar, composer, welcome, screens."""

from cost_intel_ui.fake_data import InMemoryDataSource
from cost_intel_ui.session import AppState
from cost_intel_ui.shell import (
    BRAND,
    COMPOSER,
    SCREENS,
    left_rail,
    mission_view,
    topbar,
    welcome_view,
)

NOW = "2026-11-13T00:00:00+00:00"


def test_brand_matches_html():
    assert BRAND.mark == "∑"
    assert BRAND.eyebrow == "NNSA · PA&E"
    assert BRAND.title == "AI MCP"


def test_left_rail_sections_and_empty_conversation_note():
    source = InMemoryDataSource()
    rail = left_rail(AppState(), source.list_projects())
    assert rail.new_analysis_label == "＋ New analysis"
    assert [s.title for s in rail.sections] == [
        "Your conversations",
        "NNSA example projects",
        "Resources",
    ]
    conversations, examples, resources = rail.sections
    assert conversations.items == ()
    assert conversations.empty_note == "Your analyses appear here."
    assert [i.label for i in examples.items] == [
        "Y-12 utility resilience",
        "Pantex facility renewal",
        "Los Alamos lab expansion",
    ]
    assert [i.action for i in examples.items] == [
        "start:y12",
        "start:pantex",
        "start:lanl",
    ]
    assert [(i.label, i.action) for i in resources.items] == [
        ("Why this matters", "mission"),
        ("Evidence & audit", "audit"),
    ]
    assert rail.footer_eyebrow == "The goal"


def test_left_rail_lists_sessions_and_marks_the_active_one():
    source = InMemoryDataSource()
    state = AppState().start(source, "y12", now=NOW).start(source, "lanl", now=NOW)
    conversations = left_rail(state, source.list_projects()).sections[0]
    assert [(i.label, i.selected) for i in conversations.items] == [
        ("Los Alamos Research Support Building", True),
        ("Y-12 Site Utility Resilience Upgrade", False),
    ]
    assert conversations.items[0].action == "session:2"


def test_topbar_subtitle_tracks_phase_and_contract_state():
    source = InMemoryDataSource()
    assert topbar(None).subtitle == "Talk to your data. Keep the evidence."
    session = AppState().start(source, "y12", now=NOW).active
    assert topbar(session).subtitle == (
        "Y-12 Site Utility Resilience Upgrade · Reviewing proposed indices"
    )
    bar = topbar(session)
    assert bar.title == "Cost Intelligence"
    assert bar.crumb == "/ Escalation Agent"
    assert bar.pill == "● Sample sources available · Offline"


def test_topbar_subtitle_for_approved_and_blocked_results():
    from dataclasses import replace

    source = InMemoryDataSource()
    session = replace(AppState().start(source, "y12", now=NOW).active, phase="approved")
    assert topbar(session).subtitle.endswith("Index result ready")
    assert topbar(session, result_blocked=True).subtitle.endswith(
        "Result blocked · contract error"
    )


def test_composer_copy_matches_html():
    assert COMPOSER.placeholder.startswith("Ask about cost escalation")
    assert COMPOSER.hint == "Ask naturally · Enter to send, Shift+Enter for a new line"
    assert COMPOSER.foot_note.startswith("Offline demonstration")


def test_welcome_view_has_three_steps_and_one_starter_per_project():
    view = welcome_view(InMemoryDataSource().list_projects())
    assert view.title_lines == (
        "Ask a project question.",
        "Get an index you can defend.",
    )
    assert [s.kicker for s in view.steps] == ["01 · ASK", "02 · REVIEW", "03 · EXPLAIN"]
    assert [s.project_key for s in view.starters] == ["y12", "pantex", "lanl"]
    assert view.starters[0].blurb == (
        "Power distribution, steel, foundations, and equipment."
    )


def test_mission_view_has_read_review_audit_units():
    view = mission_view()
    assert view.title == "The mission: explainable cost escalation"
    assert [u.eyebrow for u in view.units] == ["READ", "REVIEW", "AUDIT"]


def test_screen_inventory_covers_every_html_surface():
    assert [s.key for s in SCREENS] == [
        "welcome",
        "basket",
        "results",
        "comparison",
        "audit",
        "pars",
        "mission",
        "context",
    ]


def test_nav_actions_start_activate_reset_and_open_modals():
    from cost_intel_ui.shell import apply_nav_action

    source = InMemoryDataSource()
    state, modal = apply_nav_action(AppState(), "start:pantex", source, NOW)
    assert state.active.project_key == "pantex" and modal is None
    state, _ = apply_nav_action(state, "start:y12", source, NOW)
    state, _ = apply_nav_action(state, "session:1", source, NOW)
    assert state.active.project_key == "pantex"
    assert apply_nav_action(state, "mission", source, NOW)[1] == "mission"
    assert apply_nav_action(state, "audit", source, NOW)[1] == "audit"
    assert apply_nav_action(state, "new", source, NOW)[0].active is None


def test_unknown_nav_action_is_a_no_op():
    from cost_intel_ui.shell import apply_nav_action

    state = AppState()
    assert apply_nav_action(state, "bogus", InMemoryDataSource(), NOW) == (state, None)
