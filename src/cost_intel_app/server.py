"""FastMCP MCP App: the Recommended PPI escalation basket.

The model sees one tool, ``ppi_basket``. Calling it returns a Prefab UI that an
MCP Apps host renders in a sandboxed iframe from the tool's ``ui://`` renderer
resource. The include checkboxes, weight inputs, presets, Normalize, and
Approve call UI-only backend tools, which recompute the basket with the same
``cost_intel_ui`` session logic the Streamlit screen uses.

There is no chat surface here; the host's model owns the conversation.

Preview locally::

    fastmcp dev apps src/cost_intel_app/server.py:mcp
"""

from __future__ import annotations

import csv
import io
import os
import re
import secrets
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Any, Literal

from fastmcp import FastMCP, FastMCPApp
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_http_request
from prefab_ui.actions import OpenLink, SetState, ShowToast
from prefab_ui.actions.mcp import CallTool
from prefab_ui.app import PrefabApp
from prefab_ui.components import (
    Badge,
    Button,
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
    Checkbox,
    Column,
    DataTable,
    DataTableColumn,
    Else,
    ForEach,
    If,
    Input,
    Muted,
    Row,
    Select,
    SelectOption,
    Small,
    Tab,
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
    Tabs,
    Text,
)
from prefab_ui.components.charts import (
    AreaChart,
    ChartSeries,
    LineChart,
    WaterfallChart,
)
from prefab_ui.rx import ERROR, EVENT, RESULT, STATE, Rx
from pydantic import BaseModel, Field, StringConstraints, ValidationError
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response

if __package__ in (None, ""):  # loaded by file path, e.g. ``fastmcp dev apps``
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cost_intel_app import (  # noqa: E402
    basket_state,  # noqa: E402
    pars_live,
    pars_panels,
)
from cost_intel_app.caef_live_inference import predict_retrieved_project  # noqa: E402
from cost_intel_app.caef_summary import (  # noqa: E402
    CAEF_CATEGORY_SLOTS,
    empty_caef_summary,
    read_caef_summary,
    run_model_for_project,
    saved_prediction_path,
)
from cost_intel_app.chat_bridge import ask_readonly_chat  # noqa: E402
from cost_intel_app.wbs_bls_mapping import (  # noqa: E402
    empty_mapping_review,
    review_mapping,
)
from cost_intel_ui.fake_data import InMemoryDataSource  # noqa: E402

APP_NAME = "nnsa-cost-intel-basket"
ENTRY_TOOL = "ppi_basket"

ProjectKey = Literal["y12", "pantex", "lanl"]
PhaseArg = Literal["review", "approved"]
ModeArg = Literal["normalized", "raw"]
SortArg = Literal["asc", "desc"]

app = FastMCPApp(APP_NAME)
_source = InMemoryDataSource()
# The basket is built from fixed lists: one row per source, three presets, and
# five columns. The view unrolls them with literal state paths, so no action
# key or argument depends on a ForEach variable.
# The layout follows the HTML reference and uses NNSA PA&E accents. The
# renderer must support Tailwind arbitrary-value utilities for precise colors.

# NNSA PA&E palette: PMS 282 navy, PMS 193 red, and a light gray tint.
# Keep universal contrast rules scoped to the App; Prefab renders controls in
# its own iframe. Explicit !important utilities defeat default theme colors.
NNSA_NAVY = "#041E42"
NNSA_RED = "#BF0D3E"
NNSA_GRAY = "#D8D5D2"
# Focus: a 2px outline set off from the control, in the existing focus color.
# #8DB5C4 is 3:1 or better on the navy and card surfaces; light panels override it.
FOCUS_OUTLINE_CLASS = (
    "focus-visible:!outline-solid focus-visible:!outline-2 "
    "focus-visible:!outline-offset-2 focus-visible:!outline-[#8DB5C4]"
)
BUTTON_CLASS = (
    "!bg-[#F4F2F0] !text-[#041E42] !border-[#8995A7] "
    "hover:!bg-[#D8D5D2] " + FOCUS_OUTLINE_CLASS + " "
    # Disabled keeps Prefab's 50% dimming. The navy label on the light fill still
    # reaches 3:1 after dimming, so disabled stays distinct from enabled.
    "disabled:!bg-[#F4F2F0] disabled:!text-[#041E42]"
)
# The selected mode is disabled to avoid redundant calls, but stays visibly
# active: full opacity, muted blue, and a border that is 3:1 on the card.
ACTIVE_MODE_BUTTON_CLASS = (
    BUTTON_CLASS + " disabled:!opacity-100 disabled:!bg-[#285A77] "
    "disabled:!text-white disabled:!border-[#8995A7]"
)
SHELL_CLASS = (
    "w-full min-w-0 rounded-xl p-3 !bg-[#041E42] !text-white "
    "[&_input]:!text-[#041E42] [&_input]:!bg-white "
    "[&_select]:!text-[#041E42] [&_select]:!bg-white"
)
# Dark cards must override Prefab's inherited dark text and muted labels.
_CARD_TEXT = (
    " [&_p]:!text-slate-100 [&_small]:!text-slate-200 "
    "[&_.text-muted-foreground]:!text-slate-200 "
    "[&_[data-slot=card-description]]:!text-slate-200 "
    "[&_label]:!text-slate-100 [&_td]:!text-slate-100 [&_th]:!text-slate-100 "
    "[&_[role=tabpanel]]:!text-slate-100 "
    "[&_.recharts-cartesian-axis-tick_text]:!fill-white "
    "[&_.recharts-legend-item-text]:!text-white"
)
PANE_CARD_CLASS = (
    "border border-[#6C7C90] bg-[#142D4F] rounded-[13px] !text-white" + _CARD_TEXT
)
EVIDENCE_CARD_CLASS = (
    "border border-[#6C7C90] bg-[#142D4F] rounded-[11px] !text-white" + _CARD_TEXT
)
# The "outline" Badge variant defaults to a dark foreground color meant for light
# backgrounds; every card in this app is dark navy, so it renders unreadable
# (black-on-navy) unless overridden. Apply to every outline-variant Badge.
OUTLINE_BADGE_CLASS = "!text-slate-100 !border-slate-400"

BASKET_ROW_COUNT = len(_source.list_sources())
_PRESET_KEYS = ("recommended", "materials", "equipment")
_BASKET_COLUMN_COUNT = 5
# Option lists for the explorer's selects. Each is fixed at build time from the
# catalog; an unavailable choice for one result is refused, not hidden.
_SOURCE_YEARS = basket_state.catalog_adjustment_years(_source)
_PERIOD_CHOICES = (
    ("all", "All years"),
    *((p, p) for p in basket_state.catalog_periods(_source)),
)
_COMPONENT_CHOICES = (
    ("all", "All components"),
    *((s.component_id, s.name) for s in _source.list_sources()),
)
_SORT_CHOICES = (("asc", "Period ascending"), ("desc", "Period descending"))


class BasketRowInput(BaseModel):
    """A basket row as the UI sends it back; display fields are ignored."""

    enabled: bool = False
    weight: str | float | int | None = None


def _rows(rows: list[BasketRowInput]) -> list[dict[str, Any]]:
    return [r.model_dump() for r in rows]


@app.tool()
def choose_demo_project(project_key: ProjectKey) -> dict[str, Any]:
    """Switch the synthetic NNSA example, never a PARS project selection."""
    return _with_workflow(basket_state.initial_basket(_source, project_key))


@app.tool()
def update_basket(
    project_key: ProjectKey,
    rows: list[BasketRowInput],
    phase: PhaseArg,
    scenario: str | None = None,
) -> dict[str, Any]:
    """Recompute totals and status after an include or weight edit."""
    return _with_workflow(
        basket_state.update_basket(_source, project_key, _rows(rows), phase, scenario)
    )


@app.tool()
def reopen_allocation(
    project_key: ProjectKey,
    rows: list[BasketRowInput],
) -> dict[str, Any]:
    """Return an approved allocation to editable review without approving edits."""
    return _with_workflow(
        basket_state.update_basket(_source, project_key, _rows(rows), "review")
    )


@app.tool()
def normalize_basket(
    project_key: ProjectKey,
    rows: list[BasketRowInput],
    phase: PhaseArg,
    scenario: str | None = None,
) -> dict[str, Any]:
    """Rescale the included weights to total 100%."""
    return _with_workflow(
        basket_state.normalize_basket(
            _source, project_key, _rows(rows), phase, scenario
        )
    )


@app.tool()
def approve_basket(
    project_key: ProjectKey,
    rows: list[BasketRowInput],
    phase: PhaseArg,
    scenario: str | None = None,
) -> dict[str, Any]:
    """Approve a valid preset or synthetic locally calculated allocation."""
    now = datetime.now(UTC).isoformat(timespec="seconds")
    return _with_workflow(
        basket_state.approve_basket(
            _source, project_key, _rows(rows), phase, now, scenario
        )
    )


@app.tool()
def choose_preset(
    project_key: ProjectKey, preset_key: str, phase: PhaseArg
) -> dict[str, Any]:
    """Load one of the precomputed preset allocations for review."""
    return _with_workflow(
        basket_state.choose_preset(_source, project_key, preset_key, phase)
    )


@app.tool()
def explore_basket(
    project_key: ProjectKey,
    rows: list[BasketRowInput],
    phase: PhaseArg,
    scenario: str | None = None,
    component: str = "",
    mode: ModeArg = "normalized",
    source_year: str = "",
    table_year: str = "all",
    table_comp: str = "all",
    table_sort: SortArg = "asc",
) -> dict[str, Any]:
    """Apply the component, unit, year, and table choices to an approved basket."""
    return _with_workflow(
        basket_state.explore_basket(
            _source,
            project_key,
            _rows(rows),
            phase,
            scenario,
            component=component,
            mode=mode,
            source_year=source_year,
            table_year=table_year,
            table_comp=table_comp,
            table_sort=table_sort,
        )
    )


# Downloads are served by this app's own HTTP route, not as data: links. A
# sandboxed MCP App frame cannot save files, so the view asks the host to open
# the route (openLink), and the browser saves the response as an attachment.
EXPORT_LIMIT = 32
_EXPORTS: dict[str, tuple[str, bytes]] = {}
# Every value in this export is synthetic. No PARS project details are included.
_SYNTHETIC_SOURCE = "Synthetic demo (PPI fixtures)"
_FORMULA_START = re.compile(r"^\s*[=+\-@]")


def _csv_text(value: Any) -> str:
    """Neutralize text cells that a spreadsheet would read as a formula."""
    text = "" if value is None else str(value)
    return "'" + text if _FORMULA_START.match(text) else text


def _scenario_label(scenario: str | None) -> str:
    if not scenario:
        return ""
    return "custom allocation" if scenario.startswith("custom:") else scenario


def _csv_document(table: dict[str, Any], project_key: str, scenario: str) -> str:
    """Serialize the filtered approved table, labelled with its basket context."""
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(
        [
            "Illustrative project",
            "Scenario",
            "Data source",
            *(label for _, label in _TABLE_COLUMNS),
        ]
    )
    for row in table["rows"]:
        writer.writerow(
            [
                _csv_text(project_key),
                _csv_text(scenario),
                _SYNTHETIC_SOURCE,
                *(_csv_text(row.get(key)) for key, _ in _TABLE_COLUMNS),
            ]
        )
    return stream.getvalue()


def _export_error(message: str) -> dict[str, str]:
    return {"state": "error", "message": message, "filename": "", "url": ""}


def _request_base_url() -> str | None:
    """The address the browser reached this server at, or None without HTTP."""
    try:
        request = get_http_request()
    except RuntimeError:
        return None
    return str(request.base_url).rstrip("/")


