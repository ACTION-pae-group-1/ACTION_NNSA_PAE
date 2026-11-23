> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# response_limiting

# `fastmcp.server.middleware.response_limiting`

Response limiting middleware for controlling tool response sizes.

## Classes

### `ResponseLimitingMiddleware` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/response\_limiting.py#L22](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/response_limiting.py#L22)</sup>

Middleware that limits the response size of tool calls.

Intercepts tool call responses and enforces size limits. If a response
exceeds the limit, it extracts text content, truncates it, and returns
a single TextContent block.

**Methods:**

#### `on_list_tools` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/response\_limiting.py#L107](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/response_limiting.py#L107)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_list_tools(self, context: MiddlewareContext[mt.ListToolsRequest], call_next: CallNext[mt.ListToolsRequest, Sequence[Tool]]) -> Sequence[Tool]
```

Hide schemas for tools whose response shape may be truncated to text.

#### `on_call_tool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/response\_limiting.py#L121](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/response_limiting.py#L121)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_call_tool(self, context: MiddlewareContext[mt.CallToolRequestParams], call_next: CallNext[mt.CallToolRequestParams, ToolResult]) -> ToolResult
```

Intercept tool calls and limit response size.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.