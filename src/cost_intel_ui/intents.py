"""Quick prompts and free-text routing (ports the HTML's ``submitQuery``).

Routing is keyword-based, as in the prototype. A connected agent would
replace this; the function boundary stays the same.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Literal

from cost_intel_ui.data_access import CostIntelDataSource
from cost_intel_ui.session import (
    AppState,
    Message,
    approve,
    ask_why,
    compare,
    matching_scenario,
    previous,
    weights_valid,
)

ModalKind = Literal["audit", "pars", "mission"]


@dataclass(frozen=True)
class QuickPrompt:
    label: str
    query: str


QUICK_PROMPTS: tuple[QuickPrompt, ...] = (
    QuickPrompt("Find PPI indices", "Find relevant cost indices"),
    QuickPrompt("Explain the weights", "Why these weights?"),
    QuickPrompt("Compare scenarios", "Compare cost scenarios"),
    QuickPrompt("View source trail", "Show the audit trail"),
)

FALLBACK_ANSWER = (
    "In this offline prototype I can demonstrate proposed PPI series, an approved "
    "weighted index, a selectable component detail chart, adjustment-to-base "
    "waterfalls, and the auditable data/CSV. A connected MCP agent would answer "
    "broader questions using live approved tools."
)


@dataclass(frozen=True)
class QueryOutcome:
    state: AppState
    toast: str | None = None
    modal: ModalKind | None = None


def _pair(state: AppState, question: str, answer: str) -> AppState:
    s = state.active
    assert s is not None
    return state.replace_active(
        replace(
            s,
            messages=(
                *s.messages,
                Message("user", text=question),
                Message("assistant", text=answer),
            ),
        )
    )


def submit_query(
    text: str, state: AppState, source: CostIntelDataSource, now: str
) -> QueryOutcome:
    query = text.strip()
    if not query:
        return QueryOutcome(state)
    s = state.active
    if s is None:
        return QueryOutcome(state.start(source, None, now=now, custom_text=query))
    lower = query.lower()
    approved = s.phase == "approved"

    if re.search(r"why|explain|rationale|defensible", lower):
        return QueryOutcome(state.replace_active(ask_why(s).session))
    if re.search(r"compar|scenario|sensitiv|alternativ", lower):
        return QueryOutcome(state.replace_active(compare(s).session))
    if re.search(r"aud|source|provenance|json|trace", lower):
        answer = (
            "The full calculation evidence includes versioned component "
            "observations, normalization, fixed allocations, composite factors and "
            "year-to-base adjustment steps. Open the evidence panel to inspect and "
            "download it."
        )
        return QueryOutcome(_pair(state, query, answer), modal="audit")
    if re.search(r"waterfall|adjust.*base|year.to.base", lower):
        if not approved:
            return QueryOutcome(
                _pair(
                    state,
                    query,
                    "Approve a basket first to view the adjustment-to-base waterfall.",
                )
            )
        state = state.replace_active(replace(s, detail_tab="adjustment"))
        return QueryOutcome(
            _pair(
                state,
                query,
                "The adjustment-to-base tab in your index results shows precomputed "
                "contributions for each eligible source year. Scroll to the latest "
                "result card.",
            )
        )
    if re.search(r"csv|data table|export table", lower):
        if not approved:
            return QueryOutcome(
                _pair(
                    state,
                    query,
                    "Approve the basket to open the auditable source table.",
                )
            )
        state = state.replace_active(replace(s, detail_tab="table"))
        return QueryOutcome(
            _pair(
                state,
                query,
                "The Data & CSV tab on the calculated result shows one row per "
                "component and annual period and supports filtered CSV export.",
            )
        )
    if re.search(r"calculat|approve|run.*index|result", lower):
        if approved:
            return QueryOutcome(
                _pair(
                    state,
                    query,
                    "The read-only, precomputed result is in the conversation. You can "
                    "select components or view adjustment and data tabs without "
                    "recalculating the index.",
                )
            )
        presets = dict(source.scenario_weights(s.data_project_key))
        if weights_valid(s.rows) and matching_scenario(s.rows, presets):
            out = approve(s, source, now)
            return QueryOutcome(state.replace_active(out.session), out.toast)
        return QueryOutcome(
            _pair(
                state,
                query,
                "For the offline demo, choose one of the three precomputed allocation "
                "presets and ensure it totals 100%. The production MCP calculator will "
                "accept your custom approved specification.",
            )
        )
    if re.search(r"save|pars|write", lower):
        answer = (
            "PARS write-back is planned. This demo can display the proposed payload "
            "but does not submit changes."
        )
        return QueryOutcome(_pair(state, query, answer), modal="pars")
    if re.search(r"histor|previous|past|prior", lower):
        return QueryOutcome(state.replace_active(previous(s).session))
    return QueryOutcome(_pair(state, query, FALLBACK_ANSWER))
