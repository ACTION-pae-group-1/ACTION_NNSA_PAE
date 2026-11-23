> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# authorization

# `fastmcp.server.middleware.authorization`

Authorization middleware for FastMCP.

This module provides middleware-based authorization using callable auth checks.
AuthMiddleware applies auth checks globally to all components on the server.

Example:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import FastMCP
from fastmcp.server.auth import require_scopes, restrict_tag
from fastmcp.server.middleware import AuthMiddleware

# Require specific scope for all components
mcp = FastMCP(middleware=[
    AuthMiddleware(auth=require_scopes("api"))
])

# Tag-based: components tagged "admin" require "admin" scope
mcp = FastMCP(middleware=[
    AuthMiddleware(auth=restrict_tag("admin", scopes=["admin"]))
])
```

## Classes

### `AuthMiddleware` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/authorization.py#L82](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/authorization.py#L82)</sup>

Global authorization middleware using callable checks.

This middleware applies auth checks to all components (tools, resources,
prompts) on the server. It uses the same callable API as component-level
auth checks.

The middleware:

* Filters tools/resources/prompts from list responses based on auth checks
* Checks auth before tool execution, resource read, and prompt render
* Skips all auth checks for STDIO transport (no OAuth concept)

**Args:**

* `auth`: A single auth check function or list of check functions.
  All checks must pass for authorization to succeed (AND logic).

**Methods:**

#### `on_list_tools` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/authorization.py#L170](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/authorization.py#L170)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_list_tools(self, context: MiddlewareContext[mt.ListToolsRequest], call_next: CallNext[mt.ListToolsRequest, Sequence[Tool]]) -> Sequence[Tool]
```

Filter tools/list response based on auth checks.

#### `on_call_tool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/authorization.py#L198](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/authorization.py#L198)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_call_tool(self, context: MiddlewareContext[mt.CallToolRequestParams], call_next: CallNext[mt.CallToolRequestParams, ToolResult]) -> ToolResult
```

Check auth before tool execution.

#### `on_list_resources` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/authorization.py#L256](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/authorization.py#L256)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_list_resources(self, context: MiddlewareContext[mt.ListResourcesRequest], call_next: CallNext[mt.ListResourcesRequest, Sequence[Resource]]) -> Sequence[Resource]
```

Filter resources/list response based on auth checks.

#### `on_read_resource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/authorization.py#L283](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/authorization.py#L283)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_read_resource(self, context: MiddlewareContext[mt.ReadResourceRequestParams], call_next: CallNext[mt.ReadResourceRequestParams, ResourceResult]) -> ResourceResult
```

Check auth before resource read.

#### `on_list_resource_templates` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/authorization.py#L344](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/authorization.py#L344)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_list_resource_templates(self, context: MiddlewareContext[mt.ListResourceTemplatesRequest], call_next: CallNext[mt.ListResourceTemplatesRequest, Sequence[ResourceTemplate]]) -> Sequence[ResourceTemplate]
```

Filter resource templates/list response based on auth checks.

#### `on_list_prompts` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/authorization.py#L373](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/authorization.py#L373)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_list_prompts(self, context: MiddlewareContext[mt.ListPromptsRequest], call_next: CallNext[mt.ListPromptsRequest, Sequence[Prompt]]) -> Sequence[Prompt]
```

Filter prompts/list response based on auth checks.

#### `on_get_prompt` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/authorization.py#L400](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/authorization.py#L400)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_get_prompt(self, context: MiddlewareContext[mt.GetPromptRequestParams], call_next: CallNext[mt.GetPromptRequestParams, PromptResult]) -> PromptResult
```

Check auth before prompt render.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.