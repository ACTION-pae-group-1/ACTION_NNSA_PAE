"""What an episode records: the conversation and every tool call."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from fastmcp import Client

from eval.bls import tracing

CALCULATION_TOOLS = frozenset(
    {
        "calculate_index_from_bls",
        "calculate_index_spec",
        "calculate_component_escalation",
    }
)


@dataclass(frozen=True)
class ToolCall:
    turn: int
    name: str
    arguments: dict[str, Any]
    result: Any
    is_error: bool
    error_text: str = ""


@dataclass(frozen=True)
class Message:
    turn: int
    role: str  # "user" or "agent"
    text: str


@dataclass
class Transcript:
    messages: list[Message] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    #: fact name -> turn at which the simulated user disclosed it
    revealed: dict[str, int] = field(default_factory=dict)
    error: str | None = None
    #: True when *error* came from infrastructure, not from agent behaviour.
    infrastructure_failure: bool = False

    def agent_messages(self) -> list[Message]:
        return [m for m in self.messages if m.role == "agent"]

    @property
    def final_message(self) -> str:
        agent = self.agent_messages()
        return agent[-1].text if agent else ""

    def calls(self, *names: str, ok_only: bool = False) -> list[ToolCall]:
        return [
            c
            for c in self.tool_calls
            if c.name in names and not (ok_only and c.is_error)
        ]

    def first_calculation_turn(self) -> int | None:
        turns = [c.turn for c in self.tool_calls if c.name in CALCULATION_TOOLS]
        return min(turns) if turns else None

    def final_source_calculation(self) -> ToolCall | None:
        """The last successful snapshot-backed calculation, if any."""
        done = self.calls("calculate_index_from_bls", ok_only=True)
        return done[-1] if done else None


class ToolSession:
    """The only route an agent has to the server; every call is recorded."""

    def __init__(self, client: Client, transcript: Transcript) -> None:
        self._client = client
        self._transcript = transcript
        self.turn = 0

    async def list_tools(self) -> list[Any]:
        return list(await self._client.list_tools())

    async def call(self, name: str, arguments: dict[str, Any]) -> ToolCall:
        with tracing.span("mcp.tool", tool_name=name, turn=self.turn) as tool_span:
            outcome = await self._client.call_tool(
                name, arguments, raise_on_error=False
            )
            if tool_span is not None:
                tool_span.set_attribute("mcp.is_error", bool(outcome.is_error))
        content = outcome.structured_content
        # FastMCP wraps non-object returns (lists, None) as {"result": ...};
        # objects, including ones with their own "result" field, come unwrapped.
        result = (
            content["result"] if content and set(content) == {"result"} else content
        )
        error_text = ""
        if outcome.is_error:
            error_text = " ".join(
                getattr(block, "text", "") for block in outcome.content
            )
        call = ToolCall(
            self.turn, name, arguments, result, bool(outcome.is_error), error_text
        )
        self._transcript.tool_calls.append(call)
        return call
