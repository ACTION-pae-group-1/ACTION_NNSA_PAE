from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from bls_mcp.clients.bls import BLSClient
from bls_mcp.exceptions import BLSAPIError, InvalidPeriodError
from bls_mcp.models.enums import Periodicity
from bls_mcp.models.observations import Observation
from bls_mcp.models.periods import EconomicPeriod
from bls_mcp.services.access import BLSAccessService
from bls_mcp.storage.store import BLSStore


def _period_from_bls(year: int, bls_code: str) -> EconomicPeriod:
    """Map a BLS period code (e.g. M01, M13, Q01) to an EconomicPeriod."""
    code = bls_code.upper()
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
    if code.startswith("S"):
        # S01/S02/S03 are semi-annual averages — treat as annual
        return EconomicPeriod(year=year, periodicity=Periodicity.ANNUAL)
    return EconomicPeriod(year=year, periodicity=Periodicity.ANNUAL)


class ObservationService:
    """Retrieve observations without persisting or replacing them."""

    def __init__(
        self, client: BLSClient, access: BLSAccessService, store: BLSStore
    ) -> None:
        self.client = client
        self.access = access
        self.store = store

    async def fetch(
        self, series_ids: list[str], start_year: int, end_year: int
    ) -> list[Observation]:
        if start_year <= 0 or end_year < start_year:
            raise InvalidPeriodError(
                "Years must be positive and end_year must be >= start_year."
            )
        self.access.require_configured()
        limits = self.access.limits
        if len(series_ids) > limits.series_per_query:
            raise BLSAPIError(
                "At most 50 series per call; automatic batching is deferred. "
                "See setup://bls-api and docs/bls_api.md."
            )
        if end_year - start_year + 1 > limits.years_per_query:
            raise BLSAPIError(
                "At most 20 inclusive calendar years per call; automatic "
                "batching is deferred. See setup://bls-api and "
                "docs/bls_api.md."
            )
        return await self.client.get_series_observations(
            series_ids, start_year, end_year
        )

    def fetch_cached(
        self,
        series_id: str,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 24,
    ) -> list[Observation]:
        """Return locally stored observations from DuckDB, without BLS API access."""
        if (start_year is not None and start_year <= 0) or (
            end_year is not None and end_year <= 0
        ):
            raise InvalidPeriodError("Years must be positive.")
        if start_year is not None and end_year is not None and end_year < start_year:
            raise InvalidPeriodError("end_year must be >= start_year.")
        if not 1 <= limit <= 100:
            raise InvalidPeriodError("limit must be between 1 and 100.")

        page = self.store.get_observations(
            [series_id],
            start_year=start_year,
            end_year=end_year,
            max_rows=100,
        )

        retrieved_at = datetime.now(UTC)
        observations: list[Observation] = []
        for rec in page.observations:
            period = _period_from_bls(rec.year, rec.period)
            footnotes = (
                rec.footnote_codes.replace(",", " ").split()
                if rec.footnote_codes
                else []
            )
            observations.append(
                Observation(
                    series_id=rec.series_id,
                    period=period,
                    value=Decimal(str(rec.value)),
                    retrieved_at=retrieved_at,
                    source="bls_snapshot",
                    is_preliminary=("P" in footnotes),
                    footnotes=footnotes,
                )
            )

        return observations[-limit:]
