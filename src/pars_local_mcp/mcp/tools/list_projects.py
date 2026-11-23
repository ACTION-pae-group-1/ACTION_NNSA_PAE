"""PARS MCP tool: list_projects."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from pars_local_mcp.config import Settings
from pars_local_mcp.mcp.errors import tool_error
from pars_local_mcp.storage.queries import PARSStore


def register(mcp: FastMCP, settings: Settings) -> None:
    """Register list_projects without changing its public MCP contract."""

    @mcp.tool()
    def list_projects() -> dict[str, Any]:
        """List all projects in the WBS database.

        Call this first. Every other project tool needs one of the IDs returned
        here. Matching ignores case, so PROJ_001 finds proj_001.

        Returns information about each project including the number of WBS
        elements and the maximum hierarchy depth.

        Returns:
            Dict with 'projects' key containing list of project metadata
        """
        db_path = settings.database_path
        try:
            with PARSStore(db_path) as store:
                projects = store.list_projects()
                return {
                    "projects": [
                        {
                            "parsid": p.parsid,
                            "project_name": p.project_name,
                            "total_elements": p.total_elements,
                            "hierarchy_depth": p.hierarchy_depth,
                        }
                        for p in projects
                    ]
                }
        except Exception as e:
            return tool_error(e)
