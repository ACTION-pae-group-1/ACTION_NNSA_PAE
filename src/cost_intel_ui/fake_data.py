"""Deterministic in-memory data source reproducing the HTML prototype's fixture.

Projects, series, raw annual values, and preset weights are copied from the
prototype's embedded JSON. Result packets are computed here with Decimal so the
fake stays small and its numbers match the design exactly. All data is
synthetic; series IDs begin with DEMO-.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from cost_intel_ui.data_access import Project, ResultPacket, SeriesSource

YEARS: tuple[int, ...] = (2021, 2022, 2023, 2024, 2025, 2026)
BASE_YEAR = 2023
SNAPSHOT_ID = "DEMO-ANNUAL-2021-2026-v1"
METHODOLOGY_VERSION = "composite-index/1.0"
WARNING_CODE = "SYNTHETIC_EXAMPLE"
RAW_UNIT = "PPI index points"
RAW_BASIS = "Synthetic raw PPI index (illustrative reference) ; not verified BLS data"
_Q12 = Decimal("0.000000000001")


@dataclass(frozen=True)
class FakeSeries:
    source: SeriesSource
    raw_by_year: tuple[str, ...]


PROJECTS: tuple[Project, ...] = (
    Project(
        key="y12",
        project_id="DEMO-NNSA-Y12-001",
        name="Y-12 Site Utility Resilience Upgrade",
        nav_label="Y-12 utility resilience",
        icon="▤",
        starter_blurb="Power distribution, steel, foundations, and equipment.",
        wbs="Site utilities / electrical distribution",
        mission="Production-site power resilience and mission continuity",
        scope=(
            "Hypothetical Y-12 infrastructure project to modernize electrical "
            "distribution and power resilience, including switchgear, structural "
            "supports, concrete equipment foundations, and skilled installation "
            "labor."
        ),
    ),
    Project(
        key="pantex",
        project_id="DEMO-NNSA-PX-002",
        name="Pantex Mission Support Facility Renewal",
        nav_label="Pantex facility renewal",
        icon="▥",
        starter_blurb="Modernization of mission-support infrastructure.",
        wbs="Mission-support facilities / building renewal",
        mission="Sustainment of mission-support facilities",
        scope=(
            "Hypothetical Pantex mission-support building renewal involving "
            "structural reinforcement, concrete repairs, electrical upgrades, and "
            "skilled construction and installation labor."
        ),
    ),
    Project(
        key="lanl",
        project_id="DEMO-NNSA-LANL-003",
        name="Los Alamos Research Support Building",
        nav_label="Los Alamos lab expansion",
        icon="◈",
        starter_blurb="Research-support building and facility systems.",
        wbs="Laboratory facilities / civil and electrical systems",
        mission="National laboratory research infrastructure",
        scope=(
            "Hypothetical Los Alamos research-support building expansion with "
            "structural steel, concrete foundations, electrical distribution, and "
            "skilled construction labor."
        ),
    ),
)


def _series(
    component_id: str,
    short_name: str,
    name: str,
    series_id: str,
    description: str,
    color_hex: str,
    raw: tuple[str, ...],
) -> FakeSeries:
    base = Decimal(raw[YEARS.index(BASE_YEAR)])
    growth = (Decimal(raw[-1]) / base - 1) * 100
    return FakeSeries(
        source=SeriesSource(
            component_id=component_id,
            short_name=short_name,
            name=name,
            series_id=series_id,
            description=description,
            color_hex=color_hex,
            sample_growth_percent=f"{growth.quantize(_Q12):f}",
        ),
        raw_by_year=raw,
    )


SERIES: tuple[FakeSeries, ...] = (
    _series(
        "steel",
        "Structural steel",
        "Steel mill products",
        "DEMO-WPU1017",
        "Illustrative producer-price series for steel used in structural frames "
        "and supports.",
        "#4F83E6",
        ("220.766", "232.896", "242.600", "261.523", "274.381", "288.209"),
    ),
    _series(
        "concrete",
        "Concrete",
        "Concrete products",
        "DEMO-WPU132",
        "Illustrative producer-price series for concrete and foundation materials.",
        "#18A88B",
        ("250.560", "264.480", "278.400", "293.990", "300.950", "307.354"),
    ),
    _series(
        "electric",
        "Electrical systems",
        "Electrical equipment",
        "DEMO-WPU117",
        "Illustrative producer-price series for power distribution equipment and "
        "switchgear.",
        "#E6A34B",
        ("186.590", "192.545", "198.500", "207.432", "217.754", "221.526"),
    ),
    _series(
        "machinery",
        "Mechanical / equipment",
        "General purpose machinery",
        "DEMO-WPU114",
        "Illustrative producer-price series for mechanical systems and "
        "installation equipment.",
        "#B27AE1",
        ("162.006", "170.368", "174.200", "180.645", "187.091", "195.278"),
    ),
)


def _weights(*values: int) -> tuple[Decimal, ...]:
    return tuple(Decimal(v) for v in values)


SCENARIO_WEIGHTS: Mapping[str, Mapping[str, tuple[Decimal, ...]]] = {
    "y12": {
        "recommended": _weights(15, 15, 45, 25),
        "materials": _weights(35, 30, 20, 15),
        "equipment": _weights(10, 10, 55, 25),
    },
    "pantex": {
        "recommended": _weights(30, 25, 15, 30),
        "materials": _weights(40, 30, 15, 15),
        "equipment": _weights(20, 15, 40, 25),
    },
    "lanl": {
        "recommended": _weights(25, 25, 25, 25),
        "materials": _weights(35, 30, 20, 15),
        "equipment": _weights(15, 15, 45, 25),
    },
}


def _q(value: Decimal) -> str:
    return f"{value.quantize(_Q12):f}"


def _adjustment(
    year: int,
    composite: Decimal,
    ordered: Sequence[tuple[int, FakeSeries, Decimal]],
    factors: Mapping[tuple[str, int], Decimal],
) -> dict[str, Any]:
    factor = 1 / composite
    running = Decimal(1)
    steps = []
    for order, (_, series, weight) in enumerate(ordered):
        cid = series.source.component_id
        normalized = factors[(cid, year)]
        delta = weight * (1 - normalized)
        contribution = delta / composite
        running = running + contribution
        steps.append(
            {
                "component_id": cid,
                "display_order": order,
                "selected_year_normalized_factor": _q(normalized),
                "index_level_delta": _q(delta),
                "adjustment_contribution": _q(contribution),
                "running_adjustment_factor": _q(running),
            }
        )
    return {
        "source_year": year,
        "base_year": BASE_YEAR,
        "source_composite_factor": _q(composite),
        "adjustment_factor": _q(factor),
        "adjustment_percent": _q(factor - 1),
        "steps": steps,
    }


def build_result_packet(
    project: Project,
    series: Sequence[FakeSeries],
    weights_percent: Sequence[Decimal],
    scenario_key: str,
) -> ResultPacket:
    """Compute an index_visualization_v1 payload plus presentation extensions."""
    weights = [(w / 100).quantize(_Q12) for w in weights_percent]
    ordered = sorted(
        ((i, s, weights[i]) for i, s in enumerate(series)),
        key=lambda item: (-item[2], item[0]),
    )
    base_index = YEARS.index(BASE_YEAR)
    factors: dict[tuple[str, int], Decimal] = {}
    for s in series:
        base_raw = Decimal(s.raw_by_year[base_index])
        for y, raw in zip(YEARS, s.raw_by_year, strict=True):
            factors[(s.source.component_id, y)] = Decimal(raw) / base_raw

    components, component_points = [], []
    weighted: dict[tuple[str, int], Decimal] = {}
    for order, (_, s, weight) in enumerate(ordered):
        src = s.source
        components.append(
            {
                "component_id": src.component_id,
                "display_order": order,
                "name": src.name,
                "description": src.description,
                "series_id": src.series_id,
                "allocation_weight": _q(weight),
                "raw_unit": RAW_UNIT,
                "raw_reference_basis": RAW_BASIS,
                "color_hex": src.color_hex,
            }
        )
        for y, raw in zip(YEARS, s.raw_by_year, strict=True):
            # Unrounded; rounding happens once when each value is serialized.
            level = weight * factors[(src.component_id, y)]
            weighted[(src.component_id, y)] = level
            component_points.append(
                {
                    "period": str(y),
                    "year": y,
                    "period_kind": "annual_average",
                    "component_id": src.component_id,
                    "raw_ppi_value": raw,
                    "normalized_factor": _q(factors[(src.component_id, y)]),
                    "weighted_level": _q(level),
                    "observation_id": f"obs:demo:{src.component_id}:{y}",
                }
            )

    composite_by_year = {
        y: sum(
            (weighted[(s.source.component_id, y)] for _, s, _ in ordered), Decimal(0)
        )
        for y in YEARS
    }
    composite_points = [
        {
            "period": str(y),
            "year": y,
            "period_kind": "annual_average",
            "composite_factor": _q(composite_by_year[y]),
        }
        for y in YEARS
    ]
    adjustments = {
        str(y): _adjustment(y, composite_by_year[y], ordered, factors) for y in YEARS
    }

    stack_layers, table_rows = [], []
    for y in YEARS:
        running = Decimal(0)
        for order, (_, s, weight) in enumerate(ordered):
            src = s.source
            level = weighted[(src.component_id, y)]
            stack_layers.append(
                {
                    "period": str(y),
                    "component_id": src.component_id,
                    "bottom": _q(running),
                    "top": _q(running + level),
                }
            )
            running += level
            normalized = factors[(src.component_id, y)]
            table_rows.append(
                {
                    "period": str(y),
                    "component_name": src.name,
                    "component_id": src.component_id,
                    "series_id": src.series_id,
                    "allocation_weight": _q(weight),
                    "raw_ppi_value": s.raw_by_year[YEARS.index(y)],
                    "normalized_factor": _q(normalized),
                    "normalized_percent": _q(normalized * 100),
                    "weighted_level": _q(level),
                    "composite_factor": _q(composite_by_year[y]),
                    "base_year": BASE_YEAR,
                    "snapshot_id": SNAPSHOT_ID,
                    "observation_id": f"obs:demo:{src.component_id}:{y}",
                    "warning_code": WARNING_CODE,
                    "display_order": order,
                }
            )

    # The prototype derives the summary from the already-rounded composite.
    latest = composite_by_year[YEARS[-1]].quantize(_Q12)
    result = {
        "schema_version": "1.0",
        "index_identity": {
            "index_id": f"demo-nnsa-{project.key}",
            "name": f"{project.name} PPI Escalation Index",
            "spec_id": f"{project.key}-{scenario_key}",
            "spec_revision": 1,
            "snapshot_id": SNAPSHOT_ID,
            "methodology_version": METHODOLOGY_VERSION,
            "frequency": "annual",
        },
        "normalization": {
            "base_year": BASE_YEAR,
            "base_factor": "1.0",
            "method": "base_year_annual_average",
        },
        "components": components,
        "component_points": component_points,
        "composite_points": composite_points,
        "base_year_adjustment": adjustments[str(YEARS[-1])],
        "warnings": [
            {
                "code": WARNING_CODE,
                "severity": "warning",
                "message": (
                    "Fictional NNSA planning scenario; PPI observations and series "
                    "identifiers are synthetic, not verified BLS data."
                ),
            }
        ],
    }
    presentation = {
        "adjustments_by_year": adjustments,
        "table_rows": table_rows,
        "stack_layers": stack_layers,
        "latest_change_percent": _q((latest - 1) * 100),
    }
    return ResultPacket(result=result, presentation=presentation)


class InMemoryDataSource:
    """Fake ``CostIntelDataSource`` backed by the prototype's synthetic data."""

    def __init__(
        self,
        projects: Sequence[Project] = PROJECTS,
        series: Sequence[FakeSeries] = SERIES,
        scenario_weights: Mapping[str, Mapping[str, tuple[Decimal, ...]]] = (
            SCENARIO_WEIGHTS
        ),
        result_overrides: Mapping[tuple[str, str], ResultPacket] | None = None,
    ) -> None:
        self._projects = {p.key: p for p in projects}
        self._series = tuple(series)
        self._weights = scenario_weights
        self._overrides = dict(result_overrides or {})
        self._cache: dict[tuple[str, str], ResultPacket] = {}

    def list_projects(self) -> Sequence[Project]:
        return tuple(self._projects.values())

    def get_project(self, key: str) -> Project | None:
        return self._projects.get(key)

    def list_sources(self) -> Sequence[SeriesSource]:
        return tuple(s.source for s in self._series)

    def scenario_weights(self, project_key: str) -> Mapping[str, tuple[Decimal, ...]]:
        return dict(self._weights.get(project_key, {}))

    def get_custom_result(
        self, project_key: str, weights_percent: Sequence[Decimal]
    ) -> ResultPacket | None:
        """Calculate a synthetic result for analyst weights without network calls."""
        project = self._projects.get(project_key)
        if project is None or len(weights_percent) != len(self._series):
            return None
        return build_result_packet(project, self._series, weights_percent, "custom")

    def get_result(self, project_key: str, scenario_key: str) -> ResultPacket | None:
        key = (project_key, scenario_key)
        if key in self._overrides:
            return self._overrides[key]
        project = self._projects.get(project_key)
        weights = self._weights.get(project_key, {}).get(scenario_key)
        if project is None or weights is None:
            return None
        if key not in self._cache:
            self._cache[key] = build_result_packet(
                project, self._series, weights, scenario_key
            )
        return self._cache[key]
