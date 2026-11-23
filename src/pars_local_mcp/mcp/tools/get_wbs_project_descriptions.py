"""PARS WBS MCP tool: get_wbs_project_descriptions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from pars_local_mcp.config import Settings
from pars_local_mcp.mcp.errors import tool_error
from pars_local_mcp.mcp.wbs_tools import MAX_READ_ROWS
from pars_local_mcp.wbs_port import pipeline as wbs_pipeline


def register(mcp: FastMCP, settings: Settings) -> None:
    """Register the project-description tool with its existing MCP contract."""

    def _source() -> Path:
        return Path(settings.wbs_source_db)

    @mcp.tool()
    def get_wbs_project_descriptions(limit: int = 20) -> dict[str, Any]:
        """Return project descriptions from the configured WBS source (read-only,
        synthetic sources only).

        Args:
            limit: rows to return, 1 to 500 (default 20)

        Returns:
            Dict with table, columns, total_rows, returned, and rows, or {"error": ...}
        """
        if not 1 <= limit <= MAX_READ_ROWS:
            return {"error": f"limit must be between 1 and {MAX_READ_ROWS}"}
        try:
            return wbs_pipeline.read_source_rows(
                _source(), "project_descriptions", limit
            )
        except Exception as e:
            return tool_error(e)
