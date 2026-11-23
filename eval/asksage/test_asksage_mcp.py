"""Opt-in Ask Sage and local BLS MCP integration smoke test."""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

import truststore

from portable_llm_mcp import (
    MCPAgent,
    MCPHub,
    create_llm_client,
    load_llm_settings,
    load_mcp_servers,
)

APPROVED_BASE_URL = "https://api.nnsa.asksage.ai/server/openai/v1"
MCP_STARTUP_TIMEOUT = 30
AGENT_TIMEOUT = 180


def log(message: str) -> None:
    print(f"[TEST] {message}", flush=True)


class TracedHub(MCPHub):
    """Trace MCP tool calls and execution times."""

    async def call_tool(self, qualified_name, arguments):
        log(f"Calling tool: {qualified_name}")
        log(f"Arguments: {arguments}")

        start = time.perf_counter()

        try:
            result = await super().call_tool(qualified_name, arguments)
        except Exception as exc:
            elapsed = time.perf_counter() - start
            log(f"Tool failed after {elapsed:.2f}s: {type(exc).__name__}: {exc}")
            raise

        elapsed = time.perf_counter() - start
        log(f"Tool completed in {elapsed:.2f}s")
        log(f"Tool result: {str(result)[:1000]}")
        return result


def resolve_mcp_config(override: str | None = None) -> Path:
    """Resolve the MCP registry independently of the working directory."""
    configured = override or os.environ.get("MCP_SERVERS_FILE")

    if configured:
        path = Path(configured).expanduser()
    else:
        path = Path(__file__).resolve().parent / "mcp_servers_test.json"

    if not path.is_file():
        source = (
            "--server-config"
            if override
            else "MCP_SERVERS_FILE"
            if configured
            else "default test registry"
        )
        raise FileNotFoundError(
            f"Ask Sage MCP configuration not found: {path} "
            f"(source: {source}). "
            "For the bundled registry, unset MCP_SERVERS_FILE. "
            "Otherwise provide an existing JSON file path."
        )

    return path.resolve()


async def main() -> None:
    """Run the live smoke test only after explicit authorization."""
    if os.environ.get("RUN_LIVE_ASKSAGE_TESTS") != "1":
        raise SystemExit(
            "Live Ask Sage testing is disabled. Set RUN_LIVE_ASKSAGE_TESTS=1 to opt in."
        )

    settings = load_llm_settings()

    if settings.provider.value != "asksage":
        raise RuntimeError("Ask Sage evaluation requires LLM_PROVIDER=asksage.")

    if settings.base_url != APPROVED_BASE_URL:
        raise RuntimeError(
            "Ask Sage evaluation requires the exact approved NNSA endpoint."
        )

    # Configure enterprise certificate trust only for explicit live execution.
    truststore.inject_into_ssl()

    total_start = time.perf_counter()

    log(f"Provider: {settings.provider.value}; model: {settings.chat_model}")

    config = resolve_mcp_config()
    log(f"MCP config: {config}")

    os.environ.setdefault("MCP_PYTHON", sys.executable)
    log(f"MCP Python: {os.environ['MCP_PYTHON']}")

    servers = load_mcp_servers(config)
    llm = create_llm_client(settings)

    hub = TracedHub(servers)
    hub_started = False

    try:
        log(f"Starting MCP server ({MCP_STARTUP_TIMEOUT}s timeout)...")
        startup_start = time.perf_counter()

        try:
            async with asyncio.timeout(MCP_STARTUP_TIMEOUT):
                await hub.__aenter__()
            hub_started = True
        except TimeoutError:
            log(f"ERROR: MCP startup exceeded {MCP_STARTUP_TIMEOUT}s.")
            raise

        log(f"MCP server initialized in {time.perf_counter() - startup_start:.2f}s")

        tools = hub.tool_definitions()
        tool_names = [tool["function"]["name"] for tool in tools]
        log(f"Discovered {len(tools)} tools: {tool_names}")

        if not tools:
            raise RuntimeError("No allowlisted MCP tools discovered.")

        agent = MCPAgent(
            llm=llm,
            hub=hub,
            model=settings.chat_model,
            max_round_trips=8,
        )

        prompt = (
            "Find up to three locally cataloged BLS PPI "
            "series relevant to steel construction materials. "
            "Prefer commodity-based PPI where appropriate. "
            "Return series IDs and titles; do not invent IDs."
        )

        system_prompt = (
            "Use only local BLS MCP catalog tools. "
            "Do not retrieve live observations or modify data. "
            "Only report IDs supported by tool results."
        )

        log("Asking model...")
        log(f"Prompt: {prompt}")
        agent_start = time.perf_counter()

        try:
            async with asyncio.timeout(AGENT_TIMEOUT):
                answer = await agent.ask(
                    prompt,
                    system_prompt=system_prompt,
                )
        except TimeoutError:
            elapsed = time.perf_counter() - agent_start
            log(
                f"ERROR: Agent timed out after {elapsed:.2f}s "
                f"(limit: {AGENT_TIMEOUT}s)."
            )
            raise

        log(f"Agent completed in {time.perf_counter() - agent_start:.2f}s")

        print()
        print("=" * 60)
        print("FINAL ANSWER")
        print("=" * 60)
        print(answer)
        print("=" * 60)

    finally:
        if hub_started:
            log("Closing MCP connections...")
            try:
                await hub.__aexit__(None, None, None)
                log("MCP connections closed.")
            except Exception as exc:
                log(f"MCP cleanup warning: {type(exc).__name__}: {exc}")

        log("Closing Ask Sage client...")
        await llm.aclose()
        log(f"Total test time: {time.perf_counter() - total_start:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())
