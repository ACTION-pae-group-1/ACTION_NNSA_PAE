> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# group

# `fastmcp.client.group`

Coordination of independent MCP client connections.

## Classes

### `ToolRoute` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/group.py#L24](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/group.py#L24)</sup>

The client and upstream name behind a public group tool name.

### `ClientGroup` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/group.py#L32](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/group.py#L32)</sup>

Coordinate independent clients without introducing a proxy server.

Each client retains its own transport, session, capabilities, and protocol
version. The group only combines tool discovery and routes tool calls.

Callers may manage the clients' connections themselves or use the group as
a convenience context manager. The group's context is reentrant in the
same way a client's is: entries are reference counted, the first entry
connects every client, and the last exit disconnects them. Entering an
already-connected FastMCP client is likewise safe because client contexts
are reference counted.

**Methods:**

#### `clients` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/group.py#L61](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/group.py#L61)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
clients(self) -> Mapping[str, Client[Any]]
```

The group's clients, keyed by server name.

Read-only: membership is fixed at construction, since discovered routes
hold the client that advertised each tool and would silently go stale
if the mapping were swapped underneath them.

#### `from_config` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/group.py#L71](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/group.py#L71)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from_config(cls, config: MCPConfig | dict[str, Any]) -> ClientGroup
```

Create one independent client for each configured server.

A server entry may include a FastMCP-specific `mode` field. It applies
only to that server; entries without one use `default_mode`.

#### `protocol_versions` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/group.py#L96](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/group.py#L96)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
protocol_versions(self) -> dict[str, str | None]
```

#### `list_tools` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/group.py#L183](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/group.py#L183)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
list_tools(self) -> list[mcp_types.Tool]
```

List tools from every client with namespaced names.

An explicit call is the group's catalog-refresh mechanism, so it
defaults to `cache_mode="refresh"`: a client-side response cache
(SEP-2549) is repopulated rather than served, and the routes reflect
what every server advertises now. Pass `cache_mode="use"` to allow
cache hits when staleness within the server's hint is acceptable.

#### `resolve_tool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/group.py#L220](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/group.py#L220)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
resolve_tool(self, name: str) -> ToolRoute
```

Resolve a public tool name to its client and upstream identity.

A known route only requires its own client to be connected; one dead
server does not couple failures onto calls routed to healthy servers.
Loading the catalog (the first resolution, or after a refresh) still
requires every client, since discovery queries them all.

#### `call_tool_mcp` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/group.py#L255](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/group.py#L255)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
call_tool_mcp(self, name: str, arguments: dict[str, Any] | None = None) -> mcp_types.CallToolResult
```

Call a namespaced tool and return its raw MCP result.

#### `call_tool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/group.py#L274](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/group.py#L274)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> CallToolResult
```

Call a namespaced tool through the client that advertised it.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.