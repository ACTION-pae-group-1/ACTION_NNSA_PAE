"""PARS agent for the eval harness.

Runs the portable MCPAgent against the PARS MCP server (stdio) through the
approved LLM endpoint (see llm_endpoint.py). The tool scope is the seven
read-only PARS tools, applied here in the eval rather than in the shared
src/mcp_servers.json, which the portable client also reads.
"""

from __future__ import annotations

import dataclasses
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from llm_endpoint import (  # noqa: E402
    REPO_ROOT,
    approved_settings,
    build_llm,
    endpoint_info,
)

from portable_llm_mcp import MCPAgent, MCPHub, load_mcp_servers  # noqa: E402

MCP_SERVERS_JSON = REPO_ROOT / "src" / "mcp_servers.json"
SERVER_NAME = "pars_mcp"
READ_ONLY_TOOLS = (
    "list_projects",
    "search_wbs",
    "get_wbs_hierarchy",
    "get_wbs_lineage",
    "get_project_info",
    "get_leaf_nodes",
    "get_wbs_by_level",
)
PROMPT_DIR = Path(__file__).resolve().parent / "prompts"


def pars_server_config():
    """The PARS stdio server, launched with this interpreter.

    The config's `uv run ...` arguments are replaced, not kept: with this
    interpreter the server is `python -m src.pars_local_mcp.server`, run from the
    repository root. Limited to the read-only tools.
    """
    cfg = load_mcp_servers(MCP_SERVERS_JSON)[SERVER_NAME]
    return dataclasses.replace(
        cfg,
        command=sys.executable,
        args=("-m", "src.pars_local_mcp.server"),
        allowed_tools=READ_ONLY_TOOLS,
    )


@dataclass
class AgentRun:
    response: str
    tool_calls: int
    tool_names: list[str] = field(default_factory=list)
    latency_s: float = 0.0
    error: str = ""


class PARSAgent:
    """One agent session.

    Use as an async context manager so the MCP server starts and stops once.
    """

    def __init__(
        self,
        *,
        system_prompt_version: str = "v1",
        use_tools: bool = True,
        max_round_trips: int = 8,
    ) -> None:
        self.settings = approved_settings()
        self.endpoint = endpoint_info(self.settings)
        self.use_tools = use_tools
        self.mode = "tools" if use_tools else "no_tools"
        self.system_prompt = (
            PROMPT_DIR / f"system_prompt_{system_prompt_version}.txt"
        ).read_text(encoding="utf-8")

        servers = {SERVER_NAME: pars_server_config()} if use_tools else {}
        self.hub = MCPHub(servers)
        self._llm = build_llm(self.settings, temperature=0.0)
        self._agent = MCPAgent(
            self._llm,
            self.hub,
            self.settings.chat_model,
            max_round_trips=max_round_trips,
        )

        self._tool_names: list[str] = []
        original_call = self.hub.call_tool

        async def recording_call(qualified_name, arguments):
            self._tool_names.append(qualified_name)
            return await original_call(qualified_name, arguments)

        self.hub.call_tool = recording_call

    async def __aenter__(self) -> "PARSAgent":
        await self.hub.__aenter__()
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self.hub.__aexit__(*exc_info)
        await self._llm.aclose()

    async def run(self, query: str) -> AgentRun:
        """Answer one query. Failures are returned as an error, never as an answer."""
        self._tool_names.clear()
        started = time.perf_counter()
        try:
            text = await self._agent.ask(query, system_prompt=self.system_prompt)
            error = ""
        except Exception as exc:  # recorded as an error row, not scored
            text, error = "", f"agent: {type(exc).__name__}: {exc}"
        return AgentRun(
            response=text or "",
            tool_calls=len(self._tool_names),
            tool_names=list(self._tool_names),
            latency_s=round(time.perf_counter() - started, 3),
            error=error,
        )
