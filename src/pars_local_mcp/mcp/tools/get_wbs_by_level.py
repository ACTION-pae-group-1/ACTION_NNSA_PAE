"""PARS MCP tool: get_wbs_by_level."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from pars_local_mcp.config import Settings
from pars_local_mcp.mcp.errors import require_range, tool_error
from pars_local_mcp.mcp.tools._project import _require_project_id, _resolve_project
from pars_local_mcp.storage.queries import PARSStore


def register(mcp: FastMCP, settings: Settings) -> None:
    """Register get_wbs_by_level without changing its public MCP contract."""

    @mcp.tool()
    def get_wbs_by_level(project_id: str, level: int) -> dict[str, Any]:
        """Get all WBS elements at a specific hierarchy level.

        Levels range from 1 (root) to the project's maximum depth.

        Args:
            project_id: Project ID
            level: Hierarchy level (1-8)

        Returns:
            Dict with 'elements' key containing all elements at that level
        """
        from pars_local_mcp.storage.models import WBSSearchFilter

        db_path = settings.database_path
        try:
            project_id = _resolve_project(db_path, _require_project_id(project_id))
            require_range("level", level, 1, 8)
            filter_obj = WBSSearchFilter(
                parsid=project_id, min_level=level, max_level=level
            )
            with PARSStore(db_path) as store:
                elements = store.search_wbs(filter_obj)
                return {
                    "elements": [
                        {
                            "wbs_code": e.wbs_code,
                            "title": e.title,
                            "parent_wbs": e.parent_wbs,
                            "leaf_node": e.leaf_node,
                        }
                        for e in elements
                    ]
                }
        except Exception as e:
            return tool_error(e)
