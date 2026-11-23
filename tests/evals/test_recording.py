"""Recording eval runs: what is written, rolled up, and read back."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from eval.bls import world
from eval.bls.cases import CASES
from eval.bls.graders import Check
from eval.bls.recording import (
    EpisodeResult,
    RunMetadata,
    find_run,
    fingerprint_eval,
    git_state,
    load_runs,
    record_run,
    summarize,
)
from eval.bls.report import compare, list_runs
from eval.bls.runner import run, scripted
from eval.bls.transcript import Transcript
from portable_llm_mcp.llm_client import LLMUnavailableError


def episode(case: str, passed: dict[str, bool], **kwargs: object) -> EpisodeResult:
    checks = [
        Check(name, "format" if "answer" in name else "accuracy", ok)
        for name, ok in passed.items()
    ]
    return EpisodeResult(case, "agent", checks, Transcript(), **kwargs)  # type: ignore[arg-type]


def test_summarize_counts_by_dimension_check_and_case() -> None:
    results = [
        episode("a", {"factor": True, "answer cites": True}),
        episode("a", {"factor": False, "answer cites": True}, repetition=2),
        episode("b", {"factor": True, "answer cites": False}),
    ]
    summary = summarize(results)

    assert (summary["episodes"], summary["scored"]) == (3, 3)
    assert summary["all_checks_passed"] == 1
    assert summary["dimensions"]["accuracy"] == {
        "passed": 2,
        "total": 3,
        "rate": 0.6667,
    }
    assert summary["dimensions"]["process"]["rate"] is None  # no such checks
    assert summary["checks"]["answer cites"]["passed"] == 2
    assert summary["cases"]["a"]["all_checks_passed"] == 1
    assert summary["cases"]["a"]["dimensions"]["accuracy"]["rate"] == 0.5


def test_infrastructure_errors_are_recorded_but_not_scored(tmp_path: Path) -> None:
    results = [
        episode("a", {"factor": True}),
        episode("a", {"factor": False}, infrastructure_error="endpoint down"),
    ]
    summary = summarize(results)
    assert (summary["scored"], summary["infrastructure_errors"]) == (1, 1)
    assert summary["dimensions"]["accuracy"]["rate"] == 1.0

    directory = record_run(RunMetadata("m", "model"), results, runs_dir=tmp_path)
    errors = [json.loads(line) for line in (directory / "errors.jsonl").open()]
    assert errors == [{"case": "a", "repetition": 1, "error": "endpoint down"}]


@pytest.mark.asyncio
async def test_endpoint_failure_is_classified_as_infrastructure(
    tmp_path: Path,
) -> None:
    class EndpointDown:
        async def respond(self, user_message: str, tools: object) -> str:
            raise LLMUnavailableError("503")

    class BadBehaviour:
        async def respond(self, user_message: str, tools: object) -> str:
            raise RuntimeError("Model exceeded 20 tool rounds")

    registry = world.build_world(tmp_path / "world")
    case = [CASES["known-basket-missing-target-year"]]
    down = await run("down", lambda c: EndpointDown(), case, registry, tmp_path / "a")
    bad = await run("bad", lambda c: BadBehaviour(), case, registry, tmp_path / "b")

    assert not down[0].scored
    assert down[0].infrastructure_error == "LLMUnavailableError: 503"
    # Running out of tool rounds is the agent's behaviour, so it is scored.
    assert bad[0].scored
    assert "episode finished without an agent error" in bad[0].failed


@pytest.mark.asyncio
async def test_recorded_run_round_trips(tmp_path: Path) -> None:
    registry = world.build_world(tmp_path / "world")
    cases = list(CASES.values())
    results = await run(
        "oracle", scripted("oracle"), cases, registry, tmp_path / "episodes"
    )
    meta = RunMetadata(
        "oracle", "scripted", tool_fingerprint="abc123", system_prompt="be careful"
    )
    directory = record_run(meta, results, runs_dir=tmp_path / "runs")

    assert sorted(p.name for p in directory.iterdir()) == [
        "episodes.jsonl",
        "run.json",
        "summary.md",
    ]
    run_record = find_run("latest", tmp_path / "runs")
    assert run_record["run_id"] == directory.name
    assert run_record["schema_version"] == 1
    assert run_record["snapshot_id"] == world.SNAPSHOT_ID
    assert run_record["fingerprints"]["eval"] == fingerprint_eval()
    assert run_record["fingerprints"]["tools"] == "abc123"
    assert run_record["fingerprints"]["system_prompt"] != "be careful"  # hashed
    assert run_record["summary"]["all_checks_passed"] == len(cases)
    assert [e["case"] for e in run_record["episodes"]] == [c.id for c in cases]
    assert all(
        isinstance(e["tool_calls"], int)
        and e["tool_calls"] >= 0
        and isinstance(e["turns"], int)
        and e["turns"] >= 0
        for e in run_record["episodes"]
    )
    # run.json holds scores, not conversations; transcripts live in the sidecar.
    assert "transcript" not in run_record["episodes"][0]
    lines = [json.loads(line) for line in (directory / "episodes.jsonl").open()]
    assert lines[0]["transcript"]["messages"][0]["role"] == "user"
    assert "100% (" in (directory / "summary.md").read_text()


def test_report_lists_finds_and_compares_runs(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    good = [episode("a", {"factor": True, "answer cites": True})]
    worse = [episode("a", {"factor": True, "answer cites": False})]
    first = record_run(
        RunMetadata("v1", "model", started_at=datetime(2026, 1, 1, tzinfo=UTC)),
        good,
        runs_dir=tmp_path,
    )
    second = record_run(
        RunMetadata("v2", "model", started_at=datetime(2026, 1, 2, tzinfo=UTC)),
        worse,
        runs_dir=tmp_path,
    )
    runs = load_runs(tmp_path)
    assert [r["run_id"] for r in runs] == [first.name, second.name]

    listing = list_runs(runs)
    assert first.name in listing and "| 1/1 |" in listing and "| 0/1 |" in listing

    assert find_run("20260101", tmp_path)["agent"] == "v1"
    with pytest.raises(LookupError, match="2 runs match"):
        find_run("2026", tmp_path)
    with pytest.raises(LookupError, match="0 runs match"):
        find_run("nope", tmp_path)

    diff = compare(runs[0], runs[1]).splitlines()
    rows = [line for line in diff if line.startswith("| ")][2:]  # skip the header
    # The regressed check is listed first, with its change in points.
    assert rows[0] == "| answer cites | 100% | 0% | -100 pts |"
    assert rows[1] == "| factor | 100% | 100% | same |"
    assert "different cases" not in "\n".join(diff)

    # A run over a different set of cases is flagged, naming the difference.
    other = record_run(
        RunMetadata("v3", "model", started_at=datetime(2026, 1, 3, tzinfo=UTC)),
        [*good, episode("b", {"factor": True, "answer cites": True})],
        runs_dir=tmp_path,
    )
    warned = compare(runs[0], find_run(other.name, tmp_path))
    assert "The runs cover different cases" in warned
    assert "Only in before: none. Only in after: ['b']." in warned


def test_same_second_runs_get_distinct_directories(tmp_path: Path) -> None:
    """A run with the same start-second is recorded alongside, never on top of.

    A completed run must not lose its record to a same-second collision; the
    second record gets a disambiguating suffix.
    """
    from datetime import UTC, datetime

    meta = RunMetadata("m", "model", started_at=datetime(2026, 1, 1, tzinfo=UTC))
    first = record_run(meta, [episode("a", {"factor": True})], runs_dir=tmp_path)
    second = record_run(meta, [episode("a", {"factor": True})], runs_dir=tmp_path)

    assert first != second
    assert first.name.endswith("Z-m")
    assert second.name.endswith("Z-m-2")
    assert (first / "run.json").is_file()
    assert (second / "run.json").is_file()


def test_find_run_matches_a_mid_id_prefix(tmp_path: Path) -> None:
    """A unique substring of the run ID finds the run; ambiguity fails loudly."""
    oracle = record_run(
        RunMetadata("oracle", "scripted"),
        [episode("a", {"factor": True})],
        runs_dir=tmp_path,
    )
    record_run(
        RunMetadata("flawed", "scripted"),
        [episode("a", {"factor": True})],
        runs_dir=tmp_path,
    )

    assert find_run("oracle", tmp_path)["run_id"] == oracle.name
    with pytest.raises(LookupError):
        find_run(oracle.name[:4], tmp_path)  # "2026" matches both
    with pytest.raises(LookupError):
        find_run("abc", tmp_path)  # no match, even with the fallback


@pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")
def test_recorded_results_do_not_make_the_tree_dirty(tmp_path: Path) -> None:
    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

    git("init", "-q")
    git("config", "user.email", "eval@example.invalid")
    git("config", "user.name", "eval")
    (tmp_path / "server.py").write_text("x = 1\n")
    results = tmp_path / "eval" / "results"
    (results / "runs").mkdir(parents=True)
    (results / "SELFTEST.md").write_text("old\n")
    git("add", ".")
    git("commit", "-q", "-m", "init")

    def dirty() -> bool:
        return git_state(tmp_path, results)["dirty"]

    assert not dirty()
    # A previous run's output, and edits to committed results, are not code.
    (results / "runs" / "20261116T000000Z-agent").mkdir()
    (results / "runs" / "20261116T000000Z-agent" / "run.json").write_text("{}")
    (results / "SELFTEST.md").write_text("new\n")
    assert not dirty()
    # Anything else still counts.
    (tmp_path / "notes.txt").write_text("untracked\n")
    assert dirty()
    (tmp_path / "notes.txt").unlink()
    (tmp_path / "server.py").write_text("x = 2\n")
    assert dirty()
