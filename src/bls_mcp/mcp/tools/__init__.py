"""Explicit registration of individual MCP tools."""

from fastmcp import FastMCP

from bls_mcp.mcp.tools import (
    calculate_component_escalation,
    calculate_index_from_bls,
    calculate_index_spec,
    calculate_labor_locality_factor,
    create_index_spec,
    describe_series,
    get_bls_access_status,
    get_cached_series_data,
    get_index_spec,
    get_index_visualization,
    get_series_data,
    get_series_hierarchy,
    save_index_spec,
    search_series,
    validate_index_spec,
)


def register_tools(mcp: FastMCP) -> None:
    """Register every tool exactly once."""
    get_bls_access_status.register(mcp)
    calculate_component_escalation.register(mcp)
    calculate_index_spec.register(mcp)
    calculate_index_from_bls.register(mcp)
    get_index_visualization.register(mcp)
    search_series.register(mcp)
    describe_series.register(mcp)
    get_series_hierarchy.register(mcp)
    calculate_labor_locality_factor.register(mcp)
    get_series_data.register(mcp)
    get_cached_series_data.register(mcp)
    create_index_spec.register(mcp)
    save_index_spec.register(mcp)
    get_index_spec.register(mcp)
    validate_index_spec.register(mcp)
