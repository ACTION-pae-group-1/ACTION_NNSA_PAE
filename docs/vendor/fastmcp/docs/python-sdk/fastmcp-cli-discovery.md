> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# discovery

# `fastmcp.cli.discovery`

Discover MCP servers configured in editor config files.

Scans filesystem-readable config files from editors like Claude Desktop,
Claude Code, Cursor, Gemini CLI, and Goose, as well as project-level
`mcp.json` files. Each discovered server can be resolved by name
(or `source:name`) so the CLI can connect without requiring a URL
or file path.

## Functions

### `discover_servers` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/discovery.py#L337](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/discovery.py#L337)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
discover_servers(start_dir: Path | None = None) -> list[DiscoveredServer]
```

Run all scanners and return the combined results.

Duplicate names across sources are preserved — callers can
use :pyattr:`DiscoveredServer.qualified_name` to disambiguate.

### `resolve_name` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/discovery.py#L354](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/discovery.py#L354)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
resolve_name(name: str, start_dir: Path | None = None) -> ClientTransport
```

Resolve a server name (or `source:name`) to a transport.

Raises :class:`ValueError` when the name is not found or is ambiguous.

## Classes

### `DiscoveredServer` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/discovery.py#L37](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/discovery.py#L37)</sup>

A single MCP server found in an editor or project config.

**Methods:**

#### `qualified_name` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/discovery.py#L46](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/discovery.py#L46)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
qualified_name(self) -> str
```

Fully qualified `source:name` identifier.

#### `transport_summary` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/discovery.py#L51](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/discovery.py#L51)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
transport_summary(self) -> str
```

Human-readable one-liner describing the transport.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.