@app.tool()
def export_analysis_csv(
    project_key: ProjectKey,
    rows: list[BasketRowInput],
    phase: PhaseArg,
    scenario: str | None = None,
    table_year: str = "all",
    table_comp: str = "all",
    table_sort: SortArg = "asc",
) -> dict[str, str]:
    """Prepare the exact approved and filtered observation table for download.

    The result carries a URL on this app's HTTP server. The view opens it with
    openLink, and the browser saves the CSV as an attachment.
    """
    if phase != "approved":
        return _export_error("Approve the allocation first.")
    basket = basket_state.explore_basket(
        _source,
        project_key,
        _rows(rows),
        phase,
        scenario,
        table_year=table_year,
        table_comp=table_comp,
        table_sort=table_sort,
    )
    if basket.get("error"):
        # The request no longer matches the approved basket, so the locked table
        # it would return is not what the analyst is looking at. Refuse it.
        return _export_error(
            "The basket changed after approval. Approve it again to download."
        )
    table = (basket.get("results") or {}).get("table")
    if not table or table["message"]:
        return _export_error("The filtered table is unavailable.")
    base_url = _request_base_url()
    if base_url is None:
        return _export_error(
            "Download needs the app's HTTP server. Open the app from its local "
            "server to save the CSV."
        )
    document = _csv_document(table, project_key, _scenario_label(basket["scenario"]))
    filename = f"nnsa_escalation_basket_{project_key}_{datetime.now():%Y%m%d-%H%M}.csv"
    token = secrets.token_urlsafe(16)
    _EXPORTS[token] = (filename, document.encode("utf-8-sig"))
    while len(_EXPORTS) > EXPORT_LIMIT:
        del _EXPORTS[next(iter(_EXPORTS))]
    return {
        "state": "ready",
        "message": f"{len(table['rows'])} observations ready to save.",
        "filename": filename,
        "url": f"{base_url}/exports/{token}",
    }


_BASKET_ARGS = {
    "project_key": STATE.basket.project_key,
    "rows": STATE.basket.rows,
    "phase": STATE.basket.phase,
    "scenario": STATE.basket.scenario,
}
_SELECTION = STATE.basket.results.selection


def _empty_csv_export() -> dict[str, str]:
    """Discard downloads prepared from an earlier basket or table selection."""
    return {"state": "idle", "message": "", "filename": "", "url": ""}


def _call(tool: Any, arguments: dict[str, Any] | None = None) -> CallTool:
    """Call a backend tool and replace the basket state with its result."""
    return CallTool(
        tool,
        arguments=arguments or _BASKET_ARGS,
        on_success=[
            SetState("basket", RESULT),
            SetState("csv_export", _empty_csv_export()),
        ],
        on_error=ShowToast("The basket could not be updated.", variant="error"),
    )


def _explore(**changes: Any) -> CallTool:
    """Explore the approved basket with the current choices, overridden by ``changes``.

    Each control sends every choice, so the server can rebuild the whole view.
    """
    arguments = {
        "project_key": STATE.basket.project_key,
        "rows": STATE.basket.rows,
        "phase": STATE.basket.phase,
        "scenario": STATE.basket.scenario,
        "component": _SELECTION.component,
        "mode": _SELECTION.mode,
        "source_year": _SELECTION.source_year,
        "table_year": _SELECTION.table_year,
        "table_comp": _SELECTION.table_comp,
        "table_sort": _SELECTION.table_sort,
        **changes,
    }
    return _call(explore_basket, arguments)


# PARS project IDs are not inferred from fictional DEMO-NNSA basket keys.
# An analyst must explicitly choose which independent PARS project to inspect.
PARS_CONTEXT_ROOT_SLOTS = 3
PARS_WBS_CHOICES = 60
PARS_PROJECT_SLOTS = 12  # Stable browser bindings; refine search for more matches.
PARS_WBS_SLOTS = 24  # Scrollable WBS choices; other elements remain read-only.


