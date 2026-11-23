"""PARS WBS MCP tool: validate_wbs_inputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from pars_local_mcp.config import Settings
from pars_local_mcp.mcp.errors import tool_error
from pars_local_mcp.wbs_port import pipeline as wbs_pipeline


def register(mcp: FastMCP, settings: Settings) -> None:
    """Register validate_wbs_inputs without changing its public MCP contract."""

    def _source() -> Path:
        return Path(settings.wbs_source_db)

    @mcp.tool()
    def validate_wbs_inputs() -> dict[str, Any]:
        """Check the configured WBS source database against the input contract.

        Reports missing tables or columns, non-integer wbs_level/parsid values, and
        whether the database is the bundled synthetic mock or a labeled fixture.
        Reads only; returns counts and problems, never records.

        Returns:
            Dict with ok, data_origin, problems, and per-table row counts.
        """
        try:
            return wbs_pipeline.validate_source(_source())
        except Exception as e:
            return tool_error(e)
