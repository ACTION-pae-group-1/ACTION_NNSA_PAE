"""Compatibility module for WBS limits and tool registration."""

from __future__ import annotations

from fastmcp import FastMCP

from pars_local_mcp.config import Settings
from pars_local_mcp.mcp.errors import PublicError, require_range
from pars_local_mcp.wbs_port import pipeline as wbs_pipeline

MAX_READ_ROWS = 500
MAX_N_ITER = 100
MAX_CV_FOLDS = 10
MAX_SEED = 2**32 - 1


def _check_search_caps(
    n_iter: int,
    cv_folds: int,
    n_jobs: int,
    search_seed: int | None,
    split_seed: int | None,
) -> None:
    """Reject bad search arguments before any run directory, copy, or log is written.

    Covers the source lower bounds, the server caps, n_jobs (joblib rejects 0 only
    after the search starts), and seeds outside the range numpy accepts.
    """
    wbs_pipeline.check_search_args(n_iter, cv_folds)
    if n_iter > MAX_N_ITER:
        raise PublicError(f"n_iter must be <= {MAX_N_ITER}")
    if cv_folds > MAX_CV_FOLDS:
        raise PublicError(f"cv_folds must be <= {MAX_CV_FOLDS}")
    require_range("n_jobs", n_jobs, -1, 8)
    if n_jobs == 0:
        raise PublicError("n_jobs must be -1 or between 1 and 8")
    for name, seed in (("search_seed", search_seed), ("split_seed", split_seed)):
        if seed is not None:
            require_range(name, seed, 0, MAX_SEED)


def register_wbs_tools(mcp: FastMCP, settings: Settings) -> None:
    """Compatibility entry point for the nine WBS tools."""
    from pars_local_mcp.mcp.tools import (
        clean_wbs_data,
        get_wbs_project_descriptions,
        get_wbs_rows,
        get_wbs_run_status,
        predict_wbs,
        run_wbs_pipeline,
        tune_and_train_wbs,
        validate_wbs_inputs,
        write_back_wbs,
    )

    validate_wbs_inputs.register(mcp, settings)
    clean_wbs_data.register(mcp, settings)
    tune_and_train_wbs.register(mcp, settings)
    predict_wbs.register(mcp, settings)
    write_back_wbs.register(mcp, settings)
    run_wbs_pipeline.register(mcp, settings)
    get_wbs_run_status.register(mcp, settings)
    get_wbs_project_descriptions.register(mcp, settings)
    get_wbs_rows.register(mcp, settings)
