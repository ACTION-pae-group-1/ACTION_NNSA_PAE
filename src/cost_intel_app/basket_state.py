"""JSON-safe basket state for the MCP app.

The MCP app is stateless between tool calls: the renderer holds the basket in
client state and sends the rows back with each action. These functions rebuild
a ``cost_intel_ui`` session from those rows, apply the same transitions the
Streamlit screen uses (``cost_intel_ui.session``), and render the result with
``cost_intel_ui.basket_view``, so both surfaces show the same numbers.

Weights travel as plain decimal strings. Normalized weights are rounded to six
places, well inside the session's 0.00001 percent tolerance, so a normalized
basket still totals 100% after a round trip through the UI.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from decimal import Decimal, InvalidOperation
from functools import partial
from typing import Any, TypeVar

from cost_intel_ui.basket_view import basket_view
from cost_intel_ui.comparison_view import ComparisonView, comparison_view
from cost_intel_ui.contract import validate_packet
from cost_intel_ui.data_access import CostIntelDataSource, ResultPacket
from cost_intel_ui.results_view import (
    MAX_LISTED_ISSUES,
    AdjustmentView,
    BlockedResult,
    ExplorerView,
    NoAdjustmentRequired,
    RibbonSegment,
    UnknownComponent,
    WaterfallBar,
    adjustment_view,
    component_detail,
    eligible_adjustment_years,
    explorer_view,
    filtered_rows,
    main_chart,
    table_view,
)
from cost_intel_ui.session import (
    BasketRow,
    Outcome,
    Phase,
    Session,
    approve,
    matching_scenario,
    normalize,
    parse_custom_scenario,
    result_for_session,
    select_component,
    start_session,
    use_preset,
)

_PLACES = Decimal("0.000001")
_PHASES: tuple[Phase, ...] = ("review", "approved")

# Fixed user-facing text for refused requests. Input is never echoed back.
UNKNOWN_PROJECT = "This project has no basket."
UNKNOWN_PHASE = "This basket phase is not recognized."
ROW_COUNT = "The basket rows do not match this project; showing the recommended basket."
WEIGHT_ERROR = "Weights must be from 0 to 100 with at most six decimal places."
APPROVED_ERROR = "This basket is approved and locked. Choose a preset to change it."
UNAVAILABLE_SCENARIO = "That allocation is not available for this project."
VIEW_ERROR = "That view option is not available for this basket."
MODES = ("normalized", "raw")
SORTS = ("asc", "desc")

# The view unrolls these lists into fixed literal slots instead of a ForEach,
# because a loop variable in a binding resolves wrongly in the browser. A slot
# past the data is blank and hidden (``visible`` False) or an empty string.
STAT_SLOTS = 3
META_CHIP_SLOTS = 5
ISSUE_SLOTS = MAX_LISTED_ISSUES

_T = TypeVar("_T")


def _slots(items: Sequence[_T], count: int, blank: Callable[[], _T]) -> list[_T]:
    """``items`` padded with fresh blanks to exactly ``count`` slots.

    More items than slots would drop data, so that raises instead of truncating.
    """
    if len(items) > count:
        raise ValueError(f"{len(items)} entries do not fit {count} view slots")
    return [*items, *(blank() for _ in range(count - len(items)))]


_blank_stat = partial(dict, visible=False, label="", value="", tone=None)
_blank_segment = partial(
    dict,
    visible=False,
    component_id="",
    name="",
    percent_label="",
    label="",
    color_hex="",
    selected=False,
)
_blank_math = partial(dict, visible=False, label="", value="")


class _Refused(Exception):
    """A request the basket cannot accept.

    ``str(exc)`` is fixed text. ``session`` is the basket to show instead, or
    None when there is no basket to show.
    """

    def __init__(self, message: str, session: Session | None = None) -> None:
        super().__init__(message)
        self.session = session


def weight_text(weight: Decimal | None) -> str:
    """Format a weight percent as a plain decimal string.

    Returns "" when the weight is missing or cannot be shown at transport precision.
    """
    if weight is None or not weight.is_finite():
        return ""
    try:
        return format(weight.quantize(_PLACES).normalize(), "f")
    except InvalidOperation:
        return ""


def _parse_weight(value: Any) -> Decimal | None:
    """A weight percent from a request.

    Blank or non-numeric input is missing (None). A finite number outside 0 to 100,
    or with more than six decimal places, is refused.
    """
    if value is None or isinstance(value, bool):
        return None
    try:
        weight = Decimal(str(value).strip())
    except InvalidOperation:
        return None
    if not weight.is_finite():
        return None
    # The range check comes first, so quantize only ever sees values from 0 to 100.
    if not 0 <= weight <= 100 or weight != weight.quantize(_PLACES):
        raise _Refused(WEIGHT_ERROR)
    return weight


def _session(
    source: CostIntelDataSource,
    project_key: str,
    rows: Sequence[Mapping[str, Any]] | None = None,
    phase: str = "review",
    scenario: str | None = None,
) -> Session:
    """The session a request asks for. Raises _Refused when it cannot be built."""
    if source.get_project(project_key) is None:
        raise _Refused(UNKNOWN_PROJECT)
    if phase not in _PHASES:
        raise _Refused(UNKNOWN_PHASE)
    # An empty source year means "the latest eligible year", so the session's
    # own default year is not used here.
    session = replace(
        start_session(source, project_key, session_id=1, now=""), selected_year=""
    )
    if rows is None:
        return replace(session, phase=phase)
    if phase == "approved":
        return _locked_session(source, session, rows, scenario)
    if len(rows) != len(session.rows):
        raise _Refused(ROW_COUNT, session)
    parsed, refusal = _rows_from(rows)
    edited = replace(session, rows=parsed)
    if refusal is not None:
        raise _Refused(refusal, edited)
    return edited


def _rows_from(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[tuple[BasketRow, ...], str | None]:
    """The request's rows, and the refusal message when a weight was refused.

    A refused weight is left blank so the rest of the basket still shows.
    """
    parsed: list[BasketRow] = []
    refusal: str | None = None
    for r in rows:
        try:
            weight = _parse_weight(r.get("weight"))
        except _Refused as exc:
            weight, refusal = None, refusal or str(exc)
        enabled = bool(r.get("enabled"))
        # Excluded components cannot retain a hidden nonzero allocation.
        # Re-enabling starts at zero and requires an explicit new weight.
        parsed.append(
            BasketRow(enabled=enabled, weight=weight if enabled else Decimal(0))
        )
    return tuple(parsed), refusal


def _locked_session(
    source: CostIntelDataSource,
    session: Session,
    rows: Sequence[Mapping[str, Any]],
    scenario: str | None = None,
) -> Session:
    """An approved basket must retain its exact preset or custom allocation."""
    presets = dict(source.scenario_weights(session.data_project_key))
    if scenario is None:
        locked = replace(session, phase="approved")
    elif scenario.startswith("custom:"):
        custom_rows = parse_custom_scenario(scenario)
        if custom_rows is None or len(custom_rows) != len(session.rows):
            raise _Refused(UNAVAILABLE_SCENARIO, replace(session, phase="approved"))
        locked = replace(session, phase="approved", rows=custom_rows, scenario=scenario)
    elif presets.get(scenario):
        locked = replace(
            session,
            phase="approved",
            rows=tuple(BasketRow(enabled=True, weight=w) for w in presets[scenario]),
            scenario=scenario,
        )
    else:
        raise _Refused(UNAVAILABLE_SCENARIO, replace(session, phase="approved"))
    if len(rows) == len(locked.rows):
        parsed, refusal = _rows_from(rows)
        matched = matching_scenario(parsed, presets) if refusal is None else None
        if scenario and scenario.startswith("custom:"):
            if refusal is None and parsed == locked.rows:
                return locked
        elif matched is not None and scenario in (None, matched):
            return replace(locked, rows=parsed, scenario=matched)
    raise _Refused(APPROVED_ERROR, locked)


def _unavailable(project_key: str, message: str) -> dict[str, Any]:
    """The state for a request with no basket to show, with the same keys."""
    return {
        "state": "error",
        "error": message,
        "project_key": project_key,
        "phase": "review",
        "locked": False,
        "scenario": None,
        "approved_at": None,
        "title": "Basket unavailable",
        "subtitle": "",
        "badge_label": "",
        "badge_tone": "amber",
        "presets": [],
        "columns": [],
        "rows": [],
        "total_label": "",
        "status_label": "",
        "status_tone": "invalid",
        "normalize_enabled": False,
        "approve_enabled": False,
        "approve_label": "",
        "notice": "",
        "fineprint": "",
        "results": None,
        "toast": message,
    }


def _respond(
    source: CostIntelDataSource,
    project_key: str,
    rows: Sequence[Mapping[str, Any]] | None,
    phase: str,
    step: Callable[[Session], Outcome] | None = None,
    scenario: str | None = None,
) -> dict[str, Any]:
    """Build the requested basket, apply ``step``, and return its state.

    A refused request returns an error state instead of raising: the basket it
    keeps, with the fixed message in ``error`` and ``toast``. A step may refuse
    too, by raising _Refused with the session to keep.
    """
    try:
        session = _session(source, project_key, rows, phase, scenario)
        outcome = step(session) if step else Outcome(session)
    except _Refused as refused:
        if refused.session is None:
            return _unavailable(project_key, str(refused))
        return _state(refused.session, source, error=str(refused))
    return _state(outcome.session, source, outcome.toast)


def _state(
    session: Session,
    source: CostIntelDataSource,
    toast: str | None = None,
    error: str = "",
) -> dict[str, Any]:
    view = basket_view(session, source)
    return {
        "state": "error" if error else "ready",
        "error": error,
        "project_key": session.project_key,
        "phase": session.phase,
        "locked": session.phase == "approved",
        "scenario": session.scenario,
        "approved_at": session.approved_at,
        # view.intro and view.why_link are chat narration; the host's model
        # owns the conversation, so they are left out of the app.
        "title": view.title,
        "subtitle": view.subtitle,
        "badge_label": view.badge_label,
        "badge_tone": view.badge_tone,
        "presets": [
            {
                "key": p.key,
                "label": p.label,
                "display_label": p.display_label,
                "current": p.current,
            }
            for p in view.presets
        ],
        "columns": list(view.columns),
        "rows": [
            {
                "index": r.index,
                "enabled": r.enabled,
                "title": r.title,
                "series_line": r.series_line,
                "type_label": r.type_label,
                "sample_label": r.sample_label,
                "weight": weight_text(r.weight),
                "checkbox_label": r.checkbox_label,
                "weight_label": r.weight_label,
                "checkbox_disabled": r.checkbox_disabled,
                "weight_disabled": r.weight_disabled,
            }
            for r in view.rows
        ],
        "total_label": view.total_label,
        "status_label": view.status_label,
        "status_tone": view.status_tone,
        "normalize_enabled": view.normalize_enabled,
        "approve_enabled": view.approve_enabled,
        "approve_label": view.approve_label,
        "notice": view.notice,
        "fineprint": view.fineprint,
        "results": _results(session, source),
        "toast": error or toast,
    }


def _segment_state(segment: RibbonSegment, component_id: str | None) -> dict[str, Any]:
    return {
        "visible": True,
        "component_id": segment.component_id,
        "name": segment.name,
        "percent_label": segment.percent_label,
        "label": f"{segment.name} · {segment.percent_label}",
        "color_hex": segment.color_hex,
        "selected": segment.component_id == component_id,
    }


def _explorer_state(
    explorer: ExplorerView | BlockedResult,
    component_id: str | None,
    segments: int,
) -> dict[str, Any]:
    """The explorer header, stats, ribbon, and issues, in fixed slots.

    Blocked and unblocked results return the same keys, so the view binds one
    shape. ``segments`` is the number of ribbon slots, one per component.
    """
    if isinstance(explorer, BlockedResult):
        return {
            "blocked": True,
            "title": explorer.title,
            "subtitle": "",
            "badge_label": "",
            "warning": "",
            "meta_chips": _slots([], META_CHIP_SLOTS, str),
            "stats": _slots([], STAT_SLOTS, _blank_stat),
            "ribbon": _slots([], segments, _blank_segment),
            "fineprint": explorer.footer,
            "body": explorer.body,
            "issues": _slots(list(explorer.issues), ISSUE_SLOTS, str),
            "footer": explorer.footer,
        }
    return {
        "blocked": False,
        "title": explorer.title,
        "subtitle": explorer.subtitle,
        "badge_label": explorer.badge_label,
        "warning": explorer.warning,
        "meta_chips": _slots(list(explorer.meta_chips), META_CHIP_SLOTS, str),
        "stats": _slots(
            [
                {"visible": True, "label": s.label, "value": s.value, "tone": s.tone}
                for s in explorer.stats
            ],
            STAT_SLOTS,
            _blank_stat,
        ),
        "ribbon": _slots(
            [_segment_state(r, component_id) for r in explorer.ribbon],
            segments,
            _blank_segment,
        ),
        "fineprint": explorer.fineprint,
        "body": "",
        "issues": _slots([], ISSUE_SLOTS, str),
        "footer": "",
    }


def _chart_rows(packet: ResultPacket) -> list[dict[str, Any]]:
    """One row per period: each component's stacked height and the composite.

    The stacked heights sum to the composite factor from the shared results view.
    """
    chart = main_chart(packet)
    rows = []
    for i, period in enumerate(chart.periods):
        row: dict[str, Any] = {"period": period, "composite": chart.composite[i]}
        for layer in chart.series:
            row[layer.component_id] = round(layer.tops[i] - layer.bottoms[i], 6)
        rows.append(row)
    return rows


def _comparison_state(view: ComparisonView) -> dict[str, Any]:
    return {
        "title": view.title,
        "intro": view.intro,
        "boxes": [
            {
                "key": b.preset_key,
                "label": b.label,
                "value": b.value,
                "weights_label": b.weights_label,
                "approved": b.approved,
            }
            for b in view.boxes
        ],
        "note": view.note,
    }


def _component_state(
    packet: ResultPacket, component_id: str | None, mode: str
) -> dict[str, Any]:
    """The selected component's history for the component tab, in ``mode``."""
    detail = component_detail(packet, component_id, mode)
    if isinstance(detail, UnknownComponent):
        return {
            "component_id": component_id,
            "title": "",
            "metadata": "",
            "footnote": "",
            "rows": [],
            "y_min": 0.0,
            "y_max": 0.0,
            "reference_line": None,
            "message": detail.message,
        }
    return {
        "component_id": detail.component_id,
        "title": detail.title,
        "metadata": detail.metadata,
        "footnote": detail.footnote,
        "rows": [
            {"period": str(year), "value": value}
            for year, value in zip(detail.years, detail.values, strict=True)
        ],
        "y_min": detail.y_min,
        "y_max": detail.y_max,
        "reference_line": detail.reference_line,
        "message": "",
    }


