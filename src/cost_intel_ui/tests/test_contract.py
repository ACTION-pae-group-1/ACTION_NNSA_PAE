"""Tests for the result-contract gate that blocks charts on invalid payloads."""

import copy

import pytest

from cost_intel_ui.contract import validate_packet
from cost_intel_ui.data_access import ResultPacket
from cost_intel_ui.fake_data import InMemoryDataSource


@pytest.fixture
def packet() -> ResultPacket:
    found = InMemoryDataSource().get_result("y12", "recommended")
    assert found is not None
    return ResultPacket(
        result=copy.deepcopy(dict(found.result)),
        presentation=copy.deepcopy(dict(found.presentation)),
    )


def _codes(issues: list[str]) -> set[str]:
    return {issue.split(":", 1)[0] for issue in issues}


def test_every_fake_packet_is_valid():
    source = InMemoryDataSource()
    for project in source.list_projects():
        for scenario in source.scenario_weights(project.key):
            found = source.get_result(project.key, scenario)
            assert found is not None
            assert validate_packet(found) == [], (project.key, scenario)


def test_missing_packet_is_reported():
    assert _codes(validate_packet(None)) == {"MISSING_RESULT"}


def test_wrong_schema_version_is_reported(packet):
    packet.result["schema_version"] = "0.9"
    assert "SCHEMA_VERSION" in _codes(validate_packet(packet))


def test_non_annual_frequency_is_reported(packet):
    packet.result["index_identity"]["frequency"] = "monthly"
    assert "FREQUENCY" in _codes(validate_packet(packet))


def test_missing_identity_field_is_reported(packet):
    packet.result["index_identity"]["snapshot_id"] = " "
    assert "IDENTITY" in _codes(validate_packet(packet))


def test_float_instead_of_decimal_string_is_reported(packet):
    packet.result["composite_points"][0]["composite_factor"] = 0.927
    assert "NUMERIC_CONTRACT" in _codes(validate_packet(packet))


def test_weights_not_summing_to_one_are_reported(packet):
    packet.result["components"][0]["allocation_weight"] = "0.500000000000"
    assert "WEIGHT_TOTAL" in _codes(validate_packet(packet))


def test_bad_color_is_reported(packet):
    packet.result["components"][0]["color_hex"] = "orange"
    assert "INVALID_COLOR" in _codes(validate_packet(packet))


def test_duplicate_component_is_reported(packet):
    packet.result["components"][1]["component_id"] = "electric"
    assert "DUPLICATE_COMPONENT" in _codes(validate_packet(packet))


def test_base_composite_not_one_is_reported(packet):
    packet.result["composite_points"][2]["composite_factor"] = "1.010000000000"
    assert "BASE_COMPOSITE" in _codes(validate_packet(packet))


def test_unsorted_periods_are_reported(packet):
    points = packet.result["composite_points"]
    points[0], points[1] = points[1], points[0]
    assert "COMPOSITE_SORT" in _codes(validate_packet(packet))


def test_weighted_level_mismatch_is_reported(packet):
    packet.result["component_points"][0]["weighted_level"] = "0.400000000000"
    codes = _codes(validate_packet(packet))
    assert "WEIGHTED_LEVEL" in codes
    assert "COMPOSITE_RECONCILIATION" in codes


def test_missing_observation_is_reported(packet):
    packet.result["component_points"].pop()
    assert "MISSING_OBSERVATION" in _codes(validate_packet(packet))


def test_summary_change_mismatch_is_reported(packet):
    packet.presentation["latest_change_percent"] = "99.0"
    assert "SUMMARY_CHANGE" in _codes(validate_packet(packet))


def test_missing_table_rows_are_reported(packet):
    packet.presentation["table_rows"] = []
    assert "MISSING_TABLE" in _codes(validate_packet(packet))


def test_adjustment_not_reciprocal_is_reported(packet):
    packet.presentation["adjustments_by_year"]["2021"]["adjustment_factor"] = "1.0"
    assert "ADJUSTMENT_RECIPROCAL" in _codes(validate_packet(packet))


def test_issue_list_is_capped_at_sixty(packet):
    for point in packet.result["component_points"]:
        point["weighted_level"] = "x"
        point["normalized_factor"] = "x"
        point["raw_ppi_value"] = "x"
    assert len(validate_packet(packet)) <= 60
