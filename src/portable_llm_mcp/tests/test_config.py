from __future__ import annotations

import json

import pytest

from portable_llm_mcp import (
    LLMConfigError,
    LLMProvider,
    MCPConfigurationError,
    load_llm_settings,
    load_mcp_servers,
)


def test_local_ollama_defaults() -> None:
    settings = load_llm_settings({"LLM_PROVIDER": "ollama", "OLLAMA_NO_CLOUD": "1"})
    assert settings.provider is LLMProvider.OLLAMA
    assert settings.base_url == "http://127.0.0.1:11434/v1"
    assert settings.api_key == "ollama"  # pragma: allowlist secret


def test_asksage_can_select_non_bearer_header() -> None:
    settings = load_llm_settings(
        {
            "LLM_PROVIDER": "asksage",
            "LLM_API_KEY": "test-token",  # pragma: allowlist secret
            "LLM_CHAT_MODEL": "approved-model-gov",
            "LLM_AUTH_HEADER": "x-access-tokens",
        }
    )
    assert settings.auth_header == "x-access-tokens"


def test_asksage_accepts_legacy_api_key_name() -> None:
    settings = load_llm_settings(
        {
            "LLM_PROVIDER": "asksage",
            "ASKSAGE_API_KEY": "legacy",  # pragma: allowlist secret
            "LLM_CHAT_MODEL": "approved-model-gov",
        }
    )
    assert settings.api_key == "legacy"  # pragma: allowlist secret


def test_provider_without_key_is_rejected() -> None:
    with pytest.raises(LLMConfigError, match="LLM_API_KEY"):
        load_llm_settings({"LLM_PROVIDER": "asksage", "LLM_CHAT_MODEL": "m"})


def test_bedrock_needs_no_api_key() -> None:
    settings = load_llm_settings(
        {
            "LLM_PROVIDER": "bedrock",
            "LLM_CHAT_MODEL": "test-model",
            "AWS_REGION": "us-gov-east-1",
        }
    )
    assert settings.aws_region == "us-gov-east-1"
    assert settings.base_url is None


def test_asksage_defaults_to_approved_gov_model() -> None:
    settings = load_llm_settings({"LLM_PROVIDER": "asksage", "LLM_API_KEY": "k"})
    assert settings.chat_model == "gpt-5.4-gov"
    assert settings.vision_model == "gpt-5.4-gov"
    assert settings.base_url == "https://api.nnsa.asksage.ai/server/openai/v1"


@pytest.mark.parametrize(
    "base_url",
    [
        "https://api.openai.com/v1",
        "https://api.anthropic.com/v1",
        "https://api.nnsa.asksage.ai.evil.example/server/openai/v1",
    ],
)
def test_asksage_rejects_unapproved_hosts(base_url: str) -> None:
    with pytest.raises(LLMConfigError, match="approved NNSA Ask Sage endpoint"):
        load_llm_settings(
            {"LLM_PROVIDER": "asksage", "LLM_API_KEY": "k", "LLM_BASE_URL": base_url}
        )


def test_ollama_remote_host_rejected() -> None:
    with pytest.raises(LLMConfigError, match="local endpoint"):
        load_llm_settings(
            {
                "LLM_PROVIDER": "ollama",
                "OLLAMA_NO_CLOUD": "1",
                "LLM_BASE_URL": "http://10.0.0.5:11434/v1",
            }
        )


def test_openai_provider_routes_to_nnsa_asksage() -> None:
    settings = load_llm_settings(
        {
            "LLM_PROVIDER": "openai",
            "LLM_API_KEY": "test-token",  # pragma: allowlist secret
        }
    )
    assert settings.provider is LLMProvider.OPENAI
    assert settings.base_url == "https://api.nnsa.asksage.ai/server/openai/v1"
    assert settings.chat_model.endswith("-gov")


@pytest.mark.parametrize("provider", ["asksage", "openai"])
@pytest.mark.parametrize(
    "base_url",
    [
        "https://api.openai.com/v1",
        "https://api.nnsa.asksage.ai/other/v1",
        "http://api.nnsa.asksage.ai/server/openai/v1",
        "https://api.nnsa.asksage.ai/server/openai/v1?redirect=1",
        "https://api.nnsa.asksage.ai:8443/server/openai/v1",
    ],
)
def test_external_provider_requires_exact_nnsa_endpoint(
    provider: str, base_url: str
) -> None:
    with pytest.raises(LLMConfigError, match="approved NNSA Ask Sage endpoint"):
        load_llm_settings(
            {
                "LLM_PROVIDER": provider,
                "LLM_API_KEY": "test-token",  # pragma: allowlist secret
                "LLM_BASE_URL": base_url,
            }
        )


def test_ollama_requires_no_cloud_setting() -> None:
    with pytest.raises(LLMConfigError, match="OLLAMA_NO_CLOUD=1"):
        load_llm_settings({"LLM_PROVIDER": "ollama"})


@pytest.mark.parametrize("model", ["some-model:cloud", "gpt-oss:120b-cloud"])
def test_ollama_rejects_cloud_models(model: str) -> None:
    with pytest.raises(LLMConfigError, match="cloud models"):
        load_llm_settings(
            {
                "LLM_PROVIDER": "ollama",
                "OLLAMA_NO_CLOUD": "1",
                "LLM_CHAT_MODEL": model,
            }
        )


def test_mcp_allowlist_and_secret_expansion(tmp_path) -> None:
    config = tmp_path / "mcp.json"
    config.write_text(
        json.dumps(
            {
                "servers": {
                    "internal": {
                        "transport": "streamable_http",
                        "url": "https://host.example/mcp",
                        "allowed_tools": ["search"],
                        "headers": {"Authorization": "Bearer ${MCP_TOKEN}"},
                    }
                }
            }
        )
    )
    servers = load_mcp_servers(config, environment={"MCP_TOKEN": "secret"})
    assert servers["internal"].allowed_tools == ("search",)
    assert servers["internal"].headers == {"Authorization": "Bearer secret"}


def test_missing_mcp_secret_fails_closed(tmp_path) -> None:
    config = tmp_path / "mcp.json"
    config.write_text(
        json.dumps(
            {
                "servers": {
                    "internal": {
                        "transport": "streamable_http",
                        "url": "https://host.example/mcp",
                        "headers": {"Authorization": "Bearer ${MISSING}"},
                    }
                }
            }
        )
    )
    with pytest.raises(MCPConfigurationError, match="MISSING"):
        load_mcp_servers(config, environment={})


def test_mcp_invalid_transport_rejected(tmp_path) -> None:
    config = tmp_path / "mcp.json"
    config.write_text(json.dumps({"servers": {"bad": {"transport": "sse"}}}))
    with pytest.raises(MCPConfigurationError, match="unsupported transport"):
        load_mcp_servers(config)


@pytest.mark.parametrize("model", ["gpt-5.5", "gpt-4.1", "claude-sonnet-5-5"])
def test_asksage_rejects_models_not_ending_in_gov(model: str) -> None:
    with pytest.raises(LLMConfigError, match="-gov"):
        load_llm_settings(
            {"LLM_PROVIDER": "asksage", "LLM_API_KEY": "k", "LLM_CHAT_MODEL": model}
        )


def test_asksage_rejects_non_gov_vision_model() -> None:
    with pytest.raises(LLMConfigError, match="-gov"):
        load_llm_settings(
            {
                "LLM_PROVIDER": "asksage",
                "LLM_API_KEY": "k",
                "LLM_VISION_MODEL": "gpt-5.5",
            }
        )
