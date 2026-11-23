"""Safe example MCP resource to customize for a new server."""

from __future__ import annotations

from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Attach one example resource to a server."""

    @mcp.resource("example://info/server")
    def server_info() -> str:
        """Describe this sample server without network or filesystem access."""
        return (
            "Example MCP Server: replace this resource and the example tool "
            "when creating a new server."
        )
