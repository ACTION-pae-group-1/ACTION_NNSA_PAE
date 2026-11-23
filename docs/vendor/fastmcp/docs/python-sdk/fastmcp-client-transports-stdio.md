> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# stdio

# `fastmcp.client.transports.stdio`

## Classes

### `StdioTransport` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/stdio.py#L25](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/stdio.py#L25)</sup>

Base transport for connecting to an MCP server via subprocess with stdio.

This is a base class that can be subclassed for specific command-based
transports like Python, Node, Uvx, etc.

**Methods:**

#### `connect_session` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/stdio.py#L79](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/stdio.py#L79)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
connect_session(self, **session_kwargs: Unpack[SessionKwargs]) -> AsyncGenerator[ClientSession, None]
```

#### `connect` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/stdio.py#L98](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/stdio.py#L98)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
connect(self, **session_kwargs: Unpack[SessionKwargs]) -> ClientSession | None
```

#### `disconnect` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/stdio.py#L188](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/stdio.py#L188)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
disconnect(self)
```

#### `close` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/stdio.py#L238](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/stdio.py#L238)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
close(self)
```

### `PythonStdioTransport` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/stdio.py#L316](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/stdio.py#L316)</sup>

Transport for running Python scripts.

### `FastMCPStdioTransport` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/stdio.py#L374](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/stdio.py#L374)</sup>

Transport for running FastMCP servers using the FastMCP CLI.

`args` are passed to the server script, not interpreted as FastMCP CLI options.

### `NodeStdioTransport` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/stdio.py#L414](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/stdio.py#L414)</sup>

Transport for running Node.js scripts.

### `UvStdioTransport` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/stdio.py#L467](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/stdio.py#L467)</sup>

Transport for running commands via the uv tool.

### `UvxStdioTransport` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/stdio.py#L544](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/stdio.py#L544)</sup>

Transport for running commands via the uvx tool.

### `NpxStdioTransport` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/stdio.py#L609](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/stdio.py#L609)</sup>

Transport for running commands via the npx tool.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.