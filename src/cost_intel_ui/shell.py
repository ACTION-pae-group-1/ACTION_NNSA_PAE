"""App shell: left rail, top bar, composer, welcome, mission, screen inventory.

The HTML lays out a three-column grid (245px rail, flexible main, 302px
context panel). In Streamlit the rail maps to ``st.sidebar`` and the main and
context areas to columns; this module holds only the content.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from cost_intel_ui.data_access import CostIntelDataSource, Project
from cost_intel_ui.session import AppState, Session


@dataclass(frozen=True)
class Brand:
    mark: str = "∑"
    eyebrow: str = "NNSA · PA&E"
    title: str = "AI MCP"


BRAND = Brand()


@dataclass(frozen=True)
class NavItem:
    label: str
    icon: str
    action: str
    selected: bool = False


@dataclass(frozen=True)
class NavSection:
    title: str
    items: tuple[NavItem, ...]
    empty_note: str | None = None


@dataclass(frozen=True)
class LeftRail:
    new_analysis_label: str
    sections: tuple[NavSection, ...]
    footer_eyebrow: str
    footer_lines: tuple[str, ...]


def left_rail(state: AppState, projects: Sequence[Project]) -> LeftRail:
    conversations = NavSection(
        "Your conversations",
        tuple(
            NavItem(s.name, "◫", f"session:{s.id}", s.id == state.active_id)
            for s in state.sessions
        ),
        empty_note="Your analyses appear here.",
    )
    examples = NavSection(
        "NNSA example projects",
        tuple(NavItem(p.nav_label, p.icon, f"start:{p.key}") for p in projects),
    )
    resources = NavSection(
        "Resources",
        (
            NavItem("Why this matters", "◎", "mission"),
            NavItem("Evidence & audit", "◫", "audit"),
        ),
    )
    return LeftRail(
        new_analysis_label="＋ New analysis",
        sections=(conversations, examples, resources),
        footer_eyebrow="The goal",
        footer_lines=(
            "Turn project descriptions into defensible cost escalation "
            "analysis—with transparent sources, weights and calculations.",
            "Offline proof of concept · No live government connections",
        ),
    )


NavModal = Literal["mission", "audit"]


def apply_nav_action(
    state: AppState, action: str, source: CostIntelDataSource, now: str
) -> tuple[AppState, NavModal | None]:
    """Apply a left-rail action string from ``NavItem.action`` or "new"."""
    kind, _, arg = action.partition(":")
    if kind == "start" and source.get_project(arg):
        return state.start(source, arg, now=now), None
    if kind == "session" and arg.isdigit():
        return state.activate(int(arg)), None
    if kind == "new":
        return state.reset(), None
    if kind in ("mission", "audit"):
        return state, kind
    return state, None


@dataclass(frozen=True)
class Topbar:
    title: str
    crumb: str
    subtitle: str
    pill: str


def topbar(session: Session | None, result_blocked: bool = False) -> Topbar:
    if session is None:
        subtitle = "Talk to your data. Keep the evidence."
    elif session.phase != "approved":
        subtitle = f"{session.name} · Reviewing proposed indices"
    elif result_blocked:
        subtitle = f"{session.name} · Result blocked · contract error"
    else:
        subtitle = f"{session.name} · Index result ready"
    return Topbar(
        title="Cost Intelligence",
        crumb="/ Escalation Agent",
        subtitle=subtitle,
        pill="● Sample sources available · Offline",
    )


@dataclass(frozen=True)
class Composer:
    placeholder: str
    hint: str
    foot_note: str


COMPOSER = Composer(
    placeholder="Ask about cost escalation, BLS indices, or a project scope…",
    hint="Ask naturally · Enter to send, Shift+Enter for a new line",
    foot_note=(
        "Offline demonstration · Synthetic annual PPI data · Backend-style results "
        "are precomputed and read-only."
    ),
)


@dataclass(frozen=True)
class Step:
    kicker: str
    title: str
    body: str


@dataclass(frozen=True)
class Starter:
    project_key: str
    icon: str
    title: str
    blurb: str


@dataclass(frozen=True)
class WelcomeView:
    tag: str
    title_lines: tuple[str, str]
    lead: str
    steps: tuple[Step, ...]
    starter_label: str
    starters: tuple[Starter, ...]
    foot: str


def welcome_view(projects: Sequence[Project]) -> WelcomeView:
    return WelcomeView(
        tag="✦ Government cost intelligence · Offline prototype",
        title_lines=("Ask a project question.", "Get an index you can defend."),
        lead=(
            "Turn an NNSA project scope into an auditable cost escalation analysis. "
            "Review an AI-proposed basket, approve its allocations, then explore the "
            "weighted index, PPI histories, year-to-base adjustments, and source "
            "observations."
        ),
        steps=(
            Step(
                "01 · ASK",
                "Start with project context",
                "Your analyst question drives the workflow.",
            ),
            Step(
                "02 · REVIEW",
                "Approve the basket",
                "Inspect indices, allocations, and alternatives.",
            ),
            Step(
                "03 · EXPLAIN",
                "Explore the evidence",
                "View charts, waterfall, table, and CSV.",
            ),
        ),
        starter_label="Choose an illustrative NNSA planning scenario",
        starters=tuple(
            Starter(p.key, p.icon, p.nav_label, p.starter_blurb) for p in projects
        ),
        foot=(
            "All projects are fictional. The PPI results here are precomputed, "
            "synthetic backend-style example records; no real government system, MCP "
            "server, or BLS API is accessed by this file."
        ),
    )


@dataclass(frozen=True)
class MissionUnit:
    eyebrow: str
    title: str
    body: str


@dataclass(frozen=True)
class MissionView:
    kicker: str
    title: str
    challenge: str
    units: tuple[MissionUnit, ...]
    connection: str
    disclaimer: str


def mission_view() -> MissionView:
    return MissionView(
        kicker="GOVERNMENT MCP HACKATHON",
        title="The mission: explainable cost escalation",
        challenge=(
            "Finding suitable BLS producer price indices, retrieving consistent time "
            "periods, matching series to project scopes, and reconciling weighted "
            "calculations is time-consuming and error-prone."
        ),
        units=(
            MissionUnit(
                "READ",
                "Connected context",
                "Retrieve project WBS descriptions and relevant economic observations "
                "through MCP tools.",
            ),
            MissionUnit(
                "REVIEW",
                "Human oversight",
                "Approve the basket and allocation weights before a backend "
                "calculation.",
            ),
            MissionUnit(
                "AUDIT",
                "Explain outcomes",
                "Explore PPI components, exact adjustments, the observation ledger "
                "and deterministic CSV export.",
            ),
        ),
        connection=(
            "NNSA PA&E and other government analysts could reuse this workflow to "
            "improve transparency when comparing costs and escalation assumptions."
        ),
        disclaimer=(
            "This local demonstration contains no live government data or network "
            "connections. Write-back to PARS is a planned integration and is not "
            "executed here."
        ),
    )


@dataclass(frozen=True)
class Screen:
    key: str
    title: str
    surface: str
    view_model: str


SCREENS: tuple[Screen, ...] = (
    Screen("welcome", "Welcome and starters", "main feed", "shell.welcome_view"),
    Screen(
        "basket",
        "Recommended PPI escalation basket",
        "chat message",
        "basket_view.basket_view",
    ),
    Screen(
        "results",
        "Custom PPI escalation index",
        "chat message",
        "results_view.explorer_view",
    ),
    Screen(
        "comparison",
        "Scenario comparison",
        "chat message",
        "comparison_view.comparison_view",
    ),
    Screen(
        "audit",
        "Calculation evidence & audit trail",
        "modal",
        "audit_view.audit_payload",
    ),
    Screen("pars", "PARS write-back preview", "modal", "audit_view.pars_preview"),
    Screen("mission", "Why this matters", "modal", "shell.mission_view"),
    Screen(
        "context", "Project & evidence", "right panel", "context_view.context_panel"
    ),
)
