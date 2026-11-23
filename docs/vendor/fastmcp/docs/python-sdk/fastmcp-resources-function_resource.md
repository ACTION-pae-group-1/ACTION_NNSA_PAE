> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# function_resource

# `fastmcp.resources.function_resource`

Standalone @resource decorator for FastMCP.

## Functions

### `resource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/function\_resource.py#L223](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/function_resource.py#L223)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
resource(uri: str) -> Callable[[F], F]
```

Standalone decorator to mark a function as an MCP resource.

Returns the original function with metadata attached. Register with a server
using mcp.add\_resource().

## Classes

### `DecoratedResource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/function\_resource.py#L40](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/function_resource.py#L40)</sup>

Protocol for functions decorated with @resource.

### `ResourceMeta` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/function\_resource.py#L49](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/function_resource.py#L49)</sup>

Metadata attached to functions by the @resource decorator.

### `FunctionResource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/function\_resource.py#L68](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/function_resource.py#L68)</sup>

A resource that defers data loading by wrapping a function.

The function is only called when the resource is read, allowing for lazy loading
of potentially expensive data. This is particularly useful when listing resources,
as the function won't be called until the resource is actually accessed.

The function can return:

* str for text content (default)
* bytes for binary content
* other types will be converted to JSON

**Methods:**

#### `from_function` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/function\_resource.py#L84](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/function_resource.py#L84)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from_function(cls, fn: Callable[..., Any], uri: str | AnyUrl | None = None) -> FunctionResource
```

Create a FunctionResource from a function.

**Args:**

* `fn`: The function to wrap
* `uri`: The URI for the resource (required if metadata not provided)
* `metadata`: ResourceMeta object with all configuration. If provided,
  individual parameters must not be passed.
* `name, title, etc.`: Individual parameters for backwards compatibility.
  Cannot be used together with metadata parameter.

#### `read` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/function\_resource.py#L201](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/function_resource.py#L201)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
read(self) -> str | bytes | ResourceResult
```

Read the resource by calling the wrapped function.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.