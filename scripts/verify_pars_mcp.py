"""Offline PARS FastMCP protocol smoke check (no model training or write-back).

Run from repository root with the project .venv active:
    python scripts/verify_pars_mcp.py

Uses an in-process FastMCP Client and a temporary hierarchy database.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Do not allow optional library update/telemetry traffic while validating.
os.environ["DO_NOT_TRACK"] = "1"
os.environ["FASTMCP_DISABLE_TELEMETRY"] = "1"
os.environ["UV_OFFLINE"] = "1"


async def verify() -> None:
    from fastmcp import Client

    from pars_local_mcp.mcp.server import create_server

    registry = json.loads(
        (ROOT / "src" / "mcp_servers.json").read_text(encoding="utf-8")
    )
    expected = set(registry["servers"]["pars_mcp"]["allowed_tools"])

    # Server initialization creates a local synthetic hierarchy database.
    # Use a temporary directory, never the checkout's default wbs.duckdb.
    with tempfile.TemporaryDirectory(prefix="pars_mcp_verify_") as directory:
        os.environ["DATABASE_PATH"] = str(Path(directory) / "hierarchy.duckdb")
        server = create_server()
        async with Client(server) as client:
            offered = {tool.name for tool in await client.list_tools()}
            missing = sorted(expected - offered)
            if missing:
                raise AssertionError(f"Missing registered PARS tools: {missing}")
            print(f"PASS: {len(expected)} allowlisted PARS tools discoverable")

            async def call(name: str, arguments: dict | None = None) -> dict:
                response = await client.call_tool(name, arguments or {})
                if getattr(response, "is_error", False):
                    raise AssertionError(f"{name}: MCP protocol returned error")
                data = getattr(response, "structured_content", None)
                if data is None:
                    chunks = [c.text for c in response.content if hasattr(c, "text")]
                    data = json.loads(chunks[0]) if chunks else None
                if not isinstance(data, dict) or "error" in data:
                    raise AssertionError(f"{name}: invalid or error response: {data!r}")
                print(f"PASS: {name}")
                return data

            projects = (await call("list_projects"))["projects"]
            if not projects:
                raise AssertionError("Synthetic hierarchy has no projects")
            project_id = str(projects[0]["parsid"])
            await call("get_project_info", {"project_id": project_id})
            elements = (await call("search_wbs", {"project_id": project_id}))[
                "elements"
            ]
            if not elements:
                raise AssertionError("Synthetic project has no WBS elements")
            code = elements[0]["wbs_code"]
            await call(
                "get_wbs_hierarchy", {"project_id": project_id, "wbs_code": code}
            )
            await call("get_wbs_lineage", {"project_id": project_id, "wbs_code": code})
            await call("get_leaf_nodes", {"project_id": project_id})
            await call("get_wbs_by_level", {"project_id": project_id, "level": 1})

    print("PASS: in-process MCP discovery and hierarchy tool calls")
    print(
        "NOT RUN: WBS source validation, tuning, prediction, "
        "write-back, BLS, and HTML UI"
    )


if __name__ == "__main__":
    asyncio.run(verify())
