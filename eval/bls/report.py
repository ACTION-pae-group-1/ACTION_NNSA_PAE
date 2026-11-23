"""Read recorded eval runs.

    python -m eval.bls.report                      # list every recorded run
    python -m eval.bls.report --run latest         # one run's roll-up
    python -m eval.bls.report --compare A B        # per-check change from A to B

Run IDs may be shortened to any unique prefix, from the start or from
anywhere inside the ID (useful because all IDs share a timestamp head);
``latest`` is the newest run.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from eval.bls.recording import DIMENSIONS, find_run, load_runs, summary_markdown


def _rate(tally: dict[str, Any]) -> str:
    return "n/a" if not tally["total"] else f"{tally['rate'] * 100:.0f}%"


def list_runs(runs: list[dict[str, Any]]) -> str:
    header = "| Run | Agent | Commit | Episodes | All passed | "
    lines = [
        header + " | ".join(DIMENSIONS) + " |",
        "|" + " --- |" * (len(DIMENSIONS) + 5),
    ]
    for run in runs:
        summary = run["summary"]
        commit = run["git"]["sha"] + ("*" if run["git"]["dirty"] else "")
        episodes = f"{summary['scored']}"
        if summary["infrastructure_errors"]:
            episodes += f" (+{summary['infrastructure_errors']} errored)"
        cells = " | ".join(_rate(summary["dimensions"][d]) for d in DIMENSIONS)
        lines.append(
            f"| {run['run_id']} | {run['agent']} | {commit} | {episodes} | "
            f"{summary['all_checks_passed']}/{summary['scored']} | {cells} |"
        )
    lines.append("\n`*` after a commit means the run had uncommitted changes.")
    return "\n".join(lines)


def compare(before: dict[str, Any], after: dict[str, Any]) -> str:
    """Per-check pass rate in two runs, changed checks first."""
    notes = []
    for key, label in (("eval", "cases or graders"), ("tools", "tool definitions")):
        if before["fingerprints"][key] != after["fingerprints"][key]:
            notes.append(f"- The {label} differ between these runs.")
    cases_before, cases_after = (
        set(run["summary"]["cases"]) for run in (before, after)
    )
    if cases_before != cases_after:
        only_before = sorted(cases_before - cases_after) or "none"
        only_after = sorted(cases_after - cases_before) or "none"
        notes.append(
            "- The runs cover different cases, so a change in a check's pass "
            "rate may only reflect which cases ran. "
            f"Only in before: {only_before}. Only in after: {only_after}."
        )
    names = list(
        dict.fromkeys([*before["summary"]["checks"], *after["summary"]["checks"]])
    )

    def rate(run: dict[str, Any], name: str) -> float | None:
        check = run["summary"]["checks"].get(name)
        return check["rate"] if check else None

    rows = []
    for name in names:
        old, new = rate(before, name), rate(after, name)
        delta = None if old is None or new is None else new - old
        rows.append((name, old, new, delta))
    rows.sort(key=lambda row: (row[3] in (0, 0.0), -(abs(row[3]) if row[3] else 0)))

    def show(value: float | None) -> str:
        return "absent" if value is None else f"{value * 100:.0f}%"

    lines = [
        f"Comparing `{before['run_id']}` -> `{after['run_id']}`",
        *notes,
        "",
        "| Check | Before | After | Change |",
        "| --- | --- | --- | --- |",
    ]
    for name, old, new, delta in rows:
        change = (
            "n/a"
            if delta is None
            else ("same" if delta == 0 else f"{delta * 100:+.0f} pts")
        )
        lines.append(f"| {name} | {show(old)} | {show(new)} | {change} |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", help="Show one run (ID, unique prefix, or 'latest')")
    parser.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"))
    parser.add_argument(
        "--runs-dir", type=Path, help="Defaults to eval/bls/results/runs"
    )
    args = parser.parse_args()
    try:
        if args.compare:
            before, after = (find_run(r, args.runs_dir) for r in args.compare)
            print(compare(before, after))
        elif args.run:
            print(summary_markdown(find_run(args.run, args.runs_dir)))
        else:
            runs = load_runs(args.runs_dir)
            print(list_runs(runs) if runs else "No recorded runs yet.")
    except LookupError as exc:
        print(f"error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
