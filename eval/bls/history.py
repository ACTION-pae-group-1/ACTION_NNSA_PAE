"""Longitudinal score history derived from immutable BLS eval run records.

    python -m eval.bls.history
    python -m eval.bls.history --format csv --output score_history.csv
    python -m eval.bls.history --runs-dir /path/to/runs

No transcripts are read or exported. Runs with different eval fingerprints are
shown together but must not be interpreted as directly comparable scores.
"""

from __future__ import annotations

import argparse
import csv
import io
from pathlib import Path
from typing import Any

from eval.bls.recording import DIMENSIONS, load_runs

FIELDS = (
    "run_id",
    "started_at",
    "agent",
    "kind",
    "provider",
    "model",
    "git_sha",
    "git_dirty",
    "eval_fingerprint",
    "tool_fingerprint",
    "prompt_fingerprint",
    "snapshot_id",
    "repetitions",
    "case_id",
    "episodes",
    "scored",
    "infrastructure_errors",
    "all_checks_passed",
    "success_rate",
    *(f"{dimension}_rate" for dimension in DIMENSIONS),
)


def history_rows(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One suite-level and one case-level row per run, with explicit denominators."""
    rows: list[dict[str, Any]] = []
    for run in runs:
        summary = run["summary"]
        base = {
            "run_id": run["run_id"],
            "started_at": run["started_at"],
            "agent": run["agent"],
            "kind": run["kind"],
            "provider": (run.get("model") or {}).get("provider", ""),
            "model": (run.get("model") or {}).get("name", ""),
            "git_sha": run["git"]["sha"],
            "git_dirty": run["git"]["dirty"],
            "eval_fingerprint": run["fingerprints"]["eval"],
            "tool_fingerprint": run["fingerprints"]["tools"],
            "prompt_fingerprint": run["fingerprints"]["system_prompt"],
            "snapshot_id": run["snapshot_id"],
            "repetitions": run["repetitions"],
        }
        for case_id, stats in [("__suite__", summary), *summary["cases"].items()]:
            scored = stats["scored"] if case_id == "__suite__" else stats["episodes"]
            passed = stats["all_checks_passed"]
            row = {
                **base,
                "case_id": case_id,
                "episodes": summary["episodes"] if case_id == "__suite__" else scored,
                "scored": scored,
                "infrastructure_errors": summary["infrastructure_errors"]
                if case_id == "__suite__"
                else "",
                "all_checks_passed": passed,
                "success_rate": round(passed / scored, 4) if scored else None,
                **{f"{d}_rate": stats["dimensions"][d]["rate"] for d in DIMENSIONS},
            }
            rows.append(row)
    return rows


def render_csv(rows: list[dict[str, Any]]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def render_markdown(rows: list[dict[str, Any]]) -> str:
    def percent(value: Any) -> str:
        return "n/a" if value is None else f"{value * 100:.1f}%"

    lines = [
        "# BLS eval score history",
        "",
        "Derived from recorded run.json files. `__suite__` is the overall run; "
        "other rows are individual cases.",
        "Compare scores only with matching eval fingerprints, case coverage, "
        "and compatible model/prompt/snapshot settings.",
        "",
        "| Run | Model / agent | Commit | Eval fingerprint | Case | Passed | Success | Process | Accuracy | Format | Guardrails |",  # noqa: E501
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",  # noqa: E501
    ]
    for row in rows:
        model = row["model"] or row["agent"]
        lines.append(
            f"| {row['run_id']} | {model} | {row['git_sha']} | "
            f"{row['eval_fingerprint']} | {row['case_id']} | "
            f"{row['all_checks_passed']}/{row['scored']} | "
            f"{percent(row['success_rate'])} | "
            + " | ".join(percent(row[f"{d}_rate"]) for d in DIMENSIONS)
            + " |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--runs-dir", type=Path, help="Directory containing recorded runs"
    )
    parser.add_argument("--format", choices=("markdown", "csv"), default="markdown")
    parser.add_argument(
        "--output", type=Path, help="Write report to this path instead of stdout"
    )
    args = parser.parse_args()
    rows = history_rows(load_runs(args.runs_dir))
    result = render_csv(rows) if args.format == "csv" else render_markdown(rows)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
    else:
        print(result, end="")


if __name__ == "__main__":
    main()
