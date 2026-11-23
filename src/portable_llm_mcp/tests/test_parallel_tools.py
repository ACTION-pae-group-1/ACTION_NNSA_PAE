"""Independent read-only tool calls can overlap; writes cannot."""

from __future__ import annotations

import asyncio

import pytest

from portable_llm_mcp.llm_client import ToolCall
from portable_llm_mcp.tool_execution import execute_tool_calls


def call(name: str, i: int) -> ToolCall:
    return ToolCall(str(i), name, {"i": i})


@pytest.mark.asyncio
async def test_explicit_read_only_calls_overlap_and_preserve_order() -> None:
    active = 0
    peak = 0

    async def invoke(_name: str, args: dict) -> str:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01 * (3 - args["i"]))
        active -= 1
        return str(args["i"])

    results = await execute_tool_calls(
        [call("bls_server__search_series", i) for i in range(3)],
        invoke,
        parallel_read_only_tools={"bls_server__search_series"},
        max_parallel_read_only=2,
    )
    assert results == ["0", "1", "2"]
    assert peak == 2


@pytest.mark.asyncio
async def test_mixed_read_write_batch_stays_sequential() -> None:
    active = 0
    peak = 0
    visited: list[str] = []

    async def invoke(name: str, _args: dict) -> str:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        visited.append(name)
        await asyncio.sleep(0)
        active -= 1
        return name

    calls = [
        call("bls_server__search_series", 0),
        call("bls_server__save_index_spec", 1),
    ]
    results = await execute_tool_calls(
        calls,
        invoke,
        parallel_read_only_tools={"bls_server__search_series"},
        max_parallel_read_only=3,
    )
    assert results == visited == [c.name for c in calls]
    assert peak == 1


@pytest.mark.asyncio
async def test_parallel_execution_is_opt_in() -> None:
    active = 0
    peak = 0

    async def invoke(name: str, _args: dict) -> str:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0)
        active -= 1
        return name

    calls = [call("bls_server__search_series", i) for i in range(3)]
    await execute_tool_calls(calls, invoke, max_parallel_read_only=3)
    assert peak == 1


@pytest.mark.asyncio
async def test_bad_concurrency_limit_rejected() -> None:
    with pytest.raises(ValueError, match="at least 1"):
        await execute_tool_calls([], lambda *_: None, max_parallel_read_only=0)
