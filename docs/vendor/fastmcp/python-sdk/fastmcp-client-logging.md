> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# logging

# `fastmcp.client.logging`

## Functions

### `default_log_handler` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/logging.py#L17](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/logging.py#L17)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
default_log_handler(message: LogMessage) -> None
```

Default handler that properly routes server log messages to appropriate log levels.

### `create_log_callback` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/logging.py#L47](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/logging.py#L47)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
create_log_callback(handler: LogHandler | None = None) -> LoggingFnT
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.