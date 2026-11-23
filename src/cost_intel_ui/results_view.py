"""View models for the "Custom PPI escalation index" results explorer.

Covers the header, allocation ribbon and legend, stacked main chart, and the
three tabs (Component detail, Adjustment to base, Data & CSV). Functions only
select, format, and reshape values already in the packet; they never
recompute economics.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from cost_intel_ui.contract import validate_packet
from cost_intel_ui.data_access import ResultPacket
from cost_intel_ui.formatting import fixed, percent_of_fraction, signed

TABLE_FIELDS: tuple[str, ...] = (
    "period",
    "component_name",
    "component_id",
    "series_id",
    "allocation_weight",
    "raw_ppi_value",
    "normalized_factor",
    "normalized_percent",
    "weighted_level",
    "composite_factor",
    "base_year",
    "snapshot_id",
    "observation_id",
    "warning_code",
)
NUMERIC_FIELDS = frozenset(
    {
        "allocation_weight",
        "raw_ppi_value",
        "normalized_factor",
        "normalized_percent",
        "weighted_level",
        "composite_factor",
        "base_year",
    }
)
WATERFALL_SHORT_LABELS = {
    "steel": "Steel",
    "concrete": "Concrete",
    "electric": "Electrical",
    "machinery": "Machinery",
}
MAX_LISTED_ISSUES = 35
_FORMULA_PREFIX = re.compile(r"^\s*[=+\-@]")


@dataclass(frozen=True)
class Stat:
    label: str
    value: str
    tone: Literal["green"] | None


@dataclass(frozen=True)
class RibbonSegment:
    component_id: str
    name: str
    color_hex: str
    weight: float
    percent_label: str
    description: str


@dataclass(frozen=True)
class LegendOption:
    component_id: str
    label: str
    series_id: str
    color_hex: str
    selected: bool


@dataclass(frozen=True)
class ExplorerView:
    title: str
    subtitle: str
    badge_label: str
    warning: str
    meta_chips: tuple[str, ...]
    stats: tuple[Stat, ...]
    ribbon: tuple[RibbonSegment, ...]
    legend: tuple[LegendOption, ...]
    tabs: tuple[tuple[str, str], ...]
    actions: tuple[tuple[str, str], ...]
    fineprint: str


@dataclass(frozen=True)
class BlockedResult:
    title: str
    body: str
    issues: tuple[str, ...]
    has_more: bool
    footer: str


def _components(packet: ResultPacket) -> list[Mapping[str, Any]]:
    return list(packet.result["components"])


def _blocked(issues: list[str]) -> BlockedResult:
    return BlockedResult(
        title="Result blocked — calculation contract failed",
        body=(
            "The browser did not plot this data. Resolve the source-record or "
            "invariant errors in the authoritative backend, then request a new "
            "validated result."
        ),
        issues=tuple(issues[:MAX_LISTED_ISSUES]),
        has_more=len(issues) > MAX_LISTED_ISSUES,
        footer="No chart, waterfall, or CSV export is available for this payload.",
    )


def explorer_view(
    packet: ResultPacket | None, selected_comp: str | None
) -> ExplorerView | BlockedResult:
    issues = validate_packet(packet)
    if issues or packet is None:
        return _blocked(issues)
    result, presentation = packet.result, packet.presentation
    identity, norm = result["index_identity"], result["normalization"]
    composite = result["composite_points"]
    first, latest = composite[0], composite[-1]
    components = _components(packet)
    return ExplorerView(
        title="Custom PPI escalation index",
        subtitle=(
            f"{identity['name']} · Annual observations "
            f"{first['period']}–{latest['period']}"
        ),
        badge_label="✓ Analysis approved",
        warning=(
            "Illustrative scenario only: fictional NNSA project, synthetic annual PPI "
            "observations, and precomputed offline calculations. No live BLS, "
            "CPDS/PARS, or MCP connection."
        ),
        meta_chips=(
            f"Base year {norm['base_year']} · 1.0 factor",
            f"Annual · {norm['method'].replace('_', ' ')}",
            f"Spec {identity['spec_id']} · rev {identity['spec_revision']}",
            f"Snapshot {identity['snapshot_id']}",
            f"Method {identity['methodology_version']}",
        ),
        stats=(
            Stat("Base factor", "1.0000", None),
            Stat(
                f"{latest['period']} composite factor",
                fixed(latest["composite_factor"], 4),
                None,
            ),
            Stat(
                f"{latest['period']} vs. base",
                f"{signed(presentation['latest_change_percent'])}%",
                "green",
            ),
        ),
        ribbon=tuple(
            RibbonSegment(
                c["component_id"],
                c["name"],
                c["color_hex"],
                float(c["allocation_weight"]),
                f"{percent_of_fraction(c['allocation_weight'])}%",
                c["description"],
            )
            for c in components
        ),
        legend=tuple(
            LegendOption(
                c["component_id"],
                f"{c['name']} · {percent_of_fraction(c['allocation_weight'])}%",
                c["series_id"],
                c["color_hex"],
                c["component_id"] == selected_comp,
            )
            for c in components
        ),
        tabs=(
            ("component", "Component detail"),
            ("adjustment", "Adjustment to base"),
            ("table", "Data & CSV"),
        ),
        actions=(
            ("compare", "Compare precomputed scenarios"),
            ("audit", "Open full provenance JSON"),
            ("csv", "Export table CSV ↓"),
            ("pars", "PARS write-back preview"),
        ),
        fineprint=(
            "The result is read-only: choosing components, modes, years, and filters "
            "only selects or displays values in the precomputed payload. All economic "
            "quantities are precomputed with Decimal before packaging; this view only "
            "formats, checks, filters, and reshapes them."
        ),
    )


@dataclass(frozen=True)
class StackSeries:
    component_id: str
    name: str
    color_hex: str
    bottoms: tuple[float, ...]
    tops: tuple[float, ...]


@dataclass(frozen=True)
class StackedChart:
    periods: tuple[str, ...]
    y_max: float
    series: tuple[StackSeries, ...]
    composite: tuple[float, ...]
    footnote: str


def main_chart(packet: ResultPacket) -> StackedChart:
    result = packet.result
    periods = tuple(p["period"] for p in result["composite_points"])
    composite = tuple(float(p["composite_factor"]) for p in result["composite_points"])
    peak = max(1.10, *composite) + 0.08
    layers = {
        (r["period"], r["component_id"]): r for r in packet.presentation["stack_layers"]
    }
    series = tuple(
        StackSeries(
            c["component_id"],
            c["name"],
            c["color_hex"],
            tuple(float(layers[(p, c["component_id"])]["bottom"]) for p in periods),
            tuple(float(layers[(p, c["component_id"])]["top"]) for p in periods),
        )
        for c in _components(packet)
    )
    base = result["normalization"]["base_year"]
    return StackedChart(
        periods=periods,
        y_max=math.ceil(peak * 20) / 20,
        series=series,
        composite=composite,
        footnote=(
            f"Y-axis: composite factor; annual base year {base} = 1.0. Black line: "
            "sum of the stacked weighted component levels. Hover an area for a "
            "period-specific observation; keyboard users can focus each chart point "
            "or use the data table."
        ),
    )


@dataclass(frozen=True)
class ComponentDetail:
    component_id: str
    title: str
    mode: Literal["normalized", "raw"]
    years: tuple[int, ...]
    values: tuple[float, ...]
    y_min: float
    y_max: float
    reference_line: float | None
    color_hex: str
    metadata: str
    footnote: str


@dataclass(frozen=True)
class UnknownComponent:
    component_id: str | None
    message: str


def component_detail(
    packet: ResultPacket,
    component_id: str | None,
    mode: Literal["normalized", "raw"],
) -> ComponentDetail | UnknownComponent:
    comp = next(
        (c for c in _components(packet) if c["component_id"] == component_id), None
    )
    if comp is None:
        return UnknownComponent(
            component_id,
            f"Component {component_id} is not in the returned specification. Choose "
            "one of the named legend options; no component history was substituted.",
        )
    points = sorted(
        (
            p
            for p in packet.result["component_points"]
            if p["component_id"] == component_id
        ),
        key=lambda p: p["year"],
    )
    raw = mode == "raw"
    values = tuple(
        float(p["raw_ppi_value"]) if raw else float(p["normalized_factor"]) * 100
        for p in points
    )
    if raw:
        y_min, y_max = min(values) * 0.92, max(values) * 1.08
    else:
        y_min = min(90, math.floor(min(values) / 10) * 10)
        y_max = max(120, math.ceil(max(values) / 10) * 10)
    base = packet.result["normalization"]["base_year"]
    shows = (
        "This chart shows unweighted raw PPI values."
        if raw
        else "This chart shows the unweighted normalized factor as percent of base."
    )
    return ComponentDetail(
        component_id=comp["component_id"],
        title=f"{comp['name']} · {comp['series_id']}",
        mode=mode,
        years=tuple(p["year"] for p in points),
        values=values,
        y_min=y_min,
        y_max=y_max,
        reference_line=None if raw else 100,
        color_hex=comp["color_hex"],
        metadata=(
            f"{comp['description']} Allocation: "
            f"{percent_of_fraction(comp['allocation_weight'])}%. Raw reference: "
            f"{comp['raw_reference_basis']}. Normalization: annual average in "
            f"{base}. {shows}"
        ),
        footnote=(
            "Original synthetic index-point values; the raw series must not be "
            "compared with other components on a shared axis."
            if raw
            else f"Normalized percent of base; the dashed reference marks 100% in "
            f"{base}."
        ),
    )


def eligible_adjustment_years(packet: ResultPacket) -> list[str]:
    result = packet.result
    components = _components(packet)
    found = {(p["component_id"], p["period"]) for p in result["component_points"]}
    adjustments = packet.presentation.get("adjustments_by_year") or {}
    years = []
    for p in result["composite_points"]:
        period = str(p["period"])
        complete = p.get("period_kind") == "annual_average" and all(
            (c["component_id"], period) in found for c in components
        )
        record = adjustments.get(period)
        if complete and record and len(record.get("steps") or []) == len(components):
            years.append(period)
    return years


@dataclass(frozen=True)
class WaterfallBar:
    label: str
    start: float
    end: float
    color_hex: str
    is_total: bool
    value_label: str


@dataclass(frozen=True)
class AdjustmentView:
    source_year: str
    base_year: int
    source_composite: str
    adjustment_factor: str
    caption: str
    y_min: float
    y_max: float
    bars: tuple[WaterfallBar, ...]
    reconcile: str
    math_rows: tuple[tuple[str, str], ...]
    ending_factor: str


@dataclass(frozen=True)
class NoAdjustmentRequired:
    message: str


@dataclass(frozen=True)
class AdjustmentUnavailable:
    title: str
    detail: str


TOTAL_BAR_COLOR = "#182b36"


def adjustment_view(
    packet: ResultPacket, year: str
) -> AdjustmentView | NoAdjustmentRequired | AdjustmentUnavailable:
    base = packet.result["normalization"]["base_year"]
    record = (packet.presentation.get("adjustments_by_year") or {}).get(year)
    if not record:
        has_point = any(p["period"] == year for p in packet.result["composite_points"])
        detail = (
            f"Complete annual component observations for {year} exist, but no "
            "authoritative precomputed adjustment record was returned for that year."
            if has_point
            else f"Annual composite observations for {year} are missing or incomplete."
        )
        return AdjustmentUnavailable(
            f"Adjustment unavailable for {year}",
            f"{detail} No partial waterfall was drawn. Select another eligible year "
            "or obtain a complete backend result.",
        )
    factor_text = record["adjustment_factor"]
    if record["source_year"] == record["base_year"]:
        return NoAdjustmentRequired(
            f"The source year {base} equals the annual base year. The returned factor "
            f"is {factor_text} (100%) and every component adjustment is zero."
        )
    comps = {c["component_id"]: c for c in _components(packet)}
    steps: Sequence[Mapping[str, Any]] = record["steps"]
    factor = float(factor_text)
    running = [float(s["running_adjustment_factor"]) for s in steps]
    values = [1.0, factor, *running]
    y_min, y_max = min(values) - 0.045, max(values) + 0.045

    factor_percent = percent_of_fraction(factor_text, 8)
    bars = [
        WaterfallBar(
            "Source year", y_min, 1.0, TOTAL_BAR_COLOR, True, f"{fixed(100, 8)}%"
        )
    ]
    previous = 1.0
    for step, end in zip(steps, running, strict=True):
        comp = comps[step["component_id"]]
        label = WATERFALL_SHORT_LABELS.get(comp["component_id"], comp["name"])
        contribution = Decimal(step["adjustment_contribution"]) * 100
        bars.append(
            WaterfallBar(
                label,
                previous,
                end,
                comp["color_hex"],
                False,
                f"{signed(contribution, 8)} pp",
            )
        )
        previous = end
    bars.append(
        WaterfallBar(
            "To base", y_min, factor, TOTAL_BAR_COLOR, True, f"{factor_percent}%"
        )
    )
    return AdjustmentView(
        source_year=year,
        base_year=base,
        source_composite=record["source_composite_factor"],
        adjustment_factor=factor_text,
        caption=(
            "Convert a selected-year basket amount into base-year terms. Start at "
            "100% of the selected-year amount, add each signed component step, and "
            f"end at {factor_percent}%."
        ),
        y_min=y_min,
        y_max=y_max,
        bars=tuple(bars),
        reconcile=(
            f"{signed(Decimal(record['adjustment_percent']) * 100, 8)}% adjustment · "
            f"100% + Σ component contributions = {factor_percent}% (display rounding "
            "tolerance ±0.000001 percentage point)."
        ),
        math_rows=tuple(
            (
                comps[s["component_id"]]["name"],
                f"{signed(Decimal(s['adjustment_contribution']) * 100, 8)} pp",
            )
            for s in steps
        ),
        ending_factor=factor_text,
    )


@dataclass(frozen=True)
class TableView:
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    status: str
    empty_message: str | None
    year_options: tuple[tuple[str, str], ...]
    component_options: tuple[tuple[str, str], ...]
    sort_options: tuple[tuple[str, str], ...]


def filtered_rows(
    packet: ResultPacket, year: str, component: str, sort: str
) -> list[Mapping[str, Any]]:
    rows = list(packet.presentation.get("table_rows") or [])
    if year != "all":
        rows = [r for r in rows if r["period"] == year]
    if component != "all":
        rows = [r for r in rows if r["component_id"] == component]
    rows.sort(key=lambda r: r["display_order"])
    rows.sort(key=lambda r: r["period"], reverse=sort == "desc")
    return rows


def _display_cell(field: str, value: Any) -> str:
    if field == "allocation_weight":
        return f"{percent_of_fraction(value)}%"
    if field == "normalized_percent":
        return f"{fixed(value)}%"
    return "" if value is None else str(value)


def table_view(packet: ResultPacket, year: str, component: str, sort: str) -> TableView:
    rows = filtered_rows(packet, year, component, sort)
    total = len(packet.presentation.get("table_rows") or [])
    return TableView(
        columns=TABLE_FIELDS,
        rows=tuple(
            tuple(_display_cell(f, r.get(f)) for f in TABLE_FIELDS) for r in rows
        ),
        status=(
            f"{len(rows)} of {total} observations · Export includes every filtered "
            "row in the current deterministic sort order. CSV numeric factors retain "
            "canonical precision."
        ),
        empty_message=None if rows else "No observations match these filters.",
        year_options=(
            ("all", "All years"),
            *((p["period"], p["period"]) for p in packet.result["composite_points"]),
        ),
        component_options=(
            ("all", "All components"),
            *((c["component_id"], c["name"]) for c in _components(packet)),
        ),
        sort_options=(("asc", "Period ascending"), ("desc", "Period descending")),
    )


def _csv_cell(value: Any, is_text: bool) -> str:
    text = "" if value is None else str(value)
    if is_text and _FORMULA_PREFIX.match(text):
        text = "'" + text
    if re.search(r'[",\r\n]', text):
        text = '"' + text.replace('"', '""') + '"'
    return text


def csv_export(
    packet: ResultPacket, year: str, component: str, sort: str
) -> tuple[str, str]:
    """Return (filename, UTF-8 CSV text). Raises ValueError for invalid packets."""
    issues = validate_packet(packet)
    if issues:
        raise ValueError(f"CSV blocked: {issues[0]}")
    rows = filtered_rows(packet, year, component, sort)
    lines = [",".join(TABLE_FIELDS)]
    lines += [
        ",".join(_csv_cell(r.get(f), f not in NUMERIC_FIELDS) for f in TABLE_FIELDS)
        for r in rows
    ]
    identity = packet.result["index_identity"]
    base = packet.result["normalization"]["base_year"]
    filename = (
        f"custom-index_{identity['spec_id']}_rev-{identity['spec_revision']}"
        f"_base-{base}_{identity['snapshot_id']}.csv"
    )
    return filename, "\r\n".join(lines) + "\r\n"
