> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Local Provider

> The default provider for decorator-registered components

New in version `3.0.0`

`LocalProvider` stores components that you define directly on your server. When you use `@mcp.tool`, `@mcp.resource`, or `@mcp.prompt`, you're adding components to your server's `LocalProvider`.

## How It Works

Every FastMCP server has a `LocalProvider` as its first provider. Components registered via decorators or direct methods are stored here:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import FastMCP

mcp = FastMCP("MyServer")

# These are stored in the server's `LocalProvider`
@mcp.tool
def greet(name: str) -> str:
    """Greet someone by name."""
    return f"Hello, {name}!"

@mcp.resource("data://config")
def get_config() -> str:
    """Return configuration data."""
    return '{"version": "1.0"}'

@mcp.prompt
def analyze(topic: str) -> str:
    """Create an analysis prompt."""
    return f"Please analyze: {topic}"
```

Because the `LocalProvider` is registered first, your directly-defined components win ties against mounted or proxied components with the same identifier and version. A higher version from another provider still wins; see [Provider Order](https://gofastmcp.com/docs/servers/providers/overview.md#provider-order).

## Component Registration

### Using Decorators

The most common way to register components:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import FastMCP

mcp = FastMCP("MyServer")


@mcp.tool
def my_tool(x: int) -> str:
    return str(x)

@mcp.resource("data://info")
def my_resource() -> str:
    return "info"

@mcp.prompt
def my_prompt(topic: str) -> str:
    return f"Discuss: {topic}"
```

### Using Direct Methods

You can also add pre-built component objects:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import FastMCP
from fastmcp.prompts import Prompt
from fastmcp.resources import Resource
from fastmcp.tools import Tool


def add(a: int, b: int) -> int:
    return a + b


def read_info() -> str:
    return "info"


def discuss(topic: str) -> str:
    return f"Discuss: {topic}"


mcp = FastMCP("MyServer")

my_tool = Tool.from_function(add, name="custom_tool")
my_resource = Resource.from_function(read_info, uri="data://info")
my_prompt = Prompt.from_function(discuss)

mcp.add_tool(my_tool)
mcp.add_resource(my_resource)
mcp.add_prompt(my_prompt)
```

### Removing Components

Remove components by name or URI. Each call removes every version unless you pass `version=`, and raises `KeyError` when nothing matches:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
mcp.local_provider.remove_tool("my_tool")
mcp.local_provider.remove_resource("data://info")
mcp.local_provider.remove_prompt("my_prompt")
```

## Duplicate Handling

When you try to add a component that already exists, the behavior depends on the `on_duplicate` setting. A `FastMCP` server defaults to `"warn"`; a standalone `LocalProvider` defaults to `"error"`.

| Mode | Behavior |
| - | - |
| `"warn"` | Log a warning and replace |
| `"error"` | Raise `ValueError` |
| `"replace"` | Silently replace |
| `"ignore"` | Keep the existing component |

Configure this when creating the server:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import FastMCP

mcp = FastMCP("MyServer", on_duplicate="error")
```

## Component Visibility

New in version `3.0.0`

Components can be dynamically enabled or disabled at runtime. Disabled components don't appear in listings and can't be called.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import FastMCP

mcp = FastMCP("MyServer")


@mcp.tool(tags={"admin"})
def delete_all() -> str:
    """Delete everything."""
    return "Deleted"

@mcp.tool
def get_status() -> str:
    """Get system status."""
    return "OK"

# Disable admin tools
mcp.disable(tags={"admin"})

# Or only enable specific tools
mcp.enable(names={"get_status"}, only=True)
```

See [Visibility](https://gofastmcp.com/docs/servers/visibility.md) for the full documentation on names, tags, keys, allowlist mode, and provider-level control.

## Standalone LocalProvider

You can create a LocalProvider independently and attach it to multiple servers:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import FastMCP
from fastmcp.server.providers import LocalProvider

# Create a reusable provider
shared_tools = LocalProvider()

@shared_tools.tool
def greet(name: str) -> str:
    return f"Hello, {name}!"

@shared_tools.resource("data://version")
def get_version() -> str:
    return "1.0.0"

# Attach to multiple servers
server1 = FastMCP("Server1", providers=[shared_tools])
server2 = FastMCP("Server2", providers=[shared_tools])
```

This is useful for:

* Sharing components across servers
* Testing components in isolation
* Building reusable component libraries

Standalone providers also support visibility control with `enable()` and `disable()`. See [Visibility](https://gofastmcp.com/docs/servers/visibility.md) for details.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.