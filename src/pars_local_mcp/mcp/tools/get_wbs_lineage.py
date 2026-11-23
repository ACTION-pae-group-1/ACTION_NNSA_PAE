"""PARS MCP tool: get_wbs_lineage."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from pars_local_mcp.config import Settings
from pars_local_mcp.mcp.errors import tool_error
from pars_local_mcp.mcp.tools._project import _require_project_id, _resolve_project
from pars_local_mcp.storage.queries import PARSStore


def register(mcp: FastMCP, settings: Settings) -> None:
    """Register get_wbs_lineage without changing its public MCP contract."""

    @mcp.tool()
    def get_wbs_lineage(project_id: str, wbs_code: str) -> dict[str, Any]:
        """Get full parent chain for a WBS element (element to root).

        Returns the complete lineage starting with the specified element and
        walking up through all of its ancestors to the project root.

        Args:
            project_id: Project ID
            wbs_code: WBS code to get lineage for

        Returns:
            Dict with 'lineage' key containing list of ancestor elements
        """
        db_path = settings.database_path
        try:
            project_id = _resolve_project(db_path, _require_project_id(project_id))
            with PARSStore(db_path) as store:
                lineage = store.get_wbs_lineage(project_id, wbs_code)
                return {
                    "lineage": [
                        {
                            "wbs_code": e.wbs_code,
                            "title": e.title,
                            "level": e.level,
                        }
                        for e in lineage
                    ]
                }
        except Exception as e:
            return tool_error(e)
