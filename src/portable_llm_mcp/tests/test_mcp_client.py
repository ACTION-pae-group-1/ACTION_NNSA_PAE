"""Tests for MCP server manifest loading and startup error reporting."""

import json

import pytest

from portable_llm_mcp.mcp_client import (
    MCPConfigurationError,
    MCPServerStartError,
    load_mcp_servers,
)


def _write_manifest(tmp_path, servers):
    path = tmp_path / "mcp_servers.json"
    path.write_text(json.dumps({"servers": servers}), encoding="utf-8")
    return path


def test_loads_stdio_server_with_expanded_args(tmp_path):
    path = _write_manifest(
        tmp_path,
        {
            "pars": {
                "command": "python",
                "args": ["-m", "${MODULE}"],
                "allowed_tools": ["list_projects"],
            }
        },
    )
    servers = load_mcp_servers(path, environment={"MODULE": "pars.server"})
    config = servers["pars"]
    assert config.transport == "stdio"
    assert config.command == "python"
    assert config.args == ("-m", "pars.server")
    assert config.allowed_tools == ("list_projects",)
    assert config.env is None


def test_undefined_variable_is_refused(tmp_path):
    path = _write_manifest(
        tmp_path, {"pars": {"command": "python", "args": ["${MISSING}"]}}
    )
    with pytest.raises(MCPConfigurationError, match="Missing environment variable"):
        load_mcp_servers(path, environment={})


def test_invalid_server_name_is_refused(tmp_path):
    path = _write_manifest(tmp_path, {"bad name!": {"command": "python"}})
    with pytest.raises(MCPConfigurationError, match="Invalid MCP server name"):
        load_mcp_servers(path, environment={})


def test_stdio_server_requires_a_command(tmp_path):
    path = _write_manifest(tmp_path, {"pars": {"args": []}})
    with pytest.raises(MCPConfigurationError, match="command required"):
        load_mcp_servers(path, environment={})


def test_unsupported_transport_is_refused(tmp_path):
    path = _write_manifest(tmp_path, {"pars": {"transport": "carrier_pigeon"}})
    with pytest.raises(MCPConfigurationError, match="unsupported transport"):
        load_mcp_servers(path, environment={})


def test_unreadable_manifest_raises_configuration_error(tmp_path):
    with pytest.raises(MCPConfigurationError, match="Cannot read MCP server"):
        load_mcp_servers(tmp_path / "absent.json", environment={})


def test_start_error_names_server_without_leaking_cause_text():
    error = MCPServerStartError("pars", "FileNotFoundError")
    assert error.server == "pars"
    assert error.error_type == "FileNotFoundError"
    assert str(error) == "MCP server 'pars' failed to start (FileNotFoundError)"
