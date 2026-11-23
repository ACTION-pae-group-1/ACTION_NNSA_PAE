"""PARS MCP tool: get_wbs_hierarchy."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from pars_local_mcp.config import Settings
from pars_local_mcp.mcp.errors import tool_error
from pars_local_mcp.mcp.tools._project import _require_project_id, _resolve_project
from pars_local_mcp.storage.queries import PARSStore


def register(mcp: FastMCP, settings: Settings) -> None:
    """Register get_wbs_hierarchy without changing its public MCP contract."""

    @mcp.tool()
    def get_wbs_hierarchy(project_id: str, wbs_code: str) -> dict[str, Any]:
        """Get WBS element and its immediate children.

        Returns a tree structure showing the element and its direct descendants
        in the work breakdown structure.

        Args:
            project_id: Project ID
            wbs_code: WBS code of the element

        Returns:
            Dict with 'element' and 'children' keys representing the hierarchy
        """
        db_path = settings.database_path
        try:
            project_id = _resolve_project(db_path, _require_project_id(project_id))
            with PARSStore(db_path) as store:
                result = store.get_wbs_subtree(project_id, wbs_code, depth=1)
                # Convert to serializable format
                elem = result["element"]
                children = [
                    {
                        "element": {
                            "wbs_code": c["element"]["wbs_code"],
                            "title": c["element"]["title"],
                            "level": c["element"]["level"],
                            "leaf_node": c["element"]["leaf_node"],
                        },
                        "children": c["children"],
                    }
                    for c in result["children"]
                ]
                return {
                    "element": {
                        "wbs_code": elem["wbs_code"],
                        "title": elem["title"],
                        "level": elem["level"],
                        "parent_wbs": elem["parent_wbs"],
                        "leaf_node": elem["leaf_node"],
                    },
                    "children": children,
                }
        except Exception as e:
            return tool_error(e)
