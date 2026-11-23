"""Result-contract gate: a result is charted only if this returns no issues.

Ports the core of the HTML prototype's ``validatePayload``. Each issue is
``"CODE: detail"`` using the prototype's codes. Checks not yet ported (stack
boundaries, table-to-canonical field equality, per-step adjustment
arithmetic, display-order and reserved-color rules) are tracked as follow-up.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

from cost_intel_ui.data_access import ResultPacket

TOLERANCE = Decimal("1e-8")
MAX_ISSUES = 60
_DECIMAL_TEXT = re.compile(r"^[-+]?\d+(?:\.\d+)?$")
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
_IDENTITY_FIELDS = ("index_id", "name", "spec_id", "snapshot_id", "methodology_version")


class _Issues:
    def __init__(self) -> None:
        self.items: list[str] = []

    def add(self, code: str, detail: str) -> None:
        if len(self.items) < MAX_ISSUES:
            self.items.append(f"{code}: {detail}")

    def decimal(self, value: Any, path: str) -> Decimal | None:
        if isinstance(value, str) and _DECIMAL_TEXT.match(value):
            try:
                return Decimal(value)
            except InvalidOperation:
                pass
        self.add("NUMERIC_CONTRACT", f"{path} must be a finite decimal string")
        return None


def _near(a: Decimal | None, b: Decimal | None) -> bool:
    return a is not None and b is not None and abs(a - b) <= TOLERANCE


def _list(value: Any) -> list[Mapping[str, Any]]:
    return (
        [v for v in value if isinstance(v, Mapping)] if isinstance(value, list) else []
    )


def validate_packet(packet: ResultPacket | None) -> list[str]:
    issues = _Issues()
    if packet is None or not isinstance(packet.result, Mapping):
        issues.add("MISSING_RESULT", "No calculation result was returned")
        return issues.items
    result, presentation = packet.result, packet.presentation or {}

    if result.get("schema_version") != "1.0":
        issues.add("SCHEMA_VERSION", "Expected schema_version 1.0")
    identity = result.get("index_identity") or {}
    for key in _IDENTITY_FIELDS:
        value = identity.get(key)
        if not isinstance(value, str) or not value.strip():
            issues.add("IDENTITY", f"{key} is required")
    revision = identity.get("spec_revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
        issues.add("SPEC_REVISION", "Revision must be a nonnegative integer")
    if identity.get("frequency") != "annual":
        issues.add(
            "FREQUENCY",
            f"Annual results required; received {identity.get('frequency')}",
        )

    norm = result.get("normalization") or {}
    if norm.get("method") != "base_year_annual_average":
        issues.add("NORMALIZATION", "Expected base_year_annual_average method")
    base_year = norm.get("base_year")
    if not isinstance(base_year, int):
        issues.add("BASE_YEAR", "Missing or invalid base_year")
    base_factor = issues.decimal(norm.get("base_factor"), "normalization.base_factor")
    if base_factor is not None and not _near(base_factor, Decimal(1)):
        issues.add("BASE_FACTOR", "The base-year factor must equal 1.0")

    components = _list(result.get("components"))
    points = _list(result.get("component_points"))
    composite = _list(result.get("composite_points"))
    if not components:
        issues.add("NO_COMPONENTS", "At least one component must be returned")
    if not points:
        issues.add("NO_COMPONENT_POINTS", "No source observations were returned")
    if not composite:
        issues.add("NO_COMPOSITE", "No composite periods were returned")

    weights: dict[str, Decimal] = {}
    total = Decimal(0)
    for i, comp in enumerate(components):
        cid = comp.get("component_id")
        if not isinstance(cid, str) or not cid:
            issues.add("COMPONENT_ID", f"Missing ID at position {i}")
            continue
        if cid in weights:
            issues.add("DUPLICATE_COMPONENT", f"Component {cid} repeated")
        if not all(comp.get(k) for k in ("name", "description", "series_id")):
            issues.add(
                "COMPONENT_METADATA", f"{cid} needs name, description, series_id"
            )
        color = comp.get("color_hex")
        if not isinstance(color, str) or not _HEX.match(color):
            issues.add("INVALID_COLOR", f"{cid} has invalid hex color {color}")
        weight = issues.decimal(comp.get("allocation_weight"), f"{cid}.allocation")
        if weight is not None:
            if not Decimal(0) <= weight <= Decimal(1):
                issues.add("WEIGHT_RANGE", f"{cid} allocation must be between 0 and 1")
            weights[cid] = weight
            total += weight
    if components and not _near(total, Decimal(1)):
        issues.add("WEIGHT_TOTAL", f"Component weights must sum to 1.0; got {total}")

    composite_by_period: dict[str, Decimal] = {}
    previous_year: int | None = None
    for p in composite:
        period, year = p.get("period"), p.get("year")
        if not isinstance(year, int) or str(year) != period:
            issues.add("COMPOSITE_PERIOD", f"Invalid annual period {period}")
            continue
        if previous_year is not None and year <= previous_year:
            issues.add("COMPOSITE_SORT", f"Periods must increase at {period}")
        previous_year = year
        value = issues.decimal(p.get("composite_factor"), f"composite {period}")
        if value is not None:
            composite_by_period[period] = value
    if isinstance(base_year, int) and composite:
        base_value = composite_by_period.get(str(base_year))
        if base_value is None:
            issues.add("MISSING_BASE_COMPOSITE", f"Base-year {base_year} is missing")
        elif not _near(base_value, Decimal(1)):
            issues.add("BASE_COMPOSITE", f"Composite at {base_year} must equal 1.0")

    level_sums: dict[str, Decimal] = {}
    seen: set[tuple[str, str]] = set()
    for p in points:
        cid, period = p.get("component_id"), p.get("period")
        key = f"{cid}/{period}"
        seen.add((str(cid), str(period)))
        normalized = issues.decimal(p.get("normalized_factor"), f"{key} normalized")
        level = issues.decimal(p.get("weighted_level"), f"{key} weighted")
        issues.decimal(p.get("raw_ppi_value"), f"{key} raw")
        weight = weights.get(str(cid))
        if weight is None:
            issues.add("UNKNOWN_COMPONENT", f"Observation {key} has no component")
        elif normalized is not None and level is not None:
            if not _near(level, weight * normalized):
                issues.add("WEIGHTED_LEVEL", f"Expected weight x factor at {key}")
        if level is not None:
            level_sums[str(period)] = level_sums.get(str(period), Decimal(0)) + level
    for period, value in composite_by_period.items():
        for cid in weights:
            if (cid, period) not in seen:
                issues.add("MISSING_OBSERVATION", f"Missing {cid}/{period}")
        if period in level_sums and not _near(level_sums[period], value):
            issues.add("COMPOSITE_RECONCILIATION", f"Level sum differs at {period}")

    latest = (
        composite_by_period.get(str(composite[-1].get("period"))) if composite else None
    )
    if latest is not None:
        change = issues.decimal(
            presentation.get("latest_change_percent"), "latest_change_percent"
        )
        if change is not None and not _near(change, (latest - 1) * 100):
            issues.add("SUMMARY_CHANGE", "Latest change does not match composite")

    if not _list(presentation.get("table_rows")):
        issues.add("MISSING_TABLE", "No authoritative long-form table rows")
    adjustments = presentation.get("adjustments_by_year")
    if not isinstance(adjustments, Mapping) or not adjustments:
        issues.add("MISSING_ADJUSTMENTS", "Annual adjustment results not supplied")
    else:
        for year, record in adjustments.items():
            source = composite_by_period.get(str(year))
            factor = issues.decimal(
                (record or {}).get("adjustment_factor"), f"adjustment {year}"
            )
            if source is None:
                issues.add("ADJUSTMENT_PERIOD", f"No composite record for {year}")
            elif factor is not None and not _near(factor * source, Decimal(1)):
                issues.add("ADJUSTMENT_RECIPROCAL", f"Factor must be 1/C at {year}")
    return issues.items
