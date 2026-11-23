"""Tests for the data-access interface the UI depends on."""

import dataclasses
from decimal import Decimal

import pytest

from cost_intel_ui.data_access import (
    CostIntelDataSource,
    Project,
    ResultPacket,
    SeriesSource,
)


def _project() -> Project:
    return Project(
        key="y12",
        project_id="DEMO-1",
        name="Demo project",
        nav_label="Demo",
        icon="#",
        starter_blurb="Blurb.",
        wbs="WBS",
        mission="Mission",
        scope="Scope",
    )


def test_domain_records_are_immutable():
    project = _project()
    with pytest.raises(dataclasses.FrozenInstanceError):
        project.name = "changed"  # type: ignore[misc]


def test_series_source_carries_basket_display_fields():
    source = SeriesSource(
        component_id="steel",
        short_name="Structural steel",
        name="Steel mill products",
        series_id="DEMO-WPU1017",
        description="d",
        color_hex="#4F83E6",
        sample_growth_percent="18.8",
    )
    assert source.short_name != source.name


def test_result_packet_separates_contract_payload_from_presentation():
    packet = ResultPacket(result={"schema_version": "1.0"}, presentation={})
    assert packet.result["schema_version"] == "1.0"


class _CompleteStub:
    def list_projects(self):
        return [_project()]

    def get_project(self, key):
        return _project() if key == "y12" else None

    def list_sources(self):
        return []

    def scenario_weights(self, project_key):
        return {"recommended": (Decimal(100),)}

    def get_result(self, project_key, scenario_key):
        return None


class _IncompleteStub:
    def list_projects(self):
        return []


def test_protocol_recognizes_any_object_with_the_required_methods():
    assert isinstance(_CompleteStub(), CostIntelDataSource)


def test_protocol_rejects_objects_missing_methods():
    assert not isinstance(_IncompleteStub(), CostIntelDataSource)
