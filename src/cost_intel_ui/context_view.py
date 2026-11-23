"""View model for the right-hand "Project & evidence" panel."""

from __future__ import annotations

from dataclasses import dataclass

from cost_intel_ui.contract import validate_packet
from cost_intel_ui.data_access import CostIntelDataSource
from cost_intel_ui.formatting import fixed
from cost_intel_ui.session import Session

PROGRESS_STEPS = (
    "Project scope reviewed",
    "PPI candidates proposed",
    "Weights approved",
    "Results & audit available",
)
BACKEND_SOURCES = (
    ("CPDS / PARS", "Project descriptions / WBS context (mock)"),
    ("BLS PPI catalog", "Producer-price series metadata (mock)"),
    ("Annual economic snapshot", "2021–2026 synthetic observation ledger"),
)


@dataclass(frozen=True)
class ProgressRow:
    label: str
    text: str
    ok: bool


@dataclass(frozen=True)
class ContextPanel:
    project_status: str
    project_options: tuple[tuple[str, str], ...]
    selected_project: str
    meta_lines: tuple[tuple[str, str], ...]
    empty_note: str
    sources: tuple[tuple[str, str], ...]
    sources_note: str
    progress_status: str
    progress: tuple[ProgressRow, ...]
    composite_status: str
    composite_value: str
    composite_caption: str
    mission_note: str


def context_panel(session: Session | None, source: CostIntelDataSource) -> ContextPanel:
    approved = session is not None and session.phase == "approved"
    packet = (
        source.get_result(session.data_project_key, session.scenario)
        if session and approved
        else None
    )
    blocked = approved and bool(validate_packet(packet))
    latest = packet.result["composite_points"][-1] if approved and not blocked else None
    base_year = packet.result["normalization"]["base_year"] if latest else 2023

    done_count = 4 if approved else 2
    progress = tuple(
        ProgressRow(
            label,
            "Blocked"
            if blocked and i >= 2
            else ("✓ Done" if session and i < done_count else "—"),
            bool(not blocked and session and i < done_count),
        )
        for i, label in enumerate(PROGRESS_STEPS)
    )
    if blocked:
        progress_status = "Validation blocked"
    elif approved:
        progress_status = "Calculated"
    elif session:
        progress_status = "Reviewing"
    else:
        progress_status = "Ready"

    return ContextPanel(
        project_status="Sample loaded" if session else "Ready",
        project_options=(
            ("", "Choose an example project"),
            *((p.key, p.name) for p in source.list_projects()),
        ),
        selected_project=session.project_key if session else "",
        meta_lines=(
            ("Illustrative project ID", session.project_id),
            ("Mission relevance", session.mission),
            ("WBS context", session.wbs),
            ("Scope", session.scope),
        )
        if session
        else (),
        empty_note=(
            "Choose a project or describe a scope to begin. The production agent "
            "would obtain context through MCP tools."
        ),
        sources=BACKEND_SOURCES,
        sources_note=(
            "The interface assumes connections are handled by the backend. This "
            "local file sends no network requests."
        ),
        progress_status=progress_status,
        progress=progress,
        composite_status=f"Annual base {base_year}",
        composite_value=fixed(latest["composite_factor"], 4) if latest else "—",
        composite_caption=(
            f"{latest['period']} / base factor 1.0 · synthetic"
            if latest
            else "Available after sample basket approval."
        ),
        mission_note=(
            "Mission value: traceable escalation analysis supports review of NNSA "
            "PA&E assumptions and illustrates a reusable approach for other agencies."
        ),
    )