def _wbs_slots(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Stable state paths for the Prefab WBS selection controls."""
    visible = [{"visible": True, **row} for row in rows[:PARS_WBS_SLOTS]]
    blank = {"visible": False, "wbs_code": "", "label": ""}
    return visible + [dict(blank) for _ in range(PARS_WBS_SLOTS - len(visible))]


def _empty_pars_context(message: str = "") -> dict[str, Any]:
    return {
        "state": "idle" if not message else "error",
        "message": message,
        "project_id": "",
        "name": "",
        "summary": "",
        "origin": "",
        "evidence_label": "",
        "description": "",
        "description_status": "",
        "roots": [
            {"visible": False, "title": "", "wbs_code": ""}
            for _ in range(PARS_CONTEXT_ROOT_SLOTS)
        ],
        "wbs_choices": [],
        "wbs_slots": _wbs_slots([]),
    }


def _initial_pars_projects() -> dict[str, Any]:
    """Show the local catalog immediately; a failed lookup must not blank the UI."""
    try:
        return search_pars_projects()
    except Exception:
        return _empty_pars_projects("PARS catalog unavailable. Try Browse again.")


def _empty_pars_projects(message: str = "") -> dict[str, Any]:
    return {
        "state": "error" if message else "idle",
        "message": message,
        "rows": [],
        "choices": _project_slots([]),
    }


def _project_slots(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Fixed paths avoid renderer-scoped variables inside dropdown options."""
    return [{"visible": True, **row} for row in rows[:PARS_PROJECT_SLOTS]] + [
        {"visible": False, "label": "", "parsid": ""}
        for _ in range(max(0, PARS_PROJECT_SLOTS - len(rows)))
    ]


@app.tool()
def search_pars_projects(query: str = "") -> dict[str, Any]:
    """Search the read-only PARS project catalog by name or ID."""
    if not isinstance(query, str) or len(query) > 100:
        return _empty_pars_projects("Search terms must be 100 characters or fewer.")
    with _pars_session() as session:
        listing = pars_panels.project_list(pars_panels.GuardedClient(session))
        startup_problem = (
            getattr(session, "problem", "") if listing["state"] == "error" else ""
        )
    if listing["state"] == "error":
        return _empty_pars_projects(
            startup_problem
            if startup_problem != "" and startup_problem != pars_live.NOT_STARTED
            else "PARS catalog unavailable. Check local PARS startup and database."
        )
    needle = query.strip().casefold()
    rows = sorted(
        (
            {
                "parsid": item["parsid"],
                "label": f"{item['project_name']} — {item['parsid']}",
            }
            for item in listing["rows"]
            if needle in item["project_name"].casefold()
            or needle in item["parsid"].casefold()
        ),
        key=lambda item: (item["label"].casefold(), item["parsid"]),
    )[:30]
    return {
        "state": "loaded" if rows else "empty",
        "message": (
            "Refine the search to see additional matches."
            if len(rows) > PARS_PROJECT_SLOTS
            else ("" if rows else "No matching PARS projects.")
        ),
        "rows": rows,
        "choices": _project_slots(rows),
    }


@app.tool()
def load_pars_context(project_id: str) -> dict[str, Any]:
    """Read an explicitly selected PARS project for the basket evidence rail.

    This is contextual evidence only; it does not change the synthetic PPI
    calculation, approve a WBS allocation, or write anything to PARS.
    """
    chosen = project_id.strip()
    if not chosen:
        return _empty_pars_context(pars_panels.CHOOSE_PROJECT)
    if len(chosen) > 128:
        return _empty_pars_context(
            "Enter a PARS project ID of 128 characters or fewer."
        )
    with _pars_session() as session:
        client = pars_panels.LoggedClient(session)
        header = pars_panels.project_header(client, chosen)
        evidence = pars_panels.evidence(client)
        available = (
            evidence["state"] != "error"
            and evidence["ok"]
            and evidence["read_only_views"]
        )
        roots = pars_panels.project_roots(client, chosen) if available else None
        leaves = pars_panels.leaf_nodes(client, chosen) if available else None
        descriptions = (
            pars_panels.read_only_data(client, "descriptions", True, limit=500)
            if available
            else None
        )
    if header["state"] == "error":
        return _empty_pars_context(header["message"])
    if evidence["state"] == "error":
        return _empty_pars_context(evidence["message"])
    if not evidence["read_only_views"] or not evidence["ok"]:
        return _empty_pars_context(
            "PARS context requires validated synthetic WBS inputs."
        )
    if roots is None:
        return _empty_pars_context("PARS WBS context is unavailable.")
    if roots["state"] == "error":
        return _empty_pars_context(roots["message"])
    rows = roots["rows"][:PARS_CONTEXT_ROOT_SLOTS]
    if leaves is None or leaves["state"] == "error":
        return _empty_pars_context("PARS WBS elements are unavailable.")
    project_description = ""
    if descriptions and descriptions["state"] == "loaded":
        for record in descriptions["rows"]:
            if str(record.get("parsid", "")).strip() == chosen:
                project_description = str(
                    record.get("project_description") or record.get("description") or ""
                ).strip()
                break
    description_status = (
        "Project description unavailable in the current read-only source."
        if not project_description
        else ""
    )
    return {
        "state": "loaded",
        "message": "",
        "project_id": chosen,
        "description": project_description,
        "description_status": description_status,
        "name": header["name"],
        "summary": header["summary"],
        "origin": evidence["origin"],
        "evidence_label": evidence["label"],
        "wbs_choices": [
            {
                "wbs_code": element["wbs_code"],
                "label": f"{element['wbs_code']} — {element['title']}",
            }
            for element in leaves["rows"][:PARS_WBS_CHOICES]
        ],
        "wbs_slots": _wbs_slots(
            [
                {
                    "wbs_code": element["wbs_code"],
                    "label": f"{element['wbs_code']} — {element['title']}",
                }
                for element in leaves["rows"][:PARS_WBS_CHOICES]
            ]
        ),
        "roots": [
            {"visible": True, "title": row["title"], "wbs_code": row["wbs_code"]}
            for row in rows
        ]
        + [
            {"visible": False, "title": "", "wbs_code": ""}
            for _ in range(PARS_CONTEXT_ROOT_SLOTS - len(rows))
        ],
    }


@app.tool()
def load_caef_mapping_summary(project_id: str) -> dict[str, Any]:
    """Load the configured saved CAEF predictions; do not run a model."""
    if (
        not isinstance(project_id, str)
        or not project_id.strip()
        or len(project_id) > 128
    ):
        return empty_caef_summary("Choose a PARS project first.")
    return read_caef_summary(saved_prediction_path(), project_id)


@app.tool()
def run_caef_mapping_model(project_id: str) -> dict[str, Any]:
    """Run the trained CAEF classifier on the selected PARS project's WBS.

    The packaged demo project 100 keeps its saved-bundle route. Every other project
    is classified from the WBS records that PARS MCP returns for it. The adapter never
    opens the PARS database itself. If PARS is unavailable, the result is an error.
    """
    if project_id.strip() == "100":
        return run_model_for_project(project_id)
    try:
        with _pars_session() as session:
            return predict_retrieved_project(project_id, session)
    except Exception:  # PARS unavailable: controlled, no internals shown
        return empty_caef_summary("PARS is not connected for this project.")


@app.tool()
def review_wbs_bls_mapping(
    project_id: str,
    wbs_code: str,
    component_id: str,
    rationale: str,
) -> dict[str, Any]:
    """Review a WBS-to-synthetic-PPI candidate without saving or calculating.

    The project and element are verified through read-only PARS MCP calls.
    The returned candidate is an explicit analyst assumption, never an
    authorized cost allocation or a real BLS observation.
    """
    if not all(
        isinstance(v, str) for v in (project_id, wbs_code, component_id, rationale)
    ):
        return empty_mapping_review("Invalid mapping input.")
    if not project_id.strip() or len(project_id) > 128:
        return empty_mapping_review("Enter a valid PARS project ID.")
    if not wbs_code.strip() or len(wbs_code) > 128:
        return empty_mapping_review("Choose a valid WBS code.")
    if len(rationale) > 500:
        return empty_mapping_review(
            "The mapping rationale must be 500 characters or fewer."
        )
    # Refuse invalid inputs before starting the PARS subprocess.
    if component_id not in {src.component_id for src in _source.list_sources()}:
        return empty_mapping_review("Choose a listed BLS basket component.")
    if len(rationale.strip()) < 12:
        return empty_mapping_review(
            "Enter a mapping rationale of at least 12 characters."
        )

    with _pars_session() as session:
        client = pars_panels.GuardedClient(session)
        header = pars_panels.project_header(client, project_id)
        evidence = pars_panels.evidence(client)
        element = (
            pars_panels.hierarchy(client, project_id, wbs_code)
            if evidence["state"] != "error"
            and evidence["ok"]
            and evidence["read_only_views"]
            else None
        )
    return review_mapping(
        project_id=project_id,
        wbs_code=wbs_code,
        component_id=component_id,
        rationale=rationale,
        sources=_source.list_sources(),
        header=header,
        evidence=evidence,
        hierarchy=element,
    )


def _evidence_collapsed() -> None:
    """The collapsed panel: one visible control that reopens the same panel.

    Only the panel body is hidden. Its state (search text, selected project,
    loaded context, WBS choice, CAEF results) stays in app state, so reopening
    shows it again with no reload. Opening and closing send no tool calls.
    """
    with Card(
        css_class="w-full min-w-0 lg:w-[56px] lg:shrink-0 " + EVIDENCE_CARD_CLASS
    ):
        with CardContent(css_class="p-2"):
            Button(
                "Show project evidence",
                variant="outline",
                size="sm",
                css_class=(
                    BUTTON_CLASS + " w-full h-auto min-h-10 whitespace-normal "
                    "lg:min-h-[14rem] lg:[writing-mode:vertical-rl] lg:rotate-180"
                ),
                aria_label="Show project evidence (panel collapsed)",
                on_click=SetState("evidence_open", True),
            )


def _context_rail() -> None:
    """Reference HTML's evidence rail, with read-only PARS / BLS linkage.

    The body can be collapsed with the header control; see _evidence_collapsed.
    """
    with Column(gap=3, css_class="w-full min-w-0 lg:w-[302px] lg:shrink-0"):
        with Card(css_class=EVIDENCE_CARD_CLASS):
            with CardHeader():
                with Row(gap=2, align="center", justify="between"):
                    CardTitle("Project & evidence", css_class="!text-slate-100")
                    Button(
                        "Collapse panel",
                        variant="outline",
                        size="sm",
                        css_class=BUTTON_CLASS,
                        aria_label="Collapse panel: project and evidence (expanded)",
                        on_click=SetState("evidence_open", False),
                    )
                CardDescription(
                    "PARS WBS · independent read-only context",
                    css_class="!text-slate-300",
                )
                Small("Project context", css_class="!text-slate-300")
            with CardContent():
                with Column(gap=3):
                    Badge("PARS / WBS", variant="secondary")
                    Small(
                        "Browse PARS projects and select the WBS element "
                        "to review its economic-index mapping."
                    )
                    Small("Find a PARS project by name or ID")
                    with Row(gap=2, css_class="w-full flex-wrap"):
                        Input(
                            value=STATE.pars_query,
                            placeholder="Search project name or ID",
                            aria_label="Search PARS project names or IDs",
                            on_change=SetState("pars_query", EVENT),
                            css_class="min-w-0 flex-1 !bg-white !text-slate-900",
                        )
                        Button(
                            "Browse / filter projects",
                            variant="outline",
                            size="sm",
                            css_class=BUTTON_CLASS,
                            on_click=CallTool(
                                search_pars_projects,
                                arguments={"query": STATE.pars_query},
                                on_success=[
                                    SetState("pars_projects", RESULT),
                                    SetState("pars_context_input", ""),
                                    SetState("pars_context", _empty_pars_context()),
                                    SetState("caef_summary", empty_caef_summary()),
                                    SetState("mapping_review", empty_mapping_review()),
                                    SetState("mapping_wbs_code", ""),
                                ],
                                on_error=ShowToast(
                                    "PARS project search is unavailable.",
                                    variant="error",
                                ),
                            ),
                        )
                    with If(STATE.pars_projects.state == "idle"):
                        Small(
                            "Choose Browse / filter projects to list available "
                            "PARS projects."
                        )
                    with If(STATE.pars_projects.state == "loaded"):
                        Small("Select a project, then load its read-only context.")
                        # Explicit paths avoid a ForEach-generated option in the
                        # Prefab browser renderer. All returned IDs stay in state.
                        for i in range(PARS_PROJECT_SLOTS):
                            key = f"pars_projects.choices.{i}"
                            with If(Rx(f"{key}.visible")):
                                Button(
                                    Rx(f"{key}.label"),
                                    variant="outline",
                                    size="sm",
                                    css_class=BUTTON_CLASS + " w-full justify-start",
                                    on_click=[
                                        SetState(
                                            "pars_context_input", Rx(f"{key}.parsid")
                                        ),
                                        SetState("pars_context", _empty_pars_context()),
                                        SetState("caef_summary", empty_caef_summary()),
                                        SetState(
                                            "mapping_review", empty_mapping_review()
                                        ),
                                        SetState("mapping_wbs_code", ""),
                                    ],
                                )
                        with If(STATE.pars_context_input != ""):
                            Small("Selected project ID:")
                            Text(STATE.pars_context_input)
                            # A chosen ID is not loaded data until Load runs.
                            with If(STATE.pars_context.state != "loaded"):
                                Small(
                                    "Not loaded yet. Choose Load PARS context to "
                                    "read this project's details."
                                )
                        with If(STATE.pars_projects.message != ""):
                            Small(STATE.pars_projects.message)
                    with If(STATE.pars_projects.state == "empty"):
                        Small(STATE.pars_projects.message)
                    with If(STATE.pars_projects.state == "error"):
                        Small(STATE.pars_projects.message)
                    with If(STATE.pars_context_input == ""):
                        Small("Choose a PARS project above to enable loading.")
                    Button(
                        "Load PARS context",
                        variant="outline",
                        size="sm",
                        disabled=STATE.pars_context_input == "",
                        css_class=BUTTON_CLASS,
                        on_click=CallTool(
                            load_pars_context,
                            arguments={"project_id": STATE.pars_context_input},
                            on_success=[
                                SetState("pars_context", RESULT),
                                SetState("caef_summary", empty_caef_summary()),
                                SetState("mapping_review", empty_mapping_review()),
                                SetState("mapping_wbs_code", ""),
                                *CHAT_CONTEXT_RESET,
                            ],
                            on_error=ShowToast(
                                "PARS context is unavailable.", variant="error"
                            ),
                        ),
                    )
                    with If(STATE.pars_context.state == "loaded"):
                        Badge(STATE.pars_context.evidence_label, variant="secondary")
                        Text(STATE.pars_context.name, css_class="font-semibold")
                        Muted(STATE.pars_context.project_id)
                        Small(STATE.pars_context.summary)
                        Text(
                            "Project description",
                            css_class="font-semibold !text-white",
                        )
                        with If(STATE.pars_context.description != ""):
                            Small(STATE.pars_context.description)
                        with Else():
                            Small(STATE.pars_context.description_status)
                        Text("WBS cost structure", css_class="font-semibold")
                        Small(
                            "Select a WBS element to inspect its place in the project."
                        )
                        Small("Available WBS elements (choose one):")
                        with Column(
                            gap=1,
                            css_class="max-h-56 overflow-y-auto w-full min-w-0",
                        ):
                            for i in range(PARS_WBS_SLOTS):
                                key = f"pars_context.wbs_slots.{i}"
                                with If(Rx(f"{key}.visible")):
                                    Button(
                                        Rx(f"{key}.label"),
                                        variant="outline",
                                        size="sm",
                                        css_class=(
                                            BUTTON_CLASS
                                            + " w-full min-w-0 text-left justify-start"
                                        ),
                                        on_click=[
                                            SetState(
                                                "mapping_wbs_code",
                                                Rx(f"{key}.wbs_code"),
                                            ),
                                            SetState(
                                                "mapping_review", empty_mapping_review()
                                            ),
                                        ],
                                    )
                        with If(STATE.mapping_wbs_code != ""):
                            Small("Selected WBS:")
                            Text(STATE.mapping_wbs_code, css_class="!text-white")
                        Small(
                            "First 24 WBS elements shown. Candidate selection "
                            "does not modify PARS."
                        )
                        for i in range(PARS_CONTEXT_ROOT_SLOTS):
                            key = f"pars_context.roots.{i}"
                            with If(Rx(f"{key}.visible")):
                                with Column(gap=1):
                                    Small(Rx(f"{key}.title"))
                                    Button(
                                        Rx(f"{key}.wbs_code"),
                                        variant="outline",
                                        size="sm",
                                        css_class=BUTTON_CLASS,
                                        on_click=[
                                            SetState(
                                                "mapping_wbs_code",
                                                Rx(f"{key}.wbs_code"),
                                            ),
                                            SetState(
                                                "mapping_review", empty_mapping_review()
                                            ),
                                        ],
                                    )
                    with If(STATE.pars_context.state == "error"):
                        Muted(STATE.pars_context.message)
        with Card(css_class=EVIDENCE_CARD_CLASS):
            with CardHeader():
                CardTitle("Project CAEF 2.0 mapping", css_class="!text-slate-100")
                CardDescription("Review a completed whole-project WBS classification")
            with CardContent():
                with Column(gap=2):
                    Small(
                        "See saved mapping results, or choose to run the already "
                        "trained model. Running it updates a local results file; "
                        "it does not retrain the model or change PARS data. "
                        "The saved run may contain several projects; your selection "
                        "only filters the displayed results."
                    )
                    with If(STATE.pars_context.state != "loaded"):
                        Small(
                            "Load PARS context first. These actions need a "
                            "loaded project."
                        )
                    Button(
                        "View saved CAEF mapping",
                        variant="outline",
                        size="sm",
                        disabled=STATE.pars_context.state != "loaded",
                        css_class=BUTTON_CLASS,
                        on_click=CallTool(
                            load_caef_mapping_summary,
                            arguments={"project_id": STATE.pars_context.project_id},
                            on_success=SetState("caef_summary", RESULT),
                            on_error=ShowToast(
                                "CAEF classification could not be loaded.",
                                variant="error",
                            ),
                        ),
                    )
                    Button(
                        "Run model on bundled data",
                        variant="outline",
                        size="sm",
                        disabled=STATE.pars_context.state != "loaded",
                        css_class=BUTTON_CLASS,
                        on_click=CallTool(
                            run_caef_mapping_model,
                            arguments={"project_id": STATE.pars_context.project_id},
                            on_success=SetState("caef_summary", RESULT),
                            on_error=ShowToast(
                                "CAEF prediction failed. See local model logs.",
                                variant="error",
                            ),
                        ),
                    )
                    with If(STATE.caef_summary.state == "loaded"):
                        Text(STATE.caef_summary.coverage, css_class="!text-white")
                        Small("Most common predicted CAEF categories:")
                        for i in range(CAEF_CATEGORY_SLOTS):
                            path = f"caef_summary.categories.{i}"
                            with If(Rx(f"{path}.visible")):
                                Small(Rx(f"{path}.label"))
                        Small("Counts reflect WBS rows, not project cost weights.")
                    with If(STATE.caef_summary.state == "unavailable"):
                        Small(STATE.caef_summary.message)
                    with If(STATE.caef_summary.state == "error"):
                        Small(STATE.caef_summary.message)
                    Small(
                        "CAEF-based BLS suggestions are optional and not yet "
                        "configured. Manual basket review remains available."
                    )
        with Card(css_class=EVIDENCE_CARD_CLASS):
            with CardHeader():
                CardTitle("Optional economic index review", css_class="!text-slate-100")
                CardDescription(
                    "Optional review only; does not change the escalation basket"
                )
            with CardContent():
                with Column(gap=3):
                    Small(
                        "Optional: select a WBS element above to explore a possible "
                        "economic index. This is separate from CAEF classification.",
                        css_class="!text-slate-300",
                    )
                    with If(STATE.mapping_wbs_code != ""):
                        Badge(
                            STATE.mapping_wbs_code,
                            variant="outline",
                            css_class=OUTLINE_BADGE_CLASS,
                        )
                    Small(
                        "Choose an illustrative index candidate (not an allocation).",
                        css_class="!text-slate-300",
                    )
                    with Select(
                        name="mapping_component",
                        value="{{ mapping_component }}",
                        onChange=[
                            SetState("mapping_component", EVENT),
                            SetState("mapping_review", empty_mapping_review()),
                        ],
                    ):
                        for component in _source.list_sources():
                            SelectOption(
                                component.short_name, value=component.component_id
                            )
                    Small(
                        "Explain why this index may suit the selected work.",
                        css_class="!text-slate-300",
                    )
                    Input(
                        value=STATE.mapping_rationale,
                        placeholder="Mapping rationale (required)",
                        aria_label="Analyst rationale for WBS to BLS mapping",
                        on_change=[
                            SetState("mapping_rationale", EVENT),
                            SetState("mapping_review", empty_mapping_review()),
                        ],
                    )
                    with If(
                        (STATE.pars_context.state != "loaded")
                        | (STATE.mapping_wbs_code == "")
                    ):
                        Small(
                            "Needs a loaded PARS project, a selected WBS element, "
                            "and a rationale of at least 12 characters."
                        )
                    Button(
                        "Review candidate mapping",
                        variant="outline",
                        size="sm",
                        css_class=BUTTON_CLASS,
                        disabled=(STATE.pars_context.state != "loaded")
                        | (STATE.mapping_wbs_code == ""),
                        on_click=CallTool(
                            review_wbs_bls_mapping,
                            arguments={
                                "project_id": STATE.pars_context.project_id,
                                "wbs_code": STATE.mapping_wbs_code,
                                "component_id": STATE.mapping_component,
                                "rationale": STATE.mapping_rationale,
                            },
                            on_success=SetState("mapping_review", RESULT),
                            on_error=ShowToast(
                                "Could not verify the mapping.", variant="error"
                            ),
                        ),
                    )
                    with If(STATE.mapping_review.state == "reviewed"):
                        Badge("Read-only candidate", variant="success")
                        Text(
                            STATE.mapping_review.element_title,
                            css_class="font-medium",
                        )
                        Small(STATE.mapping_review.series_name)
                        Muted(STATE.mapping_review.series_id)
                        Small(STATE.mapping_review.rationale)
                        Small(STATE.mapping_review.disclaimer)
                    with If(STATE.mapping_review.state == "error"):
                        Muted(STATE.mapping_review.message)
        with Card(css_class=EVIDENCE_CARD_CLASS):
            with CardHeader():
                CardTitle("About this analysis", css_class="!text-slate-100")
            with CardContent():
                with Column(gap=2):
                    Small(
                        "The price-index charts use sample data, not live BLS figures."
                    )
                    Small("PARS project information is read-only.")
                    Small("Suggested indexes are for review, not automatic choices.")
                    Small("No actual PARS project costs are changed or recalculated.")
                    Small("See Evidence & audit for sources and calculation details.")


# Workflow steps. The basket is built and approved on its own; PARS context is
# optional evidence and is never an input to a step. Each step's state is derived
# in code (``workflow_steps``) from the basket state; the strip only displays it.
_STEP_DEFS = (
    (
        "step1",
        "01",
        "Review allocation",
        "Choose an example project, include components, and set weights.",
        "✓ DONE",
        "NEXT STEP",
    ),
    (
        "step2",
        "02",
        "Approve allocation",
        "Approve a valid allocation to calculate its result.",
        "✓ APPROVED",
        "NEXT STEP",
    ),
    (
        "step3",
        "03",
        "Explore results",
        "Inspect components, adjustments, observations, and audit evidence.",
        "✓ DONE",
        "AWAITING APPROVALS",
    ),
)
_WEIGHT_TOLERANCE = Decimal("0.00001")  # Same tolerance as cost_intel_ui.session.
_BADGE = "inline-flex w-fit rounded-full px-3 py-1 font-bold "
_BADGE_ACTIVE = _BADGE + "!bg-[#285A77] !text-white"
_BADGE_DONE = _BADGE + "!bg-[#CBEBDD] !text-[#041E42]"
_BADGE_BLOCKED = _BADGE + "!bg-[#BF0D3E] !text-white"
# Neutral: a step not reached yet, but nothing is wrong (plain sequencing).
# Distinct from _BADGE_BLOCKED, which is reserved for a real failure.
_BADGE_UPCOMING = _BADGE + "!bg-[#E5E9EE] !text-[#041E42]"


def _included_weights_problem(basket: dict[str, Any]) -> str:
    """Why the included weights cannot be approved yet, or "" when they can."""
    included = [row for row in basket["rows"] if row["enabled"]]
    if not included:
        return "Include at least one component."
    if any(row["weight"] == "" for row in included):
        return "Enter a weight for every included component."
    total = sum((Decimal(row["weight"]) for row in included), Decimal(0))
    if abs(total - 100) >= _WEIGHT_TOLERANCE:
        return (
            f"Included weights total {basket['total_label']}. "
            "They must total 100.00% before approval."
        )
    return ""


def _workflow(
    step1: tuple[str, bool, str],
    step2: tuple[str, bool, str],
    step3: tuple[str, bool, str],
    *,
    badge_label: str,
) -> dict[str, Any]:
    """One step's (state, available, reason) triple, keyed for the view."""
    steps = {"step1": step1, "step2": step2, "step3": step3}
    result: dict[str, Any] = {"badge_label": badge_label}
    for key, (state, available, reason) in steps.items():
        result[key] = {"state": state, "available": available, "reason": reason}
    return result


def workflow_steps(basket: dict[str, Any]) -> dict[str, Any]:
    """Derive each step's state from the basket state.

    ``state`` is ``active`` (the current step), ``complete`` (its requirements are
    met), ``upcoming`` (not reached yet, but nothing is wrong — plain sequencing),
    or ``blocked`` (a real failure: an approved result that cannot be used).
    ``available`` is True when the step's controls are enabled; this is tracked
    independently of ``state`` (the Approve control is available whenever weights
    are valid, even while step 1 still displays as the current step).  ``reason``
    is the plain-language explanation shown on screen. Results exist only once
    the basket is approved, so a stale result can never read as current.

    Step 1 (Review allocation) stays the current step through the whole review
    and approval process; it only becomes complete once the basket is approved.
    """
    if not basket.get("rows"):
        reason = basket.get("error") or (
            "The allocation could not be loaded. "
            "Choose an example project to try again."
        )
        return _workflow(
            ("blocked", False, reason),
            ("blocked", False, "Load an allocation before approving it."),
            ("blocked", False, "Approve an allocation to see its results."),
            badge_label="Not available",
        )
    if basket.get("locked"):
        results = basket.get("results")
        if results is None or results["explorer"]["blocked"]:
            return _workflow(
                ("complete", False, "Approved."),
                (
                    "blocked",
                    False,
                    "The approved result failed a data check and cannot be used. "
                    "Choose Edit approved allocation, then approve again.",
                ),
                (
                    "blocked",
                    False,
                    "No usable result is available for this allocation.",
                ),
                badge_label="Result blocked",
            )
        return _workflow(
            (
                "complete",
                False,
                "Approved. Choose Edit approved allocation to change it.",
            ),
            ("complete", False, "Approved. The result is shown below."),
            ("active", True, "Explore the approved result below."),
            badge_label="Approved",
        )
    approval_wait = "Approve the allocation first. Results appear after approval."
    if basket.get("status_tone") == "valid":
        return _workflow(
            (
                "active",
                True,
                "Weights total 100%. Approve to calculate the result.",
            ),
            ("upcoming", True, "Approve to calculate the result from these weights."),
            ("upcoming", False, approval_wait),
            badge_label="Not approved",
        )
    problem = _included_weights_problem(basket) or (
        "A local calculator is not available for this allocation."
    )
    return _workflow(
        ("active", True, problem),
        ("upcoming", False, problem),
        ("upcoming", False, approval_wait),
        badge_label="Not approved",
    )


def _with_workflow(basket: dict[str, Any]) -> dict[str, Any]:
    """The basket state the browser holds, with its derived workflow steps."""
    return {**basket, "workflow": workflow_steps(basket)}


def _workflow_strip() -> None:
    """Three plain-language steps. Every state is read from ``basket.workflow``."""
    with Row(gap=2, css_class="flex flex-col md:flex-row w-full"):
        for key, number, title, detail, done_label, upcoming_label in _STEP_DEFS:
            state = Rx(f"basket.workflow.{key}.state")
            with Card(css_class="flex-1 " + EVIDENCE_CARD_CLASS):
                with CardContent():
                    with Column(gap=1):
                        with If(state == "active"):
                            Text("CURRENT STEP", css_class=_BADGE_ACTIVE)
                        with Else():
                            with If(state == "complete"):
                                Text(done_label, css_class=_BADGE_DONE)
                            with Else():
                                with If(state == "blocked"):
                                    Text("BLOCKED", css_class=_BADGE_BLOCKED)
                                with Else():
                                    Text(upcoming_label, css_class=_BADGE_UPCOMING)
                        Text(
                            f"{number} · {title}",
                            css_class="font-semibold !text-white",
                        )
                        Small(detail, css_class="!text-slate-200")
                        Small(
                            Rx(f"basket.workflow.{key}.reason"),
                            css_class="!text-white",
                        )


def _demo_project_picker() -> None:
    """NNSA example-project navigation from the HTML reference."""
    with Column(gap=2):
        Text("NNSA example projects", css_class="font-semibold !text-slate-100")
        Small(
            "Choose an example scope for index allocation review",
            css_class="!text-slate-300",
        )
        with Row(gap=2, css_class="flex-wrap items-stretch"):
            for project in _source.list_projects():
                with If(STATE.basket.project_key == project.key):
                    Button(
                        project.nav_label + " ✓",
                        variant="default",
                        size="sm",
                        css_class=(
                            "min-h-10 min-w-[116px] rounded-lg px-3 font-semibold "
                            + FOCUS_OUTLINE_CLASS
                            + " !bg-[#285A77] !text-white !border-[#8995A7]"
                        ),
                    )
                with Else():
                    Button(
                        project.nav_label,
                        variant="outline",
                        size="sm",
                        css_class=(
                            "min-h-10 min-w-[116px] rounded-lg px-3 " + BUTTON_CLASS
                        ),
                        on_click=[
                            _call(choose_demo_project, {"project_key": project.key}),
                            SetState("mapping_review", empty_mapping_review()),
                            *CHAT_CONTEXT_RESET,
                        ],
                    )


def _presets() -> None:
    with Row(gap=2, css_class="flex-wrap"):
        for i, key in enumerate(_PRESET_KEYS):
            label = Rx(f"basket.presets.{i}.display_label")
            with If(Rx(f"basket.presets.{i}.current")):
                Button(
                    label,
                    variant="default",
                    size="sm",
                    css_class=BUTTON_CLASS,
                )
            with Else():
                Button(
                    label,
                    variant="outline",
                    size="sm",
                    css_class=BUTTON_CLASS,
                    on_click=_call(
                        choose_preset,
                        {
                            "project_key": STATE.basket.project_key,
                            "preset_key": key,
                            "phase": STATE.basket.phase,
                        },
                    ),
                )


def _row_cells(index: int, *, locked: bool) -> None:
    """One basket row, bound to literal state paths such as ``basket.rows.0``.

    The checkbox binds its row through `name`, which the renderer reads and
    writes as state. A template in `value` fails the browser's boolean schema.
    """
    row = f"basket.rows.{index}"
    state_key = f"{row}.enabled"
    with TableCell():
        if locked:
            Checkbox(
                name=state_key,
                aria_label=Rx(f"{row}.checkbox_label"),
                disabled=True,
            )
        else:
            Checkbox(
                name=state_key,
                aria_label=Rx(f"{row}.checkbox_label"),
                on_change=[
                    SetState(state_key, EVENT),
                    SetState(f"{row}.weight", "0"),
                    _call(update_basket),
                ],
            )
    with TableCell(css_class="min-w-0 break-words"):
        with Column(gap=0, css_class="min-w-0"):
            Text(
                Rx(f"{row}.title"),
                css_class="font-medium break-words !text-slate-100",
            )
            Muted(
                Rx(f"{row}.series_line"),
                css_class="break-words !text-slate-300",
            )
            if not locked:
                with If(~Rx(f"{row}.enabled")):
                    Small(
                        "Excluded from calculation",
                        css_class="!text-slate-300",
                    )
    TableCell(Rx(f"{row}.type_label"))
    TableCell(Rx(f"{row}.sample_label"))
    with TableCell(css_class="min-w-0"):
        weight = {
            "input_type": "number",
            # Same state key the edit writes; binding it keeps typed values in sync.
            "name": f"{row}.weight",
            "value": Rx(f"{row}.weight"),
            "aria_label": Rx(f"{row}.weight_label"),
            "min": 0,
            "max": 100,
            "step": 0.01,
            "css_class": "w-full min-w-0",
        }
        if locked:
            Input(**weight, disabled=True)
        else:
            with If(Rx(f"{row}.enabled")):
                Input(
                    **weight,
                    on_change=[
                        SetState(f"{row}.weight", EVENT),
                        _call(update_basket),
                    ],
                )
            with Else():
                Input(**weight, disabled=True)


def _table() -> None:
    # Keep all five state-bound fields visible within the narrow basket pane.
    widths = ("w-[7%]", "w-[43%]", "w-[8%]", "w-[20%]", "w-[22%]")
    with Table(css_class="w-full min-w-0 table-fixed"):
        with TableHeader(css_class="!bg-[#D8D5D2]"):
            with TableRow():
                for i in range(_BASKET_COLUMN_COUNT):
                    TableHead(
                        Rx(f"basket.columns.{i}"),
                        css_class=(
                            f"{widths[i]} whitespace-normal break-words "
                            "!text-[#041E42] font-semibold"
                        ),
                    )
        with TableBody():
            with If(STATE.basket.locked):
                for i in range(BASKET_ROW_COUNT):
                    with TableRow():
                        _row_cells(i, locked=True)
            with Else():
                for i in range(BASKET_ROW_COUNT):
                    with TableRow():
                        _row_cells(i, locked=False)


def _status() -> None:
    with Row(gap=3, align="center"):
        Text("Total", css_class="font-medium")
        Text(STATE.basket.total_label, css_class="font-semibold tabular-nums")
        with If(STATE.basket.status_tone == "valid"):
            Badge(STATE.basket.status_label, variant="success")
        with Else():
            Badge(STATE.basket.status_label, variant="warning")


def _actions() -> None:
    with Row(gap=2, justify="end", css_class="flex-wrap"):
        with If(STATE.basket.locked):
            Button(
                "Edit approved allocation",
                variant="outline",
                css_class=BUTTON_CLASS,
                on_click=_call(
                    reopen_allocation,
                    {
                        "project_key": STATE.basket.project_key,
                        "rows": STATE.basket.rows,
                    },
                ),
            )
        with Else():
            Button(
                "Normalize",
                variant="outline",
                css_class=BUTTON_CLASS,
                disabled=~STATE.basket.normalize_enabled,
                on_click=_call(normalize_basket),
            )
            Button(
                STATE.basket.approve_label,
                css_class=BUTTON_CLASS,
                disabled=~STATE.basket.approve_enabled,
                on_click=_call(approve_basket),
            )
    # A disabled Approve says why: the same plain reason the strip shows.
    with If(~STATE.basket.approve_enabled & ~STATE.basket.locked):
        Small(
            Rx("basket.workflow.step2.reason"),
            css_class="w-full text-right !text-white",
        )


def _chart_series() -> list[ChartSeries]:
    """Stacked layers in source order, labeled with the component names.

    Series labels are fixed catalog metadata, not per-result data, so they are
    the one exception to keeping strings in state. The legend and tooltips use
    them to name each layer.
    """
    return [
        ChartSeries(dataKey=s.component_id, label=s.name, color=s.color_hex)
        for s in _source.list_sources()
    ]


def _explorer_blocked() -> None:
    with Column(gap=2):
        Muted(STATE.basket.results.explorer.body)
        for i in range(basket_state.ISSUE_SLOTS):
            with If(Rx(f"basket.results.explorer.issues.{i}")):
                Small(Rx(f"basket.results.explorer.issues.{i}"))
        Small(STATE.basket.results.explorer.footer)


def _explorer_stats() -> None:
    with Row(gap=3, css_class="w-full flex-wrap"):
        for i in range(basket_state.STAT_SLOTS):
            stat = f"basket.results.explorer.stats.{i}"
            with If(Rx(f"{stat}.visible")):
                with Column(
                    gap=1,
                    css_class="min-w-36 flex-1 rounded-lg border border-slate-200 p-3",
                ):
                    Muted(Rx(f"{stat}.label"))
                    Text(
                        Rx(f"{stat}.value"),
                        css_class="text-2xl font-semibold tabular-nums",
                    )


def _ribbon() -> None:
    with Column(gap=1):
        for i in range(BASKET_ROW_COUNT):
            segment = f"basket.results.explorer.ribbon.{i}"
            with If(Rx(f"{segment}.visible")):
                with Row(gap=3, align="center", justify="between"):
                    Button(
                        Rx(f"{segment}.name"),
                        variant="outline",
                        size="sm",
                        css_class=BUTTON_CLASS,
                        on_click=_explore(component=Rx(f"{segment}.component_id")),
                    )
                    Muted(Rx(f"{segment}.percent_label"))


def _explorer_select(
    label: str, key: str, options: tuple[tuple[str, str], ...]
) -> None:
    """Choose a result option, then refresh from the backend's canonical state."""
    with Column(gap=1):
        Muted(label)
        with Select(
            name=key,
            value=f"{{{{ {key} }}}}",
            onChange=[
                SetState(key, EVENT),
                SetState("csv_export", _empty_csv_export()),
                _explore(),
            ],
        ):
            for value, description in options:
                SelectOption(description, value=value)


def _comparison() -> None:
    with Column(gap=2):
        Text(STATE.basket.results.comparison.title, css_class="font-medium")
        Muted(STATE.basket.results.comparison.intro)
        with Row(gap=3, css_class="flex-wrap"):
            for i, key in enumerate(_PRESET_KEYS):
                box = f"basket.results.comparison.boxes.{i}"
                with Card(css_class="w-56"):
                    with CardContent():
                        with Column(gap=1):
                            with Row(gap=2, align="center"):
                                Text(Rx(f"{box}.label"), css_class="font-medium")
                                with If(Rx(f"{box}.approved")):
                                    Badge("Approved", variant="success")
                            Text(
                                Rx(f"{box}.value"),
                                css_class="font-semibold tabular-nums",
                            )
                            Muted(Rx(f"{box}.weights_label"))
                            Button(
                                "Review this allocation",
                                variant="outline",
                                css_class=BUTTON_CLASS,
                                size="sm",
                                on_click=_call(
                                    choose_preset,
                                    {
                                        "project_key": STATE.basket.project_key,
                                        "preset_key": key,
                                        "phase": STATE.basket.phase,
                                    },
                                ),
                            )
        Small(STATE.basket.results.comparison.note)


def _component_tab() -> None:
    with Column(gap=2):
        with If(STATE.basket.results.component.message):
            Muted(STATE.basket.results.component.message)
        with Else():
            Text(STATE.basket.results.component.title, css_class="font-medium")
            Muted(STATE.basket.results.component.metadata)
            with Row(gap=2):
                Button(
                    "Normalized (%)",
                    variant="outline",
                    size="sm",
                    css_class=ACTIVE_MODE_BUTTON_CLASS,
                    disabled=STATE.basket.results.selection.mode == "normalized",
                    on_click=_explore(mode="normalized"),
                )
                Button(
                    "Raw PPI",
                    variant="outline",
                    size="sm",
                    css_class=ACTIVE_MODE_BUTTON_CLASS,
                    disabled=STATE.basket.results.selection.mode == "raw",
                    on_click=_explore(mode="raw"),
                )
            # The disabled button is the view already on screen.
            Small(
                "The button for the current view is disabled.",
                css_class="!text-slate-200",
            )
            LineChart(
                data=STATE.basket.results.component.rows,
                series=[ChartSeries(dataKey="value")],
                xAxis="period",
                showLegend=False,
                height=240,
            )


def _adjustment_tab() -> None:
    adjustment = STATE.basket.results.adjustment
    with Column(gap=2):
        _explorer_select(
            "Source year",
            "basket.results.selection.source_year",
            tuple((year, year) for year in _SOURCE_YEARS),
        )
        with If(adjustment.message):
            Muted(adjustment.message)
        with Else():
            with Row(gap=6, css_class="flex-wrap"):
                with Column(gap=0):
                    Muted(f"Source-year composite factor · {adjustment.year}")
                    Text(
                        adjustment.source_composite,
                        css_class="font-semibold tabular-nums",
                    )
                with Column(gap=0):
                    Muted(f"Adjustment to base year · {adjustment.base_year}")
                    Text(
                        f"{adjustment.adjustment_factor} ×",
                        css_class="font-semibold tabular-nums",
                    )
            Text(adjustment.caption, css_class="font-medium")
            with If(adjustment.note):
                Muted(adjustment.note)
            WaterfallChart(
                data=adjustment.waterfall,
                dataKey="value",
                nameKey="label",
                totalKey="total",
                height=260,
            )
            Small(adjustment.reconcile)
            for i in range(BASKET_ROW_COUNT):
                row = f"basket.results.adjustment.math_rows.{i}"
                with If(Rx(f"{row}.visible")):
                    with Row(gap=3, justify="between"):
                        Muted(Rx(f"{row}.label"))
                        Text(Rx(f"{row}.value"), css_class="tabular-nums")
            Muted(adjustment.ending_factor)


# Column headers are fixed labels, like the chart's series names, so they live
# in the DataTable definition. The rows are read from state as one array.
_TABLE_COLUMNS = (
    ("period", "Period"),
    ("component_name", "Component"),
    ("allocation_weight", "Weight"),
    ("normalized_factor", "Normalized factor"),
    ("composite_factor", "Composite factor"),
)


def _data_tab() -> None:
    with Column(gap=2):
        with Row(gap=3, css_class="flex-wrap"):
            _explorer_select(
                "Period", "basket.results.selection.table_year", _PERIOD_CHOICES
            )
            _explorer_select(
                "Component", "basket.results.selection.table_comp", _COMPONENT_CHOICES
            )
            _explorer_select(
                "Order", "basket.results.selection.table_sort", _SORT_CHOICES
            )
        # Prepare is disabled until the allocation is approved; the reason is shown.
        # Download appears only for a result prepared from the current basket.
        with Row(gap=2, align="center", css_class="flex-wrap"):
            Button(
                "Prepare CSV",
                variant="outline",
                size="sm",
                css_class=BUTTON_CLASS,
                disabled=STATE.basket.phase != "approved",
                on_click=CallTool(
                    export_analysis_csv,
                    arguments={
                        "project_key": STATE.basket.project_key,
                        "rows": STATE.basket.rows,
                        "phase": STATE.basket.phase,
                        "scenario": STATE.basket.scenario,
                        "table_year": STATE.basket.results.selection.table_year,
                        "table_comp": STATE.basket.results.selection.table_comp,
                        "table_sort": STATE.basket.results.selection.table_sort,
                    },
                    on_success=SetState("csv_export", RESULT),
                    on_error=ShowToast("Could not prepare the CSV.", variant="error"),
                ),
            )
            with If(STATE.csv_export.state == "ready"):
                Button(
                    "Download CSV",
                    variant="outline",
                    size="sm",
                    css_class=BUTTON_CLASS,
                    on_click=OpenLink(STATE.csv_export.url),
                )
        with If(STATE.basket.phase != "approved"):
            Muted(
                "Approve the allocation to prepare its CSV. "
                "Downloads are available only for approved results."
            )
        with If(STATE.csv_export.state == "ready"):
            Small(STATE.csv_export.message)
            Small(STATE.csv_export.filename)
        with If(STATE.csv_export.state == "error"):
            Small(STATE.csv_export.message)
        with If(STATE.basket.results.table.message):
            Muted(STATE.basket.results.table.message)
        with Else():
            Muted(STATE.basket.results.table.count_label)
            DataTable(
                columns=[
                    DataTableColumn(key=key, header=header)
                    for key, header in _TABLE_COLUMNS
                ],
                rows=STATE.basket.results.table.rows,
            )


def _audit_tab() -> None:
    """Readable evidence ledger for the approved synthetic calculation.

    The basket and PARS context are independent; this view must never imply
    that a synthetic PPI factor was applied to a PARS project cost estimate.
    """
    with Column(gap=3):
        Badge("Synthetic calculation · read-only", variant="secondary")
        Text("Approval and calculation evidence", css_class="font-semibold")
        with Row(gap=4, css_class="flex-wrap"):
            with Column(gap=1):
                Muted("Illustrative project")
                Text(STATE.basket.project_key)
            with Column(gap=1):
                Muted("Allocation scenario")
                Text(STATE.basket.scenario)
            with Column(gap=1):
                Muted("Allocation total")
                Text(STATE.basket.total_label)
        Muted(STATE.basket.results.explorer.fineprint)
        Text("Economic data", css_class="font-semibold")
        Small(
            "PPI observations and index factors are local synthetic fixtures, "
            "not live BLS observations. The component ledger in Data & CSV "
            "shows the inputs used by the displayed calculation."
        )
        Text("PARS project evidence", css_class="font-semibold")
        with If(STATE.pars_context.state == "loaded"):
            Badge(STATE.pars_context.evidence_label, variant="secondary")
            Text(STATE.pars_context.name)
            Muted(STATE.pars_context.project_id)
        with Else():
            Small("No PARS project linked. Load one from the evidence panel.")
        Text("WBS-to-index mapping", css_class="font-semibold")
        with If(STATE.mapping_review.state == "reviewed"):
            Small(STATE.mapping_review.wbs_code)
            Small(STATE.mapping_review.series_id)
            Small(STATE.mapping_review.rationale)
        with Else():
            Small("No reviewed WBS-to-index candidate for this session.")
        Small(
            "Mapping candidates are not cost allocations. No PARS baseline "
            "cost is escalated and no PARS write-back is performed."
        )


def _tabs() -> None:
    with Tabs(
        value="component",
        css_class=(
            "[&_[role=tab]]:!text-[#041E42] "
            "[&_[role=tab]]:!bg-[#F4F2F0] "
            # The tab panel is light (#F5F5F5), so tabs need a border and a navy
            # focus outline to stay visible against it. The focus shadow ring is
            # removed because it is white and would be invisible on that panel.
            "[&_[role=tab]]:!border [&_[role=tab]]:!border-[#6C7C90] "
            "[&_[role=tab]:focus-visible]:!shadow-none "
            "[&_[role=tab]:focus-visible]:!outline-solid "
            "[&_[role=tab]:focus-visible]:!outline-2 "
            "[&_[role=tab]:focus-visible]:!outline-offset-2 "
            "[&_[role=tab]:focus-visible]:!outline-[#041E42] "
            "[&_[role=tab][aria-selected=true]]:!bg-[#285A77] "
            "[&_[role=tab][aria-selected=true]]:!text-white"
        ),
    ):
        with Tab(title="Component detail", value="component"):
            _component_tab()
        with Tab(title="Adjustment to base", value="adjustment"):
            _adjustment_tab()
        with Tab(title="Data & CSV", value="data"):
            _data_tab()
        with Tab(title="Evidence & audit", value="audit"):
            _audit_tab()
        with Tab(title="Scenario comparison", value="comparison"):
            _comparison()


def _meta_chips() -> None:
    with Row(gap=2, css_class="flex-wrap"):
        for i in range(basket_state.META_CHIP_SLOTS):
            Badge(
                Rx(f"basket.results.explorer.meta_chips.{i}"),
                variant="outline",
                css_class=OUTLINE_BADGE_CLASS,
            )


def _results() -> None:
    """The explorer and comparison, shown once the basket is approved."""
    with Card(css_class=PANE_CARD_CLASS):
        with CardHeader():
            with Row(gap=3, align="center", justify="between"):
                CardTitle(
                    STATE.basket.results.explorer.title,
                    css_class="!text-slate-100",
                )
                with If(STATE.basket.results.explorer.badge_label != ""):
                    Badge(STATE.basket.results.explorer.badge_label, variant="success")
        with CardContent():
            with Column(gap=4):
                with If(STATE.basket.results.explorer.blocked):
                    _explorer_blocked()
                with Else():
                    Muted(STATE.basket.results.explorer.subtitle)
                    with If(STATE.basket.results.explorer.warning):
                        Muted(STATE.basket.results.explorer.warning)
                    _meta_chips()
                    with If(STATE.pars_context.state == "loaded"):
                        with Column(gap=1):
                            Badge("PARS context · read-only", variant="secondary")
                            Small(STATE.pars_context.name)
                            Muted(STATE.pars_context.project_id)
                            Small(
                                "Context only; synthetic index factors do not "
                                "adjust PARS baseline costs."
                            )
                    with If(STATE.mapping_review.state == "reviewed"):
                        Small(
                            "WBS-to-BLS mapping candidate (not applied to calculation)"
                        )
                        Small(STATE.mapping_review.wbs_code)
                        Small(STATE.mapping_review.series_id)
                    _explorer_stats()
                    Text(
                        f"Allocation basis · {STATE.basket.total_label}",
                        css_class="font-medium",
                    )
                    _ribbon()
                    Text(
                        "Weighted component levels and composite factor",
                        css_class="font-medium",
                    )
                    AreaChart(
                        data=STATE.basket.results.chart,
                        series=_chart_series(),
                        xAxis="period",
                        stacked=True,
                        showLegend=True,
                        height=320,
                    )
                    Small(
                        "Explore the tabs for component detail, adjustment, "
                        "observations, audit evidence, and scenario comparison.",
                        css_class="!text-slate-200",
                    )
                    _tabs()
                    Small(STATE.basket.results.explorer.fineprint)


# Example questions for the chat card. Each one was run end-to-end against the
# configured provider with the synthetic PARS and BLS sources. Clicking one only
# fills the input; the analyst still presses Search, and the text stays editable.
CHAT_EXAMPLES = (
    ("List PARS projects", "List the available PARS projects."),
    ("WBS for proj_001", "Show the top-level WBS elements for proj_001."),
    ("Steel price series", "Search the BLS catalog for steel price series."),
)


@app.tool()
async def ask_cost_intelligence(
    question: str,
    previous_question: str = "",
    previous_answer: str = "",
    previous_grounded: bool = False,
) -> dict[str, Any]:
    """Ask the locally configured LLM to query permitted read-only MCP tools."""
    result = await ask_readonly_chat(
        question,
        previous_question=previous_question,
        previous_answer=previous_answer,
        previous_grounded=previous_grounded,
    )
    result.setdefault("grounded", False)
    return result


# The chat keeps one previous question and answer, for follow-ups only. It is
# cleared when the analyst closes the chat, changes the basket project, or loads a
# PARS project, so an old answer cannot leak into an unrelated question.
CHAT_CONTEXT_RESET = [
    SetState("chat_previous_question", ""),
    SetState("chat_previous_answer", ""),
    SetState("chat_previous_grounded", False),
]


@app.ui(title="Recommended PPI escalation basket")
def ppi_basket(project_key: ProjectKey = "y12") -> PrefabApp:
    """Open the Recommended PPI escalation basket for an illustrative project.

    Shows the candidate PPI series with include checkboxes, allocation weights,
    the running total, and Normalize and Approve actions. Once approved, the
    results explorer and scenario comparison appear in the analysis pane.
    Data is synthetic.
    """
    with Column(
        gap=3,
        css_class=SHELL_CLASS,
    ) as view:
        with Row(gap=3, align="center", css_class="px-2 pt-2 min-h-[68px] flex-wrap"):
            Text(
                "ACTION Cost Intelligence",
                css_class="font-bold !text-white tracking-wide",
            )
            Small(
                "NNSA · PA&E / Review allocation / Approve allocation / "
                "Explore results",
                css_class="!text-slate-200",
            )
        _workflow_strip()
        with Row(gap=2, align="center", css_class="px-2 flex-wrap"):
            with If(STATE.show_chat):
                Button(
                    "Close Ask Cost Intelligence",
                    variant="outline",
                    size="sm",
                    css_class=BUTTON_CLASS,
                    on_click=[SetState("show_chat", False), *CHAT_CONTEXT_RESET],
                )
            with Else():
                Button(
                    "Ask Cost Intelligence (optional chat)",
                    variant="outline",
                    size="sm",
                    css_class=BUTTON_CLASS,
                    on_click=SetState("show_chat", True),
                )
        with If(STATE.show_chat):
            with Card(css_class=PANE_CARD_CLASS):
                with CardHeader():
                    CardTitle("Ask Cost Intelligence", css_class="!text-white")
                    CardDescription(
                        "Ask the local assistant to explore approved MCP sources. "
                        "Chat does not change basket weights or approvals.",
                        css_class="!text-slate-200",
                    )
                with CardContent():
                    with Column(gap=2):
                        # Explicit name: the field and the examples share one state key,
                        # so a clicked example replaces typed text (see test_server.py).
                        Input(
                            name="chat_question",
                            value=STATE.chat_question,
                            on_change=SetState("chat_question", EVENT),
                            placeholder=(
                                "Ask about PARS projects or BLS index candidates"
                            ),
                            css_class="!bg-white !text-[#041E42]",
                        )
                        with Row(gap=2, align="center", css_class="flex-wrap"):
                            Small("Examples:", css_class="!text-slate-200")
                            for label, text in CHAT_EXAMPLES:
                                Button(
                                    label,
                                    variant="outline",
                                    size="sm",
                                    css_class=BUTTON_CLASS,
                                    on_click=SetState("chat_question", text),
                                )
                        Button(
                            "Search",
                            css_class=BUTTON_CLASS,
                            on_click=CallTool(
                                ask_cost_intelligence,
                                arguments={
                                    "question": STATE.chat_question,
                                    "previous_question": STATE.chat_previous_question,
                                    "previous_answer": STATE.chat_previous_answer,
                                    "previous_grounded": STATE.chat_previous_grounded,
                                },
                                on_success=[
                                    SetState("chat_reply", RESULT),
                                    SetState(
                                        "chat_previous_question", STATE.chat_question
                                    ),
                                    SetState("chat_previous_answer", RESULT.answer),
                                    SetState("chat_previous_grounded", RESULT.grounded),
                                ],
                                on_error=ShowToast(
                                    "Local chat request failed. Basket is unaffected.",
                                    variant="error",
                                ),
                            ),
                        )
                        with If(STATE.chat_reply.state == "loaded"):
                            Text(STATE.chat_reply.answer, css_class="!text-white")
                            Small("Executed MCP tools", css_class="!text-slate-200")
                            with ForEach("chat_reply.tools") as tool:
                                Small(tool.tool)
                        with Else():
                            Muted(STATE.chat_reply.message)
        with Row(gap=3, css_class="flex flex-col lg:flex-row items-start w-full"):
            with Column(gap=0, css_class="w-full min-w-0 lg:w-[33%] lg:shrink-0"):
                with Card(css_class=PANE_CARD_CLASS):
                    with CardHeader():
                        with Row(gap=3, align="center", justify="between"):
                            CardTitle(STATE.basket.title, css_class="!text-slate-100")
                            with If(STATE.basket.locked):
                                Badge(
                                    STATE.basket.workflow.badge_label, variant="success"
                                )
                            with Else():
                                Badge(
                                    STATE.basket.workflow.badge_label, variant="warning"
                                )
                        CardDescription(
                            STATE.basket.subtitle, css_class="!text-slate-300"
                        )
                    with CardContent():
                        with Column(gap=4):
                            _demo_project_picker()
                            _presets()
                            _table()
                            with If(STATE.basket.locked):
                                Small(
                                    "The approved allocation is locked. Choose Edit "
                                    "approved allocation to change components or "
                                    "weights.",
                                    css_class="!text-slate-100",
                                )
                            _status()
                            with If(STATE.basket.toast):
                                Muted(STATE.basket.toast)
                            Muted(STATE.basket.notice)
                    with CardFooter(css_class="!bg-[#142D4F] !text-white"):
                        with Column(gap=3, css_class="w-full"):
                            _actions()
                            Small(STATE.basket.fineprint)
            with Column(gap=0, css_class="w-full min-w-0 lg:flex-1"):
                with If(STATE.basket.locked):
                    _results()
                with Else():
                    with Card(css_class=PANE_CARD_CLASS):
                        with CardHeader():
                            CardTitle("Analysis workspace", css_class="!text-slate-100")
                            CardDescription(
                                "Results appear after basket approval",
                                css_class="!text-slate-300",
                            )
                        with CardContent():
                            with Column(gap=3):
                                Text("Approve the allocation to explore the index.")
                                Muted(
                                    "The index result, component chart, "
                                    "and audit details will appear here."
                                )
                                Badge(
                                    "Awaiting basket approval",
                                    variant="outline",
                                    css_class=OUTLINE_BADGE_CLASS,
                                )
                                Button(
                                    "Download CSV",
                                    variant="outline",
                                    size="sm",
                                    css_class=BUTTON_CLASS,
                                    disabled=True,
                                )
                                Muted(
                                    "Download CSV is unavailable until the allocation "
                                    "is approved; results are then in Data & CSV."
                                )
            # The evidence panel can be collapsed; its state is kept either way.
            with If(STATE.evidence_open):
                _context_rail()
            with Else():
                _evidence_collapsed()
    return PrefabApp(
        view=view,
        state={
            "basket": _with_workflow(basket_state.initial_basket(_source, project_key)),
            "evidence_open": True,
            "show_chat": False,
            "chat_question": "",
            "chat_previous_question": "",
            "chat_previous_answer": "",
            "chat_previous_grounded": False,
            "chat_reply": {"state": "idle", "message": "", "answer": "", "tools": []},
            "pars_query": "",
            "pars_projects": _initial_pars_projects(),
            "pars_context_input": "",
            "pars_context": _empty_pars_context(),
            "caef_summary": empty_caef_summary(),
            "mapping_wbs_code": "",
            "mapping_component": _source.list_sources()[0].component_id,
            "mapping_rationale": "",
            "mapping_review": empty_mapping_review(),
            "csv_export": _empty_csv_export(),
        },
    )


@contextmanager
def _pars_session() -> Iterator[pars_live.LiveParsSession]:
    """The live PARS session for one render; without PARS_REPO it is not connected."""
    configured = os.environ.get("PARS_REPO", "").strip()
    # The PARS MCP server ships in this repository. A local checkout should
    # work without requiring every developer to set PARS_REPO manually.
    checkout = Path(__file__).resolve().parents[2]
    same_checkout = checkout / "src" / "pars_local_mcp" / "server.py"
    repo = configured or (str(checkout) if same_checkout.is_file() else None)
    with pars_live.live_session(repo) as session:
        yield session


def _pars_header() -> None:
    with Card(css_class="m-4 " + EVIDENCE_CARD_CLASS):
        with CardHeader():
            CardTitle("PARS project")
        with CardContent():
            with If(STATE.pars.header.state == "error"):
                Muted(STATE.pars.header.message)
            with Else():
                with If(STATE.pars.header.label != ""):
                    Badge(STATE.pars.header.label, variant="secondary")
                Text(STATE.pars.header.name, css_class="font-medium")
                Muted(STATE.pars.project_id)
                Muted(STATE.pars.header.summary)


def _pars_evidence() -> None:
    with Card(css_class="m-4 " + EVIDENCE_CARD_CLASS):
        with CardHeader():
            CardTitle("Input evidence")
        with CardContent():
            with If(STATE.pars.evidence.state == "error"):
                Muted(STATE.pars.evidence.message)
            with Else():
                Badge(STATE.pars.evidence.label, variant="secondary")
                with If(STATE.pars.evidence.ok):
                    Muted("Inputs check passed.")
                with Else():
                    Muted("Inputs need attention:")
                    with ForEach("pars.evidence.problems") as problem:
                        Small(problem)
                    Muted(STATE.pars.evidence.detail)


def _pars_roots() -> None:
    with Card(css_class="m-4 " + EVIDENCE_CARD_CLASS):
        with CardHeader():
            CardTitle("WBS hierarchy")
        with CardContent():
            with If(STATE.pars.roots.state == "loaded"):
                with ForEach("pars.roots.rows") as row:
                    with Row(gap=3, justify="between"):
                        Text(row.title)
                        Muted(row.wbs_code)
            with If(STATE.pars.roots.state == "empty"):
                Muted("No top-level elements.")
            with If(STATE.pars.roots.state == "error"):
                Muted(STATE.pars.roots.message)


def _pars_descriptions() -> None:
    with Card(css_class="m-4 " + EVIDENCE_CARD_CLASS):
        with CardHeader():
            CardTitle("Project descriptions (all projects)")
        with CardContent():
            with If(STATE.pars.descriptions.state == "hidden"):
                Muted("Read-only views are hidden for this source.")
            with If(STATE.pars.descriptions.state == "loaded"):
                with ForEach("pars.descriptions.rows") as row:
                    with Column(gap=0):
                        Text(row.project_name, css_class="font-medium")
                        Muted(row.project_status)
            with If(STATE.pars.descriptions.state == "empty"):
                Muted("No rows.")
            Muted(STATE.pars.descriptions.summary)
            with If(STATE.pars.descriptions.state == "error"):
                Muted(STATE.pars.descriptions.message)


def _pars_rows() -> None:
    with Card(css_class="m-4 " + EVIDENCE_CARD_CLASS):
        with CardHeader():
            CardTitle("Source rows (all projects)")
        with CardContent():
            with If(STATE.pars.rows.state == "hidden"):
                Muted("Read-only views are hidden for this source.")
            with If(STATE.pars.rows.state == "loaded"):
                with ForEach("pars.rows.rows") as row:
                    with Row(gap=3):
                        Muted(row.wbs)
                        Text(row.wbs_title)
            with If(STATE.pars.rows.state == "empty"):
                Muted("No rows.")
            Muted(STATE.pars.rows.summary)
            with If(STATE.pars.rows.state == "error"):
                Muted(STATE.pars.rows.message)


def _pars_log() -> None:
    with Card(css_class="m-4 " + EVIDENCE_CARD_CLASS):
        with CardHeader():
            CardTitle("PARS tool calls")
        with CardContent():
            with If(STATE.pars.log.state == "loaded"):
                with ForEach("pars.log.rows") as entry:
                    with Row(gap=3, justify="between"):
                        Text(entry.tool)
                        Badge(entry.status, variant="secondary")
            with If(STATE.pars.log.state == "empty"):
                Muted("No tool calls yet.")


PANEL_NAMES = ("search", "lineage", "leaves", "level", "run")


def _refused(message: str) -> dict[str, Any]:
    """A refused request, with every key a panel result has, so views bind."""
    return {
        "state": "error",
        "message": message,
        "rows": [],
        "run_id": "",
        "created_at": "",
        "label": "",
        "stages": [],
    }


def _level(value: str) -> int | None:
    text = value.strip()
    if not (text.isascii() and text.isdigit()):
        return None
    level = int(text)
    return level if 1 <= level <= 8 else None


def _refusal(panel: str, project_id: str, value: str) -> dict[str, Any] | None:
    """Refuse a bad request before any PARS session opens."""
    if panel not in PANEL_NAMES:
        return _refused("Choose a panel.")
    if not project_id.strip():
        return _refused(pars_panels.CHOOSE_PROJECT)
    if panel == "search" and not value.strip():
        return _refused(pars_panels.CHOOSE_SEARCH)
    if panel == "search" and ("%" in value or "_" in value):
        return _refused(pars_panels.SEARCH_CODES_ONLY)
    if panel == "lineage" and not value.strip():
        return _refused(pars_panels.CHOOSE_ELEMENT)
    if panel == "run" and not value.strip():
        return _refused(pars_panels.CHOOSE_RUN)
    if panel == "level" and _level(value) is None:
        return _refused(pars_panels.CHOOSE_LEVEL)
    return None


class CallRow(BaseModel):
    """One PARS call in the log, in the shape pars.log.rows uses."""

    tool: str
    status: Literal["ok", "error", "refused"]


@app.tool()
def pars_panel(
    project_id: str,
    panel: str,
    value: str = "",
    log: list[CallRow] | None = None,
) -> dict[str, Any]:
    """One explore panel of the PARS workspace, loaded when the user asks for it.

    Returns the panel state and the call log: ``log`` as the view sent it, with
    the calls this request made added.
    """
    prior = [row.model_dump() for row in log or []]
    refused = _refusal(panel, project_id, value)
    if refused is not None:
        return {"panel": refused, "log": pars_panels.chat_log(prior)}
    with _pars_session() as session:
        client = pars_panels.LoggedClient(session)
        if panel == "search":
            result = pars_panels.search(client, project_id, pattern=value)
        elif panel == "lineage":
            result = pars_panels.lineage(client, project_id, value)
        elif panel == "leaves":
            result = pars_panels.leaf_nodes(client, project_id)
        elif panel == "run":
            result = pars_panels.run_status(client, value)
        else:
            result = pars_panels.by_level(client, project_id, _level(value) or 0)
    return {"panel": result, "log": pars_panels.chat_log([*prior, *client.entries])}


def _panel(panel: str, value: Any, state_key: str) -> CallTool:
    """Load one explore panel through the backend tool and store its result.

    AppendState adds one value, so the log is replaced with the list the tool
    returns, which already holds the calls made so far plus this request's calls.
    """
    return CallTool(
        pars_panel,
        arguments={
            "project_id": STATE.pars.project_id,
            "panel": panel,
            "value": value,
            "log": STATE.pars.log.rows,
        },
        on_success=[
            SetState(state_key, RESULT.panel),
            SetState("pars.log", RESULT.log),
        ],
        on_error=ShowToast("That PARS panel could not be loaded.", variant="error"),
    )


def _element_rows(panel: str, empty: str, *, level: bool = False) -> None:
    state = getattr(STATE.pars.panels, panel)
    with If(state.state == "loaded"):
        with ForEach(f"pars.panels.{panel}.rows") as row:
            with Row(gap=3, justify="between"):
                Text(row.title)
                with Row(gap=2):
                    if level:
                        Badge(
                            row.level,
                            variant="outline",
                            css_class=OUTLINE_BADGE_CLASS,
                        )
                    Muted(row.wbs_code)
    with If(state.state == "empty"):
        Muted(empty)
    with If(state.state == "error"):
        Muted(state.message)


def _run_panel() -> None:
    run = STATE.pars.panels.run
    with Row(gap=2):
        Input(
            value=STATE.pars.inputs.run,
            placeholder="Run id",
            on_change=SetState("pars.inputs.run", EVENT),
        )
        Button(
            "Show run",
            variant="default",
            size="sm",
            css_class=BUTTON_CLASS,
            on_click=_panel("run", STATE.pars.inputs.run, "pars.panels.run"),
        )
    with If(run.state == "loaded"):
        Badge(run.label, variant="secondary")
        Muted(run.created_at)
        with ForEach("pars.panels.run.stages") as stage:
            with Row(gap=3, justify="between"):
                Text(stage.stage)
                Muted(stage.status)
    with If(run.state == "empty"):
        Muted("No stages recorded.")
    with If(run.state == "error"):
        Muted(run.message)


def _pars_explore() -> None:
    with Card(css_class="m-4 " + EVIDENCE_CARD_CLASS):
        with CardHeader():
            CardTitle("Explore the WBS")
        with CardContent():
            with Row(gap=2):
                Input(
                    value=STATE.pars.inputs.search,
                    placeholder="WBS code prefix, e.g. 1.2",
                    on_change=SetState("pars.inputs.search", EVENT),
                )
                Button(
                    "Search codes",
                    variant="default",
                    size="sm",
                    css_class=BUTTON_CLASS,
                    on_click=_panel(
                        "search", STATE.pars.inputs.search, "pars.panels.search"
                    ),
                )
            _element_rows("search", "No matching elements.", level=True)
            with Row(gap=2):
                Input(
                    value=STATE.pars.inputs.lineage,
                    placeholder="WBS code of an element",
                    on_change=SetState("pars.inputs.lineage", EVENT),
                )
                Button(
                    "Show lineage",
                    variant="default",
                    size="sm",
                    css_class=BUTTON_CLASS,
                    on_click=_panel(
                        "lineage", STATE.pars.inputs.lineage, "pars.panels.lineage"
                    ),
                )
            _element_rows("lineage", "No lineage for this element.")
            with Row(gap=2):
                Input(
                    value=STATE.pars.inputs.level,
                    placeholder="Level 1 to 8",
                    on_change=SetState("pars.inputs.level", EVENT),
                )
                Button(
                    "Show level",
                    variant="default",
                    size="sm",
                    css_class=BUTTON_CLASS,
                    on_click=_panel(
                        "level", STATE.pars.inputs.level, "pars.panels.level"
                    ),
                )
                Button(
                    "Leaf nodes",
                    variant="outline",
                    size="sm",
                    css_class=BUTTON_CLASS,
                    on_click=_panel("leaves", "", "pars.panels.leaves"),
                )
            _element_rows("level", "No elements at this level.")
            _element_rows("leaves", "No leaf elements.")
            _run_panel()


MAX_DRAFT_LINES = 50
MAX_CODE_LENGTH = 64
MAX_TITLE_LENGTH = 200


class DraftLine(BaseModel):
    wbs_code: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True, min_length=1, max_length=MAX_CODE_LENGTH
        ),
    ]
    title: Annotated[
        str, StringConstraints(strip_whitespace=True, max_length=MAX_TITLE_LENGTH)
    ] = ""


