"""Tool-call execution evaluation of the 16 PARS MCP tools through a LOCAL OLLAMA agent.

Local Ollama only: the endpoint is pinned to http://localhost:11434/v1 before any eval
module reads the environment, and the run refuses any other provider or host. Ask Sage
is not used. No LLM judge is used; every check is deterministic (tool names, order,
arguments, run_id chaining, and tool errors).

Isolation: the agent launches eval/phoenix/pars_gap_stdio_server.py, not the default
entry point. The launcher refuses to start unless the five PARS path variables are set
and point under C:/tmp/pars_eval_gap/runs/. Those variables are set in the server
environment here, to a disposable copy of the frozen snapshot and per-run directories.

Usage (from the repository root):
    .venv\\Scripts\\python.exe eval\\phoenix\\run_pars_gap_agent.py --run-id <id>
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse  # noqa: E402
import asyncio  # noqa: E402
import dataclasses  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import re  # noqa: E402
import shutil  # noqa: E402
import time  # noqa: E402
from datetime import datetime, timezone  # noqa: E402
from pathlib import Path  # noqa: E402

EVAL_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVAL_DIR.parents[1]
GAP_ROOT = Path("C:/tmp/pars_eval_gap")
CASES_PATH = EVAL_DIR / "datasets" / "pars-eval-gap" / "agent_cases.json"
STDIO_LAUNCHER = EVAL_DIR / "pars_gap_stdio_server.py"
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(EVAL_DIR))

# Pin the approved endpoint to local Ollama. Explicit environment values take precedence
# over src/portable_llm_mcp/.env (its load_dotenv uses override=False).
OLLAMA = {
    "LLM_PROVIDER": "ollama",
    "LLM_BASE_URL": "http://localhost:11434/v1",
    "LLM_CHAT_MODEL": "gemma4:12b-mtp",
    "LLM_API_KEY": "ollama-local",  # pragma: allowlist secret
}
os.environ.update(OLLAMA)

import agent as agent_mod  # noqa: E402
import run_pars_gap_eval as gap  # noqa: E402
from llm_endpoint import approved_settings, endpoint_info  # noqa: E402
from tracing import setup_tracing  # noqa: E402

PARS_KEYS = {
    "DATABASE_PATH": "db/pars_gap_synthetic.duckdb",
    "MODEL_DIR": "models",
    "MODEL_SIGNING_KEY_PATH": "keys/model_signing.key",
    "WBS_RUNS_DIR": "wbs_runs",
    "WBS_SOURCE_DB": "source/mock_pars_full_copy.duckdb",
}


def _tool_name(qualified: str) -> str:
    return qualified.split("__")[-1]


def _server_config(run_dir: Path):
    """The pars_mcp entry from src/mcp_servers.json, pointed at the isolated
    launcher."""
    cfg = agent_mod.load_mcp_servers(agent_mod.MCP_SERVERS_JSON)[agent_mod.SERVER_NAME]
    env = {key: str(run_dir / rel) for key, rel in PARS_KEYS.items()}
    for key, value in env.items():
        if not Path(value).resolve().is_relative_to(run_dir.resolve()):
            raise SystemExit(f"isolation: {key} is outside the run directory")
    return dataclasses.replace(
        cfg,
        command=sys.executable,
        args=(str(STDIO_LAUNCHER),),
        allowed_tools=tuple(gap.ALL_TOOLS),
        env=env,
    )


def _prepare(run_dir: Path) -> None:
    """Disposable copies only: the snapshot, the mock source, and empty model/key/run
    dirs."""
    (run_dir / "db").mkdir(parents=True)
    (run_dir / "models").mkdir()
    (run_dir / "keys").mkdir()
    (run_dir / "wbs_runs").mkdir()
    (run_dir / "source").mkdir()
    shutil.copyfile(gap.SNAPSHOT_PATH, run_dir / "db" / "pars_gap_synthetic.duckdb")
    shutil.copyfile(gap.MOCK_SOURCE, run_dir / "source" / "mock_pars_full_copy.duckdb")
    if (
        gap.sha256_file(run_dir / "db" / "pars_gap_synthetic.duckdb")
        != gap.SNAPSHOT_SHA256
    ):
        raise SystemExit("served copy hash does not match the snapshot checksum")


def _check_calls(case: dict, calls: list[dict], agent_error: str) -> list[dict]:
    checks: list[dict] = []
    checks.append(
        {
            "name": "no_agent_error",
            "pass": agent_error == "",
            "detail": agent_error[:200],
        }
    )
    names = [c["tool"] for c in calls]
    # Expected tools appear as an ordered subsequence of the calls made.
    it = iter(names)
    ordered = all(any(n == t for n in it) for t in case["expect_tools"])
    checks.append(
        {"name": "expected_tools_in_order", "pass": ordered, "detail": f"calls={names}"}
    )
    checks.append(
        {
            "name": "only_registered_tools",
            "pass": all(n in gap.ALL_TOOLS for n in names),
            "detail": "",
        }
    )
    for tool, wanted in case.get("required_args", {}).items():
        matching = [c for c in calls if c["tool"] == tool]
        ok = any(
            all(str(c["args"].get(k)) == str(v) for k, v in wanted.items())
            for c in matching
        )
        checks.append(
            {
                "name": f"args_{tool}",
                "pass": ok,
                "detail": json.dumps([c["args"] for c in matching], default=str)[:200],
            }
        )
    if case.get("chain_run_id"):
        clean = next((c for c in calls if c["tool"] == "clean_wbs_data"), None)
        run_id = ""
        if clean:
            m = re.search(r'"run_id":\s*"([^"]+)"', clean["result"])
            run_id = m.group(1) if m else ""
        same = all(
            c["args"].get("run_id") == run_id
            for c in calls
            if c["tool"]
            in (
                "tune_and_train_wbs",
                "predict_wbs",
                "write_back_wbs",
                "get_wbs_run_status",
            )
        )
        checks.append(
            {
                "name": "chained_run_id_consistent",
                "pass": bool(run_id) and same,
                "detail": f"clean_run_id={run_id}",
            }
        )
    if case.get("expect_success"):
        bad = [
            c["tool"]
            for c in calls
            if c["tool"] in case["expect_tools"] and '"error"' in c["result"]
        ]
        checks.append(
            {
                "name": "expected_tools_returned_no_error",
                "pass": not bad,
                "detail": f"tools_with_error={bad}",
            }
        )
    return checks


async def amain(args: argparse.Namespace) -> int:
    run_id = args.run_id or "pars-agent-gap-" + datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )
    run_dir = GAP_ROOT / "runs" / run_id
    if run_dir.exists():
        raise SystemExit(f"run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True)

    settings = approved_settings()
    info = endpoint_info(settings)
    if info.provider != "ollama" or info.host not in ("localhost", "127.0.0.1"):
        raise SystemExit(f"refusing non-local or non-Ollama endpoint: {info}")

    before = gap.snapshot_protected()
    (run_dir / "integrity_before.json").write_text(
        json.dumps(before, indent=1), encoding="utf-8"
    )
    _prepare(run_dir)
    cfg = _server_config(run_dir)
    agent_mod.pars_server_config = lambda: (
        cfg
    )  # the agent launches the isolated launcher only

    tracing = setup_tracing(
        "pars-eval-gap-agent", run_dir / "traces.jsonl", enabled=not args.no_phoenix
    )
    meta = {
        "run_id": run_id,
        "endpoint": {"provider": info.provider, "host": info.host, "model": info.model},
        "pars_env": {k: v for k, v in cfg.env.items()},
        "launcher": str(STDIO_LAUNCHER),
        "phoenix": tracing.destination,
    }
    (run_dir / "run_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")

    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]
    if args.only:
        wanted = set(args.only.split(","))
        cases = [c for c in cases if c["id"] in wanted]

    snap_hash_before = gap.sha256_file(gap.SNAPSHOT_PATH)
    out = run_dir / "agent_results.jsonl"
    rows = []
    agent = await _make_agent()
    async with agent:
        for case in cases:
            calls: list[dict] = []
            original = agent.hub.call_tool

            async def capture(qualified_name, arguments, _orig=original, _calls=calls):
                result = await _orig(qualified_name, arguments)
                _calls.append(
                    {
                        "tool": _tool_name(qualified_name),
                        "args": arguments,
                        "result": str(result)[:800],
                    }
                )
                return result

            agent.hub.call_tool = capture
            started = time.perf_counter()
            try:
                run = await asyncio.wait_for(
                    agent.run(case["query"]), timeout=args.case_timeout
                )
                agent_error = run.error
                response = run.response
            except asyncio.TimeoutError:
                agent_error, response = f"timeout after {args.case_timeout}s", ""
            finally:
                agent.hub.call_tool = original
            checks = _check_calls(case, calls, agent_error)
            row = {
                "case_id": case["id"],
                "expect_tools": case["expect_tools"],
                "calls": calls,
                "response_preview": response[:300],
                "latency_s": round(time.perf_counter() - started, 2),
                "checks": checks,
                "status": "pass" if all(c["pass"] for c in checks) else "fail",
                "snapshot_sha_unchanged": gap.sha256_file(gap.SNAPSHOT_PATH)
                == snap_hash_before,
            }
            rows.append(row)
            with out.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, default=str) + "\n")
            with tracing.span(
                "pars_gap.agent_case", {"case_id": case["id"], "status": row["status"]}
            ) as sp:
                sp.set_attributes({"calls": len(calls)})

    after = gap.snapshot_protected()
    (run_dir / "integrity_after.json").write_text(
        json.dumps(after, indent=1), encoding="utf-8"
    )
    diff = gap.diff_snapshots(before, after)
    summary = {
        "run_id": run_id,
        "cases": len(rows),
        "status_counts": {
            s: sum(1 for r in rows if r["status"] == s) for s in ("pass", "fail")
        },
        "tools_called": sorted({c["tool"] for r in rows for c in r["calls"]}),
        "protected_diff": diff,
        "protected_files_unchanged": not diff["changed"] and not diff["removed"],
        "snapshot_sha256": gap.sha256_file(gap.SNAPSHOT_PATH),
    }
    (run_dir / "summary.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8"
    )
    print(json.dumps(summary, indent=1))
    return 0


GAP_SYSTEM_PROMPT = """You are a WBS analyst assistant with the PARS tools. The data \
is synthetic.

