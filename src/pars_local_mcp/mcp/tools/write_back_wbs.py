"""PARS WBS MCP tool: write_back_wbs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from pars_local_mcp.config import Settings
from pars_local_mcp.mcp.errors import tool_error
from pars_local_mcp.wbs_port import pipeline as wbs_pipeline


def register(mcp: FastMCP, settings: Settings) -> None:
    """Register write_back_wbs without changing its public MCP contract."""

    def _runs() -> Path:
        return Path(settings.wbs_runs_dir)

    @mcp.tool()
    def write_back_wbs(run_id: str) -> dict[str, Any]:
        """Write predictions back and export parquet (notebook 02, cells 3-6).

        Re-reads the exported file and verifies row counts and predicted values.

        Args:
            run_id: run with a completed predict stage

        Returns:
            Dict with row counts, export file, and read-back check results
        """
        try:
            return wbs_pipeline.stage_write_back(_runs(), run_id)
        except Exception as e:
            return tool_error(e)
