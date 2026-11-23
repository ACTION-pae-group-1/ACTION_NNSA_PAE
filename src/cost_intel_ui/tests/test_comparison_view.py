"""Tests for the Scenario comparison view model."""

from cost_intel_ui.comparison_view import comparison_view
from cost_intel_ui.data_access import ResultPacket
from cost_intel_ui.fake_data import InMemoryDataSource
from cost_intel_ui.session import approve, start_session

NOW = "2026-11-13T00:00:00+00:00"


def _approved(source):
    s = start_session(source, "y12", session_id=1, now=NOW)
    return approve(s, source, NOW).session


def test_title_is_derived_from_latest_period_and_base_year():
    source = InMemoryDataSource()
    view = comparison_view(_approved(source), source)
    assert view.title == "Scenario comparison · 2026 vs. 2023"


def test_one_box_per_preset_with_factor_and_weights():
    source = InMemoryDataSource()
    view = comparison_view(_approved(source), source)
    assert [(b.label, b.approved, b.value) for b in view.boxes] == [
        ("Recommended", True, "1.1263"),
        ("Materials-heavy", False, "1.1384"),
        ("Equipment-heavy", False, "1.1232"),
    ]
    assert view.boxes[0].weights_label == "Weights: 15 / 15 / 45 / 25%"
    assert view.boxes[1].preset_key == "materials"
    assert view.note.startswith("These alternatives are not automatically written")


def test_invalid_scenario_shows_unavailable():
    broken = ResultPacket(result={"schema_version": "0.9"}, presentation={})
    source = InMemoryDataSource(result_overrides={("y12", "materials"): broken})
    view = comparison_view(_approved(source), source)
    assert view.boxes[1].value == "Unavailable — invalid data"
