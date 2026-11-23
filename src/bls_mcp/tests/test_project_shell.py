"""Verify launch contracts and HTTP probes without live BLS calls."""

from pathlib import Path
from unittest.mock import Mock

import httpx
import pytest
from starlette.testclient import TestClient

from bls_mcp import __version__, app
from bls_mcp.config import Settings
from bls_mcp.server import create_server
from bls_mcp.tests.harness_duckdb import build_registry


@pytest.mark.parametrize(
    ("environment", "expected"),
    [
        ({}, {"transport": "stdio"}),
        (
            {"MCP_TRANSPORT": "streamable-http", "MCP_PORT": "8123"},
            {"transport": "http", "host": "127.0.0.1", "port": 8123},
        ),
        (
            {"PORT": "8080", "MCP_TRANSPORT": "stdio"},
            {"transport": "http", "host": "0.0.0.0", "port": 8080},
        ),
        (
            {"PORT": "8080", "DATABRICKS_APP_PORT": "9000"},
            {"transport": "http", "host": "0.0.0.0", "port": 9000},
        ),
    ],
)
def test_transport_precedence(monkeypatch, tmp_path, environment, expected):
    monkeypatch.chdir(tmp_path)
    for key in (
        "PORT",
        "DATABRICKS_APP_PORT",
        "MCP_TRANSPORT",
        "MCP_HOST",
        "MCP_PORT",
    ):
        monkeypatch.delenv(key, raising=False)
    for key, value in environment.items():
        monkeypatch.setenv(key, value)
    server = Mock()
    monkeypatch.setattr(app, "create_server", lambda: server)
    app.main()
    server.run.assert_called_once_with(**expected)


@pytest.mark.parametrize("port", ["0", "65536", "not-a-port"])
def test_invalid_platform_port_never_starts(monkeypatch, tmp_path, port):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABRICKS_APP_PORT", raising=False)
    monkeypatch.setenv("PORT", port)
    factory = Mock()
    monkeypatch.setattr(app, "create_server", factory)
    with pytest.raises(ValueError):
        app.main()
    factory.assert_not_called()


def test_dotenv_with_environment_override(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("MCP_TRANSPORT", raising=False)
    monkeypatch.delenv("BLS_SPECS_DB_PATH", raising=False)
    registry = build_registry(tmp_path)
    (tmp_path / ".env").write_text(
        f"MCP_TRANSPORT=streamable-http\n"
        f"BLS_SPECS_DB_PATH=from-file.db\n"
        f"BLS_SNAPSHOT_REGISTRY_DIR={registry}\n"
    )
    assert app.LaunchSettings().mcp_transport == "streamable-http"
    assert Settings().specs_db_path == "from-file.db"
    monkeypatch.setenv("BLS_SPECS_DB_PATH", "from-environment.db")
    assert Settings().specs_db_path == "from-environment.db"


def test_http_probes(tmp_path: Path):
    registry = build_registry(tmp_path)
    server = create_server(
        Settings(
            BLS_SNAPSHOT_REGISTRY_DIR=str(registry),
            BLS_SPECS_DB_PATH=str(tmp_path / "specs.duckdb"),
        ),
        http_transport=httpx.MockTransport(lambda request: httpx.Response(500)),
    )
    with TestClient(server.http_app()) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "healthy",
            "service": "bls-escalation-mcp",
        }
        response = client.get("/version")
        assert response.status_code == 200
        assert response.json() == {"version": __version__}
