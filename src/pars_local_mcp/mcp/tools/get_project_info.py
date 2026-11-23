"""PARS MCP tool: get_project_info."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from pars_local_mcp.config import Settings
from pars_local_mcp.mcp.errors import tool_error
from pars_local_mcp.mcp.tools._project import _require_project_id, _resolve_project
from pars_local_mcp.storage.queries import PARSStore


def register(mcp: FastMCP, settings: Settings) -> None:
    """Register get_project_info without changing its public MCP contract."""

    @mcp.tool()
    def get_project_info(project_id: str) -> dict[str, Any]:
        """Get detailed information about a project.

        Returns metadata including element counts and hierarchy depth.

        Args:
            project_id: Project ID

        Returns:
            Dict with project metadata
        """
        db_path = settings.database_path
        try:
            project_id = _resolve_project(db_path, _require_project_id(project_id))
            with PARSStore(db_path) as store:
                projects = store.list_projects()
                project = next((p for p in projects if p.parsid == project_id), None)
                if not project:
                    return {"error": f"Project {project_id} not found"}
                return {
                    "parsid": project.parsid,
                    "project_name": project.project_name,
                    "total_elements": project.total_elements,
                    "hierarchy_depth": project.hierarchy_depth,
                }
        except Exception as e:
            return tool_error(e)
