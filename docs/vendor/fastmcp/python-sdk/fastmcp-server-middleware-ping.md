> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# ping

# `fastmcp.server.middleware.ping`

Ping middleware for keeping client connections alive.

## Classes

### `PingMiddleware` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/ping.py#L12](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/ping.py#L12)</sup>

Middleware that sends periodic pings to keep client connections alive.

Starts a background ping task on first message from each session. The task
sends server-to-client pings at the configured interval until the session
ends.

**Methods:**

#### `on_message` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/ping.py#L44](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/ping.py#L44)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_message(self, context: MiddlewareContext, call_next: CallNext) -> Any
```

Start ping task on first message from a connection.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.