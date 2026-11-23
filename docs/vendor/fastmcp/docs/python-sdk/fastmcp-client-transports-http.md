> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# http

# `fastmcp.client.transports.http`

Streamable HTTP transport for FastMCP Client.

## Classes

### `StreamableHttpTransport` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/http.py#L31](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/http.py#L31)</sup>

Transport implementation that connects to an MCP server via Streamable HTTP Requests.

**Methods:**

#### `connect_session` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/http.py#L161](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/http.py#L161)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
connect_session(self, **session_kwargs: Unpack[SessionKwargs]) -> AsyncGenerator[ClientSession, None]
```

#### `get_session_id` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/http.py#L236](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/http.py#L236)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_session_id(self) -> str | None
```

#### `close` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/http.py#L239](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/http.py#L239)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
close(self)
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.