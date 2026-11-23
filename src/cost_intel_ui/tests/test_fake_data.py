"""Tests for the deterministic in-memory data source.

Expected numbers are taken from the HTML prototype's embedded fixture so the
fake reproduces the design's sample values exactly.
"""

from decimal import Decimal

from cost_intel_ui.data_access import CostIntelDataSource, ResultPacket
from cost_intel_ui.fake_data import InMemoryDataSource


def _packet(project="y12", scenario="recommended") -> ResultPacket:
    packet = InMemoryDataSource().get_result(project, scenario)
    assert packet is not None
    return packet


def test_fake_satisfies_the_data_source_protocol():
    assert isinstance(InMemoryDataSource(), CostIntelDataSource)


def test_fake_lists_the_three_example_projects_in_html_order():
    source = InMemoryDataSource()
    assert [p.key for p in source.list_projects()] == ["y12", "pantex", "lanl"]
    y12 = source.get_project("y12")
    assert y12 is not None
    assert y12.project_id == "DEMO-NNSA-Y12-001"
    assert y12.nav_label == "Y-12 utility resilience"
    assert source.get_project("missing") is None


def test_fake_lists_four_ppi_sources_in_basket_order():
    ids = [s.component_id for s in InMemoryDataSource().list_sources()]
    assert ids == ["steel", "concrete", "electric", "machinery"]


def test_scenario_weights_are_percent_tuples_in_source_order():
    weights = InMemoryDataSource().scenario_weights("y12")
    assert list(weights) == ["recommended", "materials", "equipment"]
    assert weights["recommended"] == tuple(Decimal(v) for v in (15, 15, 45, 25))


def test_unknown_project_or_scenario_returns_none():
    source = InMemoryDataSource()
    assert source.get_result("missing", "recommended") is None
    assert source.get_result("y12", "missing") is None
    assert source.scenario_weights("missing") == {}


def test_components_are_ordered_by_weight_then_source_order():
    y12 = _packet()
    assert [c["component_id"] for c in y12.result["components"]] == [
        "electric",
        "machinery",
        "steel",
        "concrete",
    ]
    pantex = _packet("pantex")
    assert [c["component_id"] for c in pantex.result["components"]] == [
        "steel",
        "machinery",
        "concrete",
        "electric",
    ]


def test_identity_and_normalization_match_the_contract():
    result = _packet().result
    assert result["schema_version"] == "1.0"
    assert result["index_identity"] == {
        "index_id": "demo-nnsa-y12",
        "name": "Y-12 Site Utility Resilience Upgrade PPI Escalation Index",
        "spec_id": "y12-recommended",
        "spec_revision": 1,
        "snapshot_id": "DEMO-ANNUAL-2021-2026-v1",
        "methodology_version": "composite-index/1.0",
        "frequency": "annual",
    }
    assert result["normalization"] == {
        "base_year": 2023,
        "base_factor": "1.0",
        "method": "base_year_annual_average",
    }


def test_composite_factors_reproduce_the_html_fixture():
    composite = {
        p["period"]: p["composite_factor"] for p in _packet().result["composite_points"]
    }
    assert composite == {
        "2021": "0.927000000000",
        "2022": "0.967500574053",
        "2023": "1.000000000000",
        "2024": "1.049598200589",
        "2025": "1.093949185329",
        "2026": "1.126250052151",
    }
    pantex = _packet("pantex").result["composite_points"][-1]
    assert pantex["composite_factor"] == "1.136100262084"


def test_component_points_reproduce_raw_and_normalized_values():
    points = _packet().result["component_points"]
    assert len(points) == 24
    machinery_2022 = next(
        p for p in points if p["component_id"] == "machinery" and p["period"] == "2022"
    )
    assert machinery_2022["raw_ppi_value"] == "170.368"
    assert machinery_2022["normalized_factor"] == "0.978002296211"
    assert machinery_2022["observation_id"] == "obs:demo:machinery:2022"


def test_base_year_adjustment_reproduces_html_steps():
    adjustment = _packet().result["base_year_adjustment"]
    assert adjustment["source_year"] == 2026
    assert adjustment["adjustment_factor"] == "0.887902289629"
    assert adjustment["adjustment_percent"] == "-0.112097710371"
    machinery = adjustment["steps"][1]
    assert machinery == {
        "component_id": "machinery",
        "display_order": 1,
        "selected_year_normalized_factor": "1.120998851894",
        "index_level_delta": "-0.030249712974",
        "adjustment_contribution": "-0.026858789410",
        "running_adjustment_factor": "0.926792711071",
    }


def test_presentation_has_adjustments_for_every_year_and_a_zero_base_year():
    presentation = _packet("pantex").presentation
    assert sorted(presentation["adjustments_by_year"]) == [
        "2021",
        "2022",
        "2023",
        "2024",
        "2025",
        "2026",
    ]
    base = presentation["adjustments_by_year"]["2023"]
    assert base["adjustment_factor"] == "1.000000000000"
    assert {s["adjustment_contribution"] for s in base["steps"]} == {"0.000000000000"}
    y2021 = presentation["adjustments_by_year"]["2021"]
    assert y2021["adjustment_factor"] == "1.089324618736"
    assert y2021["steps"][-1]["running_adjustment_factor"] == "1.089324618736"


def test_presentation_table_rows_are_period_major_and_complete():
    presentation = _packet("pantex").presentation
    rows = presentation["table_rows"]
    assert len(rows) == 24
    assert [r["period"] + r["component_id"] for r in rows[:4]] == [
        "2021steel",
        "2021machinery",
        "2021concrete",
        "2021electric",
    ]
    assert rows[0]["normalized_percent"] == "91.000000000000"
    assert rows[0]["warning_code"] == "SYNTHETIC_EXAMPLE"
    assert presentation["latest_change_percent"] == "13.610026208400"


def test_stack_layers_accumulate_in_display_order_to_the_composite():
    presentation = _packet().presentation
    layers_2021 = [
        layer for layer in presentation["stack_layers"] if layer["period"] == "2021"
    ]
    assert [layer["component_id"] for layer in layers_2021][0] == "electric"
    assert layers_2021[0]["bottom"] == "0.000000000000"
    assert layers_2021[-1]["top"] == "0.927000000000"


def test_result_overrides_let_tests_inject_alternate_payloads():
    broken = ResultPacket(result={"schema_version": "0.9"}, presentation={})
    source = InMemoryDataSource(result_overrides={("y12", "materials"): broken})
    assert source.get_result("y12", "materials") is broken
    assert source.get_result("y12", "recommended") is not broken


def test_sample_growth_is_2023_to_2026_change_in_percent():
    steel = InMemoryDataSource().list_sources()[0]
    assert Decimal(steel.sample_growth_percent).quantize(Decimal("0.01")) == Decimal(
        "18.80"
    )
