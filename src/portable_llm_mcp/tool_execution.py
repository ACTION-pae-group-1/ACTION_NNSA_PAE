"""Bounded parallelism for explicitly approved independent read-only tools.

Tool descriptions / readOnlyHint annotations are untrusted hints, not permission
for speculative parallel execution.  Callers must supply an explicit list of
qualified tool names that are safe to run concurrently.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Collection, Sequence

from .llm_client import ToolCall


async def execute_tool_calls(
    calls: Sequence[ToolCall],
    invoke: Callable[[str, dict], Awaitable[str]],
    *,
    parallel_read_only_tools: Collection[str] = (),
    max_parallel_read_only: int = 1,
) -> list[str]:
    """Execute one model batch; preserve model-specified order in the results.

    If *any* call might have side effects or depend on a prior call, the whole
    batch stays sequential.  Only explicit read-only calls may fan out.
    """
    if max_parallel_read_only < 1:
        raise ValueError("max_parallel_read_only must be at least 1")
    if (
        max_parallel_read_only == 1
        or len(calls) < 2
        or not all(c.name in parallel_read_only_tools for c in calls)
    ):
        results = []
        for call in calls:
            results.append(await invoke(call.name, call.arguments))
        return results

    limiter = asyncio.Semaphore(max_parallel_read_only)

    async def run(call: ToolCall) -> str:
        async with limiter:
            return await invoke(call.name, call.arguments)

    return list(await asyncio.gather(*(run(call) for call in calls)))
