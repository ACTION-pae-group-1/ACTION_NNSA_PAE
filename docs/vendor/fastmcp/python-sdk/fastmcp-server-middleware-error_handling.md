> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# error_handling

# `fastmcp.server.middleware.error_handling`

Error handling middleware for consistent error responses and tracking.

## Classes

### `ErrorHandlingMiddleware` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/error\_handling.py#L17](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/error_handling.py#L17)</sup>

Middleware that provides consistent error handling and logging.

Catches exceptions, logs them appropriately, and converts them to
proper MCP error responses. Also tracks error patterns for monitoring.

**Methods:**

#### `on_message` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/error\_handling.py#L109](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/error_handling.py#L109)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_message(self, context: MiddlewareContext, call_next: CallNext) -> Any
```

Handle errors for all messages.

#### `get_error_stats` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/error\_handling.py#L123](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/error_handling.py#L123)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_error_stats(self) -> dict[str, int]
```

Get error statistics for monitoring.

### `RetryMiddleware` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/error\_handling.py#L128](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/error_handling.py#L128)</sup>

Middleware that implements automatic retry logic for failed requests.

Retries requests that fail with transient errors, using exponential
backoff to avoid overwhelming the server or external dependencies.

**Methods:**

#### `on_request` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/error\_handling.py#L194](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/error_handling.py#L194)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_request(self, context: MiddlewareContext, call_next: CallNext) -> Any
```

Implement retry logic for requests.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.