> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# mcp_operations

# `fastmcp.server.mixins.mcp_operations`

MCP protocol handler setup and wire-format handlers for FastMCP Server.

## Classes

### `MCPOperationsMixin` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/mixins/mcp\_operations.py#L100](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/mixins/mcp_operations.py#L100)</sup>

Mixin providing MCP protocol handler setup and wire-format handlers.

Handlers are registered via `add_request_handler(method, params_type,
handler)` on the low-level SDK server. Each adapter takes
`(ctx: ServerRequestContext, params)` and returns the bare SDK result
model (no `ServerResult` wrapping — the SDK v2 runner serializes the
result itself).


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.