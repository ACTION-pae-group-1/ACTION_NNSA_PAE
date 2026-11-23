> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# logging

# `fastmcp.server.middleware.logging`

Comprehensive logging middleware for FastMCP servers.

## Functions

### `default_serializer` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/logging.py#L15](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/logging.py#L15)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
default_serializer(data: Any) -> str
```

The default serializer for Payloads in the logging middleware.

## Classes

### `BaseLoggingMiddleware` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/logging.py#L20](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/logging.py#L20)</sup>

Base class for logging middleware.

**Methods:**

#### `on_message` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/logging.py#L124](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/logging.py#L124)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_message(self, context: MiddlewareContext[Any], call_next: CallNext[Any, Any]) -> Any
```

Log messages for configured methods.

### `LoggingMiddleware` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/logging.py#L148](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/logging.py#L148)</sup>

Middleware that provides comprehensive request and response logging.

Logs all MCP messages with configurable detail levels. Useful for debugging,
monitoring, and understanding server usage patterns.

### `StructuredLoggingMiddleware` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/logging.py#L203](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/logging.py#L203)</sup>

Middleware that provides structured JSON logging for better log analysis.

Outputs structured logs that are easier to parse and analyze with log
aggregation tools like ELK stack, Splunk, or cloud logging services.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.