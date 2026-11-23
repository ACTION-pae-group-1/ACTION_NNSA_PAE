"""Build the index visualization handoff from a saved spec and the snapshot.

The annual history of a fixed-weight basket, normalized to the base year's
annual average. For component *i* with weight ``w_i`` (weights sum to 1) and
annual index level ``I_i(y)``::

    normalized_i(y) = I_i(y) / I_i(base)
    weighted_i(y)   = w_i * normalized_i(y)
    composite(y)    = sum_i weighted_i(y)

The year-to-base adjustment for a source year ``y`` converts an amount stated
in year-``y`` terms into base-year terms::

    factor(y)        = 1 / composite(y)
    delta_i(y)       = w_i * (1 - normalized_i(y))
    contribution_i   = delta_i(y) / composite(y)
    factor(y) - 1    = sum_i contribution_i

All arithmetic is ``Decimal``; published values are rounded once to
``DECIMAL_PLACES`` and every total is the sum of the rounded parts it is
displayed with, so the payload reconciles exactly rather than approximately.

Only complete periods are emitted. A year in which any component lacks an
observation is left out and reported as a warning; a missing value is never
treated as zero or interpolated. A series that publishes quarters only (ECI)
resolves a year from its ``Q04`` observation, disclosed as a warning, the
same alignment ``calculate_index_from_bls`` applies.
"""

from __future__ import annotations

import colorsys
from collections.abc import Mapping
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation, localcontext

from pydantic import ValidationError

from bls_mcp.exceptions import (
    CalculationError,
    InvalidPeriodError,
    ObservationNotFoundError,
    SeriesNotFoundError,
)
from bls_mcp.models.basket import EscalationComponent
from bls_mcp.models.enums import Periodicity, ValidationSeverity
from bls_mcp.models.specifications import EscalationIndexSpec
from bls_mcp.models.visualization import (
    RESERVED_COLORS,
    AdjustmentStep,
    BaseYearAdjustment,
    ComponentDefinition,
    ComponentPoint,
    CompositePoint,
    Finding,
    IndexIdentity,
    IndexVisualizationData,
    IndexVisualizationPacket,
    IndexVisualizationPresentation,
    NormalizationBasis,
    StackLayer,
    TableRow,
    adjustment_violations,
)
from bls_mcp.services.source_calculation import (
    ANNUAL_BLS_CODE,
    QUARTERLY_ANNUAL_ANCHOR,
    _is_indexed,
)
from bls_mcp.services.validation import ValidationService
from bls_mcp.storage.query_models import QueryStatus, SeriesSearchFilters
from bls_mcp.storage.store import BLSStore

METHODOLOGY_VERSION = "composite-index/1.0"
DECIMAL_PLACES = 12
MAX_WINDOW_YEARS = 100
#: Weight totals this close to 1 are rounding noise, absorbed without comment.
SILENT_WEIGHT_RESIDUAL = Decimal("1e-9")

_QUANTUM = Decimal(1).scaleb(-DECIMAL_PLACES)
_PALETTE = (
    "#E6A34B",
    "#B27AE1",
    "#4F83E6",
    "#18A88B",
    "#D9627A",
    "#7FB24A",
    "#3FA7C9",
    "#C7803A",
    "#8C8FE0",
    "#D4B13F",
    "#5FB3A1",
    "#C56BB5",
)

WeightOverrides = Mapping[str, float | int | str | Decimal]


def _q(value: Decimal) -> Decimal:
    return value.quantize(_QUANTUM, rounding=ROUND_HALF_EVEN)


def _text(value: Decimal) -> str:
    """Fixed-point text; the UI's decimal check rejects exponent notation."""
    return format(value, "f")


def component_colors(count: int) -> list[str]:
    """Distinct, deterministic colors; none collides with a reserved total."""
    colors = list(_PALETTE[:count])
    step = 0
    while len(colors) < count:
        hue = (step * 0.618033988749895) % 1.0
        red, green, blue = colorsys.hls_to_rgb(hue, 0.58, 0.55)
        color = (
            f"#{round(red * 255):02X}{round(green * 255):02X}{round(blue * 255):02X}"
        )
        if color not in colors and color.lower() not in RESERVED_COLORS:
            colors.append(color)
        step += 1
    return colors


