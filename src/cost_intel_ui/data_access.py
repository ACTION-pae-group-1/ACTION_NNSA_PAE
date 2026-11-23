"""Data-access interface for the UI.

The concrete data source is an open decision (in-process call into the PARS
and BLS packages, an MCP client, or a precomputed snapshot). Screens depend
only on ``CostIntelDataSource``; ``cost_intel_ui.fake_data`` provides an
in-memory implementation.

``ResultPacket.result`` follows docs/UI Handoff schema/
index_visualization_v1.schema.json. ``ResultPacket.presentation`` carries the
backend-precomputed display extensions the HTML prototype relies on
(adjustments for every year, long-form table rows, stack layers, latest
change percent). Economic values are decimal strings throughout.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class Project:
    key: str
    project_id: str
    name: str
    nav_label: str
    icon: str
    starter_blurb: str
    wbs: str
    mission: str
    scope: str


@dataclass(frozen=True)
class SeriesSource:
    """One candidate PPI series as listed in the recommended basket."""

    component_id: str
    short_name: str
    name: str
    series_id: str
    description: str
    color_hex: str
    sample_growth_percent: str


@dataclass(frozen=True)
class ResultPacket:
    result: Mapping[str, Any]
    presentation: Mapping[str, Any]


@runtime_checkable
class CostIntelDataSource(Protocol):
    def list_projects(self) -> Sequence[Project]: ...

    def get_project(self, key: str) -> Project | None: ...

    def list_sources(self) -> Sequence[SeriesSource]:
        """Candidate series in basket order; weights below align by position."""
        ...

    def scenario_weights(self, project_key: str) -> Mapping[str, tuple[Decimal, ...]]:
        """Preset allocations in percent, keyed by scenario, in source order."""
        ...

    def get_result(self, project_key: str, scenario_key: str) -> ResultPacket | None:
        """A calculated result for a preset allocation, or None if unavailable."""
        ...
