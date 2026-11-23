"""Isolated stdio launcher for the PARS tools, used only by the gap tool-call
evaluation.

This is NOT the default entry point. src/pars_local_mcp/mcp/server.py main() reads
get_settings() and calls initialize_database() on the configured database, which can
regenerate a protected database. This launcher:

  * refuses to start unless all five PARS path variables are set (DATABASE_PATH,
    MODEL_DIR, MODEL_SIGNING_KEY_PATH, WBS_RUNS_DIR, WBS_SOURCE_DB);
  * refuses any path that is not under the isolated evaluation root;
  * builds Settings from those variables only (no .env, no defaults);
  * registers the same 16 tools with register_tools() and does NOT call
    initialize_database(), so the served database is exactly the copy it was given.
"""

from __future__ import annotations

import os
import sys

sys.dont_write_bytecode = True

from pathlib import Path  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

ISOLATION_ROOT = Path("C:/tmp/pars_eval_gap/runs").resolve()
REQUIRED = {
    "DATABASE_PATH": "database_path",
    "MODEL_DIR": "model_dir",
    "MODEL_SIGNING_KEY_PATH": "model_signing_key_path",
    "WBS_RUNS_DIR": "wbs_runs_dir",
    "WBS_SOURCE_DB": "wbs_source_db",
}


def _check_env() -> dict[str, Path]:
    missing = [k for k in REQUIRED if not os.environ.get(k)]
    if missing:
        raise SystemExit(f"refusing to start: unset {missing}")
    paths: dict[str, Path] = {}
    for key in REQUIRED:
        p = Path(os.environ[key]).resolve()
        if ISOLATION_ROOT not in p.parents:
            raise SystemExit(f"refusing to start: {key} is outside the isolation root")
        paths[key] = p
    return paths


def main() -> None:
    paths = _check_env()
    from fastmcp import FastMCP

    from pars_local_mcp.config import Settings
    from pars_local_mcp.mcp.tools import register_tools

    settings = Settings(
        database_path=paths["DATABASE_PATH"],
        model_dir=paths["MODEL_DIR"],
        model_signing_key_path=paths["MODEL_SIGNING_KEY_PATH"],
        wbs_runs_dir=paths["WBS_RUNS_DIR"],
        wbs_source_db=paths["WBS_SOURCE_DB"],
    )
    mcp = FastMCP(
        "PARS WBS Classification and Hierarchy (isolated gap launcher)",
        mask_error_details=True,
    )
    register_tools(mcp, settings)
    mcp.run(show_banner=False)


if __name__ == "__main__":
    main()
