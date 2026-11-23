> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# components

# `fastmcp.server.providers.openapi.components`

OpenAPI component classes: Tool, Resource, and ResourceTemplate.

## Classes

### `OpenAPITool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/openapi/components.py#L201](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/openapi/components.py#L201)</sup>

Tool implementation for OpenAPI endpoints.

**Methods:**

#### `run` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/openapi/components.py#L233](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/openapi/components.py#L233)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
run(self, arguments: dict[str, Any]) -> ToolResult
```

Execute the HTTP request using RequestDirector.

### `OpenAPIResource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/openapi/components.py#L316](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/openapi/components.py#L316)</sup>

Resource implementation for OpenAPI endpoints.

**Methods:**

#### `read` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/openapi/components.py#L348](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/openapi/components.py#L348)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
read(self) -> ResourceResult
```

Fetch the resource data by making an HTTP request.

### `OpenAPIResourceTemplate` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/openapi/components.py#L406](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/openapi/components.py#L406)</sup>

Resource template implementation for OpenAPI endpoints.

**Methods:**

#### `create_resource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/openapi/components.py#L438](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/openapi/components.py#L438)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
create_resource(self, uri: str, params: dict[str, Any], context: Context | None = None) -> Resource
```

Create a resource with the given parameters.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.