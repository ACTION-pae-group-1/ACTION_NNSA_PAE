"""Offline tests for Ask Sage evaluation configuration."""

import pytest

from eval.asksage.eval_asksage_mcp import CASES, MODELS, resolve_mcp_config


def test_default_registry_exists(monkeypatch):
    monkeypatch.delenv("MCP_SERVERS_FILE", raising=False)

    path = resolve_mcp_config()

    assert path.is_file()
    assert path.name == "mcp_servers_test.json"


def test_explicit_registry_path(tmp_path):
    registry = tmp_path / "servers.json"
    registry.write_text("{}", encoding="utf-8")

    assert resolve_mcp_config(str(registry)) == registry.resolve()


def test_missing_registry_is_rejected(tmp_path):
    with pytest.raises(FileNotFoundError, match="configuration not found"):
        resolve_mcp_config(str(tmp_path / "missing.json"))


def test_evaluation_cases_and_models_are_defined():
    assert MODELS
    assert all(model.endswith("-gov") for model in MODELS)
    assert {"steel", "concrete", "labor"} <= {name for name, _ in CASES}
