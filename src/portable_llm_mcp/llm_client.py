"""OpenAI-compatible and Bedrock tool-capable adapters.

No hardcoded provider keys, dependencies on an existing app, or network calls at
import time. Model responses are considered untrusted, including tool arguments.
"""

from __future__ import annotations

import asyncio
import base64
import json
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from .config import ASKSAGE_URL, OLLAMA_URLS, LLMProvider, LLMSettings


class LLMResponseError(RuntimeError):
    """Model response was unusable."""


class LLMUnavailableError(RuntimeError):
    """LLM transport/provider failure without revealing private response bodies.

    ``status_code`` (HTTP status) and ``error_type`` (httpx exception class name)
    are safe, non-sensitive diagnostics that callers may map to guidance.
    """

    status_code: int | None = None
    error_type: str | None = None


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class Completion:
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    #: Provider-native content to send back unchanged as this assistant turn.
    #: Callers store it on the assistant message under ``"replay"``. For an
    #: adapter whose reasoning must be replayed verbatim; none of the current
    #: adapters set it, and they ignore the key.
    replay: list[dict[str, Any]] | None = None


#: Message key that carries ``Completion.replay`` on an assistant message.
REPLAY_KEY = "replay"

# OpenAI-compatible message and tool dictionaries, also accepted by Bedrock adapter.
Message = dict[str, Any]
ToolDefinition = dict[str, Any]


class LLMClient(Protocol):
    async def complete(
        self,
        *,
        messages: list[Message],
        model: str,
        tools: list[ToolDefinition] | None = None,
        temperature: float | None = None,
    ) -> Completion: ...

    async def chat(
        self,
        *,
        messages: list[Message],
        model: str,
        temperature: float | None = None,
    ) -> str: ...

    async def vision(self, *, messages: list[Message], model: str) -> str: ...

    async def aclose(self) -> None: ...


