"""View model for the "Recommended PPI escalation basket" card."""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from cost_intel_ui.data_access import CostIntelDataSource
from cost_intel_ui.formatting import fixed, signed
from cost_intel_ui.session import (
    Outcome,
    Session,
    approve,
    ask_why,
    matching_scenario,
    normalize,
    set_enabled,
    set_weight,
    sum_weights,
    use_preset,
    weights_valid,
)

SCENARIO_LABELS = {
    "recommended": "Recommended",
    "materials": "Materials-heavy",
    "equipment": "Equipment-heavy",
}
_COUNT_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}


def scenario_label(key: str) -> str:
    return SCENARIO_LABELS.get(key, key)


@dataclass(frozen=True)
class PresetButton:
    key: str
    label: str
    current: bool

    @property
    def display_label(self) -> str:
        """Label that marks the current preset in text, not only by color."""
        return f"✓ {self.label} (current)" if self.current else self.label


@dataclass(frozen=True)
class BasketRowView:
    index: int
    enabled: bool
    title: str
    series_line: str
    type_label: str
    sample_label: str
    weight: Decimal | None
    checkbox_disabled: bool
    weight_disabled: bool

    @property
    def checkbox_label(self) -> str:
        return f"Include {self.title}"

    @property
    def weight_label(self) -> str:
        return f"Allocation percent for {self.title}"


@dataclass(frozen=True)
class BasketView:
    intro: str
    title: str
    subtitle: str
    badge_label: str
    badge_tone: Literal["amber", "green"]
    presets: tuple[PresetButton, ...]
    columns: tuple[str, ...]
    rows: tuple[BasketRowView, ...]
    total_label: str
    status_label: str
    status_tone: Literal["valid", "invalid"]
    normalize_enabled: bool
    approve_enabled: bool
    approve_label: str
    notice: str
    fineprint: str
    why_link: str


def basket_view(session: Session, source: CostIntelDataSource) -> BasketView:
    presets = dict(source.scenario_weights(session.data_project_key))
    sources = source.list_sources()
    mode = matching_scenario(session.rows, presets)
    valid = weights_valid(session.rows)
    locked = session.phase == "approved"
    custom_available = callable(getattr(source, "get_custom_result", None))
    ready = valid and (mode is not None or custom_available)
    count = _COUNT_WORDS.get(len(sources), str(len(sources)))

    if ready:
        status = "✓ Precomputed result ready" if mode else "✓ Custom calculation ready"
    elif valid:
        status = "No local calculator available"
    else:
        status = "Weights must equal 100%"

    rows = tuple(
        BasketRowView(
            index=i,
            enabled=row.enabled,
            title=src.short_name,
            series_line=f"{src.name} · {src.series_id}",
            type_label="PPI",
            sample_label=f"{signed(src.sample_growth_percent)}%",
            weight=row.weight,
            checkbox_disabled=locked,
            weight_disabled=locked or not row.enabled,
        )
        for i, (src, row) in enumerate(zip(sources, session.rows, strict=True))
    )
    return BasketView(
        intro=(
            f"I reviewed the {session.name} scope and identified {count} PPI cost "
            "drivers. This result-view demo follows a PPI-only specification; an "
            "expanded PPI + ECI model could be supported by a broader backend "
            "contract. The allocations below are illustrative, not verified project "
            "expenditure shares."
        ),
        title="Recommended PPI escalation basket",
        subtitle=(
            "Choose a preset or set your own weights. Valid 100% allocations "
            "are calculated locally from synthetic PPI data."
        ),
        badge_label="✓ Approved fixture" if locked else "Requires approval",
        badge_tone="green" if locked else "amber",
        presets=tuple(
            PresetButton(key, scenario_label(key), key == mode) for key in presets
        ),
        columns=(
            "Use",
            "Component / mock series",
            "Type",
            "2023→2026 sample",
            "Weight %",
        ),
        rows=rows,
        total_label=f"{fixed(sum_weights(session.rows))}%",
        status_label=status,
        status_tone="valid" if ready else "invalid",
        normalize_enabled=not locked,
        approve_enabled=ready and not locked,
        approve_label="✓ Approved" if locked else "Approve & view result →",
        notice=(
            "Precomputed result available for this basket."
            if mode
            else "Custom weights use the local synthetic PPI calculator. "
            "These illustrative estimates are not verified project costs."
            if custom_available
            else "Select a preset; this data source cannot calculate custom weights."
        ),
        fineprint=(
            "Demo series IDs begin with DEMO-. No BLS observations are represented "
            "as verified; preset and custom calculations use local synthetic data."
        ),
        why_link="Why did the agent recommend these cost drivers? →",
    )


# --- Interaction logic for UI adapters -------------------------------------


@dataclass(frozen=True)
class Toggle:
    index: int
    enabled: bool


@dataclass(frozen=True)
class SetWeight:
    index: int
    value: float | None


@dataclass(frozen=True)
class ChoosePreset:
    key: str


@dataclass(frozen=True)
class Normalize:
    pass


@dataclass(frozen=True)
class Approve:
    pass


@dataclass(frozen=True)
class AskWhy:
    pass


BasketAction = Toggle | SetWeight | ChoosePreset | Normalize | Approve | AskWhy


def _to_weight(value: float | None) -> Decimal | None:
    if value is None or not math.isfinite(value):
        return None
    return Decimal(str(value))


def apply_basket_action(
    session: Session, action: BasketAction, source: CostIntelDataSource, now: str
) -> Outcome:
    """Apply one basket interaction and return the new session and any toast."""
    if isinstance(action, Toggle):
        return Outcome(set_enabled(session, action.index, action.enabled))
    if isinstance(action, SetWeight):
        return Outcome(set_weight(session, action.index, _to_weight(action.value)))
    if isinstance(action, ChoosePreset):
        return use_preset(session, source, action.key)
    if isinstance(action, Normalize):
        return normalize(session)
    if isinstance(action, Approve):
        return approve(session, source, now)
    return ask_why(session)


def weight_widget_key(session_id: int, index: int) -> str:
    return f"basket-{session_id}-weight-{index}"


def weight_widget_values(session: Session) -> dict[str, float | None]:
    """Widget values to write back after a programmatic change (preset, normalize)."""
    return {
        weight_widget_key(session.id, i): None if r.weight is None else float(r.weight)
        for i, r in enumerate(session.rows)
    }
