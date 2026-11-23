"""The application-side PARS launcher: refusals, tool registration, no regeneration.

Each test builds its own throwaway synthetic database in a temporary directory with
the protected PARS initializer. The protected PARS data file is never opened.
"""

import asyncio
import hashlib
import json
from pathlib import Path

import pytest
from fastmcp import Client

from cost_intel_app import pars_launcher as launcher
from pars_local_mcp.storage.initialization import initialize_database

REPO = Path(__file__).resolve().parents[3]
ALLOWLIST = json.loads((REPO / "src" / "mcp_servers.json").read_text())["servers"][
    "pars_mcp"
]["allowed_tools"]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture()
def stadium_db(tmp_path):
    """A synthetic, marked PARS database created outside the protected directory."""
    path = tmp_path / "stadium_test.duckdb"
    initialize_database(path, synthetic_root=tmp_path)
    return path


def test_unset_database_is_refused():
    with pytest.raises(launcher.LauncherConfigError, match="not set"):
        launcher.check_database("")


def test_missing_database_is_refused(tmp_path):
    with pytest.raises(launcher.LauncherConfigError, match="not found"):
        launcher.check_database(str(tmp_path / "absent.duckdb"))


def test_protected_pars_data_file_is_refused():
    protected = launcher.PROTECTED_DATA_DIR / "wbs.duckdb"
    with pytest.raises(launcher.LauncherConfigError, match="protected"):
        launcher.check_database(str(protected))


def test_directory_inside_protected_data_is_refused():
    with pytest.raises(launcher.LauncherConfigError, match="protected"):
        launcher.check_database(str(launcher.PROTECTED_DATA_DIR))


def test_database_without_synthetic_marker_is_refused(tmp_path):
    import duckdb

    path = tmp_path / "unmarked.duckdb"
    con = duckdb.connect(str(path))
    con.execute("CREATE TABLE pars_synthetic_marker AS SELECT 'real' AS marker")
    for table in ("projects", "wbs_elements", "labeled_wbs"):
        con.execute(f"CREATE TABLE {table} (x INTEGER)")
    con.close()
    with pytest.raises(launcher.LauncherConfigError, match="not marked synthetic"):
        launcher.check_database(str(path))


def test_database_missing_pars_tables_is_refused(tmp_path):
    import duckdb

    path = tmp_path / "empty_marker.duckdb"
    con = duckdb.connect(str(path))
    con.execute("CREATE TABLE pars_synthetic_marker AS SELECT 'synthetic' AS marker")
    con.close()
    with pytest.raises(launcher.LauncherConfigError, match="missing PARS tables"):
        launcher.check_database(str(path))


def test_valid_database_is_accepted(stadium_db):
    assert launcher.check_database(str(stadium_db)) == stadium_db.resolve()


def test_launcher_registers_the_sixteen_allowlisted_tools(stadium_db):
    server = launcher.build_server({"PARS_STADIUM_DB": str(stadium_db)})

    async def names():
        async with Client(server) as client:
            return {tool.name for tool in await client.list_tools()}

    registered = asyncio.run(names())
    assert len(registered) == 16
    assert registered == set(ALLOWLIST)


def test_database_is_not_regenerated_by_repeated_starts(stadium_db):
    before = _sha(stadium_db)
    for _ in range(2):
        launcher.build_server({"PARS_STADIUM_DB": str(stadium_db)})
    assert _sha(stadium_db) == before


def test_read_call_leaves_the_database_unchanged(stadium_db):
    before = _sha(stadium_db)
    server = launcher.build_server({"PARS_STADIUM_DB": str(stadium_db)})

    async def read_projects():
        async with Client(server) as client:
            return await client.call_tool("list_projects", {})

    result = asyncio.run(read_projects())
    assert result is not None
    assert _sha(stadium_db) == before


def test_invalid_configuration_never_builds_a_server(tmp_path):
    with pytest.raises(launcher.LauncherConfigError):
        launcher.build_server({"PARS_STADIUM_DB": str(tmp_path / "nope.duckdb")})
