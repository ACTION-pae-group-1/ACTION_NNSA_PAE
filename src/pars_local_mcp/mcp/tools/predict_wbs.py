"""PARS WBS MCP tool: predict_wbs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from pars_local_mcp.config import Settings
from pars_local_mcp.mcp.errors import tool_error
from pars_local_mcp.wbs_port import pipeline as wbs_pipeline


def register(mcp: FastMCP, settings: Settings) -> None:
    """Register predict_wbs without changing its public MCP contract."""

    def _key() -> bytes:
        from pars_local_mcp.mcp.tools import _model_signing_key

        return _model_signing_key(settings)

    def _runs() -> Path:
        return Path(settings.wbs_runs_dir)

    @mcp.tool()
    def predict_wbs(run_id: str, model_variant: str = "untuned") -> dict[str, Any]:
        """Predict level_2..level_8 for every SPAE row (notebook 02).

        Loads the signed bundle for the chosen variant. The source notebook uses the
        untuned model by default.

        Args:
            run_id: run with a completed tune_train stage
            model_variant: "untuned" (source default) or "tuned"

        Returns:
            Dict with predicted row count and distinct labels per level
        """
        try:
            return wbs_pipeline.stage_predict(
                _runs(), run_id, signing_key=_key(), model_variant=model_variant
            )
        except Exception as e:
            return tool_error(e)