class IndexVisualizationService:
    """Assemble and validate ``IndexVisualizationData`` for one specification."""

    def __init__(self, store: BLSStore, validation: ValidationService) -> None:
        self.store = store
        self.validation = validation

    def build(
        self,
        spec: EscalationIndexSpec,
        *,
        start_year: int | None = None,
        end_year: int | None = None,
        source_year: int | None = None,
        weights: WeightOverrides | None = None,
    ) -> IndexVisualizationPacket:
        """Return the validated result and its presentation rows.

        ``start_year``/``end_year`` default to the span between the spec's
        base and target years and must include the base year. ``source_year``
        selects the top-level adjustment and defaults to the target year.
        ``weights`` replaces component weights by id for a what-if view; the
        saved specification is not modified.

        Raises:
            CalculationError: the spec fails validation, has a weighted
                component without a BLS series, or a value is not positive.
            InvalidPeriodError: the year window or source year is unusable.
            SeriesNotFoundError: a component series is absent from the snapshot.
            ObservationNotFoundError: a base-year observation is absent.
        """
        with localcontext() as context:
            context.prec = 34
            try:
                result, adjustments = self._result(
                    spec, start_year, end_year, source_year, weights
                )
            except ValidationError as exc:
                raise CalculationError(
                    f"Index visualization failed its contract: {exc.errors()[0]['msg']}"
                ) from exc
            broken = [
                problem
                for adjustment in adjustments.values()
                for problem in adjustment_violations(result, adjustment)
            ]
            if broken:
                raise CalculationError(
                    f"Index visualization failed its contract: {broken[0]}"
                )
            return IndexVisualizationPacket(
                result=result,
                presentation=_presentation(result, adjustments),
            )

    def _result(
        self,
        spec: EscalationIndexSpec,
        start_year: int | None,
        end_year: int | None,
        source_year: int | None,
        overrides: WeightOverrides | None,
    ) -> tuple[IndexVisualizationData, dict[str, BaseYearAdjustment]]:
        warnings: list[Finding] = []
        spec = _with_weights(spec, overrides)
        findings = self.validation.validate_spec(spec).findings
        errors = [f.message for f in findings if f.severity == ValidationSeverity.ERROR]
        if errors:
            raise CalculationError(
                f"Specification validation failed: {'; '.join(errors)}"
            )

        components = [c for c in spec.components if c.weight > 0]
        dropped = [c.id for c in spec.components if c.weight <= 0]
        if dropped:
            warnings.append(
                Finding(
                    code="ZERO_WEIGHT_COMPONENT_OMITTED",
                    severity="info",
                    message="Components with zero weight are not shown: "
                    + ", ".join(dropped)
                    + ".",
                )
            )
        unsourced = [c.id for c in components if not (_is_indexed(c) and c.series_id)]
        if unsourced:
            raise CalculationError(
                "The index visualization covers series-backed components only; "
                "these weighted components have no BLS series to chart: "
                + ", ".join(unsourced)
                + "."
            )
        if any(c.locality_adjustment_enabled for c in components):
            warnings.append(
                Finding(
                    code="LOCALITY_NOT_APPLIED",
                    severity="info",
                    message="Locality adjustments are not part of this view; "
                    "the factors are temporal only.",
                )
            )

        base_year = spec.base_period.year
        if spec.base_period.periodicity not in {
            Periodicity.ANNUAL,
            Periodicity.ANNUAL_AVERAGE,
        }:
            warnings.append(
                Finding(
                    code="ANNUAL_BASE_USED",
                    severity="info",
                    message=f"The specification's base period is {spec.base_period}; "
                    f"this annual view normalizes to the {base_year} annual average.",
                )
            )
        first, last = _window(spec, start_year, end_year)

        series_ids = list(dict.fromkeys(str(c.series_id) for c in components))
        snapshot_id, values, aligned = self._annual_values(series_ids, first, last)
        for series_id, aligned_years in sorted(aligned.items()):
            warnings.append(
                Finding(
                    code="QUARTERLY_TO_ANNUAL_ALIGNMENT",
                    severity="warning",
                    message=f"Series {series_id} publishes no annual average; "
                    f"years {_year_list(aligned_years)} use the "
                    f"{QUARTERLY_ANNUAL_ANCHOR} observation.",
                )
            )

        base_values: dict[str, Decimal] = {}
        for component in components:
            sid = str(component.series_id)
            base = values[sid].get(base_year)
            if base is None:
                raise ObservationNotFoundError(
                    f"No annual observation for series '{sid}' in base year "
                    f"{base_year}."
                )
            base_values[component.id] = base

        years: list[int] = []
        for year in range(first, last + 1):
            missing = sorted(
                {
                    str(c.series_id)
                    for c in components
                    if year not in values[str(c.series_id)]
                }
            )
            if missing:
                warnings.append(
                    Finding(
                        code="INCOMPLETE_PERIOD_OMITTED",
                        severity="warning",
                        message=f"{year} is omitted: no annual observation for "
                        + ", ".join(missing)
                        + ". Missing values are never estimated.",
                    )
                )
            else:
                years.append(year)

        weight_by_id = _allocation_weights(components, warnings)
        definitions = self._definitions(components, weight_by_id)

        points: list[ComponentPoint] = []
        composites: list[CompositePoint] = []
        factors: dict[int, dict[str, Decimal]] = {}
        composite_by_year: dict[int, Decimal] = {}
        for year in years:
            total = Decimal(0)
            factors[year] = {}
            for component in components:
                sid = str(component.series_id)
                raw = values[sid][year]
                normalized = _q(raw / base_values[component.id])
                weighted = _q(weight_by_id[component.id] * normalized)
                total += weighted
                factors[year][component.id] = normalized
                code = (
                    QUARTERLY_ANNUAL_ANCHOR
                    if year in aligned.get(sid, ())
                    else (ANNUAL_BLS_CODE)
                )
                points.append(
                    ComponentPoint(
                        period=str(year),
                        year=year,
                        period_kind="annual_average",
                        component_id=component.id,
                        raw_ppi_value=_text(raw),
                        normalized_factor=_text(normalized),
                        weighted_level=_text(weighted),
                        observation_id=f"obs:{component.id}:{sid}:{year}-{code}",
                    )
                )
            composite_by_year[year] = total
            composites.append(
                CompositePoint(
                    period=str(year),
                    year=year,
                    period_kind="annual_average",
                    composite_factor=_text(total),
                )
            )

        adjustments = {
            str(year): _adjustment(
                year,
                base_year,
                composite_by_year[year],
                definitions,
                weight_by_id,
                factors[year],
            )
            for year in years
        }
        chosen = spec.target_period.year if source_year is None else source_year
        top_level = adjustments.get(str(chosen))
        if top_level is None and source_year is not None:
            raise InvalidPeriodError(
                f"No complete annual result for source year {source_year}; "
                f"available years are {_year_list(years)}."
            )

        result = IndexVisualizationData(
            schema_version="1.0",
            index_identity=IndexIdentity(
                index_id=spec.id,
                name=spec.name,
                spec_id=spec.id,
                spec_revision=spec.revision,
                snapshot_id=snapshot_id,
                methodology_version=METHODOLOGY_VERSION,
                frequency="annual",
            ),
            normalization=NormalizationBasis(
                base_year=base_year, method="base_year_annual_average"
            ),
            components=tuple(definitions),
            component_points=tuple(points),
            composite_points=tuple(composites),
            base_year_adjustment=top_level,
            warnings=tuple(warnings),
        )
        return result, adjustments

    def _annual_values(
        self, series_ids: list[str], first: int, last: int
    ) -> tuple[str, dict[str, dict[int, Decimal]], dict[str, list[int]]]:
        """Return (snapshot_id, {series: {year: value}}, {series: aligned years})."""
        page = self.store.get_observations(series_ids, start_year=first, end_year=last)
        unknown = [
            outcome.series_id
            for outcome in page.statuses
            if outcome.status == QueryStatus.UNKNOWN_SERIES
        ]
        if unknown:
            raise SeriesNotFoundError(
                f"Series not found in the BLS snapshot: {', '.join(unknown)}."
            )
        by_code: dict[tuple[str, int], dict[str, float]] = {}
        for record in page.observations:
            codes = by_code.setdefault((record.series_id, record.year), {})
            if codes.setdefault(record.period, record.value) != record.value:
                raise CalculationError(
                    f"Snapshot has conflicting values for series "
                    f"'{record.series_id}' at {record.year}/{record.period}."
                )
        values: dict[str, dict[int, Decimal]] = {sid: {} for sid in series_ids}
        aligned: dict[str, list[int]] = {}
        for (series_id, year), codes in sorted(by_code.items()):
            if ANNUAL_BLS_CODE in codes:
                value = codes[ANNUAL_BLS_CODE]
            elif QUARTERLY_ANNUAL_ANCHOR in codes:
                value = codes[QUARTERLY_ANNUAL_ANCHOR]
                aligned.setdefault(series_id, []).append(year)
            else:
                continue
            decimal_value = Decimal(str(value))
            if not decimal_value.is_finite() or decimal_value <= 0:
                raise CalculationError(
                    f"Observation for series '{series_id}' in {year} is not a "
                    f"positive index level ({value})."
                )
            values[series_id][year] = decimal_value
        return page.snapshot_id, values, aligned

    def _definitions(
        self,
        components: list[EscalationComponent],
        weight_by_id: dict[str, Decimal],
    ) -> list[ComponentDefinition]:
        colors = component_colors(len(components))
        definitions = []
        for order, component in enumerate(components):
            sid = str(component.series_id)
            page = self.store.search_series(
                SeriesSearchFilters(query=sid, active_only=False, limit=10)
            )
            record = next(
                (hit.series for hit in page.matches if hit.series.series_id == sid),
                None,
            )
            title = record.title if record is not None else None
            reference = record.original_reference_base if record is not None else None
            definitions.append(
                ComponentDefinition(
                    component_id=component.id,
                    display_order=order,
                    name=component.name,
                    description=component.description
                    or component.official_series_title
                    or title
                    or component.name,
                    series_id=sid,
                    allocation_weight=_text(weight_by_id[component.id]),
                    raw_unit=(record.units if record is not None else None) or "index",
                    raw_reference_basis=(
                        f"BLS published basis (reference base {reference})"
                        if reference
                        else "BLS published basis"
                    ),
                    color_hex=colors[order],
                )
            )
        return definitions