_TAB_ERRORS = (KeyError, TypeError, ValueError, ArithmeticError)
_TAB_FAILED = "This tab could not be drawn from the returned result."


def _waterfall_rows(bars: Sequence[WaterfallBar]) -> list[dict[str, Any]]:
    """Waterfall rows for the chart: totals in percent, steps in percentage points.

    The chart adds each step to a running total and draws totals from zero, so
    the first total is the 100% source year and the last is the base factor.
    """
    return [
        {
            "label": bar.label,
            "value": round((bar.end if bar.is_total else bar.end - bar.start) * 100, 8),
            "total": bar.is_total,
        }
        for bar in bars
    ]


def _adjustment_state(
    packet: ResultPacket, segments: int, requested: str = ""
) -> dict[str, Any]:
    """The adjustment-to-base waterfall for a source year, as rows.

    The year is ``requested`` when one is chosen, otherwise the latest eligible
    year. ``segments`` is the number of math-row slots, one per component step.
    A malformed record fails only this tab; the rest of the result still shows.
    """
    empty: dict[str, Any] = {
        "year": None,
        "source_year": "",
        "base_year": None,
        "caption": "",
        "source_composite": "",
        "adjustment_factor": "",
        "waterfall": [],
        "math_rows": _slots([], segments, _blank_math),
        "ending_factor": "",
        "reconcile": "",
        "note": "",
        "message": "",
    }
    try:
        years = eligible_adjustment_years(packet)
        if not years:
            return {**empty, "message": "No complete adjustment year is available."}
        year = requested or years[-1]
        latest = packet.result["composite_points"][-1]["period"]
        note = (
            f"No complete adjustment for {latest}; showing {year}."
            if not requested and year != latest
            else ""
        )
        view = adjustment_view(packet, year)
        if isinstance(view, AdjustmentView):
            return {
                "year": year,
                "source_year": view.source_year,
                "base_year": view.base_year,
                "caption": view.caption,
                "source_composite": view.source_composite,
                "adjustment_factor": view.adjustment_factor,
                "waterfall": _waterfall_rows(view.bars),
                "math_rows": _slots(
                    [
                        {"visible": True, "label": label, "value": value}
                        for label, value in view.math_rows
                    ],
                    segments,
                    _blank_math,
                ),
                "ending_factor": view.ending_factor,
                "reconcile": view.reconcile,
                "note": note,
                "message": "",
            }
        if isinstance(view, NoAdjustmentRequired):
            return {**empty, "year": year, "note": note, "message": view.message}
        detail = f"{view.title}. {view.detail}"
        return {**empty, "year": year, "note": note, "message": detail}
    except _TAB_ERRORS:
        return {**empty, "message": _TAB_FAILED}


