> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# The FastMCP Server

> The core FastMCP server class for building MCP applications

The `FastMCP` class is the central piece of every FastMCP application. It acts as the container for your tools, resources, and prompts, managing communication with MCP clients and orchestrating the entire server lifecycle.

## Creating a Server

At its simplest, a FastMCP server just needs a name. Everything else has sensible defaults.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import FastMCP

mcp = FastMCP("MyServer")
```

Instructions help clients (and the LLMs behind them) understand what your server does and how to use it effectively.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
mcp = FastMCP(
    "DataAnalysis",
    instructions="Provides tools for analyzing numerical datasets. Start with get_summary() for an overview.",
)
```

## Components

FastMCP servers expose three types of components to clients, each serving a distinct role in the MCP protocol.

**Tools** are functions that clients invoke to perform actions or access external systems.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
@mcp.tool
def multiply(a: float, b: float) -> float:
    """Multiplies two numbers together."""
    return a * b
```

**Resources** expose data that clients can read — passive data sources rather than invocable functions.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
@mcp.resource("data://config")
def get_config() -> dict:
    return {"theme": "dark", "version": "1.0"}
```

**Prompts** are reusable message templates that guide LLM interactions.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
@mcp.prompt
def analyze_data(data_points: list[float]) -> str:
    formatted_data = ", ".join(str(point) for point in data_points)
    return f"Please analyze these data points: {formatted_data}"
```

Each component type has detailed documentation: [Tools](https://gofastmcp.com/docs/servers/tools.md), [Resources](https://gofastmcp.com/docs/servers/resources.md) (including [Resource Templates](https://gofastmcp.com/docs/servers/resources.md#resource-templates)), and [Prompts](https://gofastmcp.com/docs/servers/prompts.md).

## Running the Server

Start your server by calling `mcp.run()`. The `if __name__` guard ensures compatibility with MCP clients that launch your server as a subprocess.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import FastMCP

mcp = FastMCP("MyServer")

@mcp.tool
def greet(name: str) -> str:
    """Greet a user by name."""
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run()
```

FastMCP supports several transports:

