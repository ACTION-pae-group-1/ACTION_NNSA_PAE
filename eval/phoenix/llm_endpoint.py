"""Approved LLM endpoint for the PARS eval harness.

Every model call in the eval (agent and judges) goes through the portable client
configuration in src/portable_llm_mcp. Only endpoints approved there can be used
(Ask Sage and local Ollama); anything else fails when the configuration loads.
Each run records the provider, endpoint host, and model it used.
"""

from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

EVAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVAL_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from portable_llm_mcp import (  # noqa: E402
    LLMConfigError,
    LLMProvider,
    LLMSettings,
    OpenAICompatibleLLMClient,
    create_llm_client,
    load_llm_settings,
)
from portable_llm_mcp.config import ASKSAGE_MODEL_SUFFIX  # noqa: E402

PORTABLE_ENV = REPO_ROOT / "src" / "portable_llm_mcp" / ".env"
EVAL_PROVIDERS = (LLMProvider.ASKSAGE, LLMProvider.OLLAMA)


class JudgeError(RuntimeError):
    """A judge produced no usable verdict."""


@dataclass(frozen=True)
class EndpointInfo:
    provider: str
    host: str
    model: str

    @property
    def label(self) -> str:
        return f"{self.provider}@{self.host}"


def approved_settings() -> LLMSettings:
    """Load the approved LLM settings.

    Raises LLMConfigError for unapproved endpoints.
    """
    load_dotenv(PORTABLE_ENV, override=False)
    settings = load_llm_settings(os.environ)
    if settings.provider not in EVAL_PROVIDERS:
        raise LLMConfigError("The eval allows only Ask Sage or local Ollama endpoints")
    return settings


def _host(settings: LLMSettings) -> str:
    return (urlsplit(settings.base_url or "").hostname or "").lower()


def endpoint_info(settings: LLMSettings) -> EndpointInfo:
    return EndpointInfo(
        provider=settings.provider.value,
        host=_host(settings),
        model=settings.chat_model,
    )


def judge_model(settings: LLMSettings) -> str:
    name = os.getenv("JUDGE_MODEL") or settings.chat_model
    if settings.provider is LLMProvider.ASKSAGE and not name.endswith(
        ASKSAGE_MODEL_SUFFIX
    ):
        raise JudgeError("JUDGE_MODEL must be an Ask Sage -gov model")
    return name


def judge_endpoint() -> EndpointInfo:
    settings = approved_settings()
    return EndpointInfo(
        provider=settings.provider.value,
        host=_host(settings),
        model=judge_model(settings),
    )


class TemperatureClient:
    """Pins temperature on every completion. MCPAgent does not pass one."""

    def __init__(self, inner: OpenAICompatibleLLMClient, temperature: float) -> None:
        self.inner = inner
        self.temperature = temperature

    async def complete(self, *, messages, model, tools=None):
        return await self.inner.complete(
            messages=messages,
            model=model,
            tools=tools,
            temperature=self.temperature,
        )

    async def aclose(self) -> None:
        await self.inner.aclose()


def build_llm(settings: LLMSettings, *, temperature: float) -> TemperatureClient:
    client = create_llm_client(settings)
    if not isinstance(client, OpenAICompatibleLLMClient):
        raise RuntimeError("The eval requires the OpenAI-compatible client")
    return TemperatureClient(client, temperature)


async def _judge_call(settings: LLMSettings, model: str, prompt: str) -> str:
    client = OpenAICompatibleLLMClient(settings)
    try:
        return await client.chat(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            temperature=0.0,
        )
    finally:
        await client.aclose()


def ask_judge(prompt: str) -> str:
    """Synchronous judge call at temperature 0.

    Run it in a worker thread from async code.
    """
    settings = approved_settings()
    return asyncio.run(_judge_call(settings, judge_model(settings), prompt))


def parse_verdict(text: str, allowed: tuple[str, ...]) -> str:
    """Accept only an exact label. Anything else is a judge failure, not a guess."""
    cleaned = (text or "").strip().strip("\"'`.").strip().lower()
    if cleaned in allowed:
        return cleaned
    raise JudgeError(f"judge returned no valid label: {cleaned[:40]!r}")
