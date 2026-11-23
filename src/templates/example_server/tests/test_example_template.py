"""Contract smoke check: the retained sample MCP must register a real tool."""

from __future__ import annotations

import pytest

from src.templates.example_server.app import mcp


def test_template_has_unique_name() -> None:
    assert mcp.name == "Example MCP Server"


@pytest.mark.asyncio
async def test_template_example_tool_is_discoverable() -> None:
    tools = await mcp.list_tools()
    names = {tool.name for tool in tools}
    assert "example_echo" in names