@app.tool()
def pars_draft(
    lines: Annotated[list[DraftLine], Field(max_length=MAX_DRAFT_LINES)],
    wbs_code: str = "",
    title: str = "",
) -> dict[str, Any]:
    """Add one line to the write-back draft, or clear it. Nothing is sent to PARS.

    A refused add raises ToolError, so the view keeps the typed inputs and the
    draft already on screen.
    """
    rows = [line.model_dump() for line in lines]
    code = wbs_code.strip()
    if not code:
        return pars_panels.write_back_preview(rows)
    if len(rows) >= MAX_DRAFT_LINES:
        raise ToolError(f"A draft holds at most {MAX_DRAFT_LINES} lines.")
    try:
        line = DraftLine(wbs_code=code, title=title)
    except ValidationError:
        raise ToolError(
            f"A WBS code holds at most {MAX_CODE_LENGTH} characters and a "
            f"title at most {MAX_TITLE_LENGTH}."
        ) from None
    rows.append(line.model_dump())
    return pars_panels.write_back_preview(rows)


def _pars_draft() -> None:
    draft = STATE.pars.draft
    clear = {"lines": [], "wbs_code": "", "title": ""}
    with Card(css_class="m-4 " + EVIDENCE_CARD_CLASS):
        with CardHeader():
            CardTitle("Write-back preview (draft)")
        with CardContent():
            Muted(draft.note)
            with Row(gap=2):
                Input(
                    value=STATE.pars.inputs.draft_code,
                    placeholder="WBS code",
                    on_change=SetState("pars.inputs.draft_code", EVENT),
                )
                Input(
                    value=STATE.pars.inputs.draft_title,
                    placeholder="Proposed title",
                    on_change=SetState("pars.inputs.draft_title", EVENT),
                )
                Button(
                    "Add line",
                    variant="default",
                    size="sm",
                    css_class=BUTTON_CLASS,
                    on_click=CallTool(
                        pars_draft,
                        arguments={
                            "lines": draft.rows,
                            "wbs_code": STATE.pars.inputs.draft_code,
                            "title": STATE.pars.inputs.draft_title,
                        },
                        on_success=[
                            SetState("pars.draft", RESULT),
                            SetState("pars.inputs.draft_code", ""),
                            SetState("pars.inputs.draft_title", ""),
                        ],
                        on_error=ShowToast(
                            "The draft could not be updated.",
                            description=ERROR,
                            variant="error",
                        ),
                    ),
                )
                Button(
                    "Clear draft",
                    variant="outline",
                    size="sm",
                    css_class=BUTTON_CLASS,
                    on_click=CallTool(
                        pars_draft,
                        arguments=clear,
                        on_success=SetState("pars.draft", RESULT),
                        on_error=ShowToast(
                            "The draft could not be cleared.", variant="error"
                        ),
                    ),
                )
            with If(draft.state == "draft"):
                with ForEach("pars.draft.rows") as row:
                    with Row(gap=3, justify="between"):
                        Text(row.title)
                        Muted(row.wbs_code)
            with If(draft.state == "empty"):
                Muted("No draft lines yet.")
            with If(draft.state == "error"):
                Muted(draft.message)