def _table_state(
    packet: ResultPacket, year: str, component: str, sort: str
) -> dict[str, Any]:
    """The observation rows that pass the filters, keyed by column, for the data tab.

    The count is "shown of total", so a filtered table says how much it hides.
    """
    try:
        view = table_view(packet, year, component, sort)
        rows = [dict(zip(view.columns, row, strict=True)) for row in view.rows]
        total = len(filtered_rows(packet, "all", "all", "asc"))
    except _TAB_ERRORS:
        return {
            "columns": [],
            "rows": [],
            "count_label": "",
            "message": _TAB_FAILED,
        }
    return {
        "columns": list(view.columns),
        "rows": rows,
        "count_label": f"{len(rows)} of {total} observations",
        "message": "",
    }


def _component_ids(packet: ResultPacket | None) -> list[str]:
    if packet is None:
        return []
    return [c.get("component_id") for c in packet.result.get("components") or []]


def _selected_component(session: Session, packet: ResultPacket | None) -> str | None:
    """The chosen component when the result has it, else the first component."""
    ids = _component_ids(packet)
    if session.selected_comp in ids:
        return session.selected_comp
    return ids[0] if ids else None


def _results(session: Session, source: CostIntelDataSource) -> dict[str, Any] | None:
    """The results explorer and scenario comparison, once a basket is approved.

    ``selection`` is the view as shown: the component, unit, source year, and
    table filters in effect. The browser sends these back with each change.
    """
    if session.phase != "approved":
        return None
    packet = result_for_session(session, source)
    segments = len(source.list_sources())
    component_id = _selected_component(session, packet)
    explorer = explorer_view(packet, component_id)
    readable = packet is not None and isinstance(explorer, ExplorerView)
    adjustment = (
        _adjustment_state(packet, segments, session.selected_year) if readable else None
    )
    return {
        "explorer": _explorer_state(explorer, component_id, segments),
        "selection": {
            "component": component_id or "",
            "mode": session.detail_mode,
            "source_year": (adjustment or {}).get("year") or session.selected_year,
            "table_year": session.table_year,
            "table_comp": session.table_comp,
            "table_sort": session.table_sort,
        },
        "chart": _chart_rows(packet) if readable else [],
        "component": (
            _component_state(packet, component_id, session.detail_mode)
            if readable
            else None
        ),
        "adjustment": adjustment,
        "table": (
            _table_state(
                packet, session.table_year, session.table_comp, session.table_sort
            )
            if readable
            else None
        ),
        "comparison": _comparison_state(comparison_view(session, source)),
    }


