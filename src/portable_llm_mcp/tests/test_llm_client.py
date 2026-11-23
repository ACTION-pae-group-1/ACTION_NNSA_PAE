from __future__ import annotations

import json

import httpx
import pytest

from portable_llm_mcp import (
    BedrockLLMClient,
    LLMProvider,
    LLMResponseError,
    LLMSettings,
    LLMUnavailableError,
    OpenAICompatibleLLMClient,
)


@pytest.mark.asyncio
async def test_custom_header_has_no_extra_authorization() -> None:
    observed = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed.update(dict(request.headers))
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "hello"}}]}
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    settings = LLMSettings(
        LLMProvider.ASKSAGE,
        "m",
        "m",
        "https://api.nnsa.asksage.ai/server/openai/v1",
        api_key="secret",  # pragma: allowlist secret
        auth_header="x-access-tokens",
    )
    client = OpenAICompatibleLLMClient(settings, http_client=http)
    assert (
        await client.chat(messages=[{"role": "user", "content": "hi"}], model="m")
        == "hello"
    )
    assert observed["x-access-tokens"] == "secret"
    assert "authorization" not in observed
    await http.aclose()


@pytest.mark.asyncio
async def test_bearer_tool_calls_round_trip() -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "tc-1",
                                    "type": "function",
                                    "function": {
                                        "name": "demo__echo",
                                        "arguments": '{"message":"hello"}',
                                    },
                                }
                            ],
                        }
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = OpenAICompatibleLLMClient(
            LLMSettings(
                LLMProvider.ASKSAGE,
                "m",
                "m",
                "https://api.nnsa.asksage.ai/server/openai/v1",
                "token",
            ),
            http_client=http,
        )
        result = await client.complete(
            messages=[{"role": "user", "content": "echo hello"}],
            model="m",
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "demo__echo",
                        "parameters": {"type": "object"},
                    },
                }
            ],
        )
        assert result.tool_calls[0].arguments == {"message": "hello"}
        assert seen["tools"][0]["function"]["name"] == "demo__echo"


@pytest.mark.asyncio
async def test_non_object_tool_arguments_rejected() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "tool_calls": [
                                {
                                    "id": "t",
                                    "function": {"name": "echo", "arguments": "[]"},
                                }
                            ]
                        }
                    }
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = OpenAICompatibleLLMClient(
            LLMSettings(
                LLMProvider.ASKSAGE,
                "m",
                "m",
                "https://api.nnsa.asksage.ai/server/openai/v1",
                "secret",
            ),
            http_client=http,
        )
        with pytest.raises(LLMResponseError):
            await client.complete(
                messages=[{"role": "user", "content": "x"}], model="m"
            )


@pytest.mark.asyncio
async def test_http_error_does_not_leak_response_body() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="sensitive-internal-diagnostics")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = OpenAICompatibleLLMClient(
            LLMSettings(
                LLMProvider.ASKSAGE,
                "m",
                "m",
                "https://api.nnsa.asksage.ai/server/openai/v1",
                "secret",
            ),
            http_client=http,
        )
        with pytest.raises(LLMUnavailableError) as error:
            await client.complete(
                messages=[{"role": "user", "content": "x"}], model="m"
            )
        assert "sensitive-internal-diagnostics" not in str(error.value)


@pytest.mark.asyncio
async def test_http_status_code_is_exposed_for_guidance() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="private-body")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = OpenAICompatibleLLMClient(
            LLMSettings(
                LLMProvider.ASKSAGE,
                "m",
                "m",
                "https://api.nnsa.asksage.ai/server/openai/v1",
                "secret",
            ),
            http_client=http,
        )
        with pytest.raises(LLMUnavailableError) as error:
            await client.complete(
                messages=[{"role": "user", "content": "x"}], model="m"
            )
    assert error.value.status_code == 401
    assert error.value.error_type == "HTTPStatusError"
    assert "private-body" not in str(error.value)


class FakeRuntime:
    def __init__(self):
        self.kwargs = None

    def converse(self, **kwargs):
        self.kwargs = kwargs
        return {
            "output": {
                "message": {
                    "content": [
                        {
                            "toolUse": {
                                "toolUseId": "b-1",
                                "name": "demo__echo",
                                "input": {"message": "hello"},
                            }
                        }
                    ]
                }
            }
        }


@pytest.mark.asyncio
async def test_bedrock_converse_maps_tool_schema_and_tool_use() -> None:
    runtime = FakeRuntime()
    client = BedrockLLMClient(
        LLMSettings(LLMProvider.BEDROCK, "bedrock", "bedrock"), runtime=runtime
    )
    result = await client.complete(
        model="bedrock",
        messages=[{"role": "user", "content": "echo"}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "demo__echo",
                    "description": "echo",
                    "parameters": {"type": "object"},
                },
            }
        ],
    )
    assert result.tool_calls[0].name == "demo__echo"
    assert runtime.kwargs["toolConfig"]["tools"][0]["toolSpec"]["name"] == "demo__echo"


@pytest.mark.asyncio
async def test_nnsa_request_does_not_follow_redirects() -> None:
    visited = []

    def handler(request: httpx.Request) -> httpx.Response:
        visited.append(str(request.url))
        return httpx.Response(
            307, headers={"Location": "https://api.openai.com/v1/chat/completions"}
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=True
    ) as http:
        client = OpenAICompatibleLLMClient(
            LLMSettings(
                LLMProvider.OPENAI,
                "test-model-gov",
                "test-model-gov",
                "https://api.nnsa.asksage.ai/server/openai/v1",
                "test-token",
            ),
            http_client=http,
        )
        with pytest.raises(LLMUnavailableError, match="redirected"):
            await client.chat(
                messages=[{"role": "user", "content": "test"}],
                model="test-model-gov",
            )
    assert visited == ["https://api.nnsa.asksage.ai/server/openai/v1/chat/completions"]


def test_manual_openai_settings_cannot_use_public_endpoint() -> None:
    with pytest.raises(ValueError, match="NNSA Ask Sage"):
        OpenAICompatibleLLMClient(
            LLMSettings(
                LLMProvider.OPENAI,
                "test-model-gov",
                "test-model-gov",
                "https://api.openai.com/v1",
                "test-token",
            )
        )