class OpenAICompatibleLLMClient:
    """Use HTTP directly so custom authentication never adds a second bearer token."""

    def __init__(
        self,
        settings: LLMSettings,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not settings.base_url:
            raise ValueError("OpenAI-compatible LLM requires base_url")
        if (
            settings.provider in (LLMProvider.OPENAI, LLMProvider.ASKSAGE)
            and settings.base_url != ASKSAGE_URL
        ):
            raise ValueError("LLM endpoint must be NNSA Ask Sage")
        if (
            settings.provider is LLMProvider.OLLAMA
            and settings.base_url not in OLLAMA_URLS
        ):
            raise ValueError("Ollama endpoint must be local")
        self._base_url = settings.base_url
        self.settings = settings
        self._client = http_client or httpx.AsyncClient(
            timeout=settings.request_timeout
        )
        self._owns_client = http_client is None

    async def complete(
        self,
        *,
        messages: list[Message],
        model: str,
        tools: list[ToolDefinition] | None = None,
        temperature: float | None = None,
    ) -> Completion:
        headers = {"Content-Type": "application/json"}
        if self.settings.auth_header == "authorization":
            headers["Authorization"] = f"Bearer {self.settings.api_key or ''}"
        else:
            headers[self.settings.auth_header] = self.settings.api_key or ""
        payload: dict[str, Any] = {
            "model": model,
            # Another provider's replay content is not part of this API.
            "messages": [
                {key: value for key, value in message.items() if key != REPLAY_KEY}
                for message in messages
            ],
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
        if temperature is not None:
            payload["temperature"] = temperature
        try:
            response = await self._client.post(
                f"{self._base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
                follow_redirects=False,
            )
            if response.is_redirect:
                raise LLMUnavailableError("LLM endpoint redirected the request")
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            # Status code only; the body is omitted (it may echo sensitive data).
            status = exc.response.status_code
            error = LLMUnavailableError(f"LLM endpoint returned HTTP {status}")
            error.status_code = status
            error.error_type = type(exc).__name__
            raise error from exc
        except httpx.HTTPError as exc:
            # Deliberately omit server response body and request headers; either
            # could contain classified/sensitive prompts or credentials.
            error = LLMUnavailableError(
                f"LLM HTTP request failed ({type(exc).__name__})"
            )
            error.error_type = type(exc).__name__
            raise error from exc
        try:
            message = response.json()["choices"][0]["message"]
            raw_calls = message.get("tool_calls") or []
            parsed = [
                ToolCall(
                    id=call["id"],
                    name=call["function"]["name"],
                    arguments=json.loads(call["function"]["arguments"]),
                )
                for call in raw_calls
            ]
            if any(not isinstance(call.arguments, dict) for call in parsed):
                raise ValueError("Tool arguments must be a JSON object")
            content = message.get("content")
            if content is not None and not isinstance(content, str):
                raise ValueError("Unsupported content structure")
            return Completion(content=content, tool_calls=parsed)
        except (
            KeyError,
            IndexError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            raise LLMResponseError("Invalid LLM response or tool arguments") from exc

    async def chat(
        self,
        *,
        messages: list[Message],
        model: str,
        temperature: float | None = None,
    ) -> str:
        result = await self.complete(
            messages=messages, model=model, temperature=temperature
        )
        return result.content or ""

    async def vision(self, *, messages: list[Message], model: str) -> str:
        return await self.chat(messages=messages, model=model)

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()


class BedrockLLMClient:
    """AWS Bedrock Converse adapter; AWS credentials use the standard SDK chain."""

    def __init__(self, settings: LLMSettings, *, runtime: Any = None) -> None:
        self.settings = settings
        self._runtime = runtime

    def _get_runtime(self) -> Any:
        if self._runtime is None:
            try:
                import boto3  # type: ignore[import-untyped]
            except ImportError as exc:
                raise LLMUnavailableError("Install portable-llm-mcp[bedrock]") from exc
            self._runtime = boto3.client(
                "bedrock-runtime", region_name=self.settings.aws_region
            )
        return self._runtime

    @staticmethod
    def _content_blocks(content: Any) -> list[dict[str, Any]]:
        if isinstance(content, str):
            return [{"text": content}]
        if not isinstance(content, list):
            raise LLMResponseError("Unsupported message content")
        blocks = []
        for part in content:
            if part.get("type") == "text":
                blocks.append({"text": part["text"]})
            elif part.get("type") == "image_url":
                url = part["image_url"]["url"]
                if not url.startswith("data:image/") or ";base64," not in url:
                    raise LLMResponseError(
                        "Bedrock requires inline base64 PNG/JPEG images"
                    )
                mime, encoded = url.split(";base64,", 1)
                image_format = mime.rsplit("/", 1)[-1]
                if image_format == "jpg":
                    image_format = "jpeg"
                if image_format not in ("png", "jpeg"):
                    raise LLMResponseError("Unsupported Bedrock image format")
                blocks.append(
                    {
                        "image": {
                            "format": image_format,
                            "source": {
                                "bytes": base64.b64decode(encoded, validate=True)
                            },
                        }
                    }
                )
            else:
                raise LLMResponseError("Unknown multimodal message part")
        return blocks

    @classmethod
    def _translate_messages(
        cls, messages: list[Message]
    ) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
        translated: list[dict[str, Any]] = []
        system: list[dict[str, str]] = []
        for message in messages:
            role = message.get("role")
            if role == "system":
                system.append({"text": str(message["content"])})
            elif role == "tool":
                translated.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "toolResult": {
                                    "toolUseId": message["tool_call_id"],
                                    "content": [
                                        {"text": str(message.get("content", ""))}
                                    ],
                                }
                            }
                        ],
                    }
                )
            elif role in {"user", "assistant"}:
                content = (
                    cls._content_blocks(message.get("content") or "")
                    if message.get("content")
                    else []
                )
                for call in message.get("tool_calls") or []:
                    content.append(
                        {
                            "toolUse": {
                                "toolUseId": call["id"],
                                "name": call["function"]["name"],
                                "input": json.loads(call["function"]["arguments"]),
                            }
                        }
                    )
                if content:
                    translated.append({"role": role, "content": content})
            else:
                raise LLMResponseError("Unknown message role")
        return translated, system

    def _sync_complete(
        self,
        messages: list[Message],
        model: str,
        tools: list[ToolDefinition] | None,
        temperature: float | None = None,
    ) -> Completion:
        aws_messages, system = self._translate_messages(messages)
        kwargs: dict[str, Any] = {"modelId": model, "messages": aws_messages}
        if temperature is not None:
            kwargs["inferenceConfig"] = {"temperature": temperature}
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["toolConfig"] = {
                "tools": [
                    {
                        "toolSpec": {
                            "name": tool["function"]["name"],
                            "description": tool["function"].get("description")
                            or "MCP tool",
                            "inputSchema": {"json": tool["function"]["parameters"]},
                        }
                    }
                    for tool in tools
                ]
            }
        try:
            result = self._get_runtime().converse(**kwargs)
            blocks = result["output"]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMResponseError("Invalid Bedrock response") from exc
        except Exception as exc:
            # AWS exceptions may include sensitive bodies: do not propagate text.
            raise LLMUnavailableError(
                f"Bedrock Converse failed ({type(exc).__name__})"
            ) from exc
        text = "\n".join(block["text"] for block in blocks if "text" in block)
        calls = [
            ToolCall(
                id=block["toolUse"]["toolUseId"],
                name=block["toolUse"]["name"],
                arguments=block["toolUse"]["input"],
            )
            for block in blocks
            if "toolUse" in block
        ]
        return Completion(text or None, calls)

    async def complete(
        self,
        *,
        messages: list[Message],
        model: str,
        tools: list[ToolDefinition] | None = None,
        temperature: float | None = None,
    ) -> Completion:
        return await asyncio.to_thread(
            self._sync_complete, messages, model, tools, temperature
        )

    async def chat(
        self,
        *,
        messages: list[Message],
        model: str,
        temperature: float | None = None,
    ) -> str:
        return (
            await self.complete(messages=messages, model=model, temperature=temperature)
        ).content or ""

    async def vision(self, *, messages: list[Message], model: str) -> str:
        return await self.chat(messages=messages, model=model)

    async def aclose(self) -> None:
        return None


def create_llm_client(settings: LLMSettings) -> LLMClient:
    if settings.provider is LLMProvider.BEDROCK:
        return BedrockLLMClient(settings)
    return OpenAICompatibleLLMClient(settings)
