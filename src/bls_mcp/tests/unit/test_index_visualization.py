"""IndexVisualizationService and the index visualization contract models."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("duckdb")

from bls_mcp.exceptions import (
    CalculationError,
    InvalidPeriodError,
    ObservationNotFoundError,
    SeriesNotFoundError,
)
from bls_mcp.models.basket import EscalationComponent
from bls_mcp.models.enums import ComponentType, Periodicity
from bls_mcp.models.periods import EconomicPeriod
from bls_mcp.models.specifications import EscalationIndexSpec
from bls_mcp.models.visualization import IndexVisualizationData
from bls_mcp.services.validation import ValidationService
from bls_mcp.services.visualization import (
    IndexVisualizationService,
    component_colors,
)
from bls_mcp.storage.connection import build_connection
from bls_mcp.storage.models import SnapshotInfo, SourceFileReceipt
from bls_mcp.storage.schema import initialize_schema
from bls_mcp.storage.snapshots import write_snapshot_info, write_source_file
from bls_mcp.storage.store import BLSStore

HANDOFF = Path(__file__).parents[4] / "docs" / "UI Handoff schema"
STEEL = "PCU100000000000"
ELECTRICAL = "PCU200000000000"
QUARTERLY = "CIU300000000000"

# Steel and electrical reproduce the handoff example: 94 -> 100 and 97 -> 100.
OBSERVATIONS = [
    (STEEL, 2022, "M13", 90.0),
    (STEEL, 2023, "M13", 94.0),
    (STEEL, 2024, "M13", 100.0),
    (STEEL, 2025, "M13", 103.0),
    (STEEL, 2024, "M12", 101.5),
    (ELECTRICAL, 2023, "M13", 97.0),
    (ELECTRICAL, 2024, "M13", 100.0),
    (ELECTRICAL, 2025, "M13", 110.0),
    (QUARTERLY, 2023, "Q04", 150.0),
    (QUARTERLY, 2024, "Q03", 158.0),
    (QUARTERLY, 2024, "Q04", 160.0),
]


@pytest.fixture()
def service(tmp_path: Path) -> IndexVisualizationService:
    path = tmp_path / "viz.duckdb"
    with build_connection(path, threads=1) as conn:
        initialize_schema(conn)
        write_snapshot_info(conn, SnapshotInfo("viz_test", datetime.now(UTC), ("pc",)))
        write_source_file(
            conn, SourceFileReceipt(1, "pc", "fixture.txt", "a" * 64, 1, "current")
        )
        series = [
            (STEEL, "Steel mill products"),
            (ELECTRICAL, "Electrical equipment"),
            (QUARTERLY, "Quarterly labor cost"),
        ]
        for index, (series_id, _) in enumerate(series, start=1):
            code = f"{index}00---"
            conn.execute("INSERT INTO pc_industry VALUES (?, ?)", [code, code])
            conn.execute("INSERT INTO pc_product VALUES (?, ?, ?)", [code, code, code])
            conn.execute(
                "INSERT INTO pc_series VALUES (?, ?, ?, 'U', '198200')",
                [series_id, code, code],
            )
        conn.executemany(
            "INSERT INTO series_catalog VALUES (?, 'pc', ?, NULL, FALSE, "
            "2020, 'M01', 2026, 'M12', 'index', '198200', TRUE)",
            series,
        )
        conn.executemany(
            "INSERT INTO observations VALUES (?, ?, ?, ?, NULL, 1)", OBSERVATIONS
        )
        conn.execute(
            "UPDATE snapshot_info "
            "SET lifecycle_state='PUBLISHED', validation_status='PASSED'"
        )
    return IndexVisualizationService(BLSStore(path), ValidationService())


def annual(year: int) -> EconomicPeriod:
    return EconomicPeriod(year=year, periodicity=Periodicity.ANNUAL)


def component(cid: str, series_id: str | None, weight: float, **extra: Any):
    return EscalationComponent(
        id=cid,
        name=cid.title(),
        component_type=extra.pop("component_type", ComponentType.MATERIAL),
        weight=weight,
        series_id=series_id,
        **extra,
    )


def courthouse(**overrides: Any) -> EscalationIndexSpec:
    fields: dict[str, Any] = {
        "id": "courthouse-renovation",
        "name": "Courthouse Renovation Escalation Index",
        "revision": 3,
        "base_period": annual(2024),
        "target_period": annual(2023),
        "components": [
            component("steel", STEEL, 0.4),
            component("electrical", ELECTRICAL, 0.6),
        ],
    }
    return EscalationIndexSpec(**{**fields, **overrides})


def test_schema_matches_the_published_handoff_schema() -> None:
    published = json.loads((HANDOFF / "index_visualization_v1.schema.json").read_text())
    assert IndexVisualizationData.model_json_schema() == published


def test_published_example_satisfies_the_contract() -> None:
    example = json.loads((HANDOFF / "index_visualization_v1.example.json").read_text())
    assert (
        IndexVisualizationData.model_validate(example).model_dump(mode="json")
        == example
    )


def test_reproduces_the_handoff_example_values(service) -> None:
    result = service.build(courthouse()).result

    assert result.index_identity.model_dump() == {
        "index_id": "courthouse-renovation",
        "name": "Courthouse Renovation Escalation Index",
        "spec_id": "courthouse-renovation",
        "spec_revision": 3,
        "snapshot_id": "viz_test",
        "methodology_version": "composite-index/1.0",
        "frequency": "annual",
    }
    assert result.normalization.base_year == 2024
    assert [c.allocation_weight for c in result.components] == [
        "0.400000000000",
        "0.600000000000",
    ]
    assert [c.description for c in result.components] == [
        "Steel mill products",
        "Electrical equipment",
    ]
    by_key = {(p.component_id, p.period): p for p in result.component_points}
    assert by_key[("steel", "2023")].raw_ppi_value == "94.0"
    assert Decimal(by_key[("steel", "2023")].normalized_factor) == Decimal("0.94")
    assert Decimal(by_key[("steel", "2023")].weighted_level) == Decimal("0.376")
    assert Decimal(by_key[("electrical", "2023")].weighted_level) == Decimal("0.582")
    assert by_key[("steel", "2023")].observation_id == f"obs:steel:{STEEL}:2023-M13"
    assert [
        (c.period, Decimal(c.composite_factor)) for c in result.composite_points
    ] == [
        ("2023", Decimal("0.958")),
        ("2024", Decimal("1")),
    ]

    adjustment = result.base_year_adjustment
    assert (adjustment.source_year, adjustment.base_year) == (2023, 2024)
    assert adjustment.adjustment_factor == "1.043841336117"
    assert adjustment.adjustment_percent == "0.043841336117"
    assert [s.adjustment_contribution for s in adjustment.steps] == [
        "0.025052192067",
        "0.018789144050",
    ]
    assert adjustment.steps[-1].running_adjustment_factor == "1.043841336117"


def test_presentation_rows_reconcile_with_the_result(service) -> None:
    packet = service.build(courthouse(), end_year=2025)
    result, presentation = packet.result, packet.presentation

    assert sorted(presentation.adjustments_by_year) == ["2023", "2024", "2025"]
    assert presentation.adjustments_by_year["2023"] == result.base_year_adjustment
    base = presentation.adjustments_by_year["2024"]
    assert Decimal(base.adjustment_factor) == 1
    assert all(Decimal(s.adjustment_contribution) == 0 for s in base.steps)

    # 2025 composite: 0.4 * 1.03 + 0.6 * 1.10 = 1.072
    assert Decimal(presentation.latest_change_percent) == Decimal("7.2")
    tops = {
        (layer.period, layer.component_id): layer for layer in presentation.stack_layers
    }
    assert Decimal(tops[("2025", "steel")].bottom) == 0
    assert tops[("2025", "electrical")].bottom == tops[("2025", "steel")].top
    assert Decimal(tops[("2025", "electrical")].top) == Decimal("1.072")
    assert len(presentation.table_rows) == 6
    row = presentation.table_rows[0]
    assert (row.period, row.component_id, row.display_order) == ("2023", "steel", 0)
    assert Decimal(row.normalized_percent) == Decimal("94")
    assert (row.snapshot_id, row.base_year) == ("viz_test", 2024)


def test_every_number_is_plain_fixed_point_text(service) -> None:
    """The web UI rejects exponent notation, which the schema would allow."""
    packet = service.build(courthouse(), end_year=2025)
    numeric = re.compile(
        r"weight|value|factor|level|percent|delta|contribution|bottom|top"
    )
    seen = 0

    def walk(node: Any, key: str = "") -> None:
        nonlocal seen
        if isinstance(node, dict):
            for name, child in node.items():
                walk(child, name)
        elif isinstance(node, list):
            for child in node:
                walk(child, key)
        elif isinstance(node, str) and numeric.search(key):
            seen += 1
            assert re.fullmatch(r"-?\d+(\.\d+)?", node), (key, node)

    walk(packet.model_dump(mode="json"))
    assert seen > 50


def test_incomplete_year_is_omitted_and_reported(service) -> None:
    result = service.build(courthouse(), start_year=2022, end_year=2025).result

    assert [c.period for c in result.composite_points] == ["2023", "2024", "2025"]
    assert {p.period for p in result.component_points} == {"2023", "2024", "2025"}
    (warning,) = result.warnings
    assert (warning.code, warning.severity) == ("INCOMPLETE_PERIOD_OMITTED", "warning")
    assert "2022" in warning.message and ELECTRICAL in warning.message


def test_source_year_selects_the_top_level_adjustment(service) -> None:
    result = service.build(courthouse(), end_year=2025, source_year=2025).result
    assert result.base_year_adjustment.source_year == 2025
    assert Decimal(result.base_year_adjustment.adjustment_percent) < 0

    with pytest.raises(InvalidPeriodError, match="source year 2022"):
        service.build(courthouse(), start_year=2022, source_year=2022)


def test_window_must_include_the_base_year(service) -> None:
    with pytest.raises(InvalidPeriodError, match="base year 2024"):
        service.build(courthouse(), start_year=2025, end_year=2025)


def test_weight_overrides_do_not_touch_the_spec(service) -> None:
    spec = courthouse()
    result = service.build(spec, weights={"steel": "0.25", "electrical": 0.75}).result

    assert [c.allocation_weight for c in result.components] == [
        "0.250000000000",
        "0.750000000000",
    ]
    # 0.25 * 0.94 + 0.75 * 0.97 = 0.9625
    assert Decimal(result.composite_points[0].composite_factor) == Decimal("0.9625")
    assert [c.weight for c in spec.components] == [0.4, 0.6]

    with pytest.raises(CalculationError, match="Total component weights"):
        service.build(spec, weights={"steel": 0.9})
    with pytest.raises(CalculationError, match="not in the specification: copper"):
        service.build(spec, weights={"copper": 0.1})


def test_zero_weight_component_is_left_out(service) -> None:
    result = service.build(courthouse(), weights={"steel": 0, "electrical": 1}).result
    assert [c.component_id for c in result.components] == ["electrical"]
    assert result.warnings[0].code == "ZERO_WEIGHT_COMPONENT_OMITTED"


def test_weights_within_tolerance_are_rescaled_with_a_warning(service) -> None:
    spec = courthouse(
        components=[
            component("steel", STEEL, 0.33333),
            component("electrical", ELECTRICAL, 0.66666),
        ]
    )
    result = service.build(spec).result
    assert sum(Decimal(c.allocation_weight) for c in result.components) == 1
    assert [w.code for w in result.warnings] == ["WEIGHTS_RENORMALIZED"]


def test_quarterly_only_series_uses_q04_and_says_so(service) -> None:
    spec = courthouse(
        components=[
            component("steel", STEEL, 0.5),
            component("labor", QUARTERLY, 0.5, component_type=ComponentType.LABOR),
        ]
    )
    result = service.build(spec).result
    labor = [p for p in result.component_points if p.component_id == "labor"]
    assert [p.raw_ppi_value for p in labor] == ["150.0", "160.0"]
    assert labor[0].observation_id == f"obs:labor:{QUARTERLY}:2023-Q04"
    assert [w.code for w in result.warnings] == ["QUARTERLY_TO_ANNUAL_ALIGNMENT"]


def test_fixed_component_cannot_be_charted(service) -> None:
    spec = courthouse(
        components=[
            component("steel", STEEL, 0.6),
            component(
                "overhead", None, 0.4, component_type=ComponentType.FIXED_UNINDEXED
            ),
        ]
    )
    with pytest.raises(CalculationError, match="no BLS series to chart: overhead"):
        service.build(spec)


def test_missing_series_and_missing_base_observation(service) -> None:
    unknown = courthouse(components=[component("ghost", "PCU999999999999", 1.0)])
    with pytest.raises(SeriesNotFoundError, match="PCU999999999999"):
        service.build(unknown)

    no_base = courthouse(base_period=annual(2022), target_period=annual(2024))
    with pytest.raises(ObservationNotFoundError, match="base year 2022"):
        service.build(no_base)


def test_contract_rejects_a_payload_that_does_not_reconcile(service) -> None:
    payload = service.build(courthouse()).result.model_dump(mode="json")
    payload["composite_points"][0]["composite_factor"] = "0.960000000000"
    with pytest.raises(ValueError, match="do not sum to composite at 2023"):
        IndexVisualizationData.model_validate(payload)


def test_colors_stay_distinct_beyond_the_palette() -> None:
    colors = component_colors(40)
    assert len({c.lower() for c in colors}) == 40
