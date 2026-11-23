"""PARS WBS MCP tool: get_wbs_run_status."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from pars_local_mcp.config import Settings
from pars_local_mcp.mcp.errors import tool_error
from pars_local_mcp.wbs_port import pipeline as wbs_pipeline


def register(mcp: FastMCP, settings: Settings) -> None:
    """Register get_wbs_run_status without changing its public MCP contract."""

    def _runs() -> Path:
        return Path(settings.wbs_runs_dir)

    @mcp.tool()
    def get_wbs_run_status(run_id: str) -> dict[str, Any]:
        """Return the stage manifest for a WBS run (status, counts, artifact paths).

        Args:
            run_id: run identifier returned by another wbs_* tool

        Returns:
            Dict with run_id, stages, and data_origin
        """
        try:
            return wbs_pipeline.run_status(_runs(), run_id)
        except Exception as e:
            return tool_error(e)
