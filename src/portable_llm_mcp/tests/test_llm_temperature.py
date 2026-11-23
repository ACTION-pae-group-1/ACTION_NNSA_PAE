from __future__ import annotations

import json

import httpx
import pytest

from portable_llm_mcp import LLMProvider, LLMSettings, OpenAICompatibleLLMClient


def _settings() -> LLMSettings:
    return LLMSettings(
        LLMProvider.ASKSAGE,
        "gpt-5.4-gov",
        "gpt-5.4-gov",
        "https://api.nnsa.asksage.ai/server/openai/v1",
        api_key="k",  # pragma: allowlist secret
    )


def _capturing_handler(seen: dict) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "ok"}}]})

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_temperature_is_sent_when_requested() -> None:
    seen: dict = {}
    async with httpx.AsyncClient(transport=_capturing_handler(seen)) as http:
        client = OpenAICompatibleLLMClient(_settings(), http_client=http)
        text = await client.chat(
            messages=[{"role": "user", "content": "hi"}],
            model="gpt-5.4-gov",
            temperature=0.0,
        )
    assert text == "ok"
    assert seen["temperature"] == 0.0


@pytest.mark.asyncio
async def test_temperature_is_omitted_by_default() -> None:
    seen: dict = {}
    async with httpx.AsyncClient(transport=_capturing_handler(seen)) as http:
        client = OpenAICompatibleLLMClient(_settings(), http_client=http)
        await client.chat(messages=[{"role": "user", "content": "hi"}], model="m")
    assert "temperature" not in seen
