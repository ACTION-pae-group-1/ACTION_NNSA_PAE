"""PARS WBS MCP tool: run_wbs_pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from pars_local_mcp.config import Settings
from pars_local_mcp.mcp.errors import tool_error
from pars_local_mcp.mcp.wbs_tools import _check_search_caps
from pars_local_mcp.wbs_port import pipeline as wbs_pipeline


def register(mcp: FastMCP, settings: Settings) -> None:
    """Register run_wbs_pipeline without changing its public MCP contract."""

    def _key() -> bytes:
        from pars_local_mcp.mcp.tools import _model_signing_key

        return _model_signing_key(settings)

    def _runs() -> Path:
        return Path(settings.wbs_runs_dir)

    def _source() -> Path:
        return Path(settings.wbs_source_db)

    @mcp.tool()
    def run_wbs_pipeline(
        run_id: str | None = None,
        n_iter: int = 10,
        cv_folds: int = 3,
        n_jobs: int = wbs_pipeline.DEFAULT_N_JOBS,
        search_seed: int | None = None,
        split_seed: int | None = None,
        model_variant: str = "untuned",
    ) -> dict[str, Any]:
        """Run the full WBS chain: clean, tune and train, predict, write back.

        Args:
            run_id: optional run to reuse; None creates a new run
            n_iter: RandomizedSearchCV iterations (source: 10)
            cv_folds: stratification folds (source: 3)
            n_jobs: parallel search jobs (default 4; -1 uses every core)
            search_seed: optional search random_state (None = source behaviour)
            split_seed: optional split RNG seed (None = source behaviour)
            model_variant: "untuned" (source default) or "tuned"

        Returns:
            Dict with run_id, per-stage results, and artifacts_dir. On failure,
            {"error": ..., "run_id": ...} so a partial run can be inspected.
        """
        # Generate the id here so every error names the run it would have used. No
        # directory exists until the arguments pass the checks below.
        run_id = run_id or wbs_pipeline.new_run_id()
        try:
            _check_search_caps(n_iter, cv_folds, n_jobs, search_seed, split_seed)
            return wbs_pipeline.run_pipeline(
                _runs(),
                _source(),
                signing_key=_key(),
                run_id=run_id,
                n_iter=n_iter,
                cv_folds=cv_folds,
                n_jobs=n_jobs,
                search_seed=search_seed,
                split_seed=split_seed,
                model_variant=model_variant,
            )
        except Exception as e:
            return {**tool_error(e), "run_id": run_id}
