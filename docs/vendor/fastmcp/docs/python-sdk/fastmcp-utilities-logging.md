> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# logging

# `fastmcp.utilities.logging`

Logging utilities for FastMCP.

## Functions

### `get_logger` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/logging.py#L27](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/logging.py#L27)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_logger(name: str) -> logging.Logger
```

Get a logger nested under FastMCP namespace.

**Args:**

* `name`: the name of the logger, which will be prefixed with 'FastMCP.'

**Returns:**

* a configured logger instance

### `configure_logging` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/logging.py#L42](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/logging.py#L42)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
configure_logging(level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] | int = 'INFO', logger: logging.Logger | None = None, enable_rich_tracebacks: bool | None = None, **rich_kwargs: Any) -> None
```

Configure logging for FastMCP.

**Args:**

* `logger`: the logger to configure
* `level`: the log level to use
* `rich_kwargs`: the parameters to use for creating RichHandler

### `temporary_log_level` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/logging.py#L127](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/logging.py#L127)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
temporary_log_level(level: str | None, logger: logging.Logger | None = None, enable_rich_tracebacks: bool | None = None, **rich_kwargs: Any)
```

Context manager to temporarily set log level and restore it afterwards.

**Args:**

* `level`: The temporary log level to set (e.g., "DEBUG", "INFO")
* `logger`: Optional logger to configure (defaults to FastMCP logger)
* `enable_rich_tracebacks`: Whether to enable rich tracebacks
* `**rich_kwargs`: Additional parameters for RichHandler


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.