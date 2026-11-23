from __future__ import annotations

from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

from bls_mcp.mcp.adapters import domain_errors, get_services
from bls_mcp.models.visualization import IndexVisualizationData


def register(mcp: FastMCP) -> None:
    @mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})
    def get_index_visualization(
        spec_id: str,
        ctx: Context,
        start_year: int | None = None,
        end_year: int | None = None,
        source_year: int | None = None,
    ) -> IndexVisualizationData:
        """Return the annual history of a saved index spec for charting.

        Loads the saved specification by *spec_id* and reads every component's
        annual observations from the BLS snapshot. Each series is normalized to
        the base year's annual average (factor 1.0), weighted by its allocation
        and summed into a composite factor per year. The result follows the
        index visualization contract, schema_version 1.0: components,
        component_points, composite_points, an optional base_year_adjustment
        and warnings. Numeric results are decimal strings; do not recompute
        them, quote them.

        The year window defaults to the span between the spec's base and target
        years; widen it with *start_year* / *end_year* (it must include the
        base year). *source_year* selects the year whose adjustment to the base
        year is returned in base_year_adjustment (default: the target year).

        Only complete years are returned. A year in which any component lacks
        an observation is left out and named in warnings; report that to the
        user rather than describing the year as flat or zero. A series that
        publishes quarters only uses its Q04 observation, also disclosed in
        warnings.

        Raises ToolError when:
        - spec_id is not found
        - the spec has ERROR-level validation findings
        - a weighted component has no BLS series (fixed/unindexed components
          cannot be charted)
        - a component series or its base-year observation is absent
        - the year window excludes the base year, or source_year has no
          complete result
        """
        with domain_errors():
            services = get_services(ctx)
            spec = services.specifications.get(spec_id)
            if spec is None:
                raise ToolError(f"Specification '{spec_id}' not found.")
            return services.visualization.build(
                spec,
                start_year=start_year,
                end_year=end_year,
                source_year=source_year,
            ).result
