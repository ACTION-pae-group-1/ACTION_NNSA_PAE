"""GSA-aligned PARS tool registry: one tool per module."""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from fastmcp import FastMCP

from pars_local_mcp.config import Settings
from pars_local_mcp.mcp.tools import (
    clean_wbs_data,
    get_leaf_nodes,
    get_project_info,
    get_wbs_by_level,
    get_wbs_hierarchy,
    get_wbs_lineage,
    get_wbs_project_descriptions,
    get_wbs_rows,
    get_wbs_run_status,
    list_projects,
    predict_wbs,
    run_wbs_pipeline,
    search_wbs,
    tune_and_train_wbs,
    validate_wbs_inputs,
    write_back_wbs,
)


def register_tools(mcp: FastMCP, settings: Settings) -> None:
    """Register the complete 16-tool PARS MCP interface."""
    list_projects.register(mcp, settings)
    search_wbs.register(mcp, settings)
    get_wbs_hierarchy.register(mcp, settings)
    get_wbs_lineage.register(mcp, settings)
    get_project_info.register(mcp, settings)
    get_leaf_nodes.register(mcp, settings)
    get_wbs_by_level.register(mcp, settings)
    validate_wbs_inputs.register(mcp, settings)
    clean_wbs_data.register(mcp, settings)
    tune_and_train_wbs.register(mcp, settings)
    predict_wbs.register(mcp, settings)
    write_back_wbs.register(mcp, settings)
    run_wbs_pipeline.register(mcp, settings)
    get_wbs_run_status.register(mcp, settings)
    get_wbs_project_descriptions.register(mcp, settings)
    get_wbs_rows.register(mcp, settings)


def _model_signing_key(settings: Settings) -> bytes:
    """Return the manifest signing key, creating it on first use.

    The key file must live outside model_dir; otherwise anyone who can write
    model files could also write a matching signature.
    """
    key_path = Path(os.path.abspath(settings.model_signing_key_path))
    model_dir = Path(os.path.abspath(settings.model_dir))
    model_dir.mkdir(parents=True, exist_ok=True)
    for ancestor in (key_path.parent, *key_path.parent.parents):
        if ancestor.exists() and os.path.samefile(ancestor, model_dir):
            raise ValueError("model_signing_key_path must be outside model_dir")
    key_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(fd, "wb") as f:
            f.write(secrets.token_bytes(32))
    return key_path.read_bytes()
