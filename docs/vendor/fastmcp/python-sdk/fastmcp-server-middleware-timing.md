> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# timing

# `fastmcp.server.middleware.timing`

Timing middleware for measuring and logging request performance.

## Classes

### `TimingMiddleware` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/timing.py#L10](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/timing.py#L10)</sup>

Middleware that logs the execution time of requests.

Only measures and logs timing for request messages (not notifications).
Provides insights into performance characteristics of your MCP server.

**Methods:**

#### `on_request` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/timing.py#L39](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/timing.py#L39)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_request(self, context: MiddlewareContext, call_next: CallNext) -> Any
```

Time request execution and log the results.

### `DetailedTimingMiddleware` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/timing.py#L60](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/timing.py#L60)</sup>

Enhanced timing middleware with per-operation breakdowns.

Provides detailed timing information for different types of MCP operations,
allowing you to identify performance bottlenecks in specific operations.

**Methods:**

#### `on_call_tool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/timing.py#L111](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/timing.py#L111)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_call_tool(self, context: MiddlewareContext, call_next: CallNext) -> Any
```

Time tool execution.

#### `on_read_resource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/timing.py#L118](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/timing.py#L118)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_read_resource(self, context: MiddlewareContext, call_next: CallNext) -> Any
```

Time resource reading.

#### `on_get_prompt` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/timing.py#L127](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/timing.py#L127)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_get_prompt(self, context: MiddlewareContext, call_next: CallNext) -> Any
```

Time prompt retrieval.

#### `on_list_tools` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/timing.py#L134](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/timing.py#L134)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_list_tools(self, context: MiddlewareContext, call_next: CallNext) -> Any
```

Time tool listing.

#### `on_list_resources` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/timing.py#L140](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/timing.py#L140)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_list_resources(self, context: MiddlewareContext, call_next: CallNext) -> Any
```

Time resource listing.

#### `on_list_resource_templates` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/timing.py#L146](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/timing.py#L146)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_list_resource_templates(self, context: MiddlewareContext, call_next: CallNext) -> Any
```

Time resource template listing.

#### `on_list_prompts` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/timing.py#L152](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/timing.py#L152)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_list_prompts(self, context: MiddlewareContext, call_next: CallNext) -> Any
```

Time prompt listing.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.