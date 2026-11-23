"""The eval harness itself: graders discriminate, and the pieces behave."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from eval.bls import world
from eval.bls.agents import ModelAgent
from eval.bls.cases import CASES, KNOWN_BASKET_FACTOR
from eval.bls.runner import grade, run_episode, selftest
from eval.bls.simulated_user import (
    Fact,
    SimulatedUser,
    asking_parts,
    question_sentences,
)
from portable_llm_mcp.llm_client import REPLAY_KEY, Completion, ToolCall


@pytest.fixture(scope="module")
def registry(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return world.build_world(tmp_path_factory.mktemp("world"))


def test_known_answer_is_hand_computable() -> None:
    """0.45*(310/200) + 0.35*(252/180) + 0.20*(195/150) = 1.4475."""
    assert KNOWN_BASKET_FACTOR == pytest.approx(0.6975 + 0.49 + 0.26)
    assert KNOWN_BASKET_FACTOR == pytest.approx(1.4475)


@pytest.mark.asyncio
async def test_selftest_oracles_pass_and_flawed_agents_are_caught(
    registry: Path, tmp_path: Path
) -> None:
    results, problems = await selftest(registry, tmp_path)
    assert problems == []
    assert {r.agent for r in results} >= {"oracle", "assumes-target-year"}


def test_user_answers_only_what_is_asked() -> None:
    user = SimulatedUser(
        "hello",
        (
            Fact("year", ("year",), "2026."),
            Fact("scope", ("labor",), "Materials only."),
        ),
    )
    assert user.reply("Which year do you want?") == ("2026.", ["year"])
    # A statement that mentions a keyword is not a question.
    assert user.reply("I will use the year 2026 and skip labor.") is None
    # A question no fact answers ends the conversation.
    assert user.reply("Anything else?") is None
    # Already-disclosed facts are not repeated alongside a new one...
    both = "Which year, and is labor included?"
    assert user.reply(both, frozenset({"year"})) == ("Materials only.", ["scope"])
    # ...but are repeated if that is all the agent asks about.
    assert user.reply("Which year?", frozenset({"year"})) == ("2026.", ["year"])


def test_user_answers_requests_phrased_as_statements() -> None:
    """Phrasings real models used in the first runs, which ended episodes."""
    user = SimulatedUser(
        "hello",
        (
            Fact("year", ("year", "period"), "2026."),
            Fact("ok", ("confirm", "approve", "satisfied with"), "Yes."),
        ),
    )
    assert user.reply("Please confirm if you would like to proceed.") == (
        "Yes.",
        ["ok"],
    )
    assert user.reply("**Do you approve of these weights?** If so, I will.") == (
        "Yes.",
        ["ok"],
    )
    assert user.reply("Are you satisfied with this allocation?") == ("Yes.", ["ok"])
    # A list introduced as a request is read item by item...
    lead_in = "To do this, I'll need a few details:\n1. **Target period** - which"
    assert user.reply(lead_in) == ("2026.", ["year"])
    # ...and so is one the agent refers back to.
    refer = "I'll need:\n- The target period\n\nCould you provide these details?"
    assert user.reply(refer) == ("2026.", ["year"])


def test_offers_results_and_proposals_are_not_requests() -> None:
    user = SimulatedUser("hello", (Fact("year", ("year", "period"), "2026."),))
    # A conditional offer at the end of an answer ends the conversation.
    assert user.reply("Done. Let me know if you'd like a different year.") is None
    # Lists of results are not read unless the agent asks about them.
    result = "Factor 1.45.\n- Base period 2014\n- Target year 2026\nThanks."
    assert user.reply(result) is None
    assert asking_parts("Here are the steps:\n1. Pick the year\n2. Calculate") == []


def test_question_sentences_handles_lists() -> None:
    text = "I found three series.\n- Which year?\n- Labor too?\nThanks."
    assert question_sentences(text) == ["- Which year?", "- Labor too?"]


class ScriptedLLM:
    """Replays completions and records the requests it was sent."""

    def __init__(self, completions: list[Completion]) -> None:
        self.completions = completions
        self.requests: list[dict[str, Any]] = []

    async def complete(self, **kwargs: Any) -> Completion:
        self.requests.append(
            {"messages": list(kwargs["messages"]), "tools": kwargs["tools"]}
        )
        return self.completions.pop(0)


@pytest.mark.asyncio
async def test_model_agent_calls_tools_and_keeps_the_conversation(
    registry: Path, tmp_path: Path
) -> None:
    """The adapter exposes MCP tools, feeds results back, and spans user turns."""
    llm = ScriptedLLM(
        [
            Completion(
                tool_calls=[
                    ToolCall(
                        "call-1",
                        "search_series",
                        {"request": {"query": "sawmills", "programs": ["pc"]}},
                    )
                ]
            ),
            Completion(content="Which year should I escalate to?"),
            Completion(content="Thanks, 2026 it is."),
        ]
    )
    case = CASES["known-basket-missing-target-year"]
    transcript = await run_episode(case, ModelAgent(llm, "fake"), registry, tmp_path)

    assert [c.name for c in transcript.tool_calls] == ["search_series"]
    assert transcript.revealed == {"target_year": 2}
    assert [m.role for m in transcript.messages] == ["user", "agent", "user", "agent"]
    tool_names = {t["function"]["name"] for t in llm.requests[0]["tools"]}
    assert "calculate_index_from_bls" in tool_names
    # The tool result reached the model, and turn two saw the whole history.
    assert llm.requests[1]["messages"][-1]["role"] == "tool"
    assert world.SAWMILLS in llm.requests[1]["messages"][-1]["content"]
    assert len(llm.requests[2]["messages"]) > len(llm.requests[1]["messages"])
    # It asked, but never calculated: accuracy and format checks must fail.
    failed = {c.name for c in grade(case, transcript) if not c.passed}
    assert "result comes from calculate_index_from_bls" in failed
    assert "asked for the target year before calculating" not in failed


@pytest.mark.asyncio
async def test_model_agent_replays_provider_content_append_only(
    registry: Path, tmp_path: Path
) -> None:
    """Thinking-model turns go back verbatim, and history is never rewritten."""
    tool_turn = [{"type": "thinking", "thinking": "", "signature": "s1"}]
    ask_turn = [{"type": "text", "text": "Which year should I escalate to?"}]
    llm = ScriptedLLM(
        [
            Completion(
                tool_calls=[
                    ToolCall(
                        "call-1",
                        "search_series",
                        {"request": {"query": "sawmills", "programs": ["pc"]}},
                    )
                ],
                replay=tool_turn,
            ),
            Completion(content="Which year should I escalate to?", replay=ask_turn),
            Completion(content="Thanks, 2026 it is."),
        ]
    )
    case = CASES["known-basket-missing-target-year"]
    await run_episode(case, ModelAgent(llm, "fake"), registry, tmp_path)

    later = llm.requests[2]["messages"]
    assistant = [m for m in later if m["role"] == "assistant"]
    assert [m.get(REPLAY_KEY) for m in assistant] == [tool_turn, ask_turn]
    for earlier, after in zip(llm.requests, llm.requests[1:], strict=False):
        assert after["messages"][: len(earlier["messages"])] == earlier["messages"]


@pytest.mark.asyncio
async def test_agent_error_is_recorded_not_raised(
    registry: Path, tmp_path: Path
) -> None:
    class Crashes:
        async def respond(self, user_message: str, tools: Any) -> str:
            raise RuntimeError("model unavailable")

    case = CASES["known-basket-missing-target-year"]
    transcript = await run_episode(case, Crashes(), registry, tmp_path)
    assert transcript.error == "RuntimeError: model unavailable"
    failed = {c.name for c in grade(case, transcript) if not c.passed}
    assert "episode finished without an agent error" in failed


def test_cited_weights_pairs_each_series_with_its_nearest_weight() -> None:
    from eval.bls.graders import cited_weights, weight_mismatches

    a, b = "PCU327320327320", "PCU331110331110"
    text = f"- 45% {a}: 200.0 -> 310.0\n- {b} carries 0.35 of the cost (index 1.0 base)"
    assert cited_weights(text, {a, b}) == {a: 0.45, b: 0.35}
    assert weight_mismatches(text, {a: 0.45, b: 0.35}) == []
    # Swapped shares are reported per series; index levels never count as weights.
    assert len(weight_mismatches(text, {a: 0.35, b: 0.45})) == 2
    assert cited_weights(f"{a}: 200.0 -> 310.0", {a}) == {a: None}


def test_alignment_disclosed_requires_quarters_next_to_the_series() -> None:
    """Quarter tokens only count on the line of the quarterly-sourced series."""
    from eval.bls.graders import alignment_disclosed
    from eval.bls.transcript import Message, ToolCall, Transcript

    labor = "CIU1010000000000I"
    result = {
        "result": {
            "components": [
                {
                    "series_id": labor,
                    "base_period": {
                        "year": 2014,
                        "quarter": 4,
                        "periodicity": "QUARTERLY",
                    },
                    "target_period": {
                        "year": 2026,
                        "quarter": 4,
                        "periodicity": "QUARTERLY",
                    },
                }
            ]
        }
    }
    call = ToolCall(
        turn=2,
        name="calculate_index_from_bls",
        arguments={"spec_id": "s"},
        result=result,
        is_error=False,
    )

    def transcript_with(answer: str) -> Transcript:
        return Transcript(
            messages=[
                Message(1, "user", "escalate"),
                Message(2, "agent", answer),
            ],
            tool_calls=[call],
        )

    correct = (
        "- 60% PCU327320327320: 200.0 -> 310.0\n"
        f"- 40% {labor}: 140.0 -> 224.0 (observed 2014-Q04, 2026-Q04)"
    )
    assert alignment_disclosed(transcript_with(correct))[0].passed

    misattributed = (
        "- 60% PCU327320327320: 200.0 -> 310.0 (observed 2014-Q04, 2026-Q04)\n"
        f"- 40% {labor}: 140.0 -> 224.0"
    )
    check = alignment_disclosed(transcript_with(misattributed))[0]
    assert not check.passed
    assert labor in check.detail


# ---------------------------------------------------------------------------
# Discovery through get_series_hierarchy
# ---------------------------------------------------------------------------


class _FindsSawmillsThroughHierarchy:
    """Searches the parent industry, then takes Sawmills from its sub-items.

    This is the workflow the server instructions ask for, so the discovery
    guardrail must credit it.
    """

    def __init__(self) -> None:
        from eval.bls.agents import KnownBasketOracle

        self.oracle = KnownBasketOracle()

    async def respond(self, user_message: str, tools: Any) -> str:
        from eval.bls.agents import calculate, cited_answer, find_series, year_in

        oracle = self.oracle
        if not oracle.basket:
            for query, weight in (
                ("ready-mix concrete manufacturing", 0.45),
                ("iron and steel mills", 0.35),
            ):
                oracle.basket[await find_series(tools, query, 2014)] = weight
            await tools.call(
                "search_series",
                {"request": {"query": "sawmills and wood preservation"}},
            )
            found = await tools.call(
                "get_series_hierarchy", {"series_id": "PCU32111-32111-"}
            )
            sawmills = next(
                e["series_id"]
                for e in found.result["sub_items"]
                if e["name"] == "Sawmills"
            )
            oracle.basket[sawmills] = 0.20
            return "Which year should I escalate the 2014 estimate to?"
        target = year_in(user_message, not_year=2014)
        response = await calculate(tools, "via-hierarchy", oracle.basket, 2014, target)
        return cited_answer(response)


@pytest.mark.asyncio
async def test_series_found_through_hierarchy_counts_as_discovered(
    registry: Path, tmp_path: Path
) -> None:
    """Search a parent, pick its sub-item, calculate: every check passes."""
    case = CASES["known-basket-missing-target-year"]
    transcript = await run_episode(
        case, _FindsSawmillsThroughHierarchy(), registry, tmp_path
    )
    assert "get_series_hierarchy" in [c.name for c in transcript.tool_calls]
    failed = {c.name for c in grade(case, transcript) if not c.passed}
    assert failed == set()


@pytest.mark.asyncio
async def test_hierarchy_does_not_launder_the_series_it_was_asked_about(
    registry: Path, tmp_path: Path
) -> None:
    """Only related series are discovered; the queried ID itself is not."""
    from eval.bls.graders import returned_series
    from eval.bls.transcript import ToolCall

    call = ToolCall(
        1,
        "get_series_hierarchy",
        {"series_id": "PCU32111-32111-"},
        {
            "series_id": "PCU32111-32111-",
            "parents": [{"series_id": "PCU3211--3211--"}, {"series_id": None}],
            "sub_items": [{"series_id": world.SAWMILLS}],
        },
        False,
    )
    assert returned_series(call) == {"PCU3211--3211--", world.SAWMILLS}
    failed_call = ToolCall(1, "get_series_hierarchy", {}, None, True)
    assert returned_series(failed_call) == set()


def test_expanded_cases_have_distinct_ids_and_scripted_agents() -> None:
    from eval.bls.agents import SCRIPTED

    added = {
        "ambiguous-escalation-request",
        "commodity-series-selection",
        "mixed-labor-materials-alignment",
        "unavailable-target-period",
        "invalid-weighted-basket",
        "source-provenance-audit",
    }
    assert len(CASES) == 9
    assert added <= CASES.keys()
    for case_id in added:
        assert "oracle" in SCRIPTED[case_id]
        assert len(SCRIPTED[case_id]) >= 2


def test_new_numeric_oracles_are_independent_of_mcp() -> None:
    from eval.bls.cases import AMBIGUOUS_BASKET, COMMODITY_BASKET

    assert world.composite(AMBIGUOUS_BASKET, 2014, 2026) == pytest.approx(1.505)
    assert world.composite(COMMODITY_BASKET, 2014, 2026) == pytest.approx(1.565)
    assert world.composite(
        {world.READY_MIX: 0.6, world.LABOR_COST: 0.4}, 2014, 2026
    ) == pytest.approx(1.57)


def test_unavailable_period_grading_does_not_require_calculation() -> None:
    from eval.bls.transcript import Message, Transcript

    transcript = Transcript(
        messages=[
            Message(1, "user", CASES["unavailable-target-period"].user.opening),
            Message(
                1,
                "agent",
                "2030 annual observations are unavailable in the active snapshot.",
            ),
        ]
    )
    checks = grade(CASES["unavailable-target-period"], transcript)
    assert all(check.passed for check in checks)
    assert not any(
        check.name == "result comes from calculate_index_from_bls" for check in checks
    )


def test_invalid_basket_user_supplies_correction_only_when_asked() -> None:
    user = CASES["invalid-weighted-basket"].user
    assert user.reply("These weights total 115%.") is None
    reply = user.reply("The weights total 115%. Can you correct the weights?")
    assert reply is not None
    assert reply[1] == ["corrected_weights"]


def test_commodity_confirmation_requires_correct_explicit_mapping() -> None:
    user = CASES["commodity-series-selection"].user
    correct = (
        "Proposed series and weights:\n"
        f"- {world.STRUCTURAL_METAL}: 60%\n"
        f"- {world.READY_MIX}: 25%\n"
        f"- {world.GYPSUM}: 15%\n"
        "Do you approve these series and weights?"
    )
    response = user.reply(correct)
    assert response is not None
    assert response[1] == ["confirmation"]
    assert "validate and calculate" in response[0]
    assert user.reply("I found the series.") is None
    vague = user.reply("Please confirm the basket.")
    assert vague is not None
    assert vague[1] == ["proposal_needs_review"]
    wrong = user.reply(correct.replace("15%", "20%"))
    assert wrong is not None
    assert wrong[1] == ["proposal_needs_review"]
