"""Run eval episodes and report graded results by dimension.

    python -m eval.bls.runner --selftest          # no model; proves the graders
    python -m eval.bls.runner --agent oracle      # scripted reference run
    python -m eval.bls.runner --agent model       # a real model (LLM_* env vars)

Every episode gets a fresh server and its own saved-specifications file. All
episodes read one synthetic snapshot built at the start of the run.

Agent runs are recorded under ``eval/bls/results/runs`` (see
:mod:`eval.bls.recording`); read them back with ``python -m eval.bls.report``.
Pass ``--no-record`` to skip that. The self-test is a check of the harness,
not a result, so it is not recorded.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

import httpx
from fastmcp import Client

from bls_mcp.config import Settings
from bls_mcp.server import create_server
from eval.bls import tracing, world
from eval.bls.agents import SCRIPTED, SYSTEM_PROMPT, Agent, ModelAgent
from eval.bls.cases import CASES, Case
from eval.bls.graders import Check
from eval.bls.recording import (
    DIMENSIONS,
    RESULTS_DIR,
    EpisodeResult,
    RunMetadata,
    fingerprint_tools,
    git_state,
    record_run,
    summarize,
)
from eval.bls.transcript import Message, ToolSession, Transcript
from portable_llm_mcp.llm_client import LLMUnavailableError

#: Failures of the model endpoint or network. They say nothing about how the
#: agent behaves, so such episodes are recorded but left out of the scores.
INFRASTRUCTURE_ERRORS = (
    LLMUnavailableError,
    httpx.HTTPError,
    TimeoutError,
    ConnectionError,
)

#: Checks each flawed scripted agent must fail, proving the graders catch it.
# For the new scenarios, require the specific intended failure. Additional
# failures may occur as downstream consequences of that mistake.
NEW_EXPECTED_FAILURES: dict[str, set[str]] = {
    "skips-ambiguous-confirmation": {
        "user confirmed the proposed basket before the final calculation",
    },
    "substitutes-cement": {
        "basket matches the stated commodities and percentages",
        "composite factor equals the known answer",
    },
    "hides-new-alignment": {
        "answer states each quarterly-sourced series' year-quarter",
    },
    "fabricates-future": {
        "unavailable 2030 period explained",
        "no fabricated future factor",
    },
    "silently-normalizes": {
        "invalid 115 percent total identified",
        "user corrected invalid weights before calculation",
        "basket matches the stated commodities and percentages",
    },
    "omits-audit-method": {
        "weighted index-relative method disclosed",
    },
}


EXPECTED_FAILURES: dict[str, set[str]] = {
    "assumes-target-year": {
        "asked for the target year before calculating",
        "periods are 2014 -> 2026",
        "composite factor equals the known answer",
    },
    "bare-number-answer": {
        "answer states the percent change",
        "answer cites every series ID",
        "answer states each series with its own weight",
        "answer states base and target periods",
        "answer cites the snapshot ID",
    },
    "swaps-cited-weights": {
        "answer states each series with its own weight",
    },
    "recalls-series-ids": {
        "every series was found through the catalog tools before use",
    },
    "hides-alignment": {
        "answer states each quarterly-sourced series' year-quarter",
    },
    "misattributes-quarters": {
        "answer states each quarterly-sourced series' year-quarter",
    },
    "changes-basket-after-confirmation": {
        "user confirmed the proposed basket before the final calculation",
    },
    "validates-after-calculating": {
        "the calculated specification was validated first, without errors",
    },
    "skips-confirmation": {
        "user confirmed the proposed basket before the final calculation",
    },
    "ignores-stated-share": {
        "steel carries the share the user stated (0.5)",
    },
    "guesses-everything": {
        "clarified periods and weights before calculating",
        "clarified project type or scope before calculating",
        "user confirmed the proposed basket before the final calculation",
        "steel carries the share the user stated (0.5)",
    },
}


def _settings(registry: Path, workdir: Path) -> Settings:
    return Settings(
        BLS_SNAPSHOT_REGISTRY_DIR=str(registry),
        BLS_SPECS_DB_PATH=str(workdir / "specs.duckdb"),
        BLS_API_KEY=None,
    )


async def run_episode(
    case: Case, agent: Agent, registry: Path, workdir: Path
) -> Transcript:
    """One conversation between the scripted user and *agent*."""
    transcript = Transcript()
    async with Client(create_server(_settings(registry, workdir))) as client:
        tools = ToolSession(client, transcript)
        message: str | None = case.user.opening
        for turn in range(1, case.max_turns + 1):
            if message is None:
                break
            tools.turn = turn
            transcript.messages.append(Message(turn, "user", message))
            try:
                with tracing.span("agent.turn", turn=turn):
                    reply = await agent.respond(message, tools)
            except Exception as exc:  # an agent failure is a result, not a crash
                transcript.error = f"{type(exc).__name__}: {exc}"
                transcript.infrastructure_failure = isinstance(
                    exc, INFRASTRUCTURE_ERRORS
                )
                break
            transcript.messages.append(Message(turn, "agent", reply))
            answer = case.user.reply(reply, frozenset(transcript.revealed))
            if answer is None:
                break
            message, facts = answer
            for fact in facts:
                transcript.revealed.setdefault(fact, turn + 1)
    return transcript


def grade(case: Case, transcript: Transcript) -> list[Check]:
    checks = [check for grader in case.graders for check in grader(transcript)]
    checks.append(
        Check(
            "episode finished without an agent error",
            "process",
            transcript.error is None,
            transcript.error or "",
        )
    )
    return checks


async def run(
    agent_name: str,
    make_agent: Callable[[Case], Agent | None],
    cases: list[Case],
    registry: Path,
    root: Path,
    *,
    repetition: int = 1,
) -> list[EpisodeResult]:
    results = []
    for case in cases:
        agent = make_agent(case)
        if agent is None:
            continue
        workdir = root / f"{agent_name}-{case.id}-{repetition}"
        workdir.mkdir(parents=True)
        started = time.perf_counter()
        with tracing.span(
            "bls.eval.episode",
            case_id=case.id,
            agent=agent_name,
            repetition=repetition,
            git_sha=git_state()["sha"],
        ) as episode_span:
            episode_trace_id = tracing.trace_id(episode_span)
            transcript = await run_episode(case, agent, registry, workdir)
            checks = grade(case, transcript)
            if episode_span is not None:
                episode_span.set_attribute("eval.passed", all(c.passed for c in checks))
                episode_span.set_attribute(
                    "eval.infrastructure_error", transcript.infrastructure_failure
                )
                episode_span.set_attribute(
                    "eval.failed_checks", sum(not c.passed for c in checks)
                )
        results.append(
            EpisodeResult(
                case.id,
                agent_name,
                checks,
                transcript,
                trace_id=episode_trace_id,
                repetition=repetition,
                duration_seconds=time.perf_counter() - started,
                infrastructure_error=(
                    transcript.error if transcript.infrastructure_failure else None
                ),
            )
        )
    return results


async def tool_fingerprint(registry: Path, workdir: Path) -> str:
    """Fingerprint of the tool definitions the server exposes to agents."""
    workdir.mkdir(parents=True, exist_ok=True)
    async with Client(create_server(_settings(registry, workdir))) as client:
        return fingerprint_tools(list(await client.list_tools()))


def scripted(name: str) -> Callable[[Case], Agent | None]:
    def make(case: Case) -> Agent | None:
        factory = SCRIPTED[case.id].get(name)
        return factory() if factory else None

    return make


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


def table(results: list[EpisodeResult]) -> str:
    header = "| Agent | Case | " + " | ".join(DIMENSIONS) + " | Failed checks |"
    lines = [header, "|" + " --- |" * (len(DIMENSIONS) + 3)]
    for result in results:
        cells = []
        for dimension in DIMENSIONS:
            passed, total = result.score(dimension)
            cells.append(f"{passed}/{total}")
        if result.scored:
            failed = "; ".join(sorted(result.failed)) or "none"
        else:
            failed = f"NOT SCORED: {result.infrastructure_error}"
        label = result.agent
        if result.repetition > 1:
            label += f" #{result.repetition}"
        lines.append(
            f"| {label} | {result.case_id} | " + " | ".join(cells) + f" | {failed} |"
        )
    return "\n".join(lines)


def rollup(results: list[EpisodeResult]) -> str:
    summary = summarize(results)
    parts = []
    for dimension in DIMENSIONS:
        tally = summary["dimensions"][dimension]
        rate = "n/a" if not tally["total"] else f"{tally['rate'] * 100:.0f}%"
        parts.append(f"{dimension} {rate}")
    line = (
        f"{summary['all_checks_passed']}/{summary['scored']} episodes passed every "
        "check; " + ", ".join(parts)
    )
    if summary["infrastructure_errors"]:
        line += f"; {summary['infrastructure_errors']} episode(s) not scored"
    return line


def details(results: list[EpisodeResult]) -> str:
    lines = []
    for result in results:
        if not result.scored:
            continue
        for check in result.checks:
            if not check.passed:
                lines.append(
                    f"- {result.agent} / {result.case_id} / {check.dimension}: "
                    f"{check.name} ({check.detail})"
                )
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Entry points
# --------------------------------------------------------------------------


async def selftest(registry: Path, root: Path) -> tuple[list[EpisodeResult], list[str]]:
    """Oracles must pass everything; each flawed agent must fail as expected."""
    cases = list(CASES.values())
    results = await run("oracle", scripted("oracle"), cases, registry, root)
    problems = [
        f"oracle failed on {r.case_id}: {sorted(r.failed)}" for r in results if r.failed
    ]
    for name, expected in {**EXPECTED_FAILURES, **NEW_EXPECTED_FAILURES}.items():
        flawed = await run(name, scripted(name), cases, registry, root)
        results.extend(flawed)
        for result in flawed:
            if (
                not expected.issubset(result.failed)
                if name in NEW_EXPECTED_FAILURES
                else result.failed != expected
            ):
                problems.append(
                    f"{name} on {result.case_id}: expected exactly "
                    f"{sorted(expected)}, failed {sorted(result.failed)}"
                )
    return results, problems


async def model_run(
    registry: Path, root: Path, cases: list[Case], repetitions: int
) -> tuple[list[EpisodeResult], dict[str, str]]:
    """Run the configured model; returns results and which model it was."""
    from portable_llm_mcp import create_llm_client, load_llm_settings

    settings = load_llm_settings()
    llm = create_llm_client(settings)
    results: list[EpisodeResult] = []
    try:
        for repetition in range(1, repetitions + 1):
            results.extend(
                await run(
                    settings.chat_model,
                    lambda case: ModelAgent(llm, settings.chat_model),
                    cases,
                    registry,
                    root,
                    repetition=repetition,
                )
            )
    finally:
        await llm.aclose()
    # Never record credentials: only the provider and the model name.
    model = {"provider": settings.provider.value, "name": settings.chat_model}
    return results, model


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument(
        "--agent", default="oracle", help="oracle, a flaw name, or model"
    )
    parser.add_argument("--case", choices=sorted(CASES), action="append")
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--write-summary", action="store_true")
    parser.add_argument("--no-record", action="store_true")
    args = parser.parse_args()
    tracing.configure()
    if args.repetitions < 1:
        parser.error("--repetitions must be at least 1")
    cases = [CASES[name] for name in args.case] if args.case else list(CASES.values())

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        registry = world.build_world(root / "world")
        episodes = root / "episodes"
        problems: list[str] = []
        meta: RunMetadata | None = None
        if args.selftest:
            results, problems = asyncio.run(selftest(registry, episodes))
        elif args.agent == "model":
            meta = RunMetadata("model", "model", args.repetitions)
            results, meta.model = asyncio.run(
                model_run(registry, episodes, cases, args.repetitions)
            )
            meta.agent = meta.model["name"]
            meta.system_prompt = SYSTEM_PROMPT
        else:
            meta = RunMetadata(args.agent, "scripted")
            results = asyncio.run(
                run(args.agent, scripted(args.agent), cases, registry, episodes)
            )
        if meta is not None and not args.no_record:
            meta.tool_fingerprint = asyncio.run(
                tool_fingerprint(registry, root / "fingerprint")
            )

    print(table(results))
    if details(results):
        print("\nFailed checks:\n" + details(results))
    print("\n" + rollup(results))

    if meta is not None and not args.no_record:
        if results:
            print(f"Recorded: {record_run(meta, results)}")
        else:
            print("Nothing to record: no agent ran.")

    tracing.shutdown()

    if args.selftest:
        if args.write_summary:
            RESULTS_DIR.mkdir(exist_ok=True)
            (RESULTS_DIR / "SELFTEST.md").write_text(
                "# Eval self-test\n\n"
                "Command: `python -m eval.bls.runner --selftest --write-summary`, "
                f"run on a working tree based on commit `{git_state()['sha']}`.\n\n"
                "The oracle agents must pass every check. Each flawed agent makes "
                "one known mistake and must fail exactly the checks listed for it."
                f"\n\nResult: {'PASS' if not problems else 'FAIL'}\n\n"
                + table(results)
                + "\n",
                encoding="utf-8",
            )
        if problems:
            print("\nSELFTEST FAILED:\n" + "\n".join(problems))
            sys.exit(1)
        print("\nSELFTEST PASSED: oracles pass; every flawed agent is caught.")


if __name__ == "__main__":
    main()
