from __future__ import annotations

from fastmcp import Context, FastMCP

from bls_mcp.mcp.adapters import domain_errors, get_services
from bls_mcp.models.series import (
    SeriesSearchRequest,
    SeriesSearchResult,
)


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
    def search_series(
        request: SeriesSearchRequest, ctx: Context
    ) -> list[SeriesSearchResult]:
        """Search the local catalog by text and explicit program filters.

        A title does not show what an index includes. Before choosing a
        result, call get_series_hierarchy to see the narrower sub-items nested
        beneath its code.
        """
        with domain_errors():
            return get_services(ctx).catalog.search(request)
