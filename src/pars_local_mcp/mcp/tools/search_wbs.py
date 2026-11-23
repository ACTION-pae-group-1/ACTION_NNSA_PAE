"""PARS MCP tool: search_wbs."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from pars_local_mcp.config import Settings
from pars_local_mcp.mcp.errors import require_range, tool_error
from pars_local_mcp.mcp.tools._project import _require_project_id, _resolve_project
from pars_local_mcp.storage.queries import PARSStore


def register(mcp: FastMCP, settings: Settings) -> None:
    """Register search_wbs without changing its public MCP contract."""

    @mcp.tool()
    def search_wbs(
        project_id: str,
        wbs_pattern: str | None = None,
        min_level: int | None = None,
        max_level: int | None = None,
    ) -> dict[str, Any]:
        """Search WBS elements in a project.

        Args:
            project_id: Project ID to search in
            wbs_pattern: SQL LIKE pattern for WBS codes (e.g., '01.01%')
            min_level: Minimum WBS level (1-8)
            max_level: Maximum WBS level (1-8)

        Returns:
            Dict with 'elements' key containing matching WBS elements
        """
        from pars_local_mcp.storage.models import WBSSearchFilter

        db_path = settings.database_path
        try:
            project_id = _resolve_project(db_path, _require_project_id(project_id))
            if min_level is not None:
                require_range("min_level", min_level, 1, 8)
            if max_level is not None:
                require_range("max_level", max_level, 1, 8)
            filter_obj = WBSSearchFilter(
                parsid=project_id,
                wbs_pattern=wbs_pattern,
                min_level=min_level,
                max_level=max_level,
            )
            with PARSStore(db_path) as store:
                elements = store.search_wbs(filter_obj)
                return {
                    "elements": [
                        {
                            "wbs_code": e.wbs_code,
                            "title": e.title,
                            "level": e.level,
                            "parent_wbs": e.parent_wbs,
                            "leaf_node": e.leaf_node,
                        }
                        for e in elements
                    ]
                }
        except Exception as e:
            return tool_error(e)
