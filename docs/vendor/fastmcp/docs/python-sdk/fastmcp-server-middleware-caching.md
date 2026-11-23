> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# caching

# `fastmcp.server.middleware.caching`

A middleware for response caching.

## Classes

### `CacheableResourceContent` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L87](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L87)</sup>

A wrapper for ResourceContent that can be cached.

### `CacheableResourceResult` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L96](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L96)</sup>

A wrapper for ResourceResult that can be cached.

**Methods:**

#### `get_size` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L102](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L102)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_size(self) -> int
```

#### `wrap` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L106](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L106)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
wrap(cls, value: ResourceResult) -> Self
```

#### `unwrap` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L124](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L124)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
unwrap(self) -> ResourceResult
```

### `CacheableToolResult` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L140](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L140)</sup>

**Methods:**

#### `wrap` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L147](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L147)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
wrap(cls, value: ToolResult) -> Self
```

#### `unwrap` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L155](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L155)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
unwrap(self) -> ToolResult
```

### `CacheableMessage` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L164](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L164)</sup>

A wrapper for Message that can be cached.

### `CacheablePromptResult` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L176](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L176)</sup>

A wrapper for PromptResult that can be cached.

**Methods:**

#### `get_size` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L183](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L183)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_size(self) -> int
```

#### `wrap` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L187](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L187)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
wrap(cls, value: PromptResult) -> Self
```

#### `unwrap` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L196](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L196)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
unwrap(self) -> PromptResult
```

### `SharedMethodSettings` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L207](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L207)</sup>

Shared config for a cache method.

### `ListToolsSettings` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L214](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L214)</sup>

Configuration options for Tool-related caching.

### `ListResourcesSettings` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L218](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L218)</sup>

Configuration options for Resource-related caching.

### `ListPromptsSettings` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L222](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L222)</sup>

Configuration options for Prompt-related caching.

### `CallToolSettings` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L226](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L226)</sup>

Configuration options for Tool-related caching.

### `ReadResourceSettings` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L233](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L233)</sup>

Configuration options for Resource-related caching.

### `GetPromptSettings` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L237](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L237)</sup>

Configuration options for Prompt-related caching.

### `ResponseCachingStatistics` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L241](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L241)</sup>

### `ResponseCachingMiddleware` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L250](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L250)</sup>

The response caching middleware offers a simple way to cache responses to mcp methods. The Middleware
supports cache invalidation via notifications from the server. The Middleware implements TTL-based caching
but cache implementations may offer additional features like LRU eviction, size limits, and more.

When items are retrieved from the cache they will no longer be the original objects, but rather no-op objects
this means that response caching may not be compatible with other middleware that expects original subclasses.

Notes:

* Caches `tools/call`, `resources/read`, `prompts/get`, `tools/list`, `resources/list`, and `prompts/list` requests.
* Cache keys are derived from the method name, requested component version,
  arguments, and the caller's access token. Entries are partitioned per-token
  so that responses filtered by per-component authorization (e.g.
  `auth=require_scopes(...)`) cannot leak across users with different
  permissions. Unauthenticated callers (including STDIO) share a single
  anonymous partition.

**Methods:**

#### `on_list_tools` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L361](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L361)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_list_tools(self, context: MiddlewareContext[mcp_types.ListToolsRequest], call_next: CallNext[mcp_types.ListToolsRequest, Sequence[Tool]]) -> Sequence[Tool]
```

List tools from the cache, if caching is enabled, and the result is in the cache. Otherwise,
otherwise call the next middleware and store the result in the cache if caching is enabled.

#### `on_list_resources` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L394](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L394)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_list_resources(self, context: MiddlewareContext[mcp_types.ListResourcesRequest], call_next: CallNext[mcp_types.ListResourcesRequest, Sequence[Resource]]) -> Sequence[Resource]
```

List resources from the cache, if caching is enabled, and the result is in the cache. Otherwise,
otherwise call the next middleware and store the result in the cache if caching is enabled.

#### `on_list_prompts` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L427](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L427)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_list_prompts(self, context: MiddlewareContext[mcp_types.ListPromptsRequest], call_next: CallNext[mcp_types.ListPromptsRequest, Sequence[Prompt]]) -> Sequence[Prompt]
```

List prompts from the cache, if caching is enabled, and the result is in the cache. Otherwise,
otherwise call the next middleware and store the result in the cache if caching is enabled.

#### `on_call_tool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L458](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L458)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_call_tool(self, context: MiddlewareContext[mcp_types.CallToolRequestParams], call_next: CallNext[mcp_types.CallToolRequestParams, ToolResult]) -> ToolResult
```

Call a tool from the cache, if caching is enabled, and the result is in the cache. Otherwise,
otherwise call the next middleware and store the result in the cache if caching is enabled.

#### `on_read_resource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L522](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L522)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_read_resource(self, context: MiddlewareContext[mcp_types.ReadResourceRequestParams], call_next: CallNext[mcp_types.ReadResourceRequestParams, ResourceResult]) -> ResourceResult
```

Read a resource from the cache, if caching is enabled, and the result is in the cache. Otherwise,
otherwise call the next middleware and store the result in the cache if caching is enabled.

#### `on_get_prompt` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L571](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L571)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_get_prompt(self, context: MiddlewareContext[mcp_types.GetPromptRequestParams], call_next: CallNext[mcp_types.GetPromptRequestParams, PromptResult]) -> PromptResult
```

Get a prompt from the cache, if caching is enabled, and the result is in the cache. Otherwise,
otherwise call the next middleware and store the result in the cache if caching is enabled.

#### `statistics` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/caching.py#L623](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/caching.py#L623)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
statistics(self) -> ResponseCachingStatistics
```

Get the statistics for the cache.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.