mcp = FastMCP("NNSA cost intelligence (basket app)", providers=[app])


# Public, dependency-free landing pages. These explain the local MCP App; they do
# not pretend that opening /mcp launches the embedded Prefab UI in a browser.
_WELCOME_CSS = """
:root {color-scheme: light;
font-family: system-ui, -apple-system, Segoe UI, sans-serif;}
* {box-sizing:border-box}
body {margin:0; background:#f4f5f7; color:#14253e; line-height:1.55}
header {background:#041e42; color:#fff;
padding:1.2rem max(1.2rem, calc((100% - 1060px)/2))}
header .eyebrow {font-size:.8rem; letter-spacing:.07em; color:#d8e4f2}
header strong {display:block; font-size:1.2rem; margin:.25rem 0}
nav {display:flex; flex-wrap:wrap; gap:1.1rem; margin-top:.8rem}
nav a {color:#fff; text-underline-offset:4px}
a:focus-visible {outline:3px solid #5ba9ce; outline-offset:4px}
main {max-width:1060px; margin:auto; padding:2.5rem 1.2rem 3rem}
h1 {font-size:clamp(2rem,4vw,3.1rem); line-height:1.15; margin:.35rem 0 1rem}
h2 {font-size:1.3rem; margin-top:0}
p {max-width:73ch}
.lead {font-size:1.14rem; max-width:65ch; color:#314660}
.eyebrow {font-size:.8rem; font-weight:750; letter-spacing:.06em;
text-transform:uppercase}
.grid {display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));
gap:1rem;margin:2rem 0}
.card {background:#fff;border:1px solid #c9d1db;border-radius:10px;padding:1.3rem}
.card a {font-weight:700; color:#17496c}
.notice {border-left:4px solid #386b86;background:#e9f0f5;
padding:1rem 1.2rem;margin:2rem 0}
.steps {padding-left:1.5rem;max-width:73ch}
.steps li {padding:.35rem 0}
code {background:#e4e9ee;padding:.1rem .3rem;border-radius:3px;overflow-wrap:anywhere}
footer {border-top:1px solid #c9d1db; padding:1.2rem;
text-align:center; color:#435269;font-size:.85rem}
@media (prefers-reduced-motion:reduce) {
*,*:before,*:after {scroll-behavior:auto!important}}
"""


