> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# components

# `fastmcp.server.providers.openapi.components`

OpenAPI component classes: Tool, Resource, and ResourceTemplate.

## Classes

### `OpenAPITool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/openapi/components.py#L172](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/openapi/components.py#L172)</sup>

Tool implementation for OpenAPI endpoints.

**Methods:**

#### `run` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/openapi/components.py#L204](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/openapi/components.py#L204)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
run(self, arguments: dict[str, Any]) -> ToolResult
```

Execute the HTTP request using RequestDirector.

### `OpenAPIResource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/openapi/components.py#L277](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/openapi/components.py#L277)</sup>

Resource implementation for OpenAPI endpoints.

**Methods:**

#### `read` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/openapi/components.py#L309](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/openapi/components.py#L309)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
read(self) -> ResourceResult
```

Fetch the resource data by making an HTTP request.

### `OpenAPIResourceTemplate` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/openapi/components.py#L378](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/openapi/components.py#L378)</sup>

Resource template implementation for OpenAPI endpoints.

**Methods:**

#### `create_resource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/openapi/components.py#L410](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/openapi/components.py#L410)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
create_resource(self, uri: str, params: dict[str, Any], context: Context | None = None) -> Resource
```

Create a resource with the given parameters.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.