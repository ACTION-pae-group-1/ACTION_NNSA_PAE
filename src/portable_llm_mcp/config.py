"""Explicit, environment-based LLM provider configuration."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum


class LLMConfigError(ValueError):
    """Invalid or incomplete provider settings."""


class LLMProvider(str, Enum):
    OLLAMA = "ollama"
    ASKSAGE = "asksage"
    OPENAI = "openai"
    BEDROCK = "bedrock"


ASKSAGE_URL = "https://api.nnsa.asksage.ai/server/openai/v1"
OLLAMA_URLS = frozenset({"http://127.0.0.1:11434/v1", "http://localhost:11434/v1"})

# Ask Sage default model when LLM_CHAT_MODEL is not set.
ASKSAGE_DEFAULT_MODEL = "gpt-5.4-gov"
# Used by the Phoenix judge guard (eval/phoenix/llm_endpoint.py). load_llm_settings
# no longer enforces this suffix for the chat model.
ASKSAGE_MODEL_SUFFIX = "-gov"


@dataclass(frozen=True)
class LLMSettings:
    provider: LLMProvider
    chat_model: str
    vision_model: str
    base_url: str | None = None
    api_key: str | None = None
    auth_header: str = "authorization"
    aws_region: str | None = None
    request_timeout: float = 90.0


def load_llm_settings(env: Mapping[str, str] | None = None) -> LLMSettings:
    """Read config without touching external services or requiring secret files."""
    values = os.environ if env is None else env

    def get(name: str, default: str = "") -> str:
        return (values.get(name) or "").strip() or default

    try:
        provider = LLMProvider(get("LLM_PROVIDER", "ollama").lower())
    except ValueError as exc:
        raise LLMConfigError("Unsupported LLM_PROVIDER") from exc

    defaults = {
        LLMProvider.OLLAMA: "http://127.0.0.1:11434/v1",
        LLMProvider.ASKSAGE: ASKSAGE_URL,
        LLMProvider.OPENAI: ASKSAGE_URL,
    }
    model_defaults = {
        LLMProvider.OLLAMA: "gemma4:12b-mtp:latest",
        LLMProvider.ASKSAGE: ASKSAGE_DEFAULT_MODEL,
        LLMProvider.OPENAI: ASKSAGE_DEFAULT_MODEL,
    }
    model_default = model_defaults.get(provider, "")
    vision_default = (
        "gemma4-26b-claude:latest" if provider is LLMProvider.OLLAMA else ""
    )
    base_url = get("LLM_BASE_URL", defaults.get(provider, "")) or None
    fallback_key = (
        "ASKSAGE_API_KEY"
        if provider in (LLMProvider.ASKSAGE, LLMProvider.OPENAI)
        else None
    )
    api_key = get("LLM_API_KEY") or (get(fallback_key) if fallback_key else "")
    if provider is LLMProvider.OLLAMA and not api_key:
        api_key = "ollama"  # pragma: allowlist secret
    if provider in (LLMProvider.ASKSAGE, LLMProvider.OPENAI) and not api_key:
        raise LLMConfigError("LLM_API_KEY is required for this provider")
    if base_url and not base_url.startswith(("https://", "http://")):
        raise LLMConfigError("LLM_BASE_URL must be an HTTP(S) URL")
    if (
        provider in (LLMProvider.ASKSAGE, LLMProvider.OPENAI)
        and base_url != ASKSAGE_URL
    ):
        raise LLMConfigError("LLM_BASE_URL must be the approved NNSA Ask Sage endpoint")
    if provider is LLMProvider.OLLAMA:
        if base_url not in OLLAMA_URLS:
            raise LLMConfigError("Ollama must use the local endpoint on port 11434")
        if get("OLLAMA_NO_CLOUD") != "1":
            raise LLMConfigError("OLLAMA_NO_CLOUD=1 is required for Ollama")
    if provider is not LLMProvider.BEDROCK and not base_url:
        raise LLMConfigError("LLM_BASE_URL is required")

    chat_model = get("LLM_CHAT_MODEL", model_default)
    vision_model = get("LLM_VISION_MODEL", vision_default or chat_model)
    if not chat_model:
        raise LLMConfigError("LLM_CHAT_MODEL is required")
    if not vision_model:
        vision_model = chat_model
    if provider is LLMProvider.OLLAMA:
        for name in (chat_model, vision_model):
            parts = name.lower().replace("-", ":").replace("_", ":").split(":")
            if "cloud" in parts:
                raise LLMConfigError("Ollama cloud models are not permitted")
    if provider in (LLMProvider.ASKSAGE, LLMProvider.OPENAI):
        for name in (chat_model, vision_model):
            if not name.endswith(ASKSAGE_MODEL_SUFFIX):
                raise LLMConfigError("Ask Sage models must end in -gov")

    auth_header = get("LLM_AUTH_HEADER", "authorization").lower()
    if auth_header not in {"authorization", "x-access-tokens", "x-api-key"}:
        raise LLMConfigError("Unsupported LLM_AUTH_HEADER")
    try:
        timeout = float(get("LLM_TIMEOUT_SECONDS", "90"))
    except ValueError as exc:
        raise LLMConfigError("LLM_TIMEOUT_SECONDS must be numeric") from exc
    if not 0 < timeout <= 600:
        raise LLMConfigError("LLM_TIMEOUT_SECONDS must be between 0 and 600")
    return LLMSettings(
        provider=provider,
        chat_model=chat_model,
        vision_model=vision_model,
        base_url=base_url,
        api_key=api_key,
        auth_header=auth_header,
        aws_region=get("AWS_REGION", "us-gov-west-1")
        if provider is LLMProvider.BEDROCK
        else None,
        request_timeout=timeout,
    )
