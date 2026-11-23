"""PARS WBS MCP tool: clean_wbs_data."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from pars_local_mcp.config import Settings
from pars_local_mcp.mcp.errors import tool_error
from pars_local_mcp.wbs_port import pipeline as wbs_pipeline


def register(mcp: FastMCP, settings: Settings) -> None:
    """Register clean_wbs_data without changing its public MCP contract."""

    def _runs() -> Path:
        return Path(settings.wbs_runs_dir)

    def _source() -> Path:
        return Path(settings.wbs_source_db)

    @mcp.tool()
    def clean_wbs_data(run_id: str | None = None) -> dict[str, Any]:
        """Run the cleaning stage (notebook 00): concatenate and clean the labelled
        sample and the full SPAE table with the source functions.

        Args:
            run_id: existing run to (re)start, or None to create a new run

        Returns:
            Dict with run_id, row counts, and data_origin, or {"error": ...}
        """
        try:
            return wbs_pipeline.stage_clean(_runs(), run_id, _source())
        except Exception as e:
            return tool_error(e)
