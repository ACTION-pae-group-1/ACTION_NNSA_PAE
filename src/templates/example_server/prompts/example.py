"""Safe example MCP prompt to customize for a new server."""

from __future__ import annotations

from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Attach one example prompt to a server."""

    @mcp.prompt()
    def explore_topic(topic: str) -> str:
        """Start an exploration of a topic using permitted MCP tools."""
        return (
            f"Help me explore {topic}. First explain what information is available, "
            "then suggest one useful next step."
        )
