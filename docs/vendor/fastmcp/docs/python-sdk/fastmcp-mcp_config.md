> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# mcp_config

# `fastmcp.mcp_config`

Canonical MCP Configuration Format.

This module defines the standard configuration format for Model Context Protocol (MCP) servers.
It provides a client-agnostic, extensible format that can be used across all MCP implementations.

The configuration format supports both stdio and remote (HTTP/SSE) transports, with comprehensive
field definitions for server metadata, authentication, and execution parameters.

Example configuration:

```json theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
{
    "mcpServers": {
        "my-server": {
            "command": "npx",
            "args": ["-y", "@my/mcp-server"],
            "env": {"API_KEY": "secret"},
            "timeout": 30000,
            "description": "My MCP server"
        }
    }
}
```

## Functions

### `infer_transport_type_from_url` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/mcp\_config.py#L56](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/mcp_config.py#L56)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
infer_transport_type_from_url(url: str | AnyUrl) -> Literal['http', 'sse']
```

Infer the appropriate transport type from the given URL.

### `update_config_file` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/mcp\_config.py#L424](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/mcp_config.py#L424)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
update_config_file(file_path: Path, server_name: str, server_config: CanonicalMCPServerTypes) -> None
```

Update an MCP configuration file from a server object, preserving existing fields.

This is used for updating the mcpServer configurations of third-party tools so we do not
worry about transforming server objects here. A missing or empty file is treated as a
config with no servers, so it is created on write.

## Classes

### `StdioMCPServer` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/mcp\_config.py#L185](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/mcp_config.py#L185)</sup>

MCP server configuration for stdio transport.

This is the canonical configuration format for MCP servers using stdio transport.
`timeout` sets the per-request timeout in milliseconds when used in an
`MCPConfig`. It takes precedence over the client timeout; zero disables it.

**Methods:**

#### `to_transport` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/mcp\_config.py#L220](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/mcp_config.py#L220)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
to_transport(self) -> StdioTransport | FastMCPTransport
```

### `TransformingStdioMCPServer` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/mcp\_config.py#L232](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/mcp_config.py#L232)</sup>

A Stdio server with tool transforms.

### `RemoteMCPServer` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/mcp\_config.py#L236](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/mcp_config.py#L236)</sup>

MCP server configuration for HTTP/SSE transport.

This is the canonical configuration format for MCP servers using remote transports.
`timeout` sets the per-request timeout in milliseconds when used in an
`MCPConfig`. It takes precedence over the client timeout; zero disables it.

**Methods:**

#### `to_transport` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/mcp\_config.py#L312](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/mcp_config.py#L312)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
to_transport(self) -> StreamableHttpTransport | SSETransport | FastMCPTransport
```

### `TransformingRemoteMCPServer` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/mcp\_config.py#L342](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/mcp_config.py#L342)</sup>

A Remote server with tool transforms.

### `MCPConfig` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/mcp\_config.py#L353](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/mcp_config.py#L353)</sup>

A configuration object for MCP Servers that conforms to the canonical MCP configuration format
while adding additional fields for enabling FastMCP-specific features like tool transformations
and filtering by tags.

For an MCPConfig that is strictly canonical, see the `CanonicalMCPConfig` class.

**Methods:**

#### `wrap_servers_at_root` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/mcp\_config.py#L367](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/mcp_config.py#L367)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
wrap_servers_at_root(cls, values: dict[str, Any]) -> dict[str, Any]
```

If there's no mcpServers key but there are server configs at root, wrap them.

#### `add_server` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/mcp\_config.py#L380](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/mcp_config.py#L380)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
add_server(self, name: str, server: MCPServerTypes) -> None
```

Add or update a server in the configuration.

#### `from_dict` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/mcp\_config.py#L385](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/mcp_config.py#L385)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from_dict(cls, config: dict[str, Any]) -> Self
```

Parse MCP configuration from dictionary format.

#### `to_dict` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/mcp\_config.py#L389](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/mcp_config.py#L389)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
to_dict(self) -> dict[str, Any]
```

Convert MCPConfig to dictionary format, preserving all fields.

#### `write_to_file` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/mcp\_config.py#L393](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/mcp_config.py#L393)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
write_to_file(self, file_path: Path) -> None
```

Write configuration to JSON file.

#### `from_file` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/mcp\_config.py#L399](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/mcp_config.py#L399)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from_file(cls, file_path: Path) -> Self
```

Load configuration from JSON file.

### `CanonicalMCPConfig` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/mcp\_config.py#L409](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/mcp_config.py#L409)</sup>

Canonical MCP configuration format.

This defines the standard configuration format for Model Context Protocol servers.
The format is designed to be client-agnostic and extensible for future use cases.

**Methods:**

#### `add_server` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/mcp\_config.py#L419](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/mcp_config.py#L419)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
add_server(self, name: str, server: CanonicalMCPServerTypes) -> None
```

Add or update a server in the configuration.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.