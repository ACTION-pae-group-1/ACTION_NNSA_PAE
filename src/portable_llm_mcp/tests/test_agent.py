from __future__ import annotations

import pytest

from portable_llm_mcp import MCPAgent, MCPHub, ServerConfig, ToolLoopError
from portable_llm_mcp.llm_client import Completion, ToolCall
from portable_llm_mcp.mcp_client import MCPConfigurationError


class FakeLLM:
    def __init__(self):
        self.calls = []

    async def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
    ) -> Completion:
        self.calls.append((messages, tools))
        if len(self.calls) == 1:
            return Completion(
                tool_calls=[ToolCall("id1", "demo__echo", {"message": "hello"})]
            )
        return Completion(content="Echo returned hello")

    from typing import Any

    async def chat(
        self,
        *,
        messages: list[dict[str, Any]],
        model: str,
        temperature: float | None = None,
    ) -> str:
        return (await self.complete(messages=messages, model=model)).content or ""

    async def vision(self, *, messages, model):
        return await self.chat(messages=messages, model=model)

    async def aclose(self):
        pass


class FakeResult:
    isError = False
    structuredContent = None

    def __init__(self, text):
        self.content = [type("Block", (), {"type": "text", "text": text})()]


class FakeSession:
    async def call_tool(self, name, arguments):
        assert name == "echo"
        return FakeResult(arguments["message"])


@pytest.mark.asyncio
async def test_agent_executes_allowlisted_tool_and_returns_final_answer() -> None:
    hub = MCPHub({"demo": ServerConfig("stdio", ("echo",), command="python")})
    hub._registry = {
        "demo__echo": (
            "demo",
            "echo",
            {"type": "function", "function": {"name": "demo__echo"}},
        )
    }
    hub._sessions = {"demo": FakeSession()}
    model = FakeLLM()
    answer = await MCPAgent(model, hub, "test-model").ask("Echo hello")
    assert answer == "Echo returned hello"
    assert model.calls[1][0][-1] == {
        "role": "tool",
        "tool_call_id": "id1",
        "content": "hello",
    }


@pytest.mark.asyncio
async def test_unknown_tools_are_rejected() -> None:
    hub = MCPHub({})
    with pytest.raises(MCPConfigurationError, match="not allowed"):
        await hub.call_tool("unlisted_tool", {})


@pytest.mark.asyncio
async def test_tool_loop_is_bounded() -> None:
    hub = MCPHub({})
    hub._registry = {
        "demo__echo": (
            "demo",
            "echo",
            {"type": "function", "function": {"name": "demo__echo"}},
        )
    }
    hub._sessions = {"demo": FakeSession()}
    with pytest.raises(ToolLoopError):
        await MCPAgent(FakeLLM(), hub, "m", max_round_trips=1).ask("hello")


def test_long_mcp_tool_names_remain_bounded_and_deterministic() -> None:
    name = MCPHub._qualified_name("server", "a" * 100)
    assert len(name) <= 64
    assert name == MCPHub._qualified_name("server", "a" * 100)
