> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Progress Monitoring

> Handle progress notifications from long-running server operations.

New in version `2.3.5`

Use this when you need to track progress of long-running operations.

MCP servers can report progress during operations. The client receives these updates through a progress handler.

## Progress Handler

Set a handler when creating the client:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from pathlib import Path

from fastmcp import Client

async def progress_handler(
    progress: float,
    total: float | None,
    message: str | None
) -> None:
    if total:
        percentage = (progress / total) * 100
        print(f"Progress: {percentage:.1f}% - {message or ''}")
    else:
        print(f"Progress: {progress} - {message or ''}")

client = Client(
    Path("my_mcp_server.py"),
    progress_handler=progress_handler
)
```

The handler receives three parameters:

> [card] Handler Parameters
>
> **progress** `float`
>
> Current progress value
>
> **total** `float | None`
>
> Expected total value (may be None if unknown)
>
> **message** `str | None`
>
> Optional status message

## Per-Call Handler

Override the client-level handler for specific tool calls:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
async with client:
    result = await client.call_tool(
        "long_running_task",
        {"param": "value"},
        progress_handler=my_progress_handler
    )
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.