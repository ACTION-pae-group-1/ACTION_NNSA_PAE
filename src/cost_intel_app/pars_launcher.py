"""Application-side PARS MCP launcher for a prepopulated synthetic stadium database.

The protected PARS server (``pars_local_mcp.mcp.server.create_server``) calls
``initialize_database()`` on every start, which regenerates the synthetic tables
at the configured path. This launcher builds the same FastMCP server and registers
the same 16 tools with ``register_tools()``, but it does not call
``initialize_database()``. It opens a database that is already prepopulated and
refuses to start otherwise.

Rules enforced here:

- ``PARS_STADIUM_DB`` must name an existing file with the PARS tables and the
  synthetic marker set to ``synthetic``. Anything else is refused.
- The database may not be the protected PARS data file or sit inside the protected
  PARS data directory.
- Settings for models, signing keys, and pipeline runs point at a local,
  git-ignored directory, never at the protected PARS data directory.
- There is no fallback. If the configuration is invalid, the process exits with an
  error and never serves tools.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path

import duckdb
from fastmcp import FastMCP

from pars_local_mcp.config import Settings
from pars_local_mcp.mcp.tools import register_tools
from pars_local_mcp.storage.initialization import PARS_TABLES, SYNTHETIC_MARKER_TABLE

ENV_DATABASE = "PARS_STADIUM_DB"
REPO = Path(__file__).resolve().parents[2]
PROTECTED_DATA_DIR = REPO / "src" / "pars_local_mcp" / "data"
LOCAL_RUNS_DIR = REPO / "data" / "local" / "pars_stadium_runs"
SERVER_NAME = "PARS WBS Classification and Hierarchy"
SERVER_INSTRUCTIONS = (
    "Use PARS tools to read WBS hierarchies (projects, hierarchy, lineage, "
    "leaf nodes, level lookups) and to run the WBS pipeline: validate inputs, "
    "clean, tune and train, predict, write back, check run status, and read "
    "source rows (read-only). All operations use synthetic data suitable for "
    "testing. Database queries are read-only."
)


class LauncherConfigError(RuntimeError):
    """The launcher configuration is invalid; the server must not start."""


def check_database(value: str | None) -> Path:
    """Return the validated database path, or raise LauncherConfigError."""
    if value is None or not value.strip():
        raise LauncherConfigError(f"{ENV_DATABASE} is not set.")
    path = Path(value.strip()).expanduser().resolve()
    protected = PROTECTED_DATA_DIR.resolve()
    if path == protected or protected in path.parents:
        raise LauncherConfigError(
            "The stadium database must not be inside the protected PARS data directory."
        )
    if not path.is_file():
        raise LauncherConfigError("The stadium database file was not found.")
    con = duckdb.connect(str(path), read_only=True)
    try:
        tables = {row[0] for row in con.execute("SHOW TABLES").fetchall()}
        required = (SYNTHETIC_MARKER_TABLE, *PARS_TABLES)
        if any(table not in tables for table in required):
            raise LauncherConfigError("The stadium database is missing PARS tables.")
        markers = con.execute(f"SELECT marker FROM {SYNTHETIC_MARKER_TABLE}").fetchall()
        if markers != [("synthetic",)]:
            raise LauncherConfigError("The stadium database is not marked synthetic.")
    finally:
        con.close()
    return path


def build_settings(database: Path) -> Settings:
    """Settings that read the given database and write nothing under protected data."""
    return Settings(
        database_path=database,
        model_dir=LOCAL_RUNS_DIR / "models",
        model_signing_key_path=LOCAL_RUNS_DIR / "keys" / "model_signing.key",
        wbs_runs_dir=LOCAL_RUNS_DIR / "runs",
    )


def build_server(environ: Mapping[str, str]) -> FastMCP:
    """The PARS MCP server over the configured prepopulated database.

    Does not call ``initialize_database()``, so the database is never regenerated.
    """
    settings = build_settings(check_database(environ.get(ENV_DATABASE)))
    mcp = FastMCP(
        SERVER_NAME, instructions=SERVER_INSTRUCTIONS, mask_error_details=True
    )
    register_tools(mcp, settings)
    return mcp


def main() -> None:
    try:
        server = build_server(os.environ)
    except LauncherConfigError as exc:
        print(f"PARS stadium launcher refused to start: {exc}", file=sys.stderr)
        sys.exit(2)
    server.run(show_banner=False)


if __name__ == "__main__":
    main()
