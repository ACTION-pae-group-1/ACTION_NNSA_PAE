"""Reproduce stadium BLS search without an LLM."""

import asyncio
import os
import sys
import time

from portable_llm_mcp import MCPHub, load_mcp_servers


async def main():
    os.environ.setdefault("MCP_PYTHON", sys.executable)

    config = os.environ.get(
        "MCP_SERVERS_FILE",
        "src/mcp_servers_bls_stadium.json",
    )

    servers = load_mcp_servers(config)

    requests = [
        ("bls_server__get_bls_access_status", {}),
        (
            "bls_server__search_series",
            {
                "request": {
                    "query": "steel",
                    "limit": 10,
                }
            },
        ),
        (
            "bls_server__search_series",
            {
                "request": {
                    "query": "concrete products",
                    "programs": ["wp"],
                    "active_only": True,
                    "limit": 10,
                }
            },
        ),
    ]

    async with MCPHub(servers) as hub:
        for name, arguments in requests:
            print(
                f"\nTesting {name}: {arguments}",
                flush=True,
            )

            started = time.perf_counter()

            try:
                result = await hub.call_tool(
                    name,
                    arguments,
                    timeout_seconds=20.0,
                )

                print(
                    f"Completed in {time.perf_counter() - started:.2f}s",
                    flush=True,
                )
                print(result[:1000])

            except Exception as exc:
                print(
                    f"Failed after "
                    f"{time.perf_counter() - started:.2f}s: "
                    f"{type(exc).__name__}: {exc}",
                    flush=True,
                )


if __name__ == "__main__":
    asyncio.run(main())
