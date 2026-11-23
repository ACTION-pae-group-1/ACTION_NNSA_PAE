> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# app

# `fastmcp.apps.app`

FastMCPApp — a Provider that represents a composable MCP application.

FastMCPApp binds entry-point tools (model calls these) together with backend
tools (the UI calls these via CallTool).  Backend tools are tagged with
`meta["fastmcp"]["app"]` so they can be found through the provider chain
even when transforms (namespace, visibility, etc.) have renamed or hidden
them — the server sets a context var that tells `Provider.get_tool` to
fall back to a direct lookup for app-visible tools.

Usage::

from fastmcp import FastMCP, FastMCPApp

app = FastMCPApp("Dashboard")

@app.ui()
def show\_dashboard() -> Component:
return Column(...)

@app.tool()
def save\_contact(name: str, email: str) -> str:
return name

server = FastMCP("Platform")
server.add\_provider(app)

## Classes

### `FastMCPApp` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/apps/app.py#L149](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/apps/app.py#L149)</sup>

A Provider that represents an MCP application.

Binds together entry-point tools (`@app.ui`), backend tools
(`@app.tool`), and the Prefab renderer resource.  Backend tools
are tagged with `meta["fastmcp"]["app"]` so `Provider.get_tool`
can find them by original name even when transforms have been applied.

**Methods:**

#### `tool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/apps/app.py#L173](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/apps/app.py#L173)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
tool(self, name_or_fn: F) -> F
```

#### `tool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/apps/app.py#L185](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/apps/app.py#L185)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
tool(self, name_or_fn: str | None = None) -> Callable[[F], F]
```

#### `tool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/apps/app.py#L196](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/apps/app.py#L196)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
tool(self, name_or_fn: str | AnyFunction | None = None) -> Any
```

Register a backend tool that the UI calls via CallTool.

Backend tools default to `visibility=["app"]`.  Pass `model=True`
to also expose the tool to the model (`visibility=["app", "model"]`).

Supports multiple calling patterns::

@app.tool
def save(name: str): ...

@app.tool()
def save(name: str): ...

@app.tool("custom\_name")
def save(name: str): ...

#### `ui` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/apps/app.py#L266](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/apps/app.py#L266)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
ui(self, name_or_fn: F) -> F
```

#### `ui` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/apps/app.py#L281](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/apps/app.py#L281)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
ui(self, name_or_fn: str | None = None) -> Callable[[F], F]
```

#### `ui` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/apps/app.py#L295](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/apps/app.py#L295)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
ui(self, name_or_fn: str | AnyFunction | None = None) -> Any
```

Register a UI entry-point tool that the model calls.

Entry-point tools default to `visibility=["model"]` and auto-wire
the Prefab renderer resource and CSP. They are tagged with the app
name so structured content includes `_meta.fastmcp.app`.

Supports multiple calling patterns::

@app.ui
def dashboard() -> Component: ...

@app.ui()
def dashboard() -> Component: ...

@app.ui("my\_dashboard")
def dashboard() -> Component: ...

#### `add_tool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/apps/app.py#L373](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/apps/app.py#L373)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
add_tool(self, tool: Tool | Callable[..., Any]) -> Tool
```

Add a tool to this app programmatically.

The tool is tagged with this app's name for routing.

#### `lifespan` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/apps/app.py#L432](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/apps/app.py#L432)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
lifespan(self) -> AsyncIterator[None]
```

#### `run` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/apps/app.py#L440](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/apps/app.py#L440)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
run(self, transport: Literal['stdio', 'http', 'sse', 'streamable-http'] | None = None, **kwargs: Any) -> None
```

Create a temporary FastMCP server and run this app standalone.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.