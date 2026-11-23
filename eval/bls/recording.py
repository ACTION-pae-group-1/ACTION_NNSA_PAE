"""Durable records of eval runs.

Each recorded run gets its own directory under ``eval/bls/results/runs``:

    <run_id>/run.json        metadata, every check, and the roll-up (commit this)
    <run_id>/summary.md      the same roll-up as a readable table (commit this)
    <run_id>/episodes.jsonl  full transcripts, one episode per line (ignored)
    <run_id>/errors.jsonl    infrastructure failures, never scored (ignored)

``run.json`` is the single source of truth; :mod:`eval.bls.report` reads only
those files, so there is no separate index to fall out of step.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from eval.bls import world
from eval.bls.graders import Check
from eval.bls.transcript import Transcript

SCHEMA_VERSION = 1
RESULTS_DIR = Path(__file__).parent / "results"
RUNS_DIR = RESULTS_DIR / "runs"
DIMENSIONS = ("process", "accuracy", "format", "guardrails")
#: Source files that define what is measured; their hash is the eval version.
#: agents.py and transcript.py are included because a scripted agent is the
#: system under test for scripted runs, and graders read the transcript.
EVAL_SOURCES = (
    "cases.py",
    "graders.py",
    "world.py",
    "simulated_user.py",
    "agents.py",
    "transcript.py",
)


@dataclass
class EpisodeResult:
    case_id: str
    agent: str
    checks: list[Check]
    transcript: Transcript
    repetition: int = 1
    trace_id: str | None = None
    duration_seconds: float = 0.0
    #: Set when the episode failed for reasons outside the agent's behaviour
    #: (model endpoint down, timeout). Such episodes are recorded, not scored.
    infrastructure_error: str | None = None

    @property
    def scored(self) -> bool:
        return self.infrastructure_error is None

    @property
    def failed(self) -> set[str]:
        return {check.name for check in self.checks if not check.passed}

    def score(self, dimension: str) -> tuple[int, int]:
        checks = [c for c in self.checks if c.dimension == dimension]
        return sum(c.passed for c in checks), len(checks)


@dataclass
class RunMetadata:
    agent: str
    kind: str  # "scripted" or "model"
    repetitions: int = 1
    model: dict[str, str] = field(default_factory=dict)
    system_prompt: str = ""
    tool_fingerprint: str = ""
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# --------------------------------------------------------------------------
# Fingerprints: what was under test
# --------------------------------------------------------------------------


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def fingerprint_tools(tools: list[Any]) -> str:
    """Hash of every tool's name, description and input schema.

    Agent behaviour depends on these, and nothing in the code breaks when
    they change, so each run records which version it saw.
    """
    described = sorted(
        (
            tool.name,
            tool.description or "",
            json.dumps(tool.inputSchema, sort_keys=True),
        )
        for tool in tools
    )
    return _digest(json.dumps(described))


def fingerprint_eval() -> str:
    """Hash of the cases, graders, world and scripted user."""
    here = Path(__file__).parent
    return _digest("".join((here / name).read_text("utf-8") for name in EVAL_SOURCES))


def git_state(
    repo_root: Path | None = None, results_dir: Path | None = None
) -> dict[str, Any]:
    """The commit under test and whether the working tree differs from it.

    Recorded results are excluded from the dirty check: a run's own output,
    or an earlier run's, is not a change to the code being evaluated.
    """
    root = repo_root if repo_root is not None else world.REPO_ROOT
    results = results_dir if results_dir is not None else RESULTS_DIR

    def git(*args: str) -> str:
        done = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            cwd=root,
            check=False,
        )
        return done.stdout.strip()

    status = ["status", "--porcelain", "--", "."]
    try:
        relative = results.resolve().relative_to(Path(root).resolve())
    except ValueError:
        relative = None
    if relative is not None:
        status.append(f":(exclude){relative.as_posix()}")
    return {
        "sha": git("rev-parse", "--short", "HEAD") or "unknown",
        "dirty": bool(git(*status)),
    }


# --------------------------------------------------------------------------
# Roll-up
# --------------------------------------------------------------------------


def summarize(results: list[EpisodeResult]) -> dict[str, Any]:
    """Pass counts per dimension, per check and per case over scored episodes."""
    scored = [r for r in results if r.scored]

    def tally(checks: list[Check]) -> dict[str, Any]:
        passed = sum(c.passed for c in checks)
        return {
            "passed": passed,
            "total": len(checks),
            "rate": round(passed / len(checks), 4) if checks else None,
        }

    every = [check for result in scored for check in result.checks]
    by_check: dict[str, dict[str, Any]] = {}
    for name in dict.fromkeys(check.name for check in every):
        matching = [c for c in every if c.name == name]
        by_check[name] = {"dimension": matching[0].dimension, **tally(matching)}

    by_case: dict[str, dict[str, Any]] = {}
    for case_id in dict.fromkeys(r.case_id for r in scored):
        episodes = [r for r in scored if r.case_id == case_id]
        by_case[case_id] = {
            "episodes": len(episodes),
            "all_checks_passed": sum(not r.failed for r in episodes),
            "dimensions": {
                d: tally([c for r in episodes for c in r.checks if c.dimension == d])
                for d in DIMENSIONS
            },
        }

    return {
        "episodes": len(results),
        "scored": len(scored),
        "infrastructure_errors": len(results) - len(scored),
        "all_checks_passed": sum(not r.failed for r in scored),
        "dimensions": {
            d: tally([c for c in every if c.dimension == d]) for d in DIMENSIONS
        },
        "cases": by_case,
        "checks": by_check,
    }


def _percent(tally: dict[str, Any]) -> str:
    if not tally["total"]:
        return "n/a"
    return f"{tally['rate'] * 100:.0f}% ({tally['passed']}/{tally['total']})"


def summary_markdown(run: dict[str, Any]) -> str:
    """A readable roll-up of one recorded run."""
    summary = run["summary"]
    model = run.get("model") or {}
    git = run["git"]
    lines = [
        f"# Eval run {run['run_id']}",
        "",
        f"- Agent: `{run['agent']}` ({run['kind']})"
        + (
            f", model `{model.get('name')}` via {model.get('provider')}"
            if model
            else ""
        ),
        f"- Started: {run['started_at']}",
        f"- Commit: `{git['sha']}`"
        + (" (uncommitted changes)" if git["dirty"] else ""),
        f"- Fingerprints: eval `{run['fingerprints']['eval']}`, "
        f"tools `{run['fingerprints']['tools']}`, "
        f"system prompt `{run['fingerprints']['system_prompt']}`",
        f"- Episodes: {summary['episodes']} run, {summary['scored']} scored, "
        f"{summary['infrastructure_errors']} infrastructure error(s) excluded",
        f"- Episodes passing every check: "
        f"{summary['all_checks_passed']}/{summary['scored']}",
        "",
        "## By case",
        "",
        "| Case | Episodes | All checks passed | " + " | ".join(DIMENSIONS) + " |",
        "|" + " --- |" * (len(DIMENSIONS) + 3),
    ]
    for case_id, case in summary["cases"].items():
        cells = " | ".join(_percent(case["dimensions"][d]) for d in DIMENSIONS)
        lines.append(
            f"| {case_id} | {case['episodes']} | "
            f"{case['all_checks_passed']}/{case['episodes']} | {cells} |"
        )
    lines += [
        "",
        "## By check",
        "",
        "| Dimension | Check | Passed |",
        "| --- | --- | --- |",
    ]
    for name, check in summary["checks"].items():
        lines.append(f"| {check['dimension']} | {name} | {_percent(check)} |")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# Writing and reading
# --------------------------------------------------------------------------


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-") or "agent"


def record_run(
    meta: RunMetadata,
    results: list[EpisodeResult],
    *,
    runs_dir: Path | None = None,
) -> Path:
    """Write one run's record and return its directory."""
    runs_dir = runs_dir if runs_dir is not None else RUNS_DIR
    finished = datetime.now(UTC)
    run_id = f"{meta.started_at:%Y%m%dT%H%M%SZ}-{_slug(meta.agent)}"
    directory = runs_dir / run_id
    suffix = 1
    while True:
        try:
            directory.mkdir(parents=True, exist_ok=False)
            break
        except FileExistsError:
            # Two runs of the same agent starting in the same second must not
            # lose the record of the run that just finished.
            suffix += 1
            run_id = f"{meta.started_at:%Y%m%dT%H%M%SZ}-{_slug(meta.agent)}-{suffix}"
            directory = runs_dir / run_id

    run = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "agent": meta.agent,
        "kind": meta.kind,
        "model": meta.model,
        "repetitions": meta.repetitions,
        "started_at": meta.started_at.isoformat(timespec="seconds"),
        "finished_at": finished.isoformat(timespec="seconds"),
        "git": git_state(),
        "snapshot_id": world.SNAPSHOT_ID,
        "fingerprints": {
            "eval": fingerprint_eval(),
            "tools": meta.tool_fingerprint or "unknown",
            "system_prompt": _digest(meta.system_prompt)
            if meta.system_prompt
            else "none",
        },
        "summary": summarize(results),
        "episodes": [
            {
                "case": r.case_id,
                "trace_id": r.trace_id,
                "repetition": r.repetition,
                "scored": r.scored,
                "duration_seconds": round(r.duration_seconds, 3),
                "turns": len(r.transcript.agent_messages()),
                "tool_calls": len(r.transcript.tool_calls),
                "error": r.infrastructure_error or r.transcript.error,
                "scores": {d: list(r.score(d)) for d in DIMENSIONS},
                "checks": [asdict(c) for c in r.checks],
            }
            for r in results
        ],
    }
    (directory / "run.json").write_text(json.dumps(run, indent=2) + "\n", "utf-8")
    (directory / "summary.md").write_text(summary_markdown(run), "utf-8")

    with (directory / "episodes.jsonl").open("w", encoding="utf-8") as handle:
        for r in results:
            line = {
                "case": r.case_id,
                "trace_id": r.trace_id,
                "repetition": r.repetition,
                "transcript": asdict(r.transcript),
            }
            handle.write(json.dumps(line, default=str) + "\n")

    errors = [r for r in results if not r.scored]
    if errors:
        with (directory / "errors.jsonl").open("w", encoding="utf-8") as handle:
            for r in errors:
                line = {
                    "case": r.case_id,
                    "repetition": r.repetition,
                    "error": r.infrastructure_error,
                }
                handle.write(json.dumps(line) + "\n")
    return directory


def load_runs(runs_dir: Path | None = None) -> list[dict[str, Any]]:
    """Every recorded run, oldest first."""
    runs_dir = runs_dir if runs_dir is not None else RUNS_DIR
    runs = [
        json.loads(path.read_text("utf-8"))
        for path in sorted(runs_dir.glob("*/run.json"))
    ]
    return sorted(runs, key=lambda run: run["started_at"])


def find_run(run_id: str, runs_dir: Path | None = None) -> dict[str, Any]:
    """The run whose ID equals, uniquely starts with, or uniquely contains
    *run_id*; "latest" works."""
    runs = load_runs(runs_dir)
    if not runs:
        raise LookupError("No recorded runs")
    if run_id == "latest":
        return runs[-1]
    matches = [run for run in runs if run["run_id"].startswith(run_id)]
    if not matches:
        # Mid-ID prefixes match as a substring, so "214134" finds
        # "20261115T214134Z-oracle"; all IDs share a timestamp head.
        matches = [run for run in runs if len(run_id) >= 4 and run_id in run["run_id"]]
    if len(matches) != 1:
        raise LookupError(f"{len(matches)} runs match {run_id!r}")
    return matches[0]