def _rounded(outcome: Outcome) -> Outcome:
    """Round weights to the transport precision so the UI sees what it sends."""
    rows = tuple(
        replace(r, weight=None if r.weight is None else r.weight.quantize(_PLACES))
        for r in outcome.session.rows
    )
    return replace(outcome, session=replace(outcome.session, rows=rows))


def initial_basket(source: CostIntelDataSource, project_key: str) -> dict[str, Any]:
    """The recommended basket for a project, ready for review."""
    return _respond(source, project_key, None, "review")


def update_basket(
    source: CostIntelDataSource,
    project_key: str,
    rows: Sequence[Mapping[str, Any]],
    phase: str,
    scenario: str | None = None,
) -> dict[str, Any]:
    """Recompute totals and status after include or weight edits.

    Approved preset and custom allocations remain locked across tool calls.
    Without a scenario token, only a preset allocation can be reconstructed.
    """
    return _respond(source, project_key, rows, phase, scenario=scenario)


def normalize_basket(
    source: CostIntelDataSource,
    project_key: str,
    rows: Sequence[Mapping[str, Any]],
    phase: str,
    scenario: str | None = None,
) -> dict[str, Any]:
    return _respond(
        source,
        project_key,
        rows,
        phase,
        lambda s: _rounded(normalize(s)),
        scenario=scenario,
    )


