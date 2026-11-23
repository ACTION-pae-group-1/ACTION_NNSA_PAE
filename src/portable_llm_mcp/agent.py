"""Minimal, bounded MCP tool-calling conversation loop."""

from __future__ import annotations

import json
from dataclasses import dataclass

from .llm_client import REPLAY_KEY, LLMClient, Message
from .mcp_client import MCPHub
from .tool_execution import execute_tool_calls


class ToolLoopError(RuntimeError):
    """Tool-calling model did not finish within the configured limit."""


@dataclass
class MCPAgent:
    llm: LLMClient
    hub: MCPHub
    model: str
    max_round_trips: int = 8
    # Opt-in by explicit qualified tool names, not untrusted MCP annotations.
    parallel_read_only_tools: frozenset[str] = frozenset()
    max_parallel_read_only: int = 1

    async def ask(self, prompt: str, *, system_prompt: str | None = None) -> str:
        if self.max_round_trips < 1:
            raise ValueError("max_round_trips must be at least 1")
        messages: list[Message] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        tools = self.hub.tool_definitions()
        for _ in range(self.max_round_trips):
            response = await self.llm.complete(
                messages=messages, model=self.model, tools=tools or None
            )
            if not response.tool_calls:
                return response.content or ""
            turn: Message = {"role": "assistant", "content": response.content}
            if response.replay is not None:
                turn[REPLAY_KEY] = response.replay
            messages.append(
                {
                    **turn,
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.name,
                                "arguments": json.dumps(
                                    call.arguments, ensure_ascii=False
                                ),
                            },
                        }
                        for call in response.tool_calls
                    ],
                }
            )
            results = await execute_tool_calls(
                response.tool_calls,
                self.hub.call_tool,
                parallel_read_only_tools=self.parallel_read_only_tools,
                max_parallel_read_only=self.max_parallel_read_only,
            )
            for call, result in zip(response.tool_calls, results, strict=True):
                messages.append(
                    {"role": "tool", "tool_call_id": call.id, "content": result}
                )
        raise ToolLoopError(f"LLM exceeded {self.max_round_trips} tool-call rounds")
