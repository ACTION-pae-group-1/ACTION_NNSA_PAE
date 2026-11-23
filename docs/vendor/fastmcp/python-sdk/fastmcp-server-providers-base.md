> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# base

# `fastmcp.server.providers.base`

Base Provider class for dynamic MCP components.

This module provides the `Provider` abstraction for providing tools,
resources, and prompts dynamically at runtime.

Example:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import FastMCP
from fastmcp.server.providers import Provider
from fastmcp.tools import Tool

class DatabaseProvider(Provider):
    def __init__(self, db_url: str):
        super().__init__()
        self.db = Database(db_url)

    async def _list_tools(self) -> list[Tool]:
        rows = await self.db.fetch("SELECT * FROM tools")
        return [self._make_tool(row) for row in rows]

    async def _get_tool(self, name: str) -> Tool | None:
        row = await self.db.fetchone("SELECT * FROM tools WHERE name = ?", name)
        return self._make_tool(row) if row else None

mcp = FastMCP("Server", providers=[DatabaseProvider(db_url)])
```

## Functions

### `hashed_lookup_target` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/base.py#L800](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/base.py#L800)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
hashed_lookup_target(provider: Provider) -> Tool | None
```

The tool a running `get_tool_by_hash()` on `provider` found, if any.

## Classes

### `Provider` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/base.py#L77](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/base.py#L77)</sup>

Base class for dynamic component providers.

Subclass and override whichever methods you need. Default implementations
return empty lists / None, so you only need to implement what your provider
supports.

**Methods:**

#### `required_extensions` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/base.py#L98](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/base.py#L98)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
required_extensions(self) -> Sequence[ServerExtension]
```

Extensions bundled with this provider.

FastMCP automatically registers a separate instance of each extension
on the receiving server. Bundled extensions must opt in with
`auto_register = True`. An explicitly registered extension with the
same identifier takes precedence, regardless of registration order.
Composite providers should include their children's extensions.

#### `transforms` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/base.py#L124](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/base.py#L124)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
transforms(self) -> list[Transform]
```

All transforms applied to components from this provider.

#### `add_transform` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/base.py#L128](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/base.py#L128)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
add_transform(self, transform: Transform) -> None
```

Add a transform to this provider.

Transforms modify components (tools, resources, prompts) as they flow
through the provider. They're applied in order - first added is innermost.

**Args:**

* `transform`: The transform to add.

#### `wrap_transform` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/base.py#L148](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/base.py#L148)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
wrap_transform(self, transform: Transform) -> Provider
```

Return a new provider with this transform applied (immutable).

Unlike add\_transform() which mutates this provider, wrap\_transform()
returns a new provider that wraps this one. The original provider
is unchanged.

This is useful when you want to apply transforms without side effects,
such as adding the same provider to multiple aggregators with different
namespaces.

**Args:**

* `transform`: The transform to apply.

**Returns:**

* A new provider that wraps this one with the transform applied.

#### `list_tools` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/base.py#L184](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/base.py#L184)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
list_tools(self) -> Sequence[Tool]
```

List tools with all transforms applied.

Applies transforms sequentially: base → transforms (in order).
Each transform receives the result from the previous transform.
Components may be marked as disabled but are NOT filtered here -
filtering happens at the server level to allow session transforms to override.

**Returns:**

* Transformed sequence of tools (including disabled ones).

#### `get_tool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/base.py#L200](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/base.py#L200)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_tool(self, name: str, version: VersionSpec | None = None) -> Tool | None
```

Get tool by transformed name with all transforms applied.

Note: This method does NOT filter disabled components. The Server
(FastMCP) performs enabled filtering after all transforms complete,
allowing session-level transforms to override provider-level disables.

**Args:**

* `name`: The transformed tool name to look up.
* `version`: Optional version filter. If None, returns highest version.

**Returns:**

* The tool if found (may be marked disabled), None if not found.

#### `get_app_tool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/base.py#L237](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/base.py#L237)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_app_tool(self, app_name: str, tool_name: str) -> Tool | None
```

Look up an app-visible tool by original name, bypassing transforms.

Searches for a tool named `tool_name` tagged with the given app
name.  Skips the transform chain entirely.

**Returns:**

* The tool if found and tagged with the given app name, else None.

#### `get_tool_by_hash` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/base.py#L263](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/base.py#L263)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_tool_by_hash(self, tool_hash: str, tool_name: str) -> Tool | None
```

Get an app-visible tool by its identity hash, through `get_tool()`.

The identity hash survives renaming, so `_get_tool_by_hash()` finds
the tool beneath this provider's transforms. Its name above the
transforms comes from their listing, and the tool is then looked up
under that name with `get_tool()`, the same public lookup a name call
uses. While that lookup runs, the bottom of the chain answers the
found tool for its own name and looks up every other name as usual,
so transforms and `get_tool()` overrides decide exactly as they would
for a name call, while a different tool sharing the name cannot take
the found tool's place. A version constraint the found tool does not
meet is looked up as usual and accepted only for the same identity.
A nested lookup of that same name on this provider while the hashed
lookup runs resolves to the found tool; tasks started during the
lookup resolve names as usual once it finishes.

