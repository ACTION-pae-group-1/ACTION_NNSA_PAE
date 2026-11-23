"""Exercise the Python smoke workflow through a real MCP client."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from fastmcp import Client, FastMCP

from bls_mcp.config import Settings
from bls_mcp.server import create_server
from bls_mcp.smoke import check_server, main
from bls_mcp.tests.harness_duckdb import FIXTURE_PC_SERIES, build_registry


@pytest.mark.asyncio
async def test_smoke_workflow_has_no_upstream_calls(tmp_path: Path, capsys):
    requests = []

    def unexpected(request):
        requests.append(request)
        return httpx.Response(500)

    registry = build_registry(tmp_path)
    server = create_server(
        Settings(
            BLS_SNAPSHOT_REGISTRY_DIR=str(registry),
            BLS_SPECS_DB_PATH=str(tmp_path / "specs.duckdb"),
            BLS_API_KEY=None,
        ),
        http_transport=httpx.MockTransport(unexpected),
    )
    await check_server(Client(server))
    assert not requests
    out = capsys.readouterr().out
    assert "110 / 100 = 1.1" in out
    assert f"PASS snapshot catalog: found series {FIXTURE_PC_SERIES}" in out


def test_main_in_process_reports_missing_setup(monkeypatch, tmp_path, capsys):
    """Without .env or a snapshot, --in-process fails with a setup hint."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BLS_SNAPSHOT_REGISTRY_DIR", raising=False)
    monkeypatch.setattr("sys.argv", ["smoke", "--in-process"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    assert "QUICKSTART.md step 2" in capsys.readouterr().out


def test_main_in_process_passes_on_a_built_snapshot(monkeypatch, tmp_path, capsys):
    registry = build_registry(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BLS_SNAPSHOT_REGISTRY_DIR", str(registry))
    monkeypatch.setenv("BLS_SPECS_DB_PATH", str(tmp_path / "specs.duckdb"))
    monkeypatch.setattr("sys.argv", ["smoke", "--in-process"])
    main()
    assert "PASS smoke check complete" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_smoke_rejects_unrelated_server():
    with pytest.raises(ValueError, match="Required smoke-test tools are missing"):
        await check_server(Client(FastMCP("Unrelated server")))


@pytest.mark.parametrize(
    "argv",
    [
        ["--url", "http://example.com/mcp"],
        ["--url", "http://user:secret@127.0.0.1:8000/mcp"],  # pragma: allowlist secret
        ["--timeout", "0"],
        ["--timeout", "nan"],
    ],
)
def test_main_rejects_invalid_local_url_and_timeout(monkeypatch, argv):
    monkeypatch.setattr("sys.argv", ["smoke", *argv])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 2
