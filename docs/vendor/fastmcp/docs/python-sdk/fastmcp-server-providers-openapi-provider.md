> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# provider

# `fastmcp.server.providers.openapi.provider`

OpenAPIProvider for creating MCP components from OpenAPI specifications.

## Classes

### `OpenAPIProvider` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/openapi/provider.py#L61](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/openapi/provider.py#L61)</sup>

Provider that creates MCP components from an OpenAPI specification.

Components are created eagerly during initialization by parsing the OpenAPI
spec. Each component makes HTTP calls to the described API endpoints.

**Methods:**

#### `lifespan` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/openapi/provider.py#L204](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/openapi/provider.py#L204)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
lifespan(self) -> AsyncGenerator[None, None]
```

Manage the lifecycle of the auto-created httpx client.

#### `get_tasks` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/openapi/provider.py#L461](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/openapi/provider.py#L461)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_tasks(self) -> Sequence[FastMCPComponent]
```

Return empty list - OpenAPI components don't support tasks.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.