Note: Like `get_tool()`, this does NOT filter disabled components. The
Server (FastMCP) performs enabled filtering after all transforms.

**Args:**

* `tool_hash`: The identity hash from a `<hash>_<local_name>` name.
* `tool_name`: The local tool name from the same name.

**Returns:**

* The tool if found and not hidden (may be marked disabled), else None.

#### `list_resources` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/base.py#L338](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/base.py#L338)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
list_resources(self) -> Sequence[Resource]
```

List resources with all transforms applied.

Components may be marked as disabled but are NOT filtered here.

#### `get_resource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/base.py#L348](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/base.py#L348)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_resource(self, uri: str, version: VersionSpec | None = None) -> Resource | None
```

Get resource by transformed URI with all transforms applied.

Note: This method does NOT filter disabled components. The Server
(FastMCP) performs enabled filtering after all transforms complete.

**Args:**

* `uri`: The transformed resource URI to look up.
* `version`: Optional version filter. If None, returns highest version.

**Returns:**

* The resource if found (may be marked disabled), None if not found.

#### `list_resource_templates` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/base.py#L378](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/base.py#L378)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
list_resource_templates(self) -> Sequence[ResourceTemplate]
```

List resource templates with all transforms applied.

Components may be marked as disabled but are NOT filtered here.

#### `get_resource_template` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/base.py#L388](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/base.py#L388)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_resource_template(self, uri: str, version: VersionSpec | None = None) -> ResourceTemplate | None
```

Get resource template by transformed URI with all transforms applied.

Note: This method does NOT filter disabled components. The Server
(FastMCP) performs enabled filtering after all transforms complete.

**Args:**

* `uri`: The transformed template URI to look up.
* `version`: Optional version filter. If None, returns highest version.

**Returns:**

* The template if found (may be marked disabled), None if not found.

#### `list_prompts` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/base.py#L421](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/base.py#L421)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
list_prompts(self) -> Sequence[Prompt]
```

List prompts with all transforms applied.

Components may be marked as disabled but are NOT filtered here.

#### `get_prompt` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/base.py#L431](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/base.py#L431)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_prompt(self, name: str, version: VersionSpec | None = None) -> Prompt | None
```

Get prompt by transformed name with all transforms applied.

Note: This method does NOT filter disabled components. The Server
(FastMCP) performs enabled filtering after all transforms complete.

**Args:**

* `name`: The transformed prompt name to look up.
* `version`: Optional version filter. If None, returns highest version.

**Returns:**

* The prompt if found (may be marked disabled), None if not found.

#### `get_tasks` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/base.py#L592](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/base.py#L592)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_tasks(self) -> Sequence[FastMCPComponent]
```

Return components that should be registered as background tasks.

Override to customize which components are task-eligible.
Default calls list\_\* methods, applies provider transforms, and filters
for components with task\_config.mode != 'forbidden'.

Used by the server during startup to register functions with Docket.

#### `lifespan` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/base.py#L663](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/base.py#L663)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
lifespan(self) -> AsyncIterator[None]
```

User-overridable lifespan for custom setup and teardown.

Override this method to perform provider-specific initialization
like opening database connections, setting up external resources,
or other state management needed for the provider's lifetime.

The lifespan scope matches the server's lifespan - code before yield
runs at startup, code after yield runs at shutdown.

#### `enable` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/base.py#L692](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/base.py#L692)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
enable(self) -> Self
```

Enable components matching all specified criteria.

Adds a visibility transform that marks matching components as enabled.
Later transforms override earlier ones, so enable after disable makes
the component enabled.

With only=True, switches to allowlist mode - first disables everything,
then enables matching components.

**Args:**

* `names`: Component names or URIs to enable.
* `keys`: Component keys to enable (e.g., tool:my\_tool\@v1).
* `version`: Component version spec to enable (e.g., VersionSpec(eq="v1") or
  VersionSpec(gte="v2")). Unversioned components will not match.
* `tags`: Enable components with these tags.
* `components`: Component types to include (e.g., {"tool", "prompt"}).
* `only`: If True, ONLY enable matching components (allowlist mode).

**Returns:**

* Self for method chaining.

#### `disable` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/base.py#L741](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/base.py#L741)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
disable(self) -> Self
```

Disable components matching all specified criteria.

Adds a visibility transform that marks matching components as disabled.
Components can be re-enabled by calling enable() with matching criteria
(the later transform wins).

**Args:**

* `names`: Component names or URIs to disable.
* `keys`: Component keys to disable (e.g., tool:my\_tool\@v1).
* `version`: Component version spec to disable (e.g., VersionSpec(eq="v1") or
  VersionSpec(gte="v2")). Unversioned components will not match.
* `tags`: Disable components with these tags.
* `components`: Component types to include (e.g., {"tool", "prompt"}).

**Returns:**

* Self for method chaining.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.