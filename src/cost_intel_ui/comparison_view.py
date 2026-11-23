"""View model for "Scenario comparison · <latest> vs. <base>"."""

from __future__ import annotations

from dataclasses import dataclass

from cost_intel_ui.basket_view import scenario_label
from cost_intel_ui.contract import validate_packet
from cost_intel_ui.data_access import CostIntelDataSource
from cost_intel_ui.formatting import fixed
from cost_intel_ui.session import Session


@dataclass(frozen=True)
class ComparisonBox:
    preset_key: str
    label: str
    approved: bool
    value: str
    weights_label: str


@dataclass(frozen=True)
class ComparisonView:
    intro: str
    title: str
    boxes: tuple[ComparisonBox, ...]
    note: str


def comparison_view(session: Session, source: CostIntelDataSource) -> ComparisonView:
    presets = source.scenario_weights(session.data_project_key)
    boxes = []
    latest_period, base_year = None, None
    for key, weights in presets.items():
        packet = source.get_result(session.data_project_key, key)
        if packet is not None and not validate_packet(packet):
            latest = packet.result["composite_points"][-1]
            value = fixed(latest["composite_factor"], 4)
            if key == session.scenario or latest_period is None:
                latest_period = latest["period"]
                base_year = packet.result["normalization"]["base_year"]
        else:
            value = "Unavailable — invalid data"
        boxes.append(
            ComparisonBox(
                preset_key=key,
                label=scenario_label(key),
                approved=key == session.scenario,
                value=value,
                weights_label="Weights: " + " / ".join(f"{w:f}" for w in weights) + "%",
            )
        )
    span = f" · {latest_period} vs. {base_year}" if latest_period else ""
    return ComparisonView(
        intro=(
            "Compare precomputed, synthetic outcomes using the same sample PPI "
            "histories with different fixed allocations. In production, the "
            "calculation tool would provide every scenario result."
        ),
        title=f"Scenario comparison{span}",
        boxes=tuple(boxes),
        note=(
            "These alternatives are not automatically written back to PARS. A change "
            "to weights requires another explicit approval and backend calculation."
        ),
    )
