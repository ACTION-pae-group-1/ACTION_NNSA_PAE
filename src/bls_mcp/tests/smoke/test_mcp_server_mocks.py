import pytest

from bls_mcp.server import create_server


@pytest.mark.asyncio
async def test_mcp_server_starts_with_mocks_enabled(monkeypatch, tmp_path):
    registry = tmp_path / "snapshots"
    registry.mkdir()

    monkeypatch.setenv("BLS_SNAPSHOT_REGISTRY_DIR", str(registry))
    monkeypatch.setenv("MOCK_BLS_DATA", "true")
    monkeypatch.setenv("MOCK_DATABRICKS", "true")
    monkeypatch.setenv("MOCK_IBM", "true")

    mcp = create_server()

    assert mcp is not None
    assert mcp.name == "BLS Cost Escalation"
