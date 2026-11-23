from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from bls_mcp.models.enums import Periodicity
from bls_mcp.models.periods import EconomicPeriod
from bls_mcp.models.series import (
    SeriesHierarchy,
    SeriesHierarchyEntry,
    SeriesMetadata,
    SeriesSearchRequest,
    SeriesSearchResult,
    UnverifiedDimension,
)
from bls_mcp.storage.query_models import (
    CIClassification,
    CUClassification,
    HierarchyEntry,
    PCClassification,
    SeriesSearchFilters,
    SeriesSearchHit,
)
from bls_mcp.storage.store import BLSStore

if TYPE_CHECKING:
    from bls_mcp.storage.query_models import SeriesSearchHit


def _period_from_bls(year: int | None, bls_period: str | None) -> EconomicPeriod | None:
    """Convert a (year, BLS period code) pair to an EconomicPeriod, or None."""
    if year is None or bls_period is None:
        return None
    code = bls_period.upper()
    if code == "M13":
        return EconomicPeriod(year=year, periodicity=Periodicity.ANNUAL_AVERAGE)
    if code.startswith("M"):
        return EconomicPeriod(
            year=year, month=int(code[1:]), periodicity=Periodicity.MONTHLY
        )
    if code.startswith("Q"):
        return EconomicPeriod(
            year=year, quarter=int(code[1:]), periodicity=Periodicity.QUARTERLY
        )
    return EconomicPeriod(year=year, periodicity=Periodicity.ANNUAL)


_HIERARCHY_BASIS = {
    "pc": "PPI industry and product code prefixes",
    "ci": "BLS display level and sort order (ECI industry and estimate)",
    "cu": "BLS display level and sort order (CPI item)",
}


class SeriesCatalogService:
    """Small metadata search service for BLS series backed by BLSStore."""

    def __init__(self, store: BLSStore) -> None:
        self.store = store

    def get(self, series_id: str) -> SeriesMetadata | None:
        page = self.store.search_series(
            SeriesSearchFilters(query=series_id, active_only=False, limit=10)
        )
        for hit in page.matches:
            if hit.series.series_id == series_id:
                return self._to_metadata(hit)
        return None

    def hierarchy(self, series_id: str) -> SeriesHierarchy | None:
        """The parent and the sub-items directly beneath a series' code."""
        found = self.store.series_hierarchy(series_id)
        if found is None:
            return None

        def entries(items: tuple[HierarchyEntry, ...]) -> list[SeriesHierarchyEntry]:
            return [
                SeriesHierarchyEntry(
                    dimension=e.dimension,
                    code=e.code,
                    name=e.name,
                    series_id=e.series_id,
                    has_observations=e.has_observations,
                )
                for e in items
            ]

        unverified = [
            UnverifiedDimension(dimension=d, reason=r) for d, r in found.unverified
        ]
        checked = set(found.dimensions) - {u.dimension for u in unverified}
        if not unverified:
            status: Literal["complete", "partial", "unknown"] = "complete"
        elif checked:
            status = "partial"
        else:
            status = "unknown"

        if found.sub_items:
            note = (
                "Each sub-item listed is included in this index. If the "
                "component covers only some of them, a narrower sub-item may "
                "fit better; check its own sub-items the same way."
            )
        else:
            note = "No narrower codes could be identified in this snapshot."
        if unverified:
            dims = ", ".join(u.dimension for u in unverified)
            note += (
                f" Relationships by {dims} could not be identified, so the "
                "parent and sub-item lists may be incomplete; verify what this "
                "series includes from BLS documentation before relying on it."
            )
        return SeriesHierarchy(
            series_id=found.series_id,
            program=found.program_code,
            title=found.title,
            snapshot_id=found.snapshot_id,
            status=status,
            basis=_HIERARCHY_BASIS.get(found.program_code, "not identified"),
            parents=entries(found.parents),
            sub_items=entries(found.sub_items),
            unverified=unverified,
            note=note,
        )

    def search(self, request: SeriesSearchRequest) -> list[SeriesSearchResult]:
        filters = SeriesSearchFilters(
            query=request.query,
            programs=tuple(request.programs) if request.programs else None,
            active_only=request.active_only,
            limit=request.limit,
        )
        page = self.store.search_series(filters)
        results = [
            SeriesSearchResult(
                series=self._to_metadata(hit),
                match_score=hit.match_score,
                match_reason=hit.match_reason,
            )
            for hit in page.matches
        ]
        # Preserve exact-ID and browsing semantics. Hierarchy expansion is a
        # discovery aid, not a reason to change the answer to an ID lookup.
        if not request.query.strip() or any(
            result.match_score == 1.0 for result in results
        ):
            return results
        if request.programs is not None and "pc" not in request.programs:
            return results

        seen = {result.series.series_id for result in results}
        parents: list[SeriesSearchResult] = []
        # Only strong industry-PPI hits can introduce a broader candidate.
        # The hierarchy service resolves actual catalog relationships; IDs
        # are never guessed by stripping suffixes.
        for result in results[:10]:
            if result.series.program != "pc" or (result.match_score or 0) < 0.75:
                continue
            hierarchy = self.store.series_hierarchy(result.series.series_id)
            if hierarchy is None:
                continue
            for parent in hierarchy.parents:
                parent_id = parent.series_id
                if not parent_id or parent_id in seen:
                    continue
                parent_page = self.store.search_series(
                    SeriesSearchFilters(
                        query=parent_id,
                        programs=tuple(request.programs) if request.programs else None,
                        active_only=request.active_only,
                        limit=1,
                    )
                )
                if not parent_page.matches:
                    continue
                hit = parent_page.matches[0]
                if hit.series.series_id != parent_id:
                    continue
                seen.add(parent_id)
                parents.append(
                    SeriesSearchResult(
                        series=self._to_metadata(hit),
                        match_score=0.45,
                        match_reason=(
                            "broader parent of matching series "
                            f"{result.series.series_id}"
                        ),
                    )
                )

        # Reserve room for at least one parent, even if the initial search
        # filled the requested limit. Direct matches keep their relative order.
        if parents:
            capacity = max(0, request.limit - min(len(parents), request.limit))
            return (results[:capacity] + parents[: request.limit - capacity])[
                : request.limit
            ]
        return results

    @staticmethod
    def _to_metadata(hit: SeriesSearchHit) -> SeriesMetadata:
        if not isinstance(hit, SeriesSearchHit):
            raise TypeError(f"Expected SeriesSearchHit, got {type(hit).__name__}")
        s = hit.series
        cl = hit.classification
        industry_code: str | None = None
        occupation_code: str | None = None
        area_code: str | None = None
        geography: str | None = None
        if isinstance(cl, PCClassification):
            industry_code = cl.industry_code
        elif isinstance(cl, CUClassification):
            area_code = cl.area_code
            geography = cl.area_name
        elif isinstance(cl, CIClassification):
            industry_code = cl.industry_code
            occupation_code = cl.occupation_code
            area_code = cl.area_code
            geography = cl.area_name

        first_period = _period_from_bls(s.first_year, s.first_period)
        last_period = _period_from_bls(s.last_year, s.last_period)

        return SeriesMetadata(
            series_id=s.series_id,
            program=s.program_code,
            title=s.title,
            description=s.description,
            seasonal_adjustment=s.seasonal_adjustment,
            units=s.units,
            active=s.active,
            first_period=first_period,
            latest_period=last_period,
            industry_code=industry_code,
            occupation_code=occupation_code,
            geography=geography,
            area_code=area_code,
        )
