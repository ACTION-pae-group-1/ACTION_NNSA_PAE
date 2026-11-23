> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# prompts_as_tools

# `fastmcp.server.transforms.prompts_as_tools`

Transform that exposes prompts as tools.

This transform generates tools for listing and getting prompts, enabling
clients that only support tools to access prompt functionality.

The generated tools route through `ctx.fastmcp` at runtime, so all server
middleware (auth, visibility, rate limiting, etc.) applies to prompt
operations exactly as it would for direct `prompts/get` calls.

Example:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import FastMCP
from fastmcp.server.transforms import PromptsAsTools

mcp = FastMCP("Server")
mcp.add_transform(PromptsAsTools(mcp))
# Now has list_prompts and get_prompt tools
```

## Classes

### `PromptsAsTools` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/prompts\_as\_tools.py#L39](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/prompts_as_tools.py#L39)</sup>

Transform that adds tools for listing and getting prompts.

Generates two tools:

* `list_prompts`: Lists all prompts
* `get_prompt`: Gets a specific prompt with optional arguments

The generated tools route through the server at runtime, so auth,
middleware, and visibility apply automatically.

This transform should be applied to a FastMCP server instance, not
a raw Provider, because the generated tools need the server's
middleware chain for auth and visibility filtering.

**Methods:**

#### `list_tools` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/prompts\_as\_tools.py#L76](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/prompts_as_tools.py#L76)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
list_tools(self, tools: Sequence[Tool]) -> Sequence[Tool]
```

Add prompt tools to the tool list.

#### `get_tool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/prompts\_as\_tools.py#L84](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/prompts_as_tools.py#L84)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_tool(self, name: str, call_next: GetToolNext) -> Tool | None
```

Get a tool by name, including generated prompt tools.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.