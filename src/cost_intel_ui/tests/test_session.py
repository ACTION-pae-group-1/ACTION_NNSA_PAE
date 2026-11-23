"""Tests for pure analysis-session transitions (mirrors the HTML's JS state)."""

from decimal import Decimal

import pytest

from cost_intel_ui.data_access import ResultPacket
from cost_intel_ui.fake_data import InMemoryDataSource
from cost_intel_ui.session import (
    AppState,
    BasketRow,
    approve,
    ask_why,
    compare,
    custom_scenario,
    matching_scenario,
    normalize,
    parse_custom_scenario,
    previous,
    result_for_session,
    select_component,
    set_enabled,
    set_weight,
    start_session,
    sum_weights,
    use_preset,
    weights_valid,
)

NOW = "2026-11-13T00:00:00+00:00"


@pytest.fixture
def source() -> InMemoryDataSource:
    return InMemoryDataSource()


def _rows(*weights, enabled=None):
    flags = enabled or [True] * len(weights)
    return tuple(
        BasketRow(enabled=f, weight=None if w is None else Decimal(w))
        for w, f in zip(weights, flags, strict=True)
    )


def test_start_session_loads_recommended_basket_and_logs_three_reads(source):
    s = start_session(source, "y12", session_id=1, now=NOW)
    assert s.project_key == "y12"
    assert s.data_project_key == "y12"
    assert s.name == "Y-12 Site Utility Resilience Upgrade"
    assert s.scenario == "recommended"
    assert [r.weight for r in s.rows] == [Decimal(v) for v in (15, 15, 45, 25)]
    assert s.phase == "review"
    assert [m.kind for m in s.messages] == ["text", "basket"]
    assert s.messages[0].text == (
        "Build a custom PPI escalation index for Y-12 Site Utility Resilience Upgrade."
    )
    assert [e.tool for e in s.audit] == [
        "cpds_pars.read_project",
        "bls_catalog.search_series",
        "snapshot.read_observations",
    ]
    assert s.detail_tab == "component"
    assert s.selected_year == "2026"


def test_custom_scope_uses_y12_data_with_custom_identity(source):
    s = start_session(source, None, session_id=2, now=NOW, custom_text="Build X")
    assert s.project_key == "custom"
    assert s.data_project_key == "y12"
    assert s.name == "Custom project scope"
    assert s.project_id == "DEMO-CUSTOM-000"
    assert s.scope == "Build X"
    assert s.messages[0].text == "Build X"


def test_sum_and_validity_follow_the_html_rules():
    assert sum_weights(_rows(15, 15, 45, 25)) == Decimal(100)
    assert weights_valid(_rows(15, 15, 45, 25))
    assert not weights_valid(_rows(15, 15, 45, 20))
    assert not weights_valid(_rows(15, 15, 45, None))
    assert weights_valid(_rows(50, 50, 45, None, enabled=[True, True, False, False]))
    assert not weights_valid(_rows(1, 1, enabled=[False, False]))
    assert not weights_valid(_rows(150, -50))


def test_matching_scenario_requires_exact_preset_weights(source):
    presets = source.scenario_weights("y12")
    assert matching_scenario(_rows(35, 30, 20, 15), presets) == "materials"
    assert matching_scenario(_rows(35, 30, 20, 15.5), presets) is None
    disabled = _rows(35, 30, 20, 15, enabled=[True, True, True, False])
    assert matching_scenario(disabled, presets) is None


def test_set_weight_and_enabled_are_ignored_once_approved(source):
    s = start_session(source, "y12", session_id=1, now=NOW)
    edited = set_weight(s, 0, Decimal(20))
    assert edited.rows[0].weight == Decimal(20)
    assert s.rows[0].weight == Decimal(15)
    approved = approve(s, source, NOW).session
    assert set_weight(approved, 0, Decimal(1)) is approved
    assert set_enabled(approved, 0, False) is approved


def test_normalize_scales_enabled_rows_to_100(source):
    s = start_session(source, "y12", session_id=1, now=NOW)
    s = set_weight(s, 0, Decimal(30))
    out = normalize(s)
    assert sum_weights(out.session.rows) == pytest.approx(Decimal(100))
    assert out.toast == (
        "Allocation normalized. Review the weights, then approve to calculate locally."
    )


def test_normalize_splits_evenly_when_total_is_zero(source):
    s = start_session(source, "y12", session_id=1, now=NOW)
    for i in range(4):
        s = set_weight(s, i, Decimal(0))
    out = normalize(s)
    assert [r.weight for r in out.session.rows] == [Decimal(25)] * 4


def test_normalize_requires_an_enabled_row(source):
    s = start_session(source, "y12", session_id=1, now=NOW)
    for i in range(4):
        s = set_enabled(s, i, False)
    out = normalize(s)
    assert out.session is s
    assert out.toast == "Include at least one component"


