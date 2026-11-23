> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# middleware

# `fastmcp.server.middleware.middleware`

## Functions

### `mark_interior_dispatched` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/middleware.py#L67](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/middleware.py#L67)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
mark_interior_dispatched() -> None
```

Record that an interior component middleware chain ran for this message.

### `make_middleware_wrapper` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/middleware.py#L113](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/middleware.py#L113)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
make_middleware_wrapper(middleware: Middleware, call_next: CallNext[T, R]) -> CallNext[T, R]
```

Create a wrapper that applies a single middleware to a context. The
closure bakes in the middleware and call\_next function, so it can be
passed to other functions that expect a call\_next function.

### `make_handler_wrapper` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/middleware.py#L126](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/middleware.py#L126)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
make_handler_wrapper(handler: Callable[..., Awaitable[Any]], call_next: CallNext[Any, Any]) -> CallNext[Any, Any]
```

## Classes

### `CallNext` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/middleware.py#L89](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/middleware.py#L89)</sup>

### `MiddlewareContext` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/middleware.py#L94](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/middleware.py#L94)</sup>

Unified context for all middleware operations.

**Methods:**

#### `copy` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/middleware.py#L109](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/middleware.py#L109)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
copy(self, **kwargs: Any) -> MiddlewareContext[T]
```

### `Middleware` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/middleware.py#L136](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/middleware.py#L136)</sup>

Base class for FastMCP middleware with dispatching hooks.

**Methods:**

#### `on_message` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/middleware.py#L204](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/middleware.py#L204)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_message(self, context: MiddlewareContext[Any], call_next: CallNext[Any, Any]) -> Any
```

#### `on_request` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/middleware.py#L211](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/middleware.py#L211)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_request(self, context: MiddlewareContext[mt.Request[Any, Any]], call_next: CallNext[mt.Request[Any, Any], Any]) -> Any
```

#### `on_notification` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/middleware.py#L218](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/middleware.py#L218)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_notification(self, context: MiddlewareContext[mt.Notification[Any, Any]], call_next: CallNext[mt.Notification[Any, Any], Any]) -> Any
```

#### `on_initialize` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/middleware.py#L225](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/middleware.py#L225)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_initialize(self, context: MiddlewareContext[mt.InitializeRequest], call_next: CallNext[mt.InitializeRequest, mt.InitializeResult | None]) -> mt.InitializeResult | None
```

#### `on_discover` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/middleware.py#L232](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/middleware.py#L232)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_discover(self, context: MiddlewareContext[mt.DiscoverRequest], call_next: CallNext[mt.DiscoverRequest, mt.DiscoverResult | dict[str, Any]]) -> mt.DiscoverResult | dict[str, Any]
```

#### `on_call_tool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/middleware.py#L239](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/middleware.py#L239)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_call_tool(self, context: MiddlewareContext[mt.CallToolRequestParams], call_next: CallNext[mt.CallToolRequestParams, ToolResult]) -> ToolResult
```

#### `on_read_resource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/middleware.py#L246](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/middleware.py#L246)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_read_resource(self, context: MiddlewareContext[mt.ReadResourceRequestParams], call_next: CallNext[mt.ReadResourceRequestParams, ResourceResult]) -> ResourceResult
```

#### `on_get_prompt` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/middleware.py#L253](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/middleware.py#L253)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_get_prompt(self, context: MiddlewareContext[mt.GetPromptRequestParams], call_next: CallNext[mt.GetPromptRequestParams, PromptResult]) -> PromptResult
```

#### `on_list_tools` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/middleware.py#L260](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/middleware.py#L260)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_list_tools(self, context: MiddlewareContext[mt.ListToolsRequest], call_next: CallNext[mt.ListToolsRequest, Sequence[Tool]]) -> Sequence[Tool]
```

#### `on_list_resources` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/middleware.py#L267](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/middleware.py#L267)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_list_resources(self, context: MiddlewareContext[mt.ListResourcesRequest], call_next: CallNext[mt.ListResourcesRequest, Sequence[Resource]]) -> Sequence[Resource]
```

#### `on_list_resource_templates` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/middleware.py#L274](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/middleware.py#L274)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_list_resource_templates(self, context: MiddlewareContext[mt.ListResourceTemplatesRequest], call_next: CallNext[mt.ListResourceTemplatesRequest, Sequence[ResourceTemplate]]) -> Sequence[ResourceTemplate]
```

#### `on_list_prompts` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/middleware.py#L283](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/middleware.py#L283)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_list_prompts(self, context: MiddlewareContext[mt.ListPromptsRequest], call_next: CallNext[mt.ListPromptsRequest, Sequence[Prompt]]) -> Sequence[Prompt]
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.