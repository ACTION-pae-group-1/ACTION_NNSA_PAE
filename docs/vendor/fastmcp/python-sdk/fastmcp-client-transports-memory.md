> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# memory

# `fastmcp.client.transports.memory`

## Classes

### `FastMCPTransport` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/memory.py#L37](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/memory.py#L37)</sup>

In-memory transport for FastMCP servers.

This transport connects directly to a FastMCP server instance in the same
Python process. It works with both FastMCP servers and the SDK's own
high-level `MCPServer` from the low-level MCP SDK. This is particularly
useful for unit tests or scenarios where client and server run in the same
runtime.

**Methods:**

#### `connect_session` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/memory.py#L58](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/memory.py#L58)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
connect_session(self, **session_kwargs: Unpack[SessionKwargs]) -> AsyncIterator[ClientSession]
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.