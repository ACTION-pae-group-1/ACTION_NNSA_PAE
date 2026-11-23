> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# stdio

# `fastmcp.client.transports.stdio`

## Classes

### `StdioTransport` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/stdio.py#L25](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/stdio.py#L25)</sup>

Base transport for connecting to an MCP server via subprocess with stdio.

This is a base class that can be subclassed for specific command-based
transports like Python, Node, Uvx, etc.

**Methods:**

#### `connect_session` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/stdio.py#L78](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/stdio.py#L78)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
connect_session(self, **session_kwargs: Unpack[SessionKwargs]) -> AsyncIterator[ClientSession]
```

#### `connect` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/stdio.py#L97](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/stdio.py#L97)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
connect(self, **session_kwargs: Unpack[SessionKwargs]) -> ClientSession | None
```

#### `disconnect` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/stdio.py#L169](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/stdio.py#L169)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
disconnect(self)
```

#### `close` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/stdio.py#L218](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/stdio.py#L218)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
close(self)
```

### `PythonStdioTransport` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/stdio.py#L296](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/stdio.py#L296)</sup>

Transport for running Python scripts.

### `FastMCPStdioTransport` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/stdio.py#L349](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/stdio.py#L349)</sup>

Transport for running FastMCP servers using the FastMCP CLI.

### `NodeStdioTransport` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/stdio.py#L378](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/stdio.py#L378)</sup>

Transport for running Node.js scripts.

### `UvStdioTransport` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/stdio.py#L431](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/stdio.py#L431)</sup>

Transport for running commands via the uv tool.

### `UvxStdioTransport` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/stdio.py#L508](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/stdio.py#L508)</sup>

Transport for running commands via the uvx tool.

### `NpxStdioTransport` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/stdio.py#L573](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/stdio.py#L573)</sup>

Transport for running commands via the npx tool.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.