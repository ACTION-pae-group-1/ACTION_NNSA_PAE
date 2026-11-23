"""Streamable HTTP credentials must reach the SDK's HTTP client."""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from types import ModuleType, SimpleNamespace
from typing import Self

import httpx
import pytest

from portable_llm_mcp.mcp_client import MCPHub, MCPServerStartError, ServerConfig


@pytest.mark.asyncio
async def test_stdio_startup_failure_names_the_server() -> None:
    # A server that exits before initializing must be identified by name, not
    # reported as an anonymous "Connection closed".
    hub = MCPHub(
        {
            "broken": ServerConfig(
                "stdio",
                ("*",),
                command=sys.executable,
                args=("-c", "import sys; sys.exit(3)"),
            )
        }
    )
    with pytest.raises(MCPServerStartError, match="'broken'") as error:
        async with hub:
            pass
    assert error.value.server == "broken"
    assert error.value.__cause__ is not None


@pytest.mark.asyncio
async def test_http_transport_passes_headers_and_closes_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clients: list[httpx.AsyncClient] = []

    @asynccontextmanager
    async def fake_transport(url: str, *, http_client: httpx.AsyncClient):
        assert url == "https://example.test/mcp"
        assert http_client.headers["Authorization"] == "Bearer test-token"
        clients.append(http_client)
        yield None, None, lambda: None

    class FakeSession:
        def __init__(self, _read: object, _write: object) -> None:
            pass

        async def __aenter__(self) -> Self:
            return self

        async def __aexit__(self, *_exc: object) -> None:
            pass

        async def initialize(self) -> None:
            pass

        async def list_tools(self) -> SimpleNamespace:
            return SimpleNamespace(tools=[])

    def sdk_module(name: str, **exports: object) -> None:
        module = ModuleType(name)
        module.__dict__.update(exports)
        if name in {"mcp", "mcp.client"}:
            module.__dict__["__path__"] = []
        monkeypatch.setitem(sys.modules, name, module)

    sdk_module("mcp", ClientSession=FakeSession, StdioServerParameters=object)
    sdk_module("mcp.client")
    sdk_module("mcp.client.stdio", stdio_client=object)
    sdk_module("mcp.client.streamable_http", streamable_http_client=fake_transport)

    async def reachable(_name: str, _url: str) -> None:
        return None  # no network in tests; the transport itself is faked below

    monkeypatch.setattr("portable_llm_mcp.mcp_client._probe_reachable", reachable)

    hub = MCPHub(
        {
            "remote": ServerConfig(
                "streamable_http",
                ("*",),
                url="https://example.test/mcp",
                headers={"Authorization": "Bearer test-token"},
            )
        }
    )
    async with hub:
        assert len(clients) == 1
        assert not clients[0].is_closed
    assert clients[0].is_closed