* **STDIO** (default): For local integrations and CLI tools
* **HTTP**: For web services using the Streamable HTTP protocol
* **SSE**: Legacy web transport (deprecated)

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
# Run with HTTP transport
mcp.run(transport="http", host="127.0.0.1", port=9000)
```

The server can also be run using the FastMCP CLI. For detailed information on transports and deployment, see [Running Your Server](https://gofastmcp.com/docs/deployment/running-server.md).

## Configuration Reference

The `FastMCP` constructor accepts parameters organized into four categories: identity, composition, behavior, and handlers.

### Identity

These parameters control how your server presents itself to clients.

> [card]
>
> **name** `str` (default: FastMCP)
>
> A human-readable name for your server, shown in client applications and logs
>
> **instructions** `str | None`
>
> Description of how to interact with this server. Clients surface these instructions to help LLMs understand the server's purpose and available functionality
>
> **version** `str | None`
>
> Version string for your server. Defaults to the FastMCP library version if not provided
>
> **website\_url** `str | None`
>
> New in version `2.13.0`
>
> URL to a website with more information about your server. Displayed in client applications
>
> **icons** `list[Icon] | None`
>
> New in version `2.13.0`
>
> List of icon representations for your server. See [Icons](https://gofastmcp.com/docs/servers/icons.md) for details
>
> **experimental\_capabilities** `dict[str, dict[str, Any]] | None`
>
> New in version `3.2.5`
>
> Arbitrary experimental capabilities to advertise in the MCP `initialize` response. Use this to declare cross-server interop conventions or draft extensions that follow the MCP spec's `experimental` field. Keys are capability names; values are free-form dicts. FastMCP's built-in derived capabilities (`tools`, `resources`, etc.) are unaffected — this only populates `capabilities.experimental`

### Composition

These parameters control what your server is built from — its components, middleware, providers, and lifecycle.

> [card]
>
> **tools** `list[Tool | Callable] | None`
>
> Tools to register on the server. An alternative to the `@mcp.tool` decorator when you need to add tools programmatically
>
> **auth** `OAuthProvider | TokenVerifier | None`
>
> Authentication provider for securing HTTP-based transports. See [Authentication](https://gofastmcp.com/docs/servers/auth/authentication.md) for configuration
>
> **middleware** `list[Middleware] | None`
>
> [Middleware](https://gofastmcp.com/docs/servers/middleware.md) that intercepts and transforms every MCP message flowing through the server — requests, responses, and notifications in both directions. Use for cross-cutting concerns like logging, error handling, and rate limiting
>
> **providers** `list[Provider] | None`
>
> [Providers](https://gofastmcp.com/docs/servers/providers/overview.md) that supply tools, resources, and prompts dynamically. Providers are queried at request time, so they can serve components from databases, APIs, or other external sources
>
> **transforms** `list[Transform] | None`
>
> New in version `3.1.0`
>
> Server-level [transforms](https://gofastmcp.com/docs/servers/transforms/transforms.md) to apply to all components. Transforms modify how tools, resources, and prompts are presented to clients — for example, [search transforms](https://gofastmcp.com/docs/servers/transforms/tool-search.md) replace large catalogs with on-demand discovery
>
> **lifespan** `Lifespan | AsyncContextManager | None`
>
> Server-level setup and teardown logic that runs when the server starts and stops. See [Lifespans](https://gofastmcp.com/docs/servers/lifespan.md) for composable lifespans

### Behavior

These parameters tune how the server processes requests and communicates with clients.

> [card]
>
> **on\_duplicate** `Literal["warn", "error", "replace", "ignore"]` (default: warn)
>
> How to handle duplicate component registrations
>
> **strict\_input\_validation** `bool` (default: False)
>
> New in version `2.13.0`
>
> When `False` (default), FastMCP uses Pydantic's flexible validation that coerces compatible inputs (e.g., `"10"` → `10` for int parameters). When `True`, validates inputs against the exact JSON Schema before calling your function, rejecting type mismatches. See [Input Validation Modes](https://gofastmcp.com/docs/servers/tools.md#input-validation-modes) for details
>
> **mask\_error\_details** `bool | None`
>
> When `True`, replaces internal error details in tool/resource responses with a generic message to avoid leaking implementation details to clients. Defaults to the `FASTMCP_MASK_ERROR_DETAILS` environment variable
>
> **list\_page\_size** `int | None` (default: None)
>
> New in version `3.0.0`
>
> Maximum items per page for list operations (`tools/list`, `resources/list`, etc.). When `None`, all results are returned in a single response. See [Pagination](https://gofastmcp.com/docs/servers/pagination.md) for details
>
> **tasks** `bool | None` (default: False)
>
> Enable background task support. When `True`, tools and resources can return `CreateTaskResult` to run work asynchronously while the client polls for results
>
> **client\_log\_level** `LoggingLevel | None`
>
> New in version `3.2.0`
>
> Default minimum log level for messages sent to MCP clients via `context.log()`. When set, messages below this level are suppressed. Individual clients can override this per-session using the MCP `logging/setLevel` request. One of `"debug"`, `"info"`, `"notice"`, `"warning"`, `"error"`, `"critical"`, `"alert"`, or `"emergency"`
>
> **dereference\_schemas** `bool` (default: True)
>
> Automatically dereference `$ref` pointers in JSON schemas generated from complex Pydantic models. Most clients require flat schemas without `$ref`, so this should usually stay enabled

### Handlers and Storage

These parameters provide custom handlers for MCP capabilities and persistent storage for session state.

> [card]
>
> **sampling\_handler** `SamplingHandler | None`
>
> Custom handler for MCP sampling requests (server-initiated LLM calls). See [Sampling](https://gofastmcp.com/docs/servers/sampling.md) for details
>
> **sampling\_handler\_behavior** `Literal["always", "fallback"] | None` (default: fallback)
>
> When `"fallback"`, the sampling handler is used only when no tool-specific handler exists. When `"always"`, this handler is used for all sampling requests
>
> **session\_state\_store** `AsyncKeyValue | None`
>
> Persistent key-value store for session state that survives across requests. Defaults to an in-memory store. Provide a custom implementation for persistence across server restarts

## Tag-Based Filtering

New in version `2.8.0`

Tags let you categorize components and selectively expose them. This is useful for creating different views of your server for different environments or user types.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
@mcp.tool(tags={"public", "utility"})
def public_tool() -> str:
    return "This tool is public"

@mcp.tool(tags={"internal", "admin"})
def admin_tool() -> str:
    return "This tool is for admins only"
```

The filtering logic works as follows:

* **Enable with `only=True`**: Switches to allowlist mode — only components with at least one matching tag are exposed
* **Disable**: Components with any matching tag are hidden
* **Precedence**: Later calls override earlier ones, so call `disable` after `enable` to exclude from an allowlist

> [!TIP]
>
> To ensure a component is never exposed, you can set `enabled=False` on the component itself. See the component-specific documentation for details.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
# Only expose components tagged with "public"
mcp = FastMCP()
mcp.enable(tags={"public"}, only=True)

# Hide components tagged as "internal" or "deprecated"
mcp = FastMCP()
mcp.disable(tags={"internal", "deprecated"})

# Combine both: show admin tools but hide deprecated ones
mcp = FastMCP()
mcp.enable(tags={"admin"}, only=True).disable(tags={"deprecated"})
```

This filtering applies to all component types (tools, resources, resource templates, and prompts) and affects both listing and access.

## Custom Routes

When running with HTTP transport, you can add custom web routes alongside your MCP endpoint using the `@custom_route` decorator.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import PlainTextResponse

mcp = FastMCP("MyServer")

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")

if __name__ == "__main__":
    mcp.run(transport="http")  # Health check at http://localhost:8000/health
```

Custom routes are useful for health checks, status endpoints, and simple webhooks. For more complex web applications, consider [mounting your MCP server into a FastAPI or Starlette app](https://gofastmcp.com/docs/deployment/http.md#integration-with-web-frameworks).


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.