def _information_page(title: str, body: str) -> HTMLResponse:
    """Render static, accessible local documentation with no external assets."""
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport"
content="width=device-width,initial-scale=1">
<title>{title} | NNSA Cost Intelligence</title>
<style>{_WELCOME_CSS}</style></head><body>
<header><div class="eyebrow">NNSA · Office of Program Analysis &amp; Evaluation</div>
<strong>Cost Intelligence</strong><nav aria-label="Primary navigation">
<a href="/">Welcome</a><a href="/quickstart">Quickstart</a>
<a href="/methodology">Methodology</a>
<a href="/data-sources">Data sources &amp; limitations</a></nav></header>
<main id="main-content">{body}</main>
<footer>Cost Intelligence · Read-only project context ·
Local analytical demonstration</footer>
</body></html>"""
    return HTMLResponse(
        html,
        headers={
            "Content-Security-Policy": (
                "default-src 'none'; style-src 'unsafe-inline'; "
                "base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
            ),
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store",
        },
    )


@mcp.custom_route("/", methods=["GET"], include_in_schema=False)
async def index(request: Request) -> Response:
    """Analyst-focused welcome page for the MCP service."""
    return _information_page(
        "Welcome",
        """<div class="eyebrow">Explore the project-to-index workflow</div>
<h1>Cost Intelligence</h1>
<p class="lead">Explore a project, review its CAEF mapping, build an escalation basket,
and follow every calculation back to its inputs.</p>
<div class="notice"><strong>Demonstration data:</strong> Basket observations
and example-project calculations are synthetic. PARS project/WBS context is
independent, read-only evidence. No PARS cost baseline is escalated.</div>
<div class="grid" aria-label="Get started and documentation">
<section class="card"><h2>Start the interactive demonstration</h2>
<p>The interactive basket is an embedded MCP App, opened from a compatible
MCP host—not directly from this web page.</p>
<a href="/quickstart">Launch instructions</a></section>
<section class="card"><h2>Methodology</h2>
<p>See how whole-project CAEF mapping and weighted economic-index
calculations fit together.</p><a href="/methodology">Read the methodology</a></section>
<section class="card"><h2>Evidence &amp; limitations</h2>
<p>Understand synthetic versus PARS data, read-only access, and what the
current application does not calculate.</p>
<a href="/data-sources">Review data sources</a></section></div>
<p>Designed for transparent, repeatable cost-estimating analysis. The
<code>/mcp</code> protocol endpoint is not a standalone browser workspace.</p>""",
    )


@mcp.custom_route("/quickstart", methods=["GET"], include_in_schema=False)
async def quickstart(request: Request) -> Response:
    """Explain the supported entry point without promising a direct web launch."""
    return _information_page(
        "Quickstart",
        """<h1>Quickstart</h1>
