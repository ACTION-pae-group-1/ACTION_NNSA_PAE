"""Streamlit adapter for the NNSA cost-intelligence UI.

Run from the repository root:

    streamlit run src/cost_intel_ui/streamlit_app.py

This module only renders view models and forwards widget events to the pure
functions in ``cost_intel_ui``. The data source is the in-memory fake; the
live source is an open decision (see ``get_data_source``).

Heading structure (WCAG 1.3.1): the sidebar brand is the page's h1, rail
sections and the main and context areas are h2, and cards are h3.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from html import escape
from pathlib import Path

if __package__ in (None, ""):  # launched as a script by `streamlit run`
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st  # noqa: E402

from cost_intel_ui.audit_view import (  # noqa: E402
    AUDIT_FILENAME,
    audit_payload,
    pars_preview,
)
from cost_intel_ui.basket_view import (  # noqa: E402
    Approve,
    AskWhy,
    BasketAction,
    ChoosePreset,
    Normalize,
    SetWeight,
    Toggle,
    apply_basket_action,
    basket_view,
    weight_widget_key,
    weight_widget_values,
)
from cost_intel_ui.components import badge, tool_trace  # noqa: E402
from cost_intel_ui.context_view import context_panel  # noqa: E402
from cost_intel_ui.data_access import CostIntelDataSource  # noqa: E402
from cost_intel_ui.fake_data import InMemoryDataSource  # noqa: E402
from cost_intel_ui.intents import QUICK_PROMPTS, submit_query  # noqa: E402
from cost_intel_ui.session import AppState, Message, Session  # noqa: E402
from cost_intel_ui.shell import (  # noqa: E402
    BRAND,
    COMPOSER,
    apply_nav_action,
    left_rail,
    mission_view,
    topbar,
    welcome_view,
)
from cost_intel_ui.theme import app_css  # noqa: E402

PAGE_TITLE = "AI MCP — NNSA Cost Intelligence | PPI Results Explorer · Validation v4"
STATE_KEY = "app_state"
SOURCE_KEY = "data_source"
TOAST_KEY = "pending_toast"
MODAL_KEY = "pending_modal"
TRACE_LABELS = ("Project context", "PPI candidates", "Offline snapshot")
NOT_BUILT = {
    "result": "Custom PPI escalation index: this screen is not built yet in the "
    "Streamlit prototype.",
    "compare": "Scenario comparison: this screen is not built yet in the Streamlit "
    "prototype.",
}
PREVIOUS_TEXT = (
    "Comparing with prior PARS project records would require the production read "
    "integration. This offline demo has no real historical project comparisons; it "
    "only illustrates the workflow."
)


# --- State plumbing ---------------------------------------------------------


def get_data_source() -> CostIntelDataSource:
    """Single switch point for the data source. Live integration is undecided."""
    if SOURCE_KEY not in st.session_state:
        st.session_state[SOURCE_KEY] = InMemoryDataSource()
    return st.session_state[SOURCE_KEY]


def _state() -> AppState:
    if STATE_KEY not in st.session_state:
        st.session_state[STATE_KEY] = AppState()
    return st.session_state[STATE_KEY]


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _toast(message: str | None) -> None:
    if message:
        st.session_state[TOAST_KEY] = message


def _sync_weight_widgets(session: Session) -> None:
    for key, value in weight_widget_values(session).items():
        st.session_state[key] = value


def _on_basket(action: BasketAction) -> None:
    state = _state()
    session = state.active
    if session is None:
        return
    if isinstance(action, SetWeight):
        action = SetWeight(
            action.index,
            st.session_state.get(weight_widget_key(session.id, action.index)),
        )
    if isinstance(action, Toggle):
        action = Toggle(
            action.index,
            bool(st.session_state.get(f"basket-{session.id}-enable-{action.index}")),
        )
    outcome = apply_basket_action(session, action, get_data_source(), _now())
    st.session_state[STATE_KEY] = state.replace_active(outcome.session)
    if isinstance(action, ChoosePreset | Normalize):
        _sync_weight_widgets(outcome.session)
    _toast(outcome.toast)


def _on_nav(action: str) -> None:
    state, modal = apply_nav_action(_state(), action, get_data_source(), _now())
    st.session_state[STATE_KEY] = state
    if modal:
        st.session_state[MODAL_KEY] = modal


def _on_query(text: str | None = None) -> None:
    query = text if text is not None else st.session_state.get("composer") or ""
    outcome = submit_query(query, _state(), get_data_source(), _now())
    st.session_state[STATE_KEY] = outcome.state
    _toast(outcome.toast)
    if outcome.modal:
        st.session_state[MODAL_KEY] = outcome.modal


def _on_pick_project(widget_key: str) -> None:
    choice = st.session_state.get(widget_key)
    _on_nav(f"start:{choice}" if choice else "new")


# --- Shell ------------------------------------------------------------------


def render_sidebar(state: AppState, source: CostIntelDataSource) -> None:
    rail = left_rail(state, source.list_projects())
    with st.sidebar:
        st.html(
            '<div class="brand"><div class="mark" aria-hidden="true">'
            f"{escape(BRAND.mark)}</div><div>"
            f'<div class="eyebrow">{escape(BRAND.eyebrow)}</div>'
            f'<h1 class="brand-title">{escape(BRAND.title)}</h1></div></div>'
        )
        st.button(
            rail.new_analysis_label,
            key="nav-new",
            on_click=_on_nav,
            args=("new",),
            type="primary",
            width="stretch",
        )
        for section in rail.sections:
            st.html(f'<h2 class="nav-title">{escape(section.title)}</h2>')
            if not section.items and section.empty_note:
                st.html(f'<p class="right-note">{escape(section.empty_note)}</p>')
            for item in section.items:
                kind, _, arg = item.action.partition(":")
                key = f"nav-{kind}-{arg}" if arg else f"nav-{kind}"
                label = f"{item.icon} {item.label}"
                st.button(
                    f"{label} (open)" if item.selected else label,
                    key=key,
                    on_click=_on_nav,
                    args=(item.action,),
                    width="stretch",
                )
        footer = "".join(f"<p>{escape(line)}</p>" for line in rail.footer_lines)
        st.html(
            f'<div class="left-footer"><div class="eyebrow">'
            f"{escape(rail.footer_eyebrow)}</div>{footer}</div>"
        )


def render_topbar(session: Session | None) -> None:
    bar = topbar(session)
    left, right = st.columns([4, 1], vertical_alignment="center")
    with left:
        st.html(
            f'<header><h2 class="top-title">{escape(bar.title)} '
            f"<span>{escape(bar.crumb)}</span></h2>"
            f'<p class="top-sub" role="status">{escape(bar.subtitle)}</p></header>'
        )
    with right:
        st.html(f'<span class="header-pill">{escape(bar.pill)}</span>')
        st.button(
            "ⓘ Mission overview",
            key="top-mission",
            help="About this project",
            on_click=_on_nav,
            args=("mission",),
        )


def render_welcome(source: CostIntelDataSource) -> None:
    view = welcome_view(source.list_projects())
    steps = "".join(
        f'<div class="mini-step"><small>{escape(s.kicker)}</small>'
        f"<strong>{escape(s.title)}</strong><p>{escape(s.body)}</p></div>"
        for s in view.steps
    )
    st.html(
        f'<section class="welcome"><div class="intro-tag">{escape(view.tag)}</div>'
        f"<h2>{escape(view.title_lines[0])}<br>"
        f"<em>{escape(view.title_lines[1])}</em></h2>"
        f'<p class="welcome-lead">{escape(view.lead)}</p>'
        f'<div class="mini-steps">{steps}</div>'
        f'<div class="starter-label">{escape(view.starter_label)}</div></section>'
    )
    for column, starter in zip(
        st.columns(len(view.starters)), view.starters, strict=True
    ):
        with column:
            st.button(
                f"{starter.icon} {starter.title}",
                key=f"welcome-start-{starter.project_key}",
                help=starter.blurb,
                on_click=_on_nav,
                args=(f"start:{starter.project_key}",),
                width="stretch",
            )
            st.caption(starter.blurb)
    st.html(f'<p class="welcome-foot">{escape(view.foot)}</p>')


# --- Basket screen ----------------------------------------------------------


def _init_widget(key: str, value: object) -> None:
    if key not in st.session_state:
        st.session_state[key] = value


def render_basket(session: Session, source: CostIntelDataSource) -> None:
    view = basket_view(session, source)
    sid = session.id
    st.html(f'<div class="agent-copy">{escape(view.intro)}</div>')
    st.html(tool_trace(TRACE_LABELS))
    with st.container(border=True):
        st.html(
            '<div class="artifact-top"><div>'
            f"<h3>{escape(view.title)}</h3><p>{escape(view.subtitle)}</p></div>"
            f"{badge(view.badge_label, view.badge_tone)}</div>"
        )
        for column, preset in zip(
            st.columns(len(view.presets)), view.presets, strict=True
        ):
            with column:
                st.button(
                    preset.display_label,
                    key=f"basket-{sid}-preset-{preset.key}",
                    on_click=_on_basket,
                    args=(ChoosePreset(preset.key),),
                    type="primary" if preset.current else "secondary",
                    width="stretch",
                )
        widths = [0.7, 3.2, 0.8, 1.5, 1.5]
        for column, name in zip(st.columns(widths), view.columns, strict=True):
            with column:
                st.html(f'<span class="basket-th">{escape(name)}</span>')
        for row in view.rows:
            use, series, kind, sample, weight = st.columns(
                widths, vertical_alignment="center"
            )
            enable_key = f"basket-{sid}-enable-{row.index}"
            weight_key = weight_widget_key(sid, row.index)
            _init_widget(enable_key, row.enabled)
            _init_widget(weight_key, None if row.weight is None else float(row.weight))
            with use:
                st.checkbox(
                    row.checkbox_label,
                    key=enable_key,
                    disabled=row.checkbox_disabled,
                    on_change=_on_basket,
                    args=(Toggle(row.index, row.enabled),),
                    label_visibility="collapsed",
                )
            with series:
                st.html(
                    f'<span class="series-title">{escape(row.title)}</span>'
                    f'<span class="series-id">{escape(row.series_line)}</span>'
                )
            with kind:
                st.html(f'<span class="source-type">{escape(row.type_label)}</span>')
            with sample:
                st.html(f"<span>{escape(row.sample_label)}</span>")
            with weight:
                st.number_input(
                    row.weight_label,
                    min_value=0.0,
                    max_value=100.0,
                    step=1.0,
                    key=weight_key,
                    disabled=row.weight_disabled,
                    on_change=_on_basket,
                    args=(SetWeight(row.index, None),),
                    label_visibility="collapsed",
                )
        total, actions = st.columns([3, 2], vertical_alignment="center")
        with total:
            st.html(
                '<div class="basket-total" role="status" aria-live="polite">'
                f"<strong>{escape(view.total_label)}</strong>"
                f'<span class="{view.status_tone}">{escape(view.status_label)}'
                "</span></div>"
            )
        with actions:
            normalize_col, approve_col = st.columns(2)
            with normalize_col:
                st.button(
                    "Normalize",
                    key=f"basket-{sid}-normalize",
                    disabled=not view.normalize_enabled,
                    on_click=_on_basket,
                    args=(Normalize(),),
                    width="stretch",
                )
            with approve_col:
                st.button(
                    view.approve_label,
                    key=f"basket-{sid}-approve",
                    disabled=not view.approve_enabled,
                    on_click=_on_basket,
                    args=(Approve(),),
                    type="primary",
                    width="stretch",
                )
        st.html(
            f'<div class="scenario-notice">{escape(view.notice)}</div>'
            f'<div class="fineprint">{escape(view.fineprint)}</div>'
        )
    st.button(
        view.why_link,
        key=f"basket-{sid}-why",
        on_click=_on_basket,
        args=(AskWhy(),),
        type="tertiary",
    )


# --- Conversation feed ------------------------------------------------------


def render_message(
    session: Session, message: Message, is_live_basket: bool, source
) -> None:
    if message.role == "user":
        st.html(f'<div class="user-bubble">{escape(message.text)}</div>')
        return
    st.html('<div class="agent-label">Cost Intelligence Agent</div>')
    if message.kind == "basket":
        if is_live_basket:
            render_basket(session, source)
        else:
            st.caption("Earlier basket proposal; the current basket is shown below.")
    elif message.kind in NOT_BUILT:
        st.info(NOT_BUILT[message.kind])
    elif message.kind == "previous":
        st.html(f'<div class="agent-copy">{escape(PREVIOUS_TEXT)}</div>')
    else:
        st.html(f'<div class="agent-copy">{escape(message.text)}</div>')


def render_feed(session: Session | None, source: CostIntelDataSource) -> None:
    if session is None:
        render_welcome(source)
        return
    baskets = [i for i, m in enumerate(session.messages) if m.kind == "basket"]
    last_basket = baskets[-1] if baskets else -1
    for i, message in enumerate(session.messages):
        render_message(session, message, i == last_basket, source)


def render_composer() -> None:
    for column, (i, prompt) in zip(
        st.columns(len(QUICK_PROMPTS)), enumerate(QUICK_PROMPTS), strict=True
    ):
        with column:
            st.button(
                prompt.label,
                key=f"quick-{i}",
                on_click=_on_query,
                args=(prompt.query,),
                width="stretch",
            )
    st.chat_input(COMPOSER.placeholder, key="composer", on_submit=_on_query)
    st.caption(f"{COMPOSER.hint} · {COMPOSER.foot_note}")


# --- Context panel ----------------------------------------------------------


def _context_card(title: str, status: str, body: str) -> str:
    return (
        '<section class="context-card"><div class="context-head">'
        f'<h3>{escape(title)}</h3><span class="mini-status">{escape(status)}</span>'
        f"</div>{body}</section>"
    )


def render_context(state: AppState, source: CostIntelDataSource) -> None:
    session = state.active
    panel = context_panel(session, source)
    st.html('<h2 class="right-header">Project &amp; evidence</h2>')
    st.html(_context_card("Project context", panel.project_status, ""))
    values = [key for key, _ in panel.project_options]
    labels = dict(panel.project_options)
    picker_key = f"context-project-{state.active_id}"
    st.selectbox(
        "Choose example project",
        values,
        index=values.index(panel.selected_project)
        if panel.selected_project in values
        else 0,
        format_func=labels.get,
        key=picker_key,
        on_change=_on_pick_project,
        args=(picker_key,),
    )
    if panel.meta_lines:
        lines = "".join(
            f'<div class="meta-line"><strong>{escape(k)}</strong><br>{escape(v)}</div>'
            for k, v in panel.meta_lines
        )
    else:
        lines = f'<div class="meta-line">{escape(panel.empty_note)}</div>'
    st.html(lines)
    sources = "".join(
        '<div class="source"><i class="source-dot" aria-hidden="true"></i><div>'
        f"<strong>{escape(name)}</strong><span>{escape(detail)}</span></div></div>"
        for name, detail in panel.sources
    )
    st.html(
        _context_card(
            "Backend data sources",
            "Simulated",
            sources + f'<p class="right-note">{escape(panel.sources_note)}</p>',
        )
    )
    rows = "".join(
        f'<div class="phase-row"><span>{escape(r.label)}</span>'
        f'<b class="{"ok" if r.ok else ""}">{escape(r.text)}</b></div>'
        for r in panel.progress
    )
    st.html(_context_card("Analysis progress", panel.progress_status, rows))
    st.html(
        _context_card(
            "Composite factor",
            panel.composite_status,
            f'<div class="overview-number">{escape(panel.composite_value)}</div>'
            f'<div class="overview-caption">{escape(panel.composite_caption)}</div>',
        )
    )
    st.button(
        "Inspect calculation & provenance →",
        key="context-audit",
        on_click=_on_nav,
        args=("audit",),
        type="tertiary",
    )
    st.html(f'<p class="right-note">{escape(panel.mission_note)}</p>')


# --- Dialogs (the HTML's modals) ------------------------------------------------


def _kicker(text: str) -> None:
    st.html(f'<div class="eyebrow modal-kicker">{escape(text)}</div>')


def open_audit_dialog(state: AppState, source: CostIntelDataSource) -> None:
    payload = json.dumps(audit_payload(state.active, source), indent=2)

    @st.dialog("Calculation evidence & audit trail", width="large")
    def _dialog() -> None:
        _kicker("VERSIONED SOURCE EVIDENCE")
        st.write(
            "Result metadata, project assumptions, component weights, annual "
            "observations, snapshot identifiers, approval, and a selected-year "
            "adjustment. The canonical factors are transmitted as decimal strings."
        )
        st.code(payload, language="json")
        st.download_button(
            "Download audit JSON ↓",
            payload,
            file_name=AUDIT_FILENAME,
            mime="application/json",
            type="primary",
        )

    _dialog()


def open_pars_dialog(state: AppState, source: CostIntelDataSource) -> None:
    view = pars_preview(state.active, source)

    @st.dialog(view.title, width="large")
    def _dialog() -> None:
        _kicker(view.kicker)
        if not view.available:
            st.error(view.body)
            return
        st.write(view.body)
        st.code(json.dumps(view.payload, indent=2), language="json")

    _dialog()


def open_mission_dialog() -> None:
    view = mission_view()

    @st.dialog(view.title, width="large")
    def _dialog() -> None:
        _kicker(view.kicker)
        st.markdown(f"**Challenge:** {view.challenge}")
        for column, unit in zip(st.columns(len(view.units)), view.units, strict=True):
            with column:
                st.html(
                    f'<div class="mission-unit"><div class="eyebrow">'
                    f"{escape(unit.eyebrow)}</div><strong>{escape(unit.title)}"
                    f"</strong><span>{escape(unit.body)}</span></div>"
                )
        st.markdown(f"**Mission connection:** {view.connection}")
        st.warning(view.disclaimer)

    _dialog()


# --- Page -------------------------------------------------------------------


def main() -> None:
    st.set_page_config(page_title=PAGE_TITLE, layout="wide")
    st.html(f"<style>{app_css()}</style>")
    source = get_data_source()
    state = _state()
    if toast := st.session_state.pop(TOAST_KEY, None):
        st.toast(toast)

    render_sidebar(state, source)
    main_area, context_area = st.columns([3, 1], gap="large")
    with main_area:
        render_topbar(state.active)
        render_feed(state.active, source)
        render_composer()
    with context_area:
        render_context(state, source)

    modal = st.session_state.pop(MODAL_KEY, None)
    if modal == "audit":
        open_audit_dialog(state, source)
    elif modal == "pars":
        open_pars_dialog(state, source)
    elif modal == "mission":
        open_mission_dialog()


main()
