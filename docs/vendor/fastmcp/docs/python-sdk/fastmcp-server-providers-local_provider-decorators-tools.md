> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# tools

# `fastmcp.server.providers.local_provider.decorators.tools`

Tool decorator mixin for LocalProvider.

This module provides the ToolDecoratorMixin class that adds tool
registration functionality to LocalProvider.

## Classes

### `ToolDecoratorMixin` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/local\_provider/decorators/tools.py#L103](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/local_provider/decorators/tools.py#L103)</sup>

Mixin class providing tool decorator functionality for LocalProvider.

This mixin contains all methods related to:

* Tool registration via add\_tool()
* Tool decorator (@provider.tool)

**Methods:**

#### `add_tool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/local\_provider/decorators/tools.py#L111](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/local_provider/decorators/tools.py#L111)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
add_tool(self: LocalProvider, tool: Tool | Callable[..., Any]) -> Tool
```

Add a tool to this provider's storage.

Accepts either a Tool object or a decorated function with **fastmcp** metadata.

#### `tool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/local\_provider/decorators/tools.py#L166](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/local_provider/decorators/tools.py#L166)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
tool(self: LocalProvider, name_or_fn: F) -> F
```

#### `tool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/local\_provider/decorators/tools.py#L187](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/local_provider/decorators/tools.py#L187)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
tool(self: LocalProvider, name_or_fn: str | None = None) -> Callable[[F], F]
```

#### `tool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/local\_provider/decorators/tools.py#L210](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/local_provider/decorators/tools.py#L210)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
tool(self: LocalProvider, name_or_fn: str | AnyFunction | None = None) -> Callable[[AnyFunction], FunctionTool] | FunctionTool | partial[Callable[[AnyFunction], FunctionTool] | FunctionTool]
```

Decorator to register a tool.

This decorator supports multiple calling patterns:

* @provider.tool (without parentheses)
* @provider.tool() (with empty parentheses)
* @provider.tool("custom\_name") (with name as first argument)
* @provider.tool(name="custom\_name") (with name as keyword argument)
* provider.tool(function, name="custom\_name") (direct function call)

**Args:**

* `name_or_fn`: Either a function (when used as @tool), a string name, or None
* `name`: Optional name for the tool (keyword-only, alternative to name\_or\_fn)
* `title`: Optional title for the tool
* `description`: Optional description of what the tool does
* `icons`: Optional icons for the tool
* `tags`: Optional set of tags for categorizing the tool
* `output_schema`: Optional JSON schema for the tool's output
* `annotations`: Optional annotations about the tool's behavior
* `meta`: Optional meta information about the tool
* `enabled`: Whether the tool is enabled (default True). If False, adds to blocklist.
* `task`: Optional task configuration for background execution

**Returns:**

* The registered FunctionTool or a decorator function.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.