def approve_basket(
    source: CostIntelDataSource,
    project_key: str,
    rows: Sequence[Mapping[str, Any]],
    phase: str,
    now: str,
    scenario: str | None = None,
) -> dict[str, Any]:
    return _respond(
        source,
        project_key,
        rows,
        phase,
        lambda s: approve(s, source, now),
        scenario=scenario,
    )


def choose_preset(
    source: CostIntelDataSource, project_key: str, preset_key: str, phase: str
) -> dict[str, Any]:
    return _respond(
        source, project_key, None, phase, lambda s: use_preset(s, source, preset_key)
    )


def _chosen_view(
    session: Session, source: CostIntelDataSource, choice: Mapping[str, str]
) -> Session:
    """The session with the explorer choices applied, or _Refused for a bad one.

    Only an approved basket with a readable result has choices. Anything else
    keeps its session, and a blocked result has no tabs to choose among.
    """
    if session.phase != "approved":
        return session
    packet = result_for_session(session, source)
    if packet is None or validate_packet(packet):
        return session
    components = _component_ids(packet)
    periods = [str(p["period"]) for p in packet.result["composite_points"]]
    valid = (
        (not choice["component"] or choice["component"] in components)
        and choice["mode"] in MODES
        and (not choice["source_year"] or choice["source_year"] in periods)
        and (choice["table_year"] == "all" or choice["table_year"] in periods)
        and (choice["table_comp"] == "all" or choice["table_comp"] in components)
        and choice["table_sort"] in SORTS
    )
    if not valid:
        raise _Refused(VIEW_ERROR, session)
    chosen = (
        select_component(session, choice["component"])
        if choice["component"]
        else session
    )
    return replace(
        chosen,
        detail_mode=choice["mode"],
        selected_year=choice["source_year"],
        table_year=choice["table_year"],
        table_comp=choice["table_comp"],
        table_sort=choice["table_sort"],
    )