Tools (all 16 are available):
- Read: list_projects, search_wbs(project_id, wbs_pattern, min_level, max_level), \
get_wbs_hierarchy(project_id, wbs_code), get_wbs_lineage(project_id, wbs_code), \
get_project_info(project_id), get_leaf_nodes(project_id), get_wbs_by_level(project_id, \
level), validate_wbs_inputs(), get_wbs_project_descriptions(limit), \
get_wbs_rows(limit), get_wbs_run_status(run_id)
- Pipeline: clean_wbs_data(run_id), tune_and_train_wbs(run_id, n_iter, cv_folds, \
n_jobs, search_seed, split_seed), predict_wbs(run_id, model_variant), \
write_back_wbs(run_id), run_wbs_pipeline(run_id, n_iter, cv_folds, n_jobs, \
search_seed, split_seed, model_variant)

When the user gives exact tool arguments, call the named tool with exactly those \
arguments. When a step needs a run_id, use the run_id returned by the earlier tool \
result. Call only the tools the request names. Report the tool result briefly."""


async def _make_agent():
    agent = agent_mod.PARSAgent(
        system_prompt_version="v1", use_tools=True, max_round_trips=10
    )
    agent.system_prompt = GAP_SYSTEM_PROMPT
    return agent


def main() -> None:
    parser = argparse.ArgumentParser(
        description="PARS 16-tool tool-call evaluation (local Ollama)"
    )
    parser.add_argument("--run-id", default="")
    parser.add_argument(
        "--only", default="", help="comma-separated case ids, e.g. A-01,A-12"
    )
    parser.add_argument("--case-timeout", type=int, default=600)
    parser.add_argument("--no-phoenix", action="store_true")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(amain(args)))


if __name__ == "__main__":
    main()
