> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# local_provider

# `fastmcp.server.providers.local_provider.local_provider`

LocalProvider for locally-defined MCP components.

This module provides the `LocalProvider` class that manages tools, resources,
templates, and prompts registered via decorators or direct methods.

LocalProvider can be used standalone and attached to multiple servers:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp.server.providers import LocalProvider

# Create a reusable provider with tools
provider = LocalProvider()

@provider.tool
def greet(name: str) -> str:
    return f"Hello, {name}!"

# Attach to any server
from fastmcp import FastMCP
server1 = FastMCP("Server1", providers=[provider])
server2 = FastMCP("Server2", providers=[provider])
```

## Classes

### `LocalProvider` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/local\_provider/local\_provider.py#L51](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/local_provider/local_provider.py#L51)</sup>

Provider for locally-defined components.

Supports decorator-based registration (`@provider.tool`, `@provider.resource`,
`@provider.prompt`) and direct object registration methods.

When used standalone, LocalProvider uses default settings. When attached
to a FastMCP server via the server's decorators, server-level settings
like `_tool_serializer` and `_support_tasks_by_default` are injected.

**Methods:**

#### `remove_tool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/local\_provider/local\_provider.py#L229](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/local_provider/local_provider.py#L229)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
remove_tool(self, name: str, version: str | None = None) -> None
```

Remove tool(s) from this provider's storage.

**Args:**

* `name`: The tool name.
* `version`: If None, removes ALL versions. If specified, removes only that version.

**Raises:**

* `KeyError`: If no matching tool is found.

#### `remove_resource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/local\_provider/local\_provider.py#L257](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/local_provider/local_provider.py#L257)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
remove_resource(self, uri: str, version: str | None = None) -> None
```

Remove resource(s) from this provider's storage.

**Args:**

* `uri`: The resource URI.
* `version`: If None, removes ALL versions. If specified, removes only that version.

**Raises:**

* `KeyError`: If no matching resource is found.

#### `remove_template` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/local\_provider/local\_provider.py#L285](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/local_provider/local_provider.py#L285)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
remove_template(self, uri_template: str, version: str | None = None) -> None
```

Remove resource template(s) from this provider's storage.

**Args:**

* `uri_template`: The template URI pattern.
* `version`: If None, removes ALL versions. If specified, removes only that version.

**Raises:**

* `KeyError`: If no matching template is found.

#### `remove_prompt` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/local\_provider/local\_provider.py#L315](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/local_provider/local_provider.py#L315)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
remove_prompt(self, name: str, version: str | None = None) -> None
```

Remove prompt(s) from this provider's storage.

**Args:**

* `name`: The prompt name.
* `version`: If None, removes ALL versions. If specified, removes only that version.

**Raises:**

* `KeyError`: If no matching prompt is found.

#### `get_tasks` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/local\_provider/local\_provider.py#L449](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/local_provider/local_provider.py#L449)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_tasks(self) -> Sequence[FastMCPComponent]
```

Return components eligible for background task execution.

Returns components that have task\_config.mode != 'forbidden'.
This includes both FunctionTool/Resource/Prompt instances created via
decorators and custom Tool/Resource/Prompt subclasses.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.