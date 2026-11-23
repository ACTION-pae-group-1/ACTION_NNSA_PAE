from __future__ import annotations

from fastmcp import Context, FastMCP

from bls_mcp.mcp.adapters import domain_errors, get_services
from bls_mcp.models.series import (
    SeriesMetadata,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
    def describe_series(series_id: str, ctx: Context) -> SeriesMetadata | None:
        """Read local series metadata; return null when the ID is absent.

        To verify what the series includes, call get_series_hierarchy: the
        sub-items nested beneath its code show it; this metadata does not.
        """
        with domain_errors():
            return get_services(ctx).catalog.get(series_id)
