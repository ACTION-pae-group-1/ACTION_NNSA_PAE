"""Compatibility entry point for the PARS MCP server.

The canonical FastMCP assembly is in ``pars_local_mcp.mcp.server``.
"""

from __future__ import annotations

from pars_local_mcp.mcp import server as _server

# Preserve this import for callers that monkeypatch the legacy entry point.
get_settings = _server.get_settings


def create_server():
    """Build the same server used by the ``pars-mcp-server`` entry point."""
    return _server.create_server(settings=get_settings())


def main() -> None:
    """Start the PARS MCP server using the canonical implementation."""
    create_server().run(show_banner=False)


if __name__ == "__main__":
    main()
