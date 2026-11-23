> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# sse

# `fastmcp.client.transports.sse`

Server-Sent Events (SSE) transport for FastMCP Client.

## Classes

### `SSETransport` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/sse.py#L33](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/sse.py#L33)</sup>

Transport implementation that connects to an MCP server via Server-Sent Events.

**Methods:**

#### `connect_session` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/sse.py#L132](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/sse.py#L132)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
connect_session(self, **session_kwargs: Unpack[SessionKwargs]) -> AsyncIterator[ClientSession]
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.