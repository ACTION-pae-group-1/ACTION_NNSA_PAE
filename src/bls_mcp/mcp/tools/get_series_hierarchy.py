from __future__ import annotations

from fastmcp import Context, FastMCP

from bls_mcp.mcp.adapters import domain_errors, get_services
from bls_mcp.models.series import SeriesHierarchy


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
    def get_series_hierarchy(series_id: str, ctx: Context) -> SeriesHierarchy | None:
        """Show the narrower sub-items nested beneath a series' code, and its parent.

        Seeing the narrower sub-items nested beneath a parent code is the
        primary way to verify what an index includes; the title alone does not
        show it. Call this before choosing a series for a component, and pick
        the level whose sub-items match the component's scope.

        Example: PPI "Sawmills" (PCU321113321113) includes hardwood lumber,
        softwood lumber, wood chips, and wood ties and siding. A component
        that is only framing lumber is better matched by "Softwood lumber"
        (PCU3211133211133) or one of its own sub-items.

        Each sub-item gives its series ID when this snapshot has one, and
        whether that series has observations. PPI nests by industry and
        product code; ECI by industry and estimate (total compensation
        includes wages and benefits); CPI by item.

        Check ``status``. "complete" means every relationship could be
        identified. "partial" or "unknown" means some could not, and
        ``unverified`` says which and why: for example, ECI occupation
        relationships are not reported because BLS's published order for them
        is not a single hierarchy, and PPI aggregates such as total
        manufacturing do not encode their member industries. An empty list
        then is not evidence that nothing is included; tell the user, and do
        not claim what such a series includes. Returns null when the series ID
        is not in the snapshot.
        """
        with domain_errors():
            return get_services(ctx).catalog.hierarchy(series_id)
