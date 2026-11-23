from __future__ import annotations

from fastmcp import Context, FastMCP

from bls_mcp.mcp.adapters import domain_errors, get_services
from bls_mcp.models.observations import Observation


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
    def get_cached_series_data(
        series_id: str,
        ctx: Context,
        start_year: int | None = None,
        end_year: int | None = None,
        limit: int = 24,
    ) -> list[Observation]:
        """Read up to 100 locally stored BLS observations for one series.

        The default returns the latest 24 observations. Optional years
        restrict the period; an empty list means nothing is cached.
        Does not call the live BLS API or require a BLS API key.
        """
        with domain_errors():
            return get_services(ctx).observations.fetch_cached(
                series_id, start_year, end_year, limit
            )
