"""Per-call MCP response timeout passes through to the SDK."""

from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

import pytest

from portable_llm_mcp.mcp_client import MCPHub


class FakeSession:
    def __init__(self) -> None:
        self.kwargs: dict | None = None

    async def call_tool(self, name: str, **kwargs):
        assert name == "search_series"
        self.kwargs = kwargs
        return SimpleNamespace(structuredContent={"result": []}, isError=False)


def make_hub() -> tuple[MCPHub, FakeSession]:
    hub = MCPHub({})
    hub._registry = {"bls_server__search_series": ("bls_server", "search_series", {})}
    session = FakeSession()
    hub._sessions = {"bls_server": session}
    return hub, session


@pytest.mark.asyncio
async def test_explicit_timeout_is_forwarded_to_mcp_sdk() -> None:
    hub, session = make_hub()
    result = await hub.call_tool(
        "bls_server__search_series", {"request": {"query": "steel"}}, timeout_seconds=20
    )
    assert result == '{"result": []}'
    assert session.kwargs == {
        "arguments": {"request": {"query": "steel"}},
        "read_timeout_seconds": timedelta(seconds=20),
    }


@pytest.mark.asyncio
async def test_default_call_preserves_existing_sdk_behavior() -> None:
    hub, session = make_hub()
    await hub.call_tool("bls_server__search_series", {})
    assert session.kwargs == {"arguments": {}}


@pytest.mark.asyncio
async def test_invalid_timeouts_rejected() -> None:
    hub, _ = make_hub()
    for timeout in (-1, 0, True):
        with pytest.raises(ValueError, match="positive"):
            await hub.call_tool(
                "bls_server__search_series", {}, timeout_seconds=timeout
            )