<p class="lead">Explore project evidence, CAEF classification, and an
illustrative
cost-index scenario.</p><ol class="steps">
<li>Connect a compatible MCP Apps host to this service's <code>/mcp</code>
endpoint, using the host's approved local configuration.</li>
<li>Invoke the <code>ppi_basket</code> tool to open the interactive workspace.
In development, use the FastMCP <code>dev apps</code> preview.</li>
<li>Select a PARS demo project and read its project description and WBS.
Choose <strong>View saved CAEF mapping</strong>, or use
<strong>Run model on bundled data</strong> to regenerate local predictions
when the packaged model is available.</li>
<li>Build an escalation basket directly; CAEF-to-BLS suggestions are optional.
Review component weights, normalize, and approve the scenario.</li>
<li>Explore the component charts, scenario comparison, and
<strong>Evidence &amp; audit</strong>. Verify <strong>Data &amp; CSV</strong>
before sharing results.</li></ol>
<div class="notice">The <code>/mcp</code> endpoint is a protocol endpoint,
not a browser page. The separate FastMCP development preview may require
runtime assets; confirm network policy before launching it.</div>
<p><a href="/">Return to welcome</a></p>""",
    )


@mcp.custom_route("/methodology", methods=["GET"], include_in_schema=False)
async def methodology(request: Request) -> Response:
    """Provide source-aligned explanation of the currently implemented method."""
    return _information_page(
        "Methodology",
        """<h1>Methodology</h1>
