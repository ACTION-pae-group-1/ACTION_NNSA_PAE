"""Source-backed calculation: resolves observations from the DuckDB snapshot.

This service closes the loop between saved specs and the BLS data store.
The LLM never needs to supply raw index values; provenance is fully captured
in the returned CalculationLedger.

The arithmetic is a fixed-weight composite of price relatives. For component
*i* with weight ``w_i`` (weights sum to 1) and index level ``I_i(t)``::

    relative_i = I_i(target) / I_i(base)      (1 for fixed/unindexed parts)
    composite  = sum_i  w_i * relative_i
    percent    = (composite - 1) * 100

Only the two index levels per series come from the snapshot; the weights and
periods come from the saved specification.

**Quarterly-to-annual alignment.** A specification states annual periods, but
some programs (ECI) publish quarterly observations only. When a series has no
annual-average row for the requested year, the service resolves it from its
own ``Q04`` observation — one exact published value, never an average the BLS
did not publish — and discloses the substitution in the component result, the
ledger warnings and the provenance notes. The same holds for monthly spec
periods: a quarterly-only series resolves from the published quarter that
contains the requested month (the quarter's value repeats across its three
months), disclosed identically. Only these two fallbacks exist; a quarterly
spec period must match a published quarter exactly.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from bls_mcp.exceptions import (
    CalculationError,
    ObservationNotFoundError,
    SeriesNotFoundError,
)
from bls_mcp.models.basket import EscalationComponent
from bls_mcp.models.calculations import (
    ComponentCalculation,
    EscalationCalculationResult,
)
from bls_mcp.models.enums import ComponentType, Periodicity, ValidationSeverity
from bls_mcp.models.periods import EconomicPeriod
from bls_mcp.models.provenance import CalculationLedger, SourceProvenance
from bls_mcp.models.specifications import EscalationIndexSpec
from bls_mcp.services.calculations import EscalationCalculationService
from bls_mcp.services.validation import ValidationService
from bls_mcp.storage.query_models import QueryStatus
from bls_mcp.storage.store import BLSStore

#: BLS period code every annual spec period resolves to (the M13 annual
#: average row, the full-year index value published in BLS data files).
ANNUAL_BLS_CODE = "M13"
#: Quarterly observation that stands in for a missing annual average when a
#: series publishes quarters only (ECI-like). The year-end quarter keeps the
#: resolution to one exact published observation.
QUARTERLY_ANNUAL_ANCHOR = "Q04"


def _quarterly_fallback(requested: str) -> str | None:
    """The quarterly code that can stand in for *requested* when absent.

    Annual periods fall back to the year-end quarter (``Q04``); a monthly
    period falls back to the published quarter containing that month (its
    value repeats across the quarter's three months). Quarterly requests
    must match exactly, so they get no fallback.
    """
    if requested == ANNUAL_BLS_CODE:
        return QUARTERLY_ANNUAL_ANCHOR
    if len(requested) == 3 and requested.startswith("M") and requested[1:].isdigit():
        month = int(requested[1:])
        return f"Q{(month + 2) // 3:02d}"
    return None


def _period_to_bls(period: EconomicPeriod) -> tuple[int, str]:
    """Map an EconomicPeriod to (year, BLS period code).

    Inverse of ``observations._period_from_bls``. EconomicPeriod already
    guarantees that monthly/quarterly periods carry their month/quarter.
    """
    if period.periodicity == Periodicity.MONTHLY:
        return (period.year, f"M{period.month:02d}")
    if period.periodicity == Periodicity.QUARTERLY:
        return (period.year, f"Q{period.quarter:02d}")
    # ANNUAL and ANNUAL_AVERAGE both resolve to the M13 annual-average row.
    return (period.year, ANNUAL_BLS_CODE)


def _aligned_period(year: int, code: str) -> EconomicPeriod:
    """The EconomicPeriod an alignment code actually resolved to."""
    return EconomicPeriod.from_storage(f"{year}-{code}")


def _alignment_kind(requested: str) -> str:
    """The provenance-note key for the alignment rule *requested* used."""
    if requested == ANNUAL_BLS_CODE:
        return "quarterly_to_annual_alignment"
    return "monthly_to_quarterly_alignment"


def _is_indexed(component: EscalationComponent) -> bool:
    """True when the component's factor must come from snapshot observations."""
    return (
        component.component_type != ComponentType.FIXED_UNINDEXED
        and component.temporal_adjustment_enabled
    )


class SourceBackedCalculationService:
    """Calculate composite escalation fully sourced from the DuckDB snapshot.

    Resolves base and target observations for every component, delegates
    arithmetic to EscalationCalculationService, and returns both the result
    and a CalculationLedger recording which series/periods/values were used.
    """

    def __init__(
        self,
        store: BLSStore,
        calculations: EscalationCalculationService,
        validation: ValidationService,
    ) -> None:
        self.store = store
        self.calculations = calculations
        self.validation = validation

    def _values_at(
        self, series_ids: list[str], year: int, bls_period: str
    ) -> tuple[str, dict[str, float], dict[str, str]]:
        """Return (snapshot_id, {series_id: value}, aligned) for one year/period.

        ``aligned`` maps a series to the BLS period code its value actually
        came from when the requested annual average was absent and the series
        publishes quarters only (see ``_quarterly_fallback``).

        Raises:
            SeriesNotFoundError: a series is absent from the snapshot catalog.
            CalculationError: the snapshot holds conflicting values for one
                series at any observation period in the requested year. The
                repo's loaders reject such conflicts at build time, so only a
                hand-built snapshot can expose this.
        """
        page = self.store.get_observations(series_ids, start_year=year, end_year=year)
        unknown = [
            outcome.series_id
            for outcome in page.statuses
            if outcome.status == QueryStatus.UNKNOWN_SERIES
        ]
        if unknown:
            raise SeriesNotFoundError(
                f"Series not found in the BLS snapshot: {', '.join(unknown)}."
            )
        per_series: dict[str, dict[str, float]] = {}
        for rec in page.observations:
            periods = per_series.setdefault(rec.series_id, {})
            if periods.setdefault(rec.period, rec.value) != rec.value:
                raise CalculationError(
                    f"Snapshot has conflicting values for series "
                    f"'{rec.series_id}' at {year}/{rec.period}."
                )
        values: dict[str, float] = {}
        aligned: dict[str, str] = {}
        fallback = _quarterly_fallback(bls_period)
        for series_id, periods in per_series.items():
            if bls_period in periods:
                values[series_id] = periods[bls_period]
            elif fallback is not None and fallback in periods:
                values[series_id] = periods[fallback]
                aligned[series_id] = fallback
        return page.snapshot_id, values, aligned

    def calculate(
        self, spec: EscalationIndexSpec
    ) -> tuple[EscalationCalculationResult, CalculationLedger]:
        """Resolve observations and calculate composite for *spec*.

        Raises:
            CalculationError: spec has ERROR-level validation findings, or a
                base value is zero.
            SeriesNotFoundError: a component series is absent from the
                snapshot catalog.
            ObservationNotFoundError: a required base or target observation is
                absent from the snapshot.
        """
        validation = self.validation.validate_spec(spec)
        errors = [
            finding.message
            for finding in validation.findings
            if finding.severity == ValidationSeverity.ERROR
        ]
        if errors:
            raise CalculationError(
                f"Specification validation failed: {'; '.join(errors)}"
            )

        base_year, base_bls = _period_to_bls(spec.base_period)
        target_year, target_bls = _period_to_bls(spec.target_period)

        # Validation guarantees every indexed component has a series_id;
        # dict.fromkeys de-duplicates while keeping component order.
        indexed_series = list(
            dict.fromkeys(
                c.series_id for c in spec.components if _is_indexed(c) and c.series_id
            )
        )

        snapshot_id = ""
        base_obs: dict[str, float] = {}
        target_obs: dict[str, float] = {}
        base_aligned: dict[str, str] = {}
        target_aligned: dict[str, str] = {}
        if indexed_series:
            (
                snapshot_id,
                base_obs,
                base_aligned,
            ) = self._values_at(indexed_series, base_year, base_bls)
            _, target_obs, target_aligned = self._values_at(
                indexed_series, target_year, target_bls
            )

        component_calcs: list[ComponentCalculation] = []
        provenance: list[SourceProvenance] = []
        observations_used: list[str] = []
        retrieved_at = datetime.now(UTC)
        periods = {
            "base_period": spec.base_period,
            "target_period": spec.target_period,
        }

        for comp in spec.components:
            if not _is_indexed(comp):
                # Factor is 1 by definition; no observation enters the result.
                fixed = self.calculations.calculate_component(comp, 1, 1)
                component_calcs.append(
                    fixed.model_copy(
                        update={**periods, "base_value": None, "target_value": None}
                    )
                )
                continue

            sid = comp.series_id
            if sid not in base_obs:
                raise ObservationNotFoundError(
                    f"No base observation found for series '{sid}' "
                    f"at {spec.base_period} (BLS {base_year}/{base_bls})."
                )
            if sid not in target_obs:
                raise ObservationNotFoundError(
                    f"No target observation found for series '{sid}' "
                    f"at {spec.target_period} (BLS {target_year}/{target_bls})."
                )
            base_val = base_obs[sid]
            target_val = target_obs[sid]

            # An aligned series reports the periods its values actually came
            # from (e.g. Q04 for an ECI series under an annual spec, or the
            # containing quarter under a monthly spec).
            aligned = sid in base_aligned or sid in target_aligned
            component_periods = periods
            base_label = str(spec.base_period)
            target_label = str(spec.target_period)
            align_notes: dict[str, list[str]] = {}
            if aligned:
                component_periods = {
                    "base_period": _aligned_period(base_year, base_aligned[sid])
                    if sid in base_aligned
                    else spec.base_period,
                    "target_period": _aligned_period(target_year, target_aligned[sid])
                    if sid in target_aligned
                    else spec.target_period,
                }
                base_label = (
                    f"{base_year}-{base_aligned[sid]}"
                    if sid in base_aligned
                    else base_label
                )
                target_label = (
                    f"{target_year}-{target_aligned[sid]}"
                    if sid in target_aligned
                    else target_label
                )
                pairing: list[tuple[int, str, str]] = []
                if sid in base_aligned:
                    pairing.append(
                        (base_year, base_aligned[sid], _alignment_kind(base_bls))
                    )
                if sid in target_aligned:
                    pairing.append(
                        (target_year, target_aligned[sid], _alignment_kind(target_bls))
                    )
                for year, code, kind in pairing:
                    align_notes.setdefault(kind, []).append(f"{year}:{code}")
            if base_val == 0:
                raise CalculationError(
                    f"Base observation for series '{sid}' is zero at {base_label}."
                )

            indexed = self.calculations.calculate_component(comp, base_val, target_val)
            component_calcs.append(indexed.model_copy(update=component_periods))
            observations_used += [
                f"{sid}@{base_label} = {base_val}",
                f"{sid}@{target_label} = {target_val}",
            ]
            notes = f"snapshot_id={snapshot_id}"
            for kind, codes in align_notes.items():
                notes += f"; {kind}=" + ",".join(codes)
            provenance.append(
                SourceProvenance(
                    source_name="bls_snapshot",
                    series_id=sid,
                    retrieved_at=retrieved_at,
                    notes=notes,
                )
            )

        alignment_warnings: list[str] = []
        for year, requested, aligned_map, spec_period in (
            (base_year, base_bls, base_aligned, spec.base_period),
            (target_year, target_bls, target_aligned, spec.target_period),
        ):
            if requested == ANNUAL_BLS_CODE:
                alignment_warnings += [
                    f"Series {sid} has no annual average for {year}; the annual "
                    f"value was resolved from its {year}-{code} observation "
                    "(quarterly-to-annual alignment)."
                    for sid, code in sorted(aligned_map.items())
                ]
            else:
                alignment_warnings += [
                    f"Series {sid} has no monthly observation for "
                    f"{year}-M{spec_period.month:02d}; the monthly value was "
                    f"resolved from its {year}-{code} observation "
                    "(monthly-to-quarterly alignment)."
                    for sid, code in sorted(aligned_map.items())
                ]

        composite = self.calculations.calculate_composite(spec, component_calcs)
        ledger = CalculationLedger(
            calculation_id=str(uuid4()),
            specification=spec.id,
            result=(
                f"temporal={composite.temporal_composite_factor:.6f} "
                f"({composite.temporal_percent_change:+.4f}%)"
            ),
            observations_used=observations_used,
            provenance=provenance,
            warnings=composite.warnings + alignment_warnings,
        )
        return composite, ledger
