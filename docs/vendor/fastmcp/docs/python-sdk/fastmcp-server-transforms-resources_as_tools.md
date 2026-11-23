> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# resources_as_tools

# `fastmcp.server.transforms.resources_as_tools`

Transform that exposes resources as tools.

This transform generates tools for listing and reading resources, enabling
clients that only support tools to access resource functionality.

The generated tools route through `ctx.fastmcp` at runtime, so all server
middleware (auth, visibility, rate limiting, etc.) applies to resource
operations exactly as it would for direct `resources/read` calls.

Example:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import FastMCP
from fastmcp.server.transforms import ResourcesAsTools

mcp = FastMCP("Server")
mcp.add_transform(ResourcesAsTools(mcp))
# Now has list_resources and read_resource tools
```

## Classes

### `ResourcesAsTools` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/resources\_as\_tools.py#L42](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/resources_as_tools.py#L42)</sup>

Transform that adds tools for listing and reading resources.

Generates two tools:

* `list_resources`: Lists all resources and templates
* `read_resource`: Reads a resource by URI

The generated tools route through the server at runtime, so auth,
middleware, and visibility apply automatically.

This transform should be applied to a FastMCP server instance, not
a raw Provider, because the generated tools need the server's
middleware chain for auth and visibility filtering.

**Methods:**

#### `list_tools` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/resources\_as\_tools.py#L79](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/resources_as_tools.py#L79)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
list_tools(self, tools: Sequence[Tool]) -> Sequence[Tool]
```

Add resource tools to the tool list.

#### `get_tool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/resources\_as\_tools.py#L87](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/resources_as_tools.py#L87)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_tool(self, name: str, call_next: GetToolNext) -> Tool | None
```

Get a tool by name, including generated resource tools.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.