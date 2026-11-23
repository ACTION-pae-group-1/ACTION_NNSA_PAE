> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# proxy

# `fastmcp.server.providers.proxy`

ProxyProvider for proxying to remote MCP servers.

This module provides the `ProxyProvider` class that proxies components from
a remote MCP server via a client factory. It also provides proxy component
classes that forward execution to remote servers.

## Functions

### `default_proxy_roots_handler` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L1516](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L1516)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
default_proxy_roots_handler(context: ServerRequestContext[Any, Any]) -> RootsList
```

Forward list roots request from remote server to proxy's connected clients.

A handshake-era backend can still issue `roots/list`, and the proxy is that
backend's client, so it relays the request onto its own front session. This
reaches the wire through the SDK session rather than a `Context` method:
`ctx.list_roots()` is not part of FastMCP's server-authoring API, because
SEP-2322 removed server-initiated requests from the modern protocol. The
relay exists only for handshake-era interop on both legs.

### `default_proxy_sampling_handler` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L1534](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L1534)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
default_proxy_sampling_handler(messages: list[mcp_types.SamplingMessage], params: mcp_types.CreateMessageRequestParams, context: ServerRequestContext[Any, Any]) -> mcp_types.CreateMessageResult
```

Forward sampling request from remote server to proxy's connected clients.

Relays through the SDK session for the same reason as
`default_proxy_roots_handler`: server-initiated sampling is not part of
FastMCP's server-authoring API, and this path only ever runs when both legs
of the proxy speak the handshake era.

### `default_proxy_elicitation_handler` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L1569](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L1569)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
default_proxy_elicitation_handler(message: str, response_type: type, params: mcp_types.ElicitRequestParams, context: ServerRequestContext[Any, Any]) -> ElicitResult
```

Forward elicitation request from remote server to proxy's connected clients.

### `default_proxy_log_handler` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L1591](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L1591)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
default_proxy_log_handler(message: LogMessage) -> None
```

Forward log notification from remote server to proxy's connected clients.

### `default_proxy_progress_handler` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L1604](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L1604)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
default_proxy_progress_handler(progress: float, total: float | None, message: str | None) -> None
```

Forward progress notification from remote server to proxy's connected clients.

## Classes

### `ProxyInitializeMiddleware` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L263](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L263)</sup>

Deprecated middleware for forwarding instructions during initialization.

**Methods:**

#### `on_initialize` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L276](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L276)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_initialize(self, context: MiddlewareContext[mcp_types.InitializeRequest], call_next: CallNext[mcp_types.InitializeRequest, mcp_types.InitializeResult | None]) -> mcp_types.InitializeResult | None
```

### `ProxyTool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L336](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L336)</sup>

A Tool that represents and executes a tool on a remote server.

**Methods:**

#### `model_copy` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L353](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L353)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
model_copy(self, **kwargs: Any) -> ProxyTool
```

Override to preserve \_backend\_name when name changes.

#### `from_mcp_tool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L363](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L363)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from_mcp_tool(cls, client_factory: ClientFactoryT, mcp_tool: mcp_types.Tool) -> ProxyTool
```

Factory method to create a ProxyTool from a raw MCP tool schema.

#### `run` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L381](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L381)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
run(self, arguments: dict[str, Any], context: Context | None = None) -> ToolResult
```

Executes the tool by making a call through the client.

#### `get_span_attributes` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L467](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L467)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_span_attributes(self) -> dict[str, Any]
```

### `ProxyResource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L474](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L474)</sup>

A Resource that represents and reads a resource from a remote server.

**Methods:**

#### `model_copy` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L499](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L499)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
model_copy(self, **kwargs: Any) -> ProxyResource
```

Override to preserve \_backend\_uri when uri changes.

#### `from_mcp_resource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L509](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L509)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from_mcp_resource(cls, client_factory: ClientFactoryT, mcp_resource: mcp_types.Resource) -> ProxyResource
```

Factory method to create a ProxyResource from a raw MCP resource schema.

#### `read` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L530](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L530)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
read(self) -> ResourceResult
```

Read the resource content from the remote server.

#### `get_span_attributes` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L581](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L581)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_span_attributes(self) -> dict[str, Any]
```

### `ProxyTemplate` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L588](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L588)</sup>

A ResourceTemplate that represents and creates resources from a remote server template.

**Methods:**

#### `model_copy` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L605](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L605)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
model_copy(self, **kwargs: Any) -> ProxyTemplate
```

Override to preserve \_backend\_uri\_template when uri\_template changes.

#### `from_mcp_template` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L615](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L615)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from_mcp_template(cls, client_factory: ClientFactoryT, mcp_template: mcp_types.ResourceTemplate) -> ProxyTemplate
```

Factory method to create a ProxyTemplate from a raw MCP template schema.

#### `create_resource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L635](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L635)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
create_resource(self, uri: str, params: dict[str, Any], context: Context | None = None) -> ProxyResource
```

Create a resource from the template by calling the remote server.

#### `get_span_attributes` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L716](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L716)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_span_attributes(self) -> dict[str, Any]
```

### `ProxyPrompt` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L725](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L725)</sup>

A Prompt that represents and renders a prompt from a remote server.

**Methods:**

