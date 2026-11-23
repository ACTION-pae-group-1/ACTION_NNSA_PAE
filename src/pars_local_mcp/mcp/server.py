"""PARS WBS classification and hierarchy query MCP server."""

from __future__ import annotations

from fastmcp import FastMCP

from pars_local_mcp.config import Settings, get_settings
from pars_local_mcp.mcp.tools import register_tools
from pars_local_mcp.storage.initialization import initialize_database


def create_server(settings: Settings | None = None) -> FastMCP:
    """Assemble the PARS MCP server with all tools registered.

    Initialize synthetic data before registering the 16 MCP tools.
    """
    if settings is None:
        settings = get_settings()
    initialize_database(settings.database_path)
    mcp = FastMCP(
        "PARS WBS Classification and Hierarchy",
        instructions=(
            "Use PARS tools to read WBS hierarchies (projects, hierarchy, lineage, "
            "leaf nodes, level lookups) and to run the WBS pipeline: validate inputs, "
            "clean, tune and train, predict, write back, check run status, and read "
            "source rows (read-only). All operations use synthetic data suitable for "
            "testing. Database queries are read-only."
        ),
        mask_error_details=True,
    )
    register_tools(mcp, settings)
    return mcp


def main() -> None:
    """Entry point for the PARS MCP server."""
    create_server().run(show_banner=False)


if __name__ == "__main__":
    main()
