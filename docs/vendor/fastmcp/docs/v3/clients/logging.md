> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Server Logging

> Receive and handle log messages from MCP servers.

New in version `2.0.0`

Use this when you need to capture or process log messages sent by the server.

MCP servers can emit log messages to clients. The client handles these through a log handler callback.

## Log Handler

Provide a `log_handler` function when creating the client:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
import logging
from fastmcp import Client
from fastmcp.client.logging import LogMessage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
LOGGING_LEVEL_MAP = logging.getLevelNamesMapping()

async def log_handler(message: LogMessage):
    """Forward MCP server logs to Python's logging system."""
    msg = message.data.get('msg')
    extra = message.data.get('extra')

    level = LOGGING_LEVEL_MAP.get(message.level.upper(), logging.INFO)
    logger.log(level, msg, extra=extra)

client = Client(
    "my_mcp_server.py",
    log_handler=log_handler,
)
```

The handler receives a `LogMessage` object:

> [card] LogMessage
>
> **level** `Literal["debug", "info", "notice", "warning", "error", "critical", "alert", "emergency"]`
>
> The log level
>
> **logger** `str | None`
>
> The logger name (may be None)
>
> **data** `dict`
>
> The log payload, containing `msg` and `extra` keys

## Structured Logs

The `message.data` attribute is a dictionary containing the log payload. This enables structured logging with rich contextual information.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
async def detailed_log_handler(message: LogMessage):
    msg = message.data.get('msg')
    extra = message.data.get('extra')

    if message.level == "error":
        print(f"ERROR: {msg} | Details: {extra}")
    elif message.level == "warning":
        print(f"WARNING: {msg} | Details: {extra}")
    else:
        print(f"{message.level.upper()}: {msg}")
```

This structure is preserved even when logs are forwarded through a FastMCP proxy, making it useful for debugging multi-server applications.

## Default Behavior

If you do not provide a custom `log_handler`, FastMCP's default handler routes server logs to Python's logging system at the appropriate severity level. The MCP levels map as follows: `notice` becomes INFO; `alert` and `emergency` become CRITICAL.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
client = Client("my_mcp_server.py")

async with client:
    # Server logs are forwarded at proper severity automatically
    await client.call_tool("some_tool")
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.