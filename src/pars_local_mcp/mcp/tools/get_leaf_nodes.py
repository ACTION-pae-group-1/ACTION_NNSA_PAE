"""PARS MCP tool: get_leaf_nodes."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from pars_local_mcp.config import Settings
from pars_local_mcp.mcp.errors import tool_error
from pars_local_mcp.mcp.tools._project import _require_project_id, _resolve_project
from pars_local_mcp.storage.queries import PARSStore


def register(mcp: FastMCP, settings: Settings) -> None:
    """Register get_leaf_nodes without changing its public MCP contract."""

    @mcp.tool()
    def get_leaf_nodes(project_id: str) -> dict[str, Any]:
        """Get all leaf nodes (terminal WBS elements) in a project.

        Leaf nodes are the lowest-level elements in the hierarchy.

        Args:
            project_id: Project ID

        Returns:
            Dict with 'leaf_nodes' key containing terminal elements
        """
        from pars_local_mcp.storage.models import WBSSearchFilter

        db_path = settings.database_path
        try:
            project_id = _resolve_project(db_path, _require_project_id(project_id))
            filter_obj = WBSSearchFilter(parsid=project_id, include_leaves_only=True)
            with PARSStore(db_path) as store:
                leaves = store.search_wbs(filter_obj)
                return {
                    "leaf_nodes": [
                        {
                            "wbs_code": e.wbs_code,
                            "title": e.title,
                            "level": e.level,
                        }
                        for e in leaves
                    ]
                }
        except Exception as e:
            return tool_error(e)
