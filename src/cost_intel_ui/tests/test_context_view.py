"""Tests for the right-hand Project & evidence panel."""

from cost_intel_ui.context_view import context_panel
from cost_intel_ui.data_access import ResultPacket
from cost_intel_ui.fake_data import InMemoryDataSource
from cost_intel_ui.session import approve, start_session

NOW = "2026-11-13T00:00:00+00:00"


def test_empty_panel_is_ready_with_project_picker():
    source = InMemoryDataSource()
    panel = context_panel(None, source)
    assert panel.project_status == "Ready"
    assert panel.project_options[0] == ("", "Choose an example project")
    assert panel.selected_project == ""
    assert panel.meta_lines == ()
    assert panel.progress_status == "Ready"
    assert [r.text for r in panel.progress] == ["—"] * 4
    assert panel.composite_value == "—"
    assert panel.composite_caption == "Available after sample basket approval."


def test_backend_sources_are_listed_as_simulated():
    panel = context_panel(None, InMemoryDataSource())
    assert [s[0] for s in panel.sources] == [
        "CPDS / PARS",
        "BLS PPI catalog",
        "Annual economic snapshot",
    ]


def test_reviewing_session_marks_first_two_steps_done():
    source = InMemoryDataSource()
    s = start_session(source, "y12", session_id=1, now=NOW)
    panel = context_panel(s, source)
    assert panel.project_status == "Sample loaded"
    assert panel.selected_project == "y12"
    assert panel.meta_lines[0] == ("Illustrative project ID", "DEMO-NNSA-Y12-001")
    assert panel.progress_status == "Reviewing"
    assert [(r.text, r.ok) for r in panel.progress] == [
        ("✓ Done", True),
        ("✓ Done", True),
        ("—", False),
        ("—", False),
    ]


def test_approved_session_shows_composite_factor():
    source = InMemoryDataSource()
    s = approve(
        start_session(source, "y12", session_id=1, now=NOW), source, NOW
    ).session
    panel = context_panel(s, source)
    assert panel.progress_status == "Calculated"
    assert all(r.ok for r in panel.progress)
    assert panel.composite_value == "1.1263"
    assert panel.composite_caption == "2026 / base factor 1.0 · synthetic"
    assert panel.composite_status == "Annual base 2023"


def test_blocked_session_marks_later_steps_blocked():
    broken = ResultPacket(result={"schema_version": "0.9"}, presentation={})
    source = InMemoryDataSource(result_overrides={("y12", "recommended"): broken})
    s = approve(
        start_session(source, "y12", session_id=1, now=NOW), source, NOW
    ).session
    panel = context_panel(s, source)
    assert panel.progress_status == "Validation blocked"
    assert [r.text for r in panel.progress][2:] == ["Blocked", "Blocked"]
    assert panel.composite_value == "—"