<p class="lead">The application constructs an illustrative weighted PPI
basket from chosen components and allocation weights.</p>
<div class="grid"><section class="card"><h2>Review and normalize</h2>
<p>Include or exclude components, edit weights, and normalize the included
weights to 100%. Edits to an approved basket require renewed review.</p></section>
<section class="card"><h2>Explore the calculation</h2>
<p>Inspect normalized and raw index views, the weighted composite factor,
scenario comparisons, adjustment-to-base analysis, and the source-row table.</p>
</section><section class="card"><h2>Review candidate mappings</h2>
<p>The entire project WBS can be classified into CAEF 2.0 categories.
A saved classification can be viewed immediately; running the model on
the bundled snapshot is optional. BLS-index suggestions from CAEF are
also optional
and not yet an automated feature. None of these assigns dollar
weights.</p></section></div>
<p><a href="/data-sources">Data sources and limitations</a></p>""",
    )


@mcp.custom_route("/data-sources", methods=["GET"], include_in_schema=False)
async def data_sources(request: Request) -> Response:
    """Make provenance and non-capabilities visible from the homepage."""
    return _information_page(
        "Data sources & limitations",
        """<h1>Data sources &amp; limitations</h1>
<p class="lead">Distinguish local scenario observations from independently
retrieved project context.</p>
<div class="grid"><section class="card"><h2>Economic-index scenarios</h2>
<p>Local synthetic PPI observations and example project allocations are
illustrative—not live Bureau of Labor Statistics releases.</p></section>
<section class="card"><h2>PARS project evidence</h2>
<p>Where available, PARS project identity and WBS elements are retrieved
through the local read-only MCP bridge. Availability depends on the
configured local source and its validation.</p></section>
<section class="card"><h2>Boundaries</h2>
<p>A WBS-to-index mapping is a reviewable candidate, not an approved
allocation. The tool does not assert PARS cost baselines, escalate actual
PARS dollars, or write changes back to PARS.</p></section></div>
<p>Use the interactive <strong>Evidence &amp; audit</strong> tab to inspect
analysis-specific inputs and approval context.</p>""",
    )


@mcp.custom_route("/favicon.ico", methods=["GET"], include_in_schema=False)
async def favicon(request: Request) -> Response:
    """Browsers request this on their own; there is no icon to serve."""
    return Response(status_code=204)


@mcp.custom_route("/exports/{token}", methods=["GET"], include_in_schema=False)
async def download_export(request: Request) -> Response:
    """Serve a prepared CSV as an attachment; unknown or evicted tokens get 404."""
    entry = _EXPORTS.get(request.path_params["token"])
    if entry is None:
        return Response(
            "This export has expired. Prepare the CSV again.",
            status_code=404,
            media_type="text/plain",
        )
    filename, body = entry
    return Response(
        body,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


if __name__ == "__main__":
    mcp.run()
