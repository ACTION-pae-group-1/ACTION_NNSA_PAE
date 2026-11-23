"""PARS WBS MCP tool: tune_and_train_wbs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastmcp import FastMCP

from pars_local_mcp.config import Settings
from pars_local_mcp.mcp.errors import tool_error
from pars_local_mcp.mcp.wbs_tools import _check_search_caps
from pars_local_mcp.wbs_port import pipeline as wbs_pipeline


def register(mcp: FastMCP, settings: Settings) -> None:
    """Register tune_and_train_wbs without changing its public MCP contract."""

    def _key() -> bytes:
        from pars_local_mcp.mcp.tools import _model_signing_key

        return _model_signing_key(settings)

    def _runs() -> Path:
        return Path(settings.wbs_runs_dir)

    @mcp.tool()
    def tune_and_train_wbs(
        run_id: str,
        n_iter: int = 10,
        cv_folds: int = 3,
        n_jobs: int = wbs_pipeline.DEFAULT_N_JOBS,
        search_seed: int | None = None,
        split_seed: int | None = None,
    ) -> dict[str, Any]:
        """Tune and train the WBS model (notebook 01, ML path).

        Stratified split, untuned SGD hierarchical pipeline, RandomizedSearchCV over
        the source search space, and signed model bundles. Defaults match the source.

        Args:
            run_id: run created by clean_wbs_data
            n_iter: RandomizedSearchCV iterations (source: 10)
            cv_folds: IterativeStratification folds (source: 3)
            n_jobs: parallel search jobs (default 4; -1 uses every core)
            search_seed: optional random_state for the search (None = source behaviour)
            split_seed: optional seed for the stratified split's RNG (None = source)

        Returns:
            Dict with split sizes, F1 scores, best parameters, and bundle paths
        """
        try:
            _check_search_caps(n_iter, cv_folds, n_jobs, search_seed, split_seed)
            return wbs_pipeline.stage_tune_train(
                _runs(),
                run_id,
                signing_key=_key(),
                n_iter=n_iter,
                cv_folds=cv_folds,
                n_jobs=n_jobs,
                search_seed=search_seed,
                split_seed=split_seed,
            )
        except Exception as e:
            return tool_error(e)
