> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# generative

# `fastmcp.apps.generative`

GenerativeUI — a Provider that adds LLM-generated UI capabilities.

Registers tools and resources from `prefab_ui.generative` so that an
LLM can write Prefab Python code, execute it in a sandbox, and render
the result as a streaming interactive UI.

Requires `fastmcp[apps]` (prefab-ui).

Usage::

from fastmcp import FastMCP
from fastmcp.apps.generative import GenerativeUI

mcp = FastMCP("My Server")
mcp.add\_provider(GenerativeUI())

## Classes

### `GenerativeUI` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/apps/generative.py#L53](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/apps/generative.py#L53)</sup>

A Provider that adds generative UI capabilities to a server.

Registers:

* A `generate_ui` tool that accepts Prefab Python code, executes
  it in a Pyodide sandbox, and returns the rendered PrefabApp.
  Supports streaming via `ontoolinputpartial`.
* A `components` tool that searches the Prefab component library.
* The generative renderer resource with CSP for Pyodide CDN access.

Example::

from fastmcp import FastMCP
from fastmcp.apps.generative import GenerativeUI

mcp = FastMCP("My Server")
mcp.add\_provider(GenerativeUI())

**Methods:**

#### `lifespan` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/apps/generative.py#L197](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/apps/generative.py#L197)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
lifespan(self) -> AsyncIterator[None]
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.