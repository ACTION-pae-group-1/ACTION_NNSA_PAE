"""Index visualization handoff: the versioned contract the results UI reads.

``IndexVisualizationData`` is the authoritative long-form payload described by
``docs/UI Handoff schema/index_visualization_v1.schema.json``; a test pins the
generated JSON Schema to that file. Numeric results travel as plain decimal
strings so no precision is lost in JSON, and every reconciliation the UI
depends on is checked here before a payload can exist.

``IndexVisualizationPresentation`` holds chart- and table-shaped rows derived
from an already validated result. It is an adapter for the bundled web UI,
not part of the authoritative contract.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

DECIMAL_PATTERN = r"^-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?$"
DecimalStr = Annotated[str, StringConstraints(pattern=DECIMAL_PATTERN)]
NonEmptyStr = Annotated[str, StringConstraints(min_length=1)]
ColorHex = Annotated[str, StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}$")]
PeriodKind = Literal["annual_average", "quarter", "month"]

#: Colors the UI reserves for totals and the composite line.
RESERVED_COLORS = frozenset({"#000000", "#101820", "#182b36", "#111111"})


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class IndexIdentity(StrictModel):
    index_id: NonEmptyStr
    name: NonEmptyStr
    spec_id: NonEmptyStr
    spec_revision: int = Field(ge=0)
    snapshot_id: NonEmptyStr
    methodology_version: NonEmptyStr
    frequency: Literal["annual", "quarterly", "monthly"]


class NormalizationBasis(StrictModel):
    base_year: int = Field(ge=1)
    base_factor: DecimalStr = "1.0"
    method: Literal["base_year_annual_average"]


class ComponentDefinition(StrictModel):
    component_id: NonEmptyStr
    display_order: int = Field(ge=0)
    name: NonEmptyStr
    description: str
    series_id: NonEmptyStr
    allocation_weight: DecimalStr
    raw_unit: str | None = None
    raw_reference_basis: str | None = None
    color_hex: ColorHex | None = None


class ComponentPoint(StrictModel):
    period: NonEmptyStr
    year: int = Field(ge=1)
    period_kind: PeriodKind
    component_id: NonEmptyStr
    raw_ppi_value: DecimalStr
    normalized_factor: DecimalStr
    weighted_level: DecimalStr
    observation_id: NonEmptyStr


class CompositePoint(StrictModel):
    period: NonEmptyStr
    year: int = Field(ge=1)
    period_kind: PeriodKind
    composite_factor: DecimalStr


class AdjustmentStep(StrictModel):
    component_id: NonEmptyStr
    display_order: int = Field(ge=0)
    selected_year_normalized_factor: DecimalStr
    index_level_delta: DecimalStr
    adjustment_contribution: DecimalStr
    running_adjustment_factor: DecimalStr


class BaseYearAdjustment(StrictModel):
    source_year: int = Field(ge=1)
    base_year: int = Field(ge=1)
    source_composite_factor: DecimalStr
    adjustment_factor: DecimalStr
    adjustment_percent: DecimalStr
    steps: tuple[AdjustmentStep, ...]


class Finding(StrictModel):
    code: NonEmptyStr
    severity: Literal["info", "warning", "error"]
    message: NonEmptyStr


class IndexVisualizationData(StrictModel):
    """Authoritative, long-form UI handoff; schema_version 1.0.

    Tolerances are validator configuration, intentionally not fields in the
    wire format. Subclasses can override them for a documented methodology.
    """

    weight_tolerance: ClassVar[Decimal] = Decimal("1e-8")
    value_tolerance: ClassVar[Decimal] = Decimal("1e-8")

    schema_version: Literal["1.0"]
    index_identity: IndexIdentity
    normalization: NormalizationBasis
    components: tuple[ComponentDefinition, ...] = Field(min_length=1)
    component_points: tuple[ComponentPoint, ...] = Field(min_length=1)
    composite_points: tuple[CompositePoint, ...] = Field(min_length=1)
    base_year_adjustment: BaseYearAdjustment | None = None
    warnings: tuple[Finding, ...] = ()

    @model_validator(mode="after")
    def _check_invariants(self) -> IndexVisualizationData:
        problems = contract_violations(self)
        if problems:
            raise ValueError(
                "index visualization contract violated: " + "; ".join(problems[:10])
            )
        return self


def contract_violations(data: IndexVisualizationData) -> list[str]:
    """Every broken invariant from section 9 of the app specification.

    A failed invariant is an application error, so construction of an
    ``IndexVisualizationData`` raises on any entry returned here.
    """
    problems: list[str] = []
    weight_tol = data.weight_tolerance
    tol = data.value_tolerance

    def near(a: Decimal, b: Decimal) -> bool:
        return abs(a - b) <= tol

    base_year = data.normalization.base_year
    if not near(Decimal(data.normalization.base_factor), Decimal(1)):
        problems.append("normalization.base_factor must equal 1.0")

    weights: dict[str, Decimal] = {}
    orders: set[int] = set()
    colors: set[str] = set()
    previous_order = -1
    for component in data.components:
        cid = component.component_id
        if cid in weights:
            problems.append(f"duplicate component_id {cid!r}")
        weight = Decimal(component.allocation_weight)
        weights[cid] = weight
        if not Decimal(0) <= weight <= Decimal(1):
            problems.append(f"allocation_weight of {cid!r} is outside 0..1")
        if component.display_order in orders:
            problems.append(f"duplicate display_order {component.display_order}")
        orders.add(component.display_order)
        if component.display_order <= previous_order:
            problems.append(f"component {cid!r} is out of display order")
        previous_order = component.display_order
        if component.color_hex is not None:
            color = component.color_hex.lower()
            if color in colors:
                problems.append(f"component {cid!r} repeats color {color}")
            if color in RESERVED_COLORS:
                problems.append(f"component {cid!r} uses reserved color {color}")
            colors.add(color)
    if abs(sum(weights.values(), Decimal(0)) - Decimal(1)) > weight_tol:
        problems.append("allocation weights must sum to 1.0")

    composites: dict[str, CompositePoint] = {}
    previous_year = 0
    for composite in data.composite_points:
        if composite.period in composites:
            problems.append(f"duplicate composite period {composite.period!r}")
        composites[composite.period] = composite
        if composite.year <= previous_year:
            problems.append(f"composite period {composite.period!r} is out of order")
        previous_year = composite.year
        if Decimal(composite.composite_factor) <= 0:
            problems.append(f"composite factor at {composite.period!r} is not positive")

    points: dict[tuple[str, str], ComponentPoint] = {}
    observation_ids: set[str] = set()
    for point in data.component_points:
        key = (point.component_id, point.period)
        label = f"{point.component_id}/{point.period}"
        if key in points:
            problems.append(f"duplicate component point {label}")
        points[key] = point
        if point.component_id not in weights:
            problems.append(f"point {label} references an unknown component")
            continue
        if point.period not in composites:
            problems.append(f"point {label} has no composite period")
        if point.observation_id in observation_ids:
            problems.append(f"duplicate observation_id {point.observation_id!r}")
        observation_ids.add(point.observation_id)
        raw = Decimal(point.raw_ppi_value)
        normalized = Decimal(point.normalized_factor)
        if raw <= 0 or normalized <= 0:
            problems.append(f"point {label} has a nonpositive value")
        expected = weights[point.component_id] * normalized
        if not near(Decimal(point.weighted_level), expected):
            problems.append(f"weighted_level at {label} is not weight x factor")
        if point.year == base_year and not near(normalized, Decimal(1)):
            problems.append(f"base-year normalized factor at {label} is not 1.0")

    base_period = str(base_year)
    if base_period not in composites:
        problems.append(f"base-year composite {base_period} is missing")
    elif not near(Decimal(composites[base_period].composite_factor), Decimal(1)):
        problems.append("base-year composite factor is not 1.0")

    for period, composite in composites.items():
        total = Decimal(0)
        complete = True
        for cid in weights:
            found = points.get((cid, period))
            if found is None:
                problems.append(f"missing observation {cid}/{period}")
                complete = False
            else:
                total += Decimal(found.weighted_level)
        if complete and not near(total, Decimal(composite.composite_factor)):
            problems.append(f"weighted levels do not sum to composite at {period}")

    for cid in weights:
        base_point = points.get((cid, base_period))
        if base_point is None:
            continue
        base_raw = Decimal(base_point.raw_ppi_value)
        if base_raw <= 0:
            continue
        for (other, period), point in points.items():
            if other == cid and not near(
                Decimal(point.raw_ppi_value) / base_raw,
                Decimal(point.normalized_factor),
            ):
                problems.append(f"raw / base raw is not the factor at {cid}/{period}")

    if data.base_year_adjustment is not None:
        problems += adjustment_violations(data, data.base_year_adjustment)
    return problems


def adjustment_violations(
    data: IndexVisualizationData, adjustment: BaseYearAdjustment
) -> list[str]:
    """Broken reconciliations in one year-to-base adjustment."""
    problems: list[str] = []
    tol = data.value_tolerance
    year = adjustment.source_year
    period = str(year)

    def near(a: Decimal, b: Decimal) -> bool:
        return abs(a - b) <= tol

    if adjustment.base_year != data.normalization.base_year:
        problems.append(f"adjustment {year} has the wrong base year")
    source = Decimal(adjustment.source_composite_factor)
    factor = Decimal(adjustment.adjustment_factor)
    composite = next((c for c in data.composite_points if c.period == period), None)
    if composite is None:
        problems.append(f"adjustment {year} has no composite period")
    elif not near(source, Decimal(composite.composite_factor)):
        problems.append(f"adjustment {year} source composite mismatch")
    if source <= 0:
        problems.append(f"adjustment {year} source composite is not positive")
        return problems
    if not near(factor, Decimal(1) / source):
        problems.append(f"adjustment {year} factor is not 1 / source composite")
    if not near(Decimal(adjustment.adjustment_percent), factor - 1):
        problems.append(f"adjustment {year} percent is not factor - 1")
    if [s.component_id for s in adjustment.steps] != [
        c.component_id for c in data.components
    ]:
        problems.append(f"adjustment {year} steps do not follow component order")
        return problems

    factors = {
        p.component_id: Decimal(p.normalized_factor)
        for p in data.component_points
        if p.period == period
    }
    running = Decimal(1)
    for step, component in zip(adjustment.steps, data.components, strict=True):
        label = f"{step.component_id}/{year}"
        weight = Decimal(component.allocation_weight)
        normalized = Decimal(step.selected_year_normalized_factor)
        delta = Decimal(step.index_level_delta)
        contribution = Decimal(step.adjustment_contribution)
        if step.display_order != component.display_order:
            problems.append(f"adjustment step {label} has the wrong display order")
        if step.component_id in factors and not near(
            normalized, factors[step.component_id]
        ):
            problems.append(f"adjustment step {label} normalized factor mismatch")
        if not near(delta, weight * (1 - normalized)):
            problems.append(f"adjustment step {label} index-level delta mismatch")
        if not near(contribution, delta / source):
            problems.append(f"adjustment step {label} contribution mismatch")
        running += contribution
        if not near(Decimal(step.running_adjustment_factor), running):
            problems.append(f"adjustment step {label} running factor mismatch")
    if not near(running, factor):
        problems.append(f"adjustment {year} steps do not reconcile to the factor")
    return problems


class TableRow(StrictModel):
    """One component-period observation with its repeated audit metadata."""

    period: NonEmptyStr
    component_name: NonEmptyStr
    component_id: NonEmptyStr
    series_id: NonEmptyStr
    display_order: int = Field(ge=0)
    allocation_weight: DecimalStr
    raw_ppi_value: DecimalStr
    normalized_factor: DecimalStr
    normalized_percent: DecimalStr
    weighted_level: DecimalStr
    composite_factor: DecimalStr
    base_year: int = Field(ge=1)
    snapshot_id: NonEmptyStr
    observation_id: NonEmptyStr
    warning_code: str | None = None


class StackLayer(StrictModel):
    """Cumulative bounds of one component's weighted level in one period."""

    period: NonEmptyStr
    component_id: NonEmptyStr
    bottom: DecimalStr
    top: DecimalStr


class IndexVisualizationPresentation(StrictModel):
    """Chart and table shapes derived from a validated result."""

    adjustments_by_year: dict[str, BaseYearAdjustment]
    table_rows: tuple[TableRow, ...]
    stack_layers: tuple[StackLayer, ...]
    latest_change_percent: DecimalStr


class IndexVisualizationPacket(StrictModel):
    """What the bundled web UI loads: the result plus its presentation rows."""

    result: IndexVisualizationData
    presentation: IndexVisualizationPresentation