def test_approve_valid_preset_appends_result_and_logs_validation(source):
    s = start_session(source, "y12", session_id=1, now=NOW)
    out = approve(s, source, NOW)
    assert out.session.phase == "approved"
    assert out.session.approved_at == NOW
    assert out.session.selected_comp == "electric"
    assert [m.kind for m in out.session.messages][-2:] == ["text", "result"]
    assert [e.tool for e in out.session.audit][-3:] == [
        "validate_index_spec",
        "calc_index_from_bls",
        "provenance.prepare",
    ]
    assert out.toast == "Validated sample result displayed."


def test_approve_rejects_invalid_and_calculates_custom_weights(source):
    s = start_session(source, "y12", session_id=1, now=NOW)
    bad_total = approve(set_weight(s, 0, Decimal(10)), source, NOW)
    assert bad_total.session.phase == "review"
    assert bad_total.toast == "Selected weights must total 100%."
    custom = set_weight(set_weight(s, 0, Decimal(16)), 1, Decimal(14))
    out = approve(custom, source, NOW)
    assert out.session.phase == "approved"
    assert out.session.scenario == "custom:1:16,1:14,1:45,1:25"
    assert out.toast == "Validated sample result displayed."
    packet = result_for_session(out.session, source)
    assert packet is not None
    assert packet.result["index_identity"]["spec_id"] == "y12-custom"
    assert (
        sum(Decimal(c["allocation_weight"]) for c in packet.result["components"]) == 1
    )


def test_custom_scenario_token_rejects_tampering():
    rows = _rows(16, 14, 45, 25)
    assert parse_custom_scenario(custom_scenario(rows)) == rows
    assert parse_custom_scenario("custom:1:16,1:14,1:45,1:26") is None
    assert parse_custom_scenario("custom:1:16,1:nan,1:45,1:25") is None
    assert parse_custom_scenario("custom:1:016,1:14,1:45,1:25") is None


def test_approve_blocked_payload_logs_block_and_toasts_first_issue():
    broken = ResultPacket(result={"schema_version": "0.9"}, presentation={})
    source = InMemoryDataSource(result_overrides={("y12", "recommended"): broken})
    s = start_session(source, "y12", session_id=1, now=NOW)
    out = approve(s, source, NOW)
    assert out.session.phase == "approved"
    assert out.session.audit[-1].detail.startswith("BLOCKED: ")
    assert out.toast is not None and out.toast.startswith("Result blocked: ")


def test_use_preset_after_approval_reopens_review(source):
    s = approve(start_session(source, "y12", session_id=1, now=NOW), source, NOW)
    s = compare(s.session).session
    out = use_preset(s, source, "materials")
    kinds = [m.kind for m in out.session.messages]
    assert out.session.phase == "review"
    assert out.session.approved_at is None
    assert "result" not in kinds and "compare" not in kinds
    assert kinds[-1] == "basket"
    assert out.session.messages[-2].text == "Review the materials allocation instead."
    assert out.toast == "Precomputed materials scenario loaded for review."


def test_use_preset_unknown_key_is_a_no_op(source):
    s = start_session(source, "y12", session_id=1, now=NOW)
    assert use_preset(s, source, "missing").session is s


def test_compare_before_approval_explains_the_prerequisite(source):
    s = start_session(source, "y12", session_id=1, now=NOW)
    out = compare(s)
    assert out.session.messages[-2].text == "Compare scenarios"
    assert out.session.messages[-1].text.startswith("First select a precomputed")


def test_ask_why_and_previous_append_message_pairs(source):
    s = start_session(source, "y12", session_id=1, now=NOW)
    assert ask_why(s).session.messages[-2].text == "Why these PPI indices?"
    assert previous(s).session.messages[-1].kind == "previous"


def test_select_component_only_after_approval(source):
    s = start_session(source, "y12", session_id=1, now=NOW)
    assert select_component(s, "steel") is s
    approved = approve(s, source, NOW).session
    chosen = select_component(approved, "steel")
    assert chosen.selected_comp == "steel"
    assert chosen.detail_tab == "component"


def test_app_state_starts_newest_first_and_resets(source):
    state = AppState()
    state = state.start(source, "y12", now=NOW)
    state = state.start(source, "lanl", now=NOW)
    assert [s.project_key for s in state.sessions] == ["lanl", "y12"]
    assert state.active is not None and state.active.project_key == "lanl"
    assert state.activate(1).active.project_key == "y12"
    assert state.reset().active is None
    replaced = state.replace_active(ask_why(state.active).session)
    assert len(replaced.active.messages) == len(state.active.messages) + 2