#### `model_copy` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L742](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L742)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
model_copy(self, **kwargs: Any) -> ProxyPrompt
```

Override to preserve \_backend\_name when name changes.

#### `from_mcp_prompt` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L752](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L752)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from_mcp_prompt(cls, client_factory: ClientFactoryT, mcp_prompt: mcp_types.Prompt) -> ProxyPrompt
```

Factory method to create a ProxyPrompt from a raw MCP prompt schema.

#### `render` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L776](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L776)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
render(self, arguments: dict[str, Any]) -> PromptResult
```

Render the prompt by making a call through the client.

#### `get_span_attributes` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L821](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L821)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_span_attributes(self) -> dict[str, Any]
```

### `ProxyProvider` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L852](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L852)</sup>

Provider that proxies to a remote MCP server via a client factory.

This provider fetches components from a remote server and returns Proxy\*
component instances that forward execution to the remote server.

All components returned by this provider have task\_config.mode="forbidden"
because tasks cannot be executed through a proxy.

Component lists (tools, resources, templates, prompts) are cached so that
individual lookups (e.g. during `call_tool`) can resolve from the cache
instead of opening a new backend connection.  The cache stores the
backend's raw component metadata and is shared across all sessions;
per-session visibility and auth filtering are applied after cache lookup
by the server layer.  The cache is refreshed whenever a `list_*` call
is made, and entries expire after `cache_ttl` seconds (default 300).
Set `cache_ttl=0` to disable caching.  Disabling is recommended for
backends whose component lists change dynamically.

**Methods:**

#### `get_tasks` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L1111](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L1111)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_tasks(self) -> Sequence[FastMCPComponent]
```

Return empty list since proxy components don't support tasks.

Override the base implementation to avoid calling list\_tools() during
server lifespan initialization, which would open the client before any
context is set. All Proxy\* components have task\_config.mode="forbidden".

### `ProxyMetadataMiddleware` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L1166](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L1166)</sup>

Forward optional server metadata from a `ProxyProvider` backend.

Instructions and namespaced metadata are forwarded with frontend values
taking precedence. Protocol versions, capabilities, cache policy, and result
type are never copied from the backend. `identity` controls whether server
identity remains the gateway's or uses the backend's when available.

**Methods:**

#### `on_initialize` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L1244](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L1244)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_initialize(self, context: MiddlewareContext[mcp_types.InitializeRequest], call_next: CallNext[mcp_types.InitializeRequest, mcp_types.InitializeResult | None]) -> mcp_types.InitializeResult | None
```

#### `on_discover` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L1261](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L1261)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_discover(self, context: MiddlewareContext[mcp_types.DiscoverRequest], call_next: CallNext[mcp_types.DiscoverRequest, mcp_types.DiscoverResult | dict[str, Any]]) -> mcp_types.DiscoverResult | dict[str, Any]
```

### `FastMCPProxy` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L1438](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L1438)</sup>

A FastMCP server that acts as a proxy to a remote MCP-compliant server.

This is a convenience wrapper that creates a FastMCP server with a
ProxyProvider. For more control, use FastMCP with add\_provider(ProxyProvider(...)).

### `ProxyClient` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L1675](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L1675)</sup>

A proxy client that forwards advanced interactions between a remote MCP server and the proxy's connected clients.

Supports forwarding roots, sampling, elicitation, logging, and progress.
Eligible inbound HTTP headers are forwarded by default; set
`forward_incoming_headers=False` to use only the backend transport's
configured headers and authentication. Applies to HTTP and SSE backends,
including backends in an MCP configuration.

The default forwarding handlers must resolve the *proxy's* request context so
they relay server-initiated requests (roots/sampling/elicitation) back to the
proxy's own connected client, not to the upstream server they are talking to.
Under SDK v2 an in-memory backend runs in the same event loop as this client,
so a naive `get_context()` inside a handler can resolve to the backend's
context and forward the request straight back to the backend — an infinite
loop. To avoid that, `ProxyTool.run` (and the other proxy components) stash
the proxy-side `RequestContext` in `_proxy_rc_ref` before each backend
call, and the handlers are wrapped to restore it before forwarding.

**Methods:**

#### `new` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L1790](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L1790)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
new(self) -> ProxyClient[ClientTransportT]
```

### `StatefulProxyClient` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L1800](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L1800)</sup>

A proxy client that provides a stateful client factory for the proxy server.

The stateful proxy client bound its copy to the server session.
And it will be disconnected when the session is exited.

This is useful to proxy a stateful mcp server such as the Playwright MCP server.
Note that it is essential to ensure that the proxy server itself is also stateful.

The base `ProxyClient` already installs the context-restoring handlers
(see its docstring); this subclass additionally caches one client per stable
`Connection` and forces disconnect when the connection is torn down.

**Methods:**

#### `new` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L1821](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L1821)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
new(self) -> StatefulProxyClient[ClientTransportT]
```

#### `clear` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L1832](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L1832)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
clear(self)
```

Clear all cached clients and force disconnect them.

#### `new_stateful` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/proxy.py#L1838](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/proxy.py#L1838)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
new_stateful(self) -> Client[ClientTransportT]
```

Create a new stateful proxy client instance with the same configuration.

Use this method as the client factory for stateful proxy server.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.