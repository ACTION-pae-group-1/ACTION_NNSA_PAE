"""Safe, local-only example tool for new MCP server implementations."""

from __future__ import annotations

from fastmcp import FastMCP


def register(mcp: FastMCP) -> None:
    """Attach one example tool to a server."""

    @mcp.tool(
        name="example_echo",
        annotations={
            "title": "Echo text (example)",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": False,
        },
    )
    def example_echo(message: str) -> dict[str, str]:
        """Return the supplied text without contacting any service."""
        return {"message": message}
