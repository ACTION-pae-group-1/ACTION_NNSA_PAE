"""Tests for the PARS agent wrapper: prompt loading, endpoint use, and error rows."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

EVAL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL_DIR))

import llm_endpoint  # noqa: E402
from agent import PARSAgent  # noqa: E402

_LLM_VARS = (
    "LLM_PROVIDER",
    "LLM_BASE_URL",
    "LLM_API_KEY",
    "ASKSAGE_API_KEY",
    "LLM_CHAT_MODEL",
    "LLM_VISION_MODEL",
    "LLM_AUTH_HEADER",
    "JUDGE_MODEL",
)


@pytest.fixture
def approved_env(monkeypatch):
    for name in _LLM_VARS:
        monkeypatch.delenv(name, raising=False)
    # Keep the real portable .env out of these tests.
    monkeypatch.setattr(llm_endpoint, "PORTABLE_ENV", EVAL_DIR / "tests" / "absent.env")
    monkeypatch.setenv("LLM_PROVIDER", "asksage")
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("LLM_CHAT_MODEL", "gpt-5.4-gov")
    return monkeypatch


def test_v1_and_v2_system_prompts_load_and_differ(approved_env) -> None:
    v1 = PARSAgent(system_prompt_version="v1", use_tools=False)
    v2 = PARSAgent(system_prompt_version="v2", use_tools=False)
    assert v1.system_prompt.strip()
    assert v2.system_prompt.strip()
    assert v1.system_prompt != v2.system_prompt


def test_unknown_prompt_version_is_refused(approved_env) -> None:
    with pytest.raises(FileNotFoundError):
        PARSAgent(system_prompt_version="v9", use_tools=False)


def test_no_tools_mode_reports_the_approved_endpoint(approved_env) -> None:
    agent = PARSAgent(use_tools=False)
    assert agent.mode == "no_tools"
    assert agent.endpoint.provider == "asksage"
    assert agent.endpoint.host == "api.nnsa.asksage.ai"
    assert agent.endpoint.model == "gpt-5.4-gov"


def test_tools_mode_is_reported(approved_env) -> None:
    assert PARSAgent(use_tools=True).mode == "tools"


def test_answer_is_returned_without_an_error(approved_env, monkeypatch) -> None:
    agent = PARSAgent(use_tools=False)

    async def fake_ask(query, system_prompt=None):
        return "There are two projects."

    monkeypatch.setattr(agent._agent, "ask", fake_ask)
    run = asyncio.run(agent.run("How many projects?"))
    assert run.response == "There are two projects."
    assert run.error == ""
    assert run.tool_calls == 0


def test_agent_failure_becomes_an_error_row_not_an_answer(
    approved_env, monkeypatch
) -> None:
    agent = PARSAgent(use_tools=False)

    async def failing_ask(query, system_prompt=None):
        raise RuntimeError("upstream 502")

    monkeypatch.setattr(agent._agent, "ask", failing_ask)
    run = asyncio.run(agent.run("How many projects?"))
    assert run.response == ""
    assert run.error == "agent: RuntimeError: upstream 502"