def explore_basket(
    source: CostIntelDataSource,
    project_key: str,
    rows: Sequence[Mapping[str, Any]],
    phase: str,
    scenario: str | None = None,
    *,
    component: str = "",
    mode: str = "normalized",
    source_year: str = "",
    table_year: str = "all",
    table_comp: str = "all",
    table_sort: str = "asc",
) -> dict[str, Any]:
    """Apply the explorer choices to an approved basket and return its state.

    An empty ``component`` keeps the current one, which starts as the first
    component. An empty ``source_year`` means the latest eligible year. Any
    value that is not in the result is refused with a fixed message.
    """
    choice = {
        "component": component,
        "mode": mode,
        "source_year": source_year,
        "table_year": table_year,
        "table_comp": table_comp,
        "table_sort": table_sort,
    }
    return _respond(
        source,
        project_key,
        rows,
        phase,
        lambda s: Outcome(_chosen_view(s, source, choice)),
        scenario=scenario,
    )


def _catalog_packets(source: CostIntelDataSource) -> list[ResultPacket]:
    packets = []
    for project in source.list_projects():
        for scenario in source.scenario_weights(project.key):
            packet = source.get_result(project.key, scenario)
            if packet is not None:
                packets.append(packet)
    return packets


def catalog_periods(source: CostIntelDataSource) -> tuple[str, ...]:
    """Every annual period in the catalog, in order: the period choices."""
    return tuple(
        sorted(
            {
                str(p["period"])
                for packet in _catalog_packets(source)
                for p in packet.result["composite_points"]
            }
        )
    )


def catalog_adjustment_years(source: CostIntelDataSource) -> tuple[str, ...]:
    """Every year that is eligible for an adjustment somewhere in the catalog."""
    return tuple(
        sorted(
            {
                year
                for packet in _catalog_packets(source)
                for year in eligible_adjustment_years(packet)
            }
        )
    )
