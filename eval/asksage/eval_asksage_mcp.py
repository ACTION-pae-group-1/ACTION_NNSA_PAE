"""Evaluate Ask Sage models against real, allowlisted BLS MCP tools.

Run from the repository root with UV's --env-file option.
Outputs CSV summary and JSONL detailed traces in eval/asksage/results/.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import truststore

from portable_llm_mcp import (
    MCPAgent,
    MCPHub,
    create_llm_client,
    load_llm_settings,
    load_mcp_servers,
)

MODELS = [
    "gpt-5.4-gov",
    "gpt-5.6-luna-gov",
    "gpt-5.6-sol-gov",
    "gpt-5.6-terra-gov",
]

CASES = [
    (
        "steel",
        (
            "Find up to three locally cataloged BLS series relevant to steel "
            "construction materials. Prefer commodity-based PPI where "
            "appropriate. Return series IDs and titles; do not invent IDs."
        ),
    ),
    (
        "concrete",
        (
            "Find up to three locally cataloged BLS series relevant to "
            "concrete materials. Return series IDs and titles; do not invent IDs."
        ),
    ),
    (
        "labor",
        (
            "Find up to three locally cataloged Employment Cost Index series "
            "relevant to labor costs. Return series IDs and titles; "
            "do not invent IDs."
        ),
    ),
    (
        "historical",
        (
            "Find up to three discontinued historical industry-based PPI "
            "series, if available. Return series IDs and titles; "
            "do not invent IDs."
        ),
    ),
    (
        "generic_ppi",
        (
            "Explore the local catalog for Producer Price Index series. "
            "Use appropriate program filters, and avoid using the generic "
            "program name as a text search when unnecessary. "
            "Return up to three IDs and titles."
        ),
    ),
]

SYSTEM = (
    "Use the available local BLS MCP catalog tools. "
    "Only report series IDs supported by actual tool results. "
    "Do not retrieve live observations, modify data, or calculate escalation. "
    "If no matches exist, say so."
)


class RecordingHub(MCPHub):
    def __init__(self, servers):
        super().__init__(servers)
        self.events = []

    async def call_tool(self, qualified_name, arguments):
        started = time.perf_counter()
        event = {"tool": qualified_name, "arguments": arguments}
        try:
            result = await super().call_tool(qualified_name, arguments)
            event["duration_seconds"] = round(time.perf_counter() - started, 3)
            event["is_error"] = result.startswith("MCP tool reported an error:")
            event["result_excerpt"] = result[:2000]
            return result
        except Exception as exc:
            event["duration_seconds"] = round(time.perf_counter() - started, 3)
            event["is_error"] = True
            event["exception"] = f"{type(exc).__name__}: {str(exc)[:300]}"
            raise
        finally:
            self.events.append(event)


def resolve_mcp_config(override: str | None = None) -> Path:
    """Find the test registry without depending on the shell working directory."""
    configured = override or os.environ.get("MCP_SERVERS_FILE")
    path = (
        Path(configured).expanduser()
        if configured
        else Path(__file__).resolve().parent / "mcp_servers_test.json"
    )
    if not path.is_file():
        source = (
            "--server-config"
            if override
            else "MCP_SERVERS_FILE"
            if configured
            else "default test registry"
        )
        raise FileNotFoundError(
            f"Ask Sage MCP configuration not found: {path} (source: {source}). "
            "For the bundled registry, unset MCP_SERVERS_FILE and omit "
            "--server-config; otherwise provide an existing JSON file path."
        )
    return path.resolve()


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="+", choices=MODELS, default=MODELS)
    parser.add_argument(
        "--cases",
        nargs="+",
        choices=[x[0] for x in CASES],
        default=["steel", "concrete", "labor"],
    )
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument(
        "--server-config",
        default=None,
        help=(
            "Override MCP registry path (otherwise uses MCP_SERVERS_FILE "
            "or the registry next to this script)"
        ),
    )
    args = parser.parse_args()

    if os.environ.get("RUN_LIVE_ASKSAGE_TESTS") != "1":
        raise SystemExit("Live Ask Sage evaluation requires RUN_LIVE_ASKSAGE_TESTS=1")

    if args.repeats < 1 or args.timeout < 1:
        parser.error("--repeats and --timeout must be positive")

    settings = load_llm_settings()
    if settings.provider.value != "asksage":
        raise RuntimeError(
            "Ask Sage evaluation requires LLM_PROVIDER=asksage; "
            "run with: uv run --env-file src/portable_llm_mcp/.env ..."
        )

    if settings.base_url != "https://api.nnsa.asksage.ai/server/openai/v1":
        raise RuntimeError(
            "Ask Sage evaluation requires the approved api.nnsa.asksage.ai endpoint."
        )

    args.server_config = resolve_mcp_config(args.server_config)
    servers = load_mcp_servers(args.server_config)
    outdir = Path(__file__).resolve().parent / "results"
    outdir.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    summary_path = outdir / f"asksage_eval_{stamp}.csv"
    details_path = outdir / f"asksage_eval_{stamp}.jsonl"
    case_lookup = dict(CASES)
    columns = [
        "model",
        "case",
        "repeat",
        "status",
        "elapsed_seconds",
        "tool_calls",
        "tool_errors",
        "tools_used",
        "final_answer",
        "error",
    ]

    truststore.inject_into_ssl()
    llm = create_llm_client(settings)
    try:
        print(f"Starting MCP hub using {args.server_config}", flush=True)
        async with RecordingHub(servers) as hub:
            available = {x["function"]["name"] for x in hub.tool_definitions()}
            print("Available tools:", ", ".join(sorted(available)), flush=True)
            if not available:
                raise RuntimeError("No allowlisted MCP tools discovered")
            with (
                summary_path.open("w", newline="", encoding="utf-8-sig") as csv_file,
                details_path.open("w", encoding="utf-8") as jsonl_file,
            ):
                writer = csv.DictWriter(csv_file, fieldnames=columns)
                writer.writeheader()
                for model in args.models:
                    for case in args.cases:
                        for repetition in range(1, args.repeats + 1):
                            hub.events = []
                            agent = MCPAgent(
                                llm=llm, hub=hub, model=model, max_round_trips=6
                            )
                            started = time.perf_counter()
                            answer, error, status = "", "", "completed"
                            print(
                                f"Running {model} / {case} / {repetition}", flush=True
                            )
                            try:
                                async with asyncio.timeout(args.timeout):
                                    answer = await agent.ask(
                                        case_lookup[case], system_prompt=SYSTEM
                                    )
                            except TimeoutError:
                                status, error = "timeout", f"Exceeded {args.timeout}s"
                            except Exception as exc:
                                status, error = (
                                    "error",
                                    f"{type(exc).__name__}: {str(exc)[:400]}",
                                )
                            elapsed = round(time.perf_counter() - started, 2)
                            events = list(hub.events)
                            errors = sum(bool(x.get("is_error")) for x in events)
                            # Observational checks only: correctness needs human review.
                            if status == "completed" and not events:
                                status = "no_tool_call"
                            elif status == "completed" and errors:
                                status = "completed_with_tool_errors"
                            row = {
                                "model": model,
                                "case": case,
                                "repeat": repetition,
                                "status": status,
                                "elapsed_seconds": elapsed,
                                "tool_calls": len(events),
                                "tool_errors": errors,
                                "tools_used": "; ".join(x["tool"] for x in events),
                                "final_answer": answer,
                                "error": error,
                            }
                            writer.writerow(row)
                            csv_file.flush()
                            detail = {
                                **row,
                                "prompt": case_lookup[case],
                                "tool_events": events,
                            }
                            jsonl_file.write(
                                json.dumps(detail, ensure_ascii=False, default=str)
                                + "\n"
                            )
                            jsonl_file.flush()
                            print(
                                f"  {status}: {len(events)} calls, "
                                f"{errors} tool errors, {elapsed}s",
                                flush=True,
                            )
    finally:
        await llm.aclose()
    print(f"CSV: {summary_path}\nTrace: {details_path}", flush=True)
    print(
        "Review answers and tool-result excerpts manually "
        "before assigning correctness scores.",
        flush=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
