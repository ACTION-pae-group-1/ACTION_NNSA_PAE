"""Verify MCP connectivity and exposed-tool allowlists without calling an LLM."""

from __future__ import annotations

import asyncio
import os

from portable_llm_mcp import MCPHub, load_mcp_servers


async def main() -> None:
    servers = load_mcp_servers(os.environ.get("MCP_SERVERS_FILE") or "mcp_servers.json")
    async with MCPHub(servers) as hub:
        for tool in hub.tool_definitions():
            print(tool["function"]["name"])
        if not hub.tool_definitions():
            print("Connected; no MCP tools exposed by the allowlist.")


if __name__ == "__main__":
    asyncio.run(main())