def _with_weights(
    spec: EscalationIndexSpec, overrides: WeightOverrides | None
) -> EscalationIndexSpec:
    """A copy of *spec* with component weights replaced by id."""
    if not overrides:
        return spec
    known = {component.id for component in spec.components}
    unknown = sorted(set(overrides) - known)
    if unknown:
        raise CalculationError(
            f"Weights name components that are not in the specification: "
            f"{', '.join(unknown)}."
        )
    updated = []
    for component in spec.components:
        if component.id not in overrides:
            updated.append(component)
            continue
        try:
            weight = Decimal(str(overrides[component.id]))
        except InvalidOperation as exc:
            raise CalculationError(
                f"Weight for component '{component.id}' is not a number."
            ) from exc
        if not weight.is_finite():
            raise CalculationError(
                f"Weight for component '{component.id}' is not a finite number."
            )
        updated.append(component.model_copy(update={"weight": float(weight)}))
    return spec.model_copy(update={"components": updated})


def _window(
    spec: EscalationIndexSpec, start_year: int | None, end_year: int | None
) -> tuple[int, int]:
    base_year = spec.base_period.year
    target_year = spec.target_period.year
    first = min(base_year, target_year) if start_year is None else start_year
    last = max(base_year, target_year) if end_year is None else end_year
    if first <= 0 or last < first:
        raise InvalidPeriodError(
            "Years must be positive and end_year must be >= start_year."
        )
    if not first <= base_year <= last:
        raise InvalidPeriodError(
            f"The year window {first}-{last} must include the base year {base_year}."
        )
    if last - first + 1 > MAX_WINDOW_YEARS:
        raise InvalidPeriodError(
            f"At most {MAX_WINDOW_YEARS} years can be charted in one request."
        )
    return first, last


