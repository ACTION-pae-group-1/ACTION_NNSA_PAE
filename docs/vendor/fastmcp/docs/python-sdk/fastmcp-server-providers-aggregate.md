> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# aggregate

# `fastmcp.server.providers.aggregate`

AggregateProvider for combining multiple providers into one.

This module provides `AggregateProvider`, a utility class that presents
multiple providers as a single unified provider. Useful when you want to
combine custom providers without creating a full FastMCP server.

Example:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp.server.providers import AggregateProvider

# Combine multiple providers into one
combined = AggregateProvider()
combined.add_provider(provider1)
combined.add_provider(provider2, namespace="api")  # Tools become "api_foo"

# Use like any other provider
tools = await combined.list_tools()
```

## Classes

### `AggregateProvider` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/aggregate.py#L58](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/aggregate.py#L58)</sup>

Utility provider that combines multiple providers into one.

Components are aggregated from all providers. For get\_\* operations,
providers are queried in parallel and the highest version is returned.

When adding providers with a namespace, wrap\_transform() is used to apply
the Namespace transform. This means namespace transformation is handled
by the wrapped provider, not by AggregateProvider.

Errors from individual providers are logged and skipped by default. Set
`provider_error_strategy="raise"` to fail the aggregate operation when
any provider fails. The `mounted_components_raise_on_load_error` setting
does the same for every aggregate.

**Methods:**

#### `required_extensions` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/aggregate.py#L103](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/aggregate.py#L103)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
required_extensions(self) -> Sequence[ServerExtension]
```

Collect bundled extensions from children in provider order.

#### `add_provider` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/aggregate.py#L129](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/aggregate.py#L129)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
add_provider(self, provider: Provider) -> None
```

Add a provider with optional namespace.

If the provider is a FastMCP server, it's automatically wrapped in
FastMCPProvider to ensure middleware is invoked correctly.

**Args:**

* `provider`: The provider to add.
* `namespace`: Optional namespace prefix. When set:
* Tools become "namespace\_toolname"
* Resources become "protocol://namespace/path"
* Prompts become "namespace\_promptname"

#### `get_app_tool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/aggregate.py#L286](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/aggregate.py#L286)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_app_tool(self, app_name: str, tool_name: str) -> Tool | None
```

Query all child providers for an app tool.

#### `get_tasks` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/aggregate.py#L413](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/aggregate.py#L413)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_tasks(self) -> Sequence[FastMCPComponent]
```

Get all task-eligible components from all providers.

#### `lifespan` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/aggregate.py#L426](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/aggregate.py#L426)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
lifespan(self) -> AsyncGenerator[None, None]
```

Combine lifespans of all providers.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.