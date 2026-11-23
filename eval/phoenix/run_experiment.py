"""Run the PARS evaluation through the approved LLM endpoint.

Usage (run from anywhere):
    python eval/phoenix/run_experiment.py --dataset-name pars-eval-0
    python eval/phoenix/run_experiment.py --dataset-name pars-eval-0 --trials 5
    python eval/phoenix/run_experiment.py --dataset-name pars-eval-0 --no-tools
    # --no-tools is the baseline run
    python eval/phoenix/run_experiment.py --dataset-name pars-eval-0 --max-examples 3
    python eval/phoenix/run_experiment.py --dataset-name pars-eval-1 --no-phoenix

Every result row records the agent and judge provider, endpoint host, and model.
Only Ask Sage and local Ollama are reachable; anything else is refused at startup.

Each row is also emitted as a trace span: to a local Phoenix server when one is
reachable, otherwise to results/<run_id>.traces.jsonl (see tracing.py).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL_DIR))

from agent import AgentRun, PARSAgent  # noqa: E402
from judges import check_answer_scope, match_expected_response  # noqa: E402
from llm_endpoint import REPO_ROOT, JudgeError, judge_endpoint  # noqa: E402
from tracing import setup_tracing  # noqa: E402

from portable_llm_mcp import LLMConfigError  # noqa: E402

RESULTS_DIR = EVAL_DIR / "results"
PREVIEW_CHARS = 200
TRACE_PROJECT = "pars-eval"
SPAN_NAME = "pars_eval.example"
COLUMNS = [
    "run_id",
    "timestamp_utc",
    "git_sha",
    "dataset",
    "prompt_version",
    "mode",
    "example",
    "trial",
    "query",
    "tool_calls",
    "tool_names",
    "latency_s",
    "response_preview",
    "agent_provider",
    "agent_endpoint_host",
    "agent_model",
    "judge_provider",
    "judge_endpoint_host",
    "judge_model",
    "scope",
    "correctness",
    "error",
]


def load_dataset_config() -> dict:
    with open(EVAL_DIR / "datasets.yaml", encoding="utf-8") as f:
        return (yaml.safe_load(f) or {}).get("datasets", {})


def load_dataset_csv(csv_path: str) -> pd.DataFrame:
    path = Path(csv_path)
    if not path.is_absolute():
        path = EVAL_DIR / path
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    return pd.read_csv(path)


def git_sha() -> str:
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        return f"{sha}-dirty" if dirty else sha
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def build_row(
    *,
    run_id: str,
    timestamp_utc: str,
    git_sha: str,
    dataset: str,
    prompt_version: str,
    mode: str,
    example: int,
    trial: int,
    query: str,
    run: AgentRun,
    agent,
    judge,
    scope: str,
    correctness: str,
    error: str,
) -> dict:
    """One result row. Every row carries the model and endpoint that produced it."""
    return {
        "run_id": run_id,
        "timestamp_utc": timestamp_utc,
        "git_sha": git_sha,
        "dataset": dataset,
        "prompt_version": prompt_version,
        "mode": mode,
        "example": example,
        "trial": trial,
        "query": query,
        "tool_calls": run.tool_calls,
        "tool_names": ";".join(run.tool_names),
        "latency_s": run.latency_s,
        "response_preview": (run.response or "")[:PREVIEW_CHARS],
        "agent_provider": agent.provider,
        "agent_endpoint_host": agent.host,
        "agent_model": agent.model,
        "judge_provider": judge.provider,
        "judge_endpoint_host": judge.host,
        "judge_model": judge.model,
        "scope": scope,
        "correctness": correctness,
        "error": error,
    }


def judge_row(query: str, response: str, expected: str) -> tuple[str, str, str]:
    """Run both judges. Returns (scope, correctness, error).

    Synchronous: call via asyncio.to_thread.
    """
    try:
        scope = check_answer_scope({"query": query}, {"response": response})
        correctness = match_expected_response(
            {"query": query}, {"response": response}, {"responses": expected}
        )
        return scope, correctness, ""
    except JudgeError as exc:
        return "", "", f"judge: {exc}"
    except Exception as exc:  # recorded as an error row, not scored
        return "", "", f"judge: {type(exc).__name__}: {exc}"


def _display(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def summarize(rows: list[dict]) -> dict:
    scored = [r for r in rows if not r["error"]]
    errors = len(rows) - len(scored)
    correct = sum(1 for r in scored if r["correctness"] == "correct")
    in_scope = sum(1 for r in scored if r["scope"] == "within_scope")

    by_example: dict[int, list[dict]] = {}
    for r in scored:
        by_example.setdefault(r["example"], []).append(r)
    consistent = sum(
        1
        for group in by_example.values()
        if len({r["correctness"] for r in group}) == 1
    )

    def rate(numerator: int, denominator: int) -> float:
        return round(numerator / denominator, 4) if denominator else float("nan")

    return {
        "rows": len(rows),
        "scored": len(scored),
        "errors": errors,
        "correctness_rate": rate(correct, len(scored)),
        "scope_rate": rate(in_scope, len(scored)),
        "examples": len(by_example),
        "consistent_examples": consistent,
    }


async def run_eval(
    dataset_name: str,
    *,
    prompt_version: str,
    trials: int,
    max_examples: int | None,
    use_tools: bool,
    validate: bool,
    tracing_enabled: bool = True,
    trace_path: Path | None = None,
) -> None:
    # Refuse unapproved endpoints first, before any dataset or model work.
    try:
        judge = judge_endpoint()
    except (LLMConfigError, JudgeError) as exc:
        print(f"REFUSED: {exc}")
        return

    datasets = load_dataset_config()
    if dataset_name not in datasets:
        print(f"ERROR: Unknown dataset '{dataset_name}'")
        return
    config = datasets[dataset_name]

    print(f"\nLoading dataset from {config.get('csv_path')}...")
    try:
        df = load_dataset_csv(config.get("csv_path"))
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        return
    if validate:
        required = set(config.get("input_keys", []) + config.get("output_keys", []))
        missing = required - set(df.columns)
        if missing:
            print(f"ERROR: Missing columns: {missing}")
            return
    if max_examples:
        df = df.head(max_examples)

    timestamp = datetime.now(timezone.utc)
    sha = git_sha()
    mode = "tools" if use_tools else "no_tools"
    run_id = f"{dataset_name}_{prompt_version}_{mode}_{timestamp:%Y%m%dT%H%M%SZ}"

    tracing = setup_tracing(
        TRACE_PROJECT,
        trace_path or RESULTS_DIR / f"{run_id}.traces.jsonl",
        enabled=tracing_enabled,
    )
    print(f"Traces: {tracing.destination}")

    rows: list[dict] = []
    try:
        async with PARSAgent(
            system_prompt_version=prompt_version, use_tools=use_tools
        ) as agent:
            agent_ep = agent.endpoint
            print(
                f"Agent: {agent_ep.provider} @ {agent_ep.host}, "
                f"model {agent_ep.model}, mode {mode}"
            )
            print(
                f"Judge: {judge.provider} @ {judge.host}, "
                f"model {judge.model}, temperature 0"
            )
            print(f"Running {len(df)} examples x {trials} trial(s)\n")

            for idx, row in df.iterrows():
                query = row.get("query")
                expected = row.get("responses")
                expected = (
                    ""
                    if expected is None
                    or (isinstance(expected, float) and math.isnan(expected))
                    else str(expected)
                )
                if not isinstance(query, str) or not query.strip():
                    print(f"Example {idx + 1}: SKIPPED (no query)")
                    continue

                for trial in range(1, trials + 1):
                    with tracing.span(
                        SPAN_NAME,
                        {"run_id": run_id, "example": idx + 1, "trial": trial},
                    ) as span:
                        run = await agent.run(query)
                        if run.error:
                            scope = correctness = ""
                            error = run.error
                        else:
                            scope, correctness, error = await asyncio.to_thread(
                                judge_row, query, run.response, expected
                            )
                        result_row = build_row(
                            run_id=run_id,
                            timestamp_utc=timestamp.isoformat(),
                            git_sha=sha,
                            dataset=dataset_name,
                            prompt_version=prompt_version,
                            mode=mode,
                            example=idx + 1,
                            trial=trial,
                            query=query,
                            run=run,
                            agent=agent_ep,
                            judge=judge,
                            scope=scope,
                            correctness=correctness,
                            error=error,
                        )
                        span.set_attributes(result_row)
                    rows.append(result_row)
                    status = (
                        f"[scope={scope or '-'} correct={correctness or '-'}]"
                        if not error
                        else f"[ERROR {error[:80]}]"
                    )
                    print(f"Example {idx + 1} trial {trial}: {status}")
    finally:
        tracing.shutdown()

    results = summarize(rows)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = RESULTS_DIR / f"{run_id}.csv"
    pd.DataFrame(rows, columns=COLUMNS).to_csv(csv_path, index=False)
    meta_path = RESULTS_DIR / f"{run_id}.json"
    meta_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "timestamp_utc": timestamp.isoformat(),
                "git_sha": sha,
                "dataset": dataset_name,
                "prompt_version": prompt_version,
                "mode": mode,
                "trials": trials,
                "agent_endpoint": agent_ep.__dict__,
                "judge_endpoint": judge.__dict__,
                "tracing": {
                    "backend": tracing.backend,
                    "endpoint": tracing.endpoint,
                    "jsonl_path": (
                        str(tracing.jsonl_path) if tracing.jsonl_path else ""
                    ),
                    "fallback_reason": tracing.fallback_reason,
                },
                "summary": results,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("\n" + "=" * 80)
    print(f"Run {run_id}")
    print(f"Agent: {agent_ep.provider} @ {agent_ep.host} / {agent_ep.model} ({mode})")
    print(f"Judge: {judge.provider} @ {judge.host} / {judge.model} (temperature 0)")
    print(
        f"Rows: {results['rows']}  scored: {results['scored']}  "
        f"errors: {results['errors']}"
    )
    print(f"Correctness rate: {results['correctness_rate']}")
    print(f"Scope rate:       {results['scope_rate']}")
    print(
        f"Consistent examples: {results['consistent_examples']}/{results['examples']}"
    )
    print(f"\nResults: {_display(csv_path)}")
    print(f"Metadata: {_display(meta_path)}")
    print(f"Traces: {tracing.destination}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run PARS evaluation experiments")
    parser.add_argument("--dataset-name", required=True, help="Dataset to evaluate")
    parser.add_argument(
        "--system-prompt-version",
        choices=["v1", "v2"],
        default="v1",
        help="System prompt version",
    )
    parser.add_argument("--trials", type=int, default=1, help="Repeats per example")
    parser.add_argument("--max-examples", type=int, help="Max examples to run")
    parser.add_argument(
        "--no-tools",
        action="store_true",
        help="No-tool baseline (agent gets no PARS tools)",
    )
    parser.add_argument(
        "--no-validate", action="store_true", help="Skip CSV validation"
    )
    parser.add_argument(
        "--no-phoenix",
        action="store_true",
        help="Skip Phoenix and write traces to the local JSONL file",
    )
    parser.add_argument(
        "--trace-jsonl",
        type=Path,
        help="JSONL trace path (default: results/<run_id>.traces.jsonl)",
    )
    args = parser.parse_args()
    if args.trials < 1:
        parser.error("--trials must be at least 1")
    # Resolve against the caller's cwd before the chdir below.
    trace_path = args.trace_jsonl.resolve() if args.trace_jsonl else None

    # The PARS stdio server is started as `python -m src.pars_local_mcp.mcp.server`,
    # which must run from the repository root.
    os.chdir(REPO_ROOT)
    asyncio.run(
        run_eval(
            args.dataset_name,
            prompt_version=args.system_prompt_version,
            trials=args.trials,
            max_examples=args.max_examples,
            use_tools=not args.no_tools,
            validate=not args.no_validate,
            tracing_enabled=not args.no_phoenix,
            trace_path=trace_path,
        )
    )


if __name__ == "__main__":
    main()