def _allocation_weights(
    components: list[EscalationComponent], warnings: list[Finding]
) -> dict[str, Decimal]:
    """Published weights that sum to exactly 1.

    Spec weights are validated to total 1 within the service tolerance, not
    exactly. Any residual is removed by rescaling, and the last rounding unit
    goes to the largest component so the published weights reconcile.
    """
    raw = {c.id: Decimal(str(c.weight)) for c in components}
    total = sum(raw.values(), Decimal(0))
    if abs(total - 1) > SILENT_WEIGHT_RESIDUAL:
        warnings.append(
            Finding(
                code="WEIGHTS_RENORMALIZED",
                severity="warning",
                message=f"Weights of the charted components total {_text(_q(total))}; "
                "they were rescaled to sum to 1.",
            )
        )
    weights = {cid: _q(value / total) for cid, value in raw.items()}
    largest = max(weights, key=lambda cid: weights[cid])
    weights[largest] += Decimal(1) - sum(weights.values(), Decimal(0))
    return weights


def _adjustment(
    year: int,
    base_year: int,
    composite: Decimal,
    definitions: list[ComponentDefinition],
    weight_by_id: dict[str, Decimal],
    factors: dict[str, Decimal],
) -> BaseYearAdjustment:
    running = Decimal(1)
    steps = []
    for definition in definitions:
        cid = definition.component_id
        delta = _q(weight_by_id[cid] * (1 - factors[cid]))
        contribution = _q(delta / composite)
        running += contribution
        steps.append(
            AdjustmentStep(
                component_id=cid,
                display_order=definition.display_order,
                selected_year_normalized_factor=_text(factors[cid]),
                index_level_delta=_text(delta),
                adjustment_contribution=_text(contribution),
                running_adjustment_factor=_text(running),
            )
        )
    factor = _q(1 / composite)
    return BaseYearAdjustment(
        source_year=year,
        base_year=base_year,
        source_composite_factor=_text(composite),
        adjustment_factor=_text(factor),
        adjustment_percent=_text(factor - 1),
        steps=tuple(steps),
    )


