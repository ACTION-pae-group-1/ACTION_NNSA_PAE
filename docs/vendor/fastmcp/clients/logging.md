> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
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
LOGGING_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "NOTICE": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
    "ALERT": logging.CRITICAL,
    "EMERGENCY": logging.CRITICAL,
}

async def log_handler(message: LogMessage):
    """Forward MCP server logs to Python's logging system."""
    data = message.data
    if isinstance(data, dict):
        msg = data.get('msg', data)
        extra = data.get('extra')
    else:
        msg = data
        extra = None

    # Python's logging requires `extra` to be a mapping, but a server can send
    # any JSON value, so fold anything else into the message instead.
    if extra is not None and not isinstance(extra, dict):
        msg = f"{msg} ({extra})"
        extra = None

    level = LOGGING_LEVEL_MAP.get(message.level.upper(), logging.INFO)
    logger.log(level, msg, extra=extra)

client = Client(
    "my_mcp_server.py",
    log_handler=log_handler,
)
```

The handler receives a `LogMessage` object:

> **LogMessage**
>
> **level** `Literal["debug", "info", "notice", "warning", "error", "critical", "alert", "emergency"]`
>
> The log level
>
> **logger** `str | None`
>
> The logger name (may be None)
>
> **data** `Any`
>
> The JSON-serializable log payload sent by the server. FastMCP's structured logger uses a dictionary with `msg` and `extra` keys, but other MCP servers may send any JSON value.

## Structured Logs

The `message.data` attribute contains the server's JSON-serializable log payload. FastMCP servers commonly send a dictionary with `msg` and `extra` keys, which enables structured logging with rich contextual information.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
async def detailed_log_handler(message: LogMessage):
    data = message.data
    msg = data.get('msg', data) if isinstance(data, dict) else data
    extra = data.get('extra') if isinstance(data, dict) else None

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
from pathlib import Path
client = Client(Path("my_mcp_server.py"))

async with client:
    # Server logs are forwarded at proper severity automatically
    await client.call_tool("some_tool")
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.