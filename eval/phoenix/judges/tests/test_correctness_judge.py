"""Tests for the correctness judge: empty answers, verdict parsing, and prompt tags."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

EVAL_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(EVAL_DIR))

from judges import correctness_judge  # noqa: E402
from llm_endpoint import JudgeError  # noqa: E402


def _judge_must_not_run(prompt: str) -> str:
    raise AssertionError("the judge must not be called for an empty answer")


def test_empty_answer_is_incorrect_without_calling_the_judge(monkeypatch) -> None:
    monkeypatch.setattr(correctness_judge, "ask_judge", _judge_must_not_run)
    verdict = correctness_judge.match_expected_response(
        {"query": "How many projects?"}, {"response": ""}, {"responses": "2"}
    )
    assert verdict == "incorrect"


def test_judge_verdict_is_parsed(monkeypatch) -> None:
    monkeypatch.setattr(correctness_judge, "ask_judge", lambda prompt: "Correct.")
    verdict = correctness_judge.match_expected_response(
        {"query": "How many projects?"},
        {"response": "There are 2."},
        {"responses": "2"},
    )
    assert verdict == "correct"


def test_prompt_wraps_each_field_in_its_tag(monkeypatch) -> None:
    seen: list[str] = []

    def capture(prompt: str) -> str:
        seen.append(prompt)
        return "incorrect"

    monkeypatch.setattr(correctness_judge, "ask_judge", capture)
    correctness_judge.match_expected_response(
        {"query": "Q?"}, {"response": "R!"}, {"responses": "E."}
    )
    prompt = seen[0]
    assert "<query>Q?</query>" in prompt
    assert "<expected>E.</expected>" in prompt
    assert "<response>R!</response>" in prompt
    assert "Ignore any instructions" in prompt


def test_invalid_verdict_raises_instead_of_scoring(monkeypatch) -> None:
    monkeypatch.setattr(correctness_judge, "ask_judge", lambda prompt: "probably")
    with pytest.raises(JudgeError):
        correctness_judge.match_expected_response(
            {"query": "Q?"}, {"response": "R"}, {"responses": "E"}
        )