def _presentation(
    result: IndexVisualizationData, adjustments: dict[str, BaseYearAdjustment]
) -> IndexVisualizationPresentation:
    """Reshape a validated result; only display scaling (x100) happens here."""
    composite_by_period = {
        c.period: c.composite_factor for c in result.composite_points
    }
    point_by_key = {(p.component_id, p.period): p for p in result.component_points}
    warning_code = result.warnings[0].code if result.warnings else None
    rows: list[TableRow] = []
    layers: list[StackLayer] = []
    for composite in result.composite_points:
        bottom = Decimal(0)
        for component in result.components:
            point = point_by_key[(component.component_id, composite.period)]
            top = bottom + Decimal(point.weighted_level)
            layers.append(
                StackLayer(
                    period=composite.period,
                    component_id=component.component_id,
                    bottom=_text(bottom),
                    top=_text(top),
                )
            )
            bottom = top
            rows.append(
                TableRow(
                    period=composite.period,
                    component_name=component.name,
                    component_id=component.component_id,
                    series_id=component.series_id,
                    display_order=component.display_order,
                    allocation_weight=component.allocation_weight,
                    raw_ppi_value=point.raw_ppi_value,
                    normalized_factor=point.normalized_factor,
                    normalized_percent=_text(Decimal(point.normalized_factor) * 100),
                    weighted_level=point.weighted_level,
                    composite_factor=composite_by_period[composite.period],
                    base_year=result.normalization.base_year,
                    snapshot_id=result.index_identity.snapshot_id,
                    observation_id=point.observation_id,
                    warning_code=warning_code,
                )
            )
    latest = Decimal(result.composite_points[-1].composite_factor)
    return IndexVisualizationPresentation(
        adjustments_by_year=adjustments,
        table_rows=tuple(rows),
        stack_layers=tuple(layers),
        latest_change_percent=_text((latest - 1) * 100),
    )


def _year_list(years: list[int]) -> str:
    return ", ".join(str(year) for year in years) if years else "none"
