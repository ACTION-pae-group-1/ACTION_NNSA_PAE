> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# Pydantic AI 🤝 FastMCP

> Connect FastMCP servers to Pydantic AI agents with MCPToolset

[Pydantic AI](https://pydantic.dev/docs/ai/)'s [`MCPToolset`](https://pydantic.dev/docs/ai/mcp/client/) is built on the [FastMCP Client](https://gofastmcp.com/clients/client.md), so an agent can use any MCP server over any FastMCP [transport](https://gofastmcp.com/clients/transports.md). It covers tools, resources, prompts, and elicitation. This page shows how to point it at a FastMCP server; for the full API, see the [Pydantic AI docs](https://pydantic.dev/docs/ai/mcp/client/).

## Install

```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
pip install "pydantic-ai-slim[mcp]>=2.45"
```

The `mcp` extra installs the client-only `fastmcp-slim[client]`. Add `fastmcp` if the same environment also runs a FastMCP server.

> [!NOTE]
>
> With FastMCP 4, use `pydantic-ai-slim` 2.45 or newer. Releases 2.32 through 2.44 import `httpx` without depending on it, and FastMCP 4 no longer installs `httpx`, so `import pydantic_ai.mcp` fails.

## Create a Server

```python server.py theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
import random
from fastmcp import FastMCP

mcp = FastMCP(name="Dice Roller")

@mcp.tool
def roll_dice(n_dice: int) -> list[int]:
    """Roll `n_dice` 6-sided dice and return the results."""
    return [random.randint(1, 6) for _ in range(n_dice)]

if __name__ == "__main__":
    mcp.run(transport="http", port=8000)
```

## Connect an Agent

Pass `MCPToolset` anything the FastMCP Client accepts. It infers the transport the same way the client does.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from pathlib import Path
from pydantic_ai import Agent
from pydantic_ai.mcp import MCPToolset

from server import mcp

in_memory = MCPToolset(mcp)  # a FastMCP instance in the same process
http = MCPToolset("http://localhost:8000/mcp")  # Streamable HTTP; a /sse URL uses SSE
stdio = MCPToolset(Path("server.py"))  # launches the script over STDIO

agent = Agent("openai:gpt-5", toolsets=[http])
result = agent.run_sync("Roll 3 dice!")
```

Pass a FastMCP [transport](https://gofastmcp.com/clients/transports.md) such as `StdioTransport` for control over the command, arguments, or environment, or a configured `fastmcp.Client` for full control.

## Authentication

For a bearer token, pass `headers`. For [OAuth](https://gofastmcp.com/clients/auth/oauth.md), pass `auth="oauth"` or build the `Client` yourself.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
toolset = MCPToolset(
    "https://your-server-url.com/mcp",
    headers={"Authorization": "Bearer your-access-token"},
)
```

For server-side token verification, see [Token Verification](https://gofastmcp.com/servers/auth/token-verification.md).

## Multiple Servers

`load_mcp_toolsets` reads an [MCP configuration](https://gofastmcp.com/integrations/mcp-json-configuration.md) file and returns one toolset per server. Tool names are prefixed with the server's key.

```json mcp_config.json theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
{
  "mcpServers": {
    "dice": {"command": "python", "args": ["server.py"]},
    "weather": {"url": "https://weather.example.com/mcp"}
  }
}
```

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from pydantic_ai import Agent
from pydantic_ai.mcp import load_mcp_toolsets

agent = Agent("openai:gpt-5", toolsets=load_mcp_toolsets("mcp_config.json"))
```

## Elicitation

Pass an `elicitation_handler` to answer a server's [elicitation](https://gofastmcp.com/servers/elicitation.md) requests. It has the same signature as the FastMCP Client's [elicitation handler](https://gofastmcp.com/clients/elicitation.md).

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
async def approve(message, response_type, params, context):
    return {"approved": True}

toolset = MCPToolset("http://localhost:8000/mcp", elicitation_handler=approve)
```

On 2026-07-28 connections, Pydantic AI may warn that `elicitation_handler` will never be called. The FastMCP Client still calls it for [input-required results](https://gofastmcp.com/servers/elicitation.md#elicitation-on-the-modern-protocol).


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.