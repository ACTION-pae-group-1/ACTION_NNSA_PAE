"""Pure analysis-session state and transitions.

Mirrors the HTML prototype's ``start``, ``approve``, ``normalize``,
``usePreset``, ``compare``, ``askWhy``, and ``previous``. Every transition
returns a new immutable value; a UI adapter stores it (for example in
Streamlit session state). Timestamps are injected so tests are deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from decimal import Decimal
from typing import Literal

from cost_intel_ui.contract import validate_packet
from cost_intel_ui.data_access import CostIntelDataSource

Phase = Literal["review", "approved"]
MessageKind = Literal["text", "basket", "result", "compare", "previous"]
CUSTOM_KEY = "custom"
CUSTOM_DATA_KEY = "y12"
WEIGHT_TOLERANCE = Decimal("0.00001")
PRESET_TOLERANCE = Decimal("0.000001")

WHY_QUESTION = "Why these PPI indices?"
WHY_ANSWER = (
    "The illustrative components represent steel, concrete, electrical systems, "
    "and mechanical equipment mentioned in the scope. Weights in this demo are "
    "planning assumptions rather than historical project expenditure shares. In "
    "production, the agent would document candidate-series validation and source "
    "observations in the result ledger."
)


@dataclass(frozen=True)
class BasketRow:
    enabled: bool
    weight: Decimal | None


@dataclass(frozen=True)
class Message:
    role: Literal["user", "assistant"]
    kind: MessageKind = "text"
    text: str = ""


@dataclass(frozen=True)
class AuditEvent:
    tool: str
    detail: str
    timestamp: str
    status: str = "simulated"


@dataclass(frozen=True)
class Session:
    id: int
    project_key: str
    data_project_key: str
    name: str
    project_id: str
    mission: str
    wbs: str
    scope: str
    rows: tuple[BasketRow, ...]
    scenario: str = "recommended"
    phase: Phase = "review"
    messages: tuple[Message, ...] = ()
    audit: tuple[AuditEvent, ...] = ()
    approved_at: str | None = None
    selected_comp: str | None = None
    detail_tab: Literal["component", "adjustment", "table"] = "component"
    detail_mode: Literal["normalized", "raw"] = "normalized"
    selected_year: str = "2026"
    table_year: str = "all"
    table_comp: str = "all"
    table_sort: Literal["asc", "desc"] = "asc"


@dataclass(frozen=True)
class Outcome:
    session: Session
    toast: str | None = None


def _say(s: Session, *messages: Message) -> Session:
    return replace(s, messages=(*s.messages, *messages))


def _pair(s: Session, question: str, answer: str) -> Session:
    return _say(s, Message("user", text=question), Message("assistant", text=answer))


def start_session(
    source: CostIntelDataSource,
    key: str | None,
    *,
    session_id: int,
    now: str,
    custom_text: str | None = None,
) -> Session:
    project = source.get_project(key) if key else None
    data_key = project.key if project else CUSTOM_DATA_KEY
    if project is None:
        # Custom identity; basket and results still come from the y12 fixture,
        # as in the prototype.
        name, project_id = "Custom project scope", "DEMO-CUSTOM-000"
        mission, wbs = "Illustrative project analysis", "User supplied cost scope"
        scope = custom_text or "Project scope entered in chat"
        project_key = CUSTOM_KEY
    else:
        name, project_id = project.name, project.project_id
        mission, wbs, scope = project.mission, project.wbs, project.scope
        project_key = project.key
    weights = source.scenario_weights(data_key).get("recommended", ())
    s = Session(
        id=session_id,
        project_key=project_key,
        data_project_key=data_key,
        name=name,
        project_id=project_id,
        mission=mission,
        wbs=wbs,
        scope=scope,
        rows=tuple(BasketRow(enabled=True, weight=w) for w in weights),
    )
    audit = (
        AuditEvent(
            "cpds_pars.read_project",
            "Project and WBS context returned (demo fixture)",
            now,
        ),
        AuditEvent(
            "bls_catalog.search_series",
            "Illustrative PPI candidates returned (synthetic)",
            now,
        ),
        AuditEvent(
            "snapshot.read_observations",
            "Annual 2021-2026 observations loaded from an offline snapshot fixture",
            now,
        ),
    )
    opening = custom_text or f"Build a custom PPI escalation index for {name}."
    return replace(
        s,
        audit=audit,
        messages=(Message("user", text=opening), Message("assistant", "basket")),
    )


def sum_weights(rows: tuple[BasketRow, ...]) -> Decimal:
    return sum(
        (r.weight for r in rows if r.enabled and r.weight is not None), Decimal(0)
    )


def weights_valid(rows: tuple[BasketRow, ...]) -> bool:
    enabled = [r for r in rows if r.enabled]
    if not enabled:
        return False
    if any(r.weight is None or not 0 <= r.weight <= 100 for r in enabled):
        return False
    return abs(sum_weights(rows) - 100) < WEIGHT_TOLERANCE


def matching_scenario(
    rows: tuple[BasketRow, ...], presets: dict[str, tuple[Decimal, ...]]
) -> str | None:
    for key, values in presets.items():
        if len(values) == len(rows) and all(
            r.enabled and r.weight is not None and abs(r.weight - v) < PRESET_TOLERANCE
            for r, v in zip(rows, values, strict=True)
        ):
            return key
    return None


def custom_scenario(rows: tuple[BasketRow, ...]) -> str:
    """Store an approved custom allocation in the stateless scenario token."""
    return "custom:" + ",".join(
        f"{int(row.enabled)}:{'' if row.weight is None else row.weight:f}"
        for row in rows
    )


def parse_custom_scenario(value: str) -> tuple[BasketRow, ...] | None:
    """Recover the exact approved rows; refuse malformed or invalid tokens."""
    if not value.startswith("custom:") or len(value) > 1024:
        return None
    rows = []
    try:
        for item in value[7:].split(","):
            enabled, weight_text = item.split(":")
            if enabled not in ("0", "1"):
                return None
            weight = Decimal(weight_text) if weight_text else None
            if weight is not None and (
                not weight.is_finite() or not 0 <= weight <= 100
            ):
                return None
            rows.append(BasketRow(enabled == "1", weight))
    except (ValueError, ArithmeticError):
        return None
    parsed = tuple(rows)
    # Canonical serialization prevents accepting altered or ambiguous locked tokens.
    return (
        parsed if weights_valid(parsed) and custom_scenario(parsed) == value else None
    )


def result_for_session(s: Session, source: CostIntelDataSource):
    """Select a preset result or compute a synthetic custom result locally."""
    if s.scenario.startswith("custom:"):
        if parse_custom_scenario(s.scenario) != s.rows:
            return None
        calculator = getattr(source, "get_custom_result", None)
        if not callable(calculator):
            return None
        weights = tuple(
            row.weight if row.enabled and row.weight is not None else Decimal(0)
            for row in s.rows
        )
        return calculator(s.data_project_key, weights)
    return source.get_result(s.data_project_key, s.scenario)


def _edit_row(s: Session, index: int, **changes: object) -> Session:
    if s.phase == "approved":
        return s
    rows = list(s.rows)
    rows[index] = replace(rows[index], **changes)
    return replace(s, rows=tuple(rows))


def set_weight(s: Session, index: int, weight: Decimal | None) -> Session:
    return _edit_row(s, index, weight=weight)


def set_enabled(s: Session, index: int, enabled: bool) -> Session:
    return _edit_row(s, index, enabled=enabled)


def normalize(s: Session) -> Outcome:
    if s.phase == "approved":
        return Outcome(s)
    selected = [r for r in s.rows if r.enabled]
    if not selected:
        return Outcome(s, "Include at least one component")
    total = sum_weights(s.rows)
    even = Decimal(100) / len(selected)
    rows = tuple(
        replace(r, weight=((r.weight or Decimal(0)) / total * 100) if total else even)
        if r.enabled
        else r
        for r in s.rows
    )
    return Outcome(
        replace(s, rows=rows),
        "Allocation normalized. Review the weights, then approve to calculate locally.",
    )


def approve(s: Session, source: CostIntelDataSource, now: str) -> Outcome:
    if s.phase == "approved":
        return Outcome(s)
    if not weights_valid(s.rows):
        return Outcome(s, "Selected weights must total 100%.")
    matched = matching_scenario(
        s.rows, dict(source.scenario_weights(s.data_project_key))
    )
    scenario = matched or custom_scenario(s.rows)
    calculated = replace(s, scenario=scenario)
    packet = result_for_session(calculated, source)
    if packet is None:
        return Outcome(s, "A local calculator is not available for this allocation.")
    issues = validate_packet(packet)
    components = list(packet.result.get("components") or []) if packet else []
    approved = replace(
        s,
        scenario=scenario,
        phase="approved",
        approved_at=now,
        selected_comp=components[0].get("component_id") if components else None,
    )
    if issues:
        events = [
            (
                "validate_index_spec",
                f"BLOCKED: {len(issues)} calculation-data contract errors",
            )
        ]
    else:
        events = [
            (
                "validate_index_spec",
                # The prototype claims "all 14 invariants"; this port runs the
                # core subset in cost_intel_ui.contract, so say so.
                "Validated schema and core contract invariants (identity, "
                "weights, annual periods, reconciliation, adjustments)",
            ),
            (
                "calc_index_from_bls",
                "Calculated locally from synthetic annual PPI observations "
                "and approved allocation weights"
                if matched is None
                else "Loaded precomputed offline Decimal fixture; no client-side "
                "economic calculation",
            ),
            (
                "provenance.prepare",
                "Prepared synthetic versioned source evidence and observation "
                "identifiers",
            ),
        ]
    audit = (*approved.audit, *(AuditEvent(t, d, now) for t, d in events))
    approved = _say(
        replace(approved, audit=audit),
        Message(
            "user", text="Approve this basket and show the PPI escalation results."
        ),
        Message("assistant", "result"),
    )
    toast = (
        f"Result blocked: {issues[0]}"
        if issues
        else "Validated sample result displayed."
    )
    return Outcome(approved, toast)


def use_preset(s: Session, source: CostIntelDataSource, key: str) -> Outcome:
    values = source.scenario_weights(s.data_project_key).get(key)
    if not values:
        return Outcome(s, "That allocation is not available for this project.")
    updated = replace(
        s,
        rows=tuple(BasketRow(enabled=True, weight=w) for w in values),
        scenario=key,
    )
    if s.phase == "approved":
        kept = tuple(m for m in s.messages if m.kind not in ("result", "compare"))
        updated = _say(
            replace(updated, phase="review", approved_at=None, messages=kept),
            Message("user", text=f"Review the {key} allocation instead."),
            Message("assistant", "basket"),
        )
    return Outcome(updated, f"Precomputed {key} scenario loaded for review.")


def compare(s: Session) -> Outcome:
    if s.phase != "approved":
        return Outcome(
            _pair(
                s,
                "Compare scenarios",
                "First select a precomputed allocation and approve the basket. Then "
                "I can show comparable backend-style scenario results.",
            )
        )
    return Outcome(
        _say(
            s,
            Message(
                "user", text="Compare escalation outcomes for alternate allocations."
            ),
            Message("assistant", "compare"),
        )
    )


def ask_why(s: Session) -> Outcome:
    return Outcome(_pair(s, WHY_QUESTION, WHY_ANSWER))


def previous(s: Session) -> Outcome:
    return Outcome(
        _say(
            s,
            Message("user", text="Compare against past PARS project work."),
            Message("assistant", "previous"),
        )
    )


def select_component(s: Session, component_id: str) -> Session:
    if s.phase != "approved":
        return s
    return replace(s, selected_comp=component_id, detail_tab="component")


@dataclass(frozen=True)
class AppState:
    """All sessions (newest first) and which one is active."""

    sessions: tuple[Session, ...] = field(default_factory=tuple)
    active_id: int | None = None
    next_id: int = 1

    @property
    def active(self) -> Session | None:
        return next((s for s in self.sessions if s.id == self.active_id), None)

    def start(
        self,
        source: CostIntelDataSource,
        key: str | None,
        *,
        now: str,
        custom_text: str | None = None,
    ) -> AppState:
        s = start_session(
            source, key, session_id=self.next_id, now=now, custom_text=custom_text
        )
        return AppState((s, *self.sessions), s.id, self.next_id + 1)

    def activate(self, session_id: int) -> AppState:
        return replace(self, active_id=session_id)

    def reset(self) -> AppState:
        return replace(self, active_id=None)

    def replace_active(self, session: Session) -> AppState:
        return replace(
            self,
            sessions=tuple(session if s.id == session.id else s for s in self.sessions),
        )
