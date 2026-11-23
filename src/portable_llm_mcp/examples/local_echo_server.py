"""Safe local demonstration MCP server. Does not make network requests."""

from mcp.server.fastmcp import FastMCP

server = FastMCP("local-echo")


@server.tool()
def echo(message: str) -> str:
    """Return the caller's text unchanged (read-only demonstration)."""
    return message


if __name__ == "__main__":
    server.run(transport="stdio")
