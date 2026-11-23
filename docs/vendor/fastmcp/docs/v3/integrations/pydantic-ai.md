> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Pydantic AI 🤝 FastMCP

> Connect FastMCP servers to Pydantic AI agents using the FastMCPToolset

[Pydantic AI](https://ai.pydantic.dev/) ships a [`FastMCPToolset`](https://ai.pydantic.dev/mcp/fastmcp-client/) that lets a Pydantic AI agent call tools exposed by any MCP server through the [FastMCP Client](https://gofastmcp.com/docs/clients/client.md). Because the toolset is built on the FastMCP Client, it works with FastMCP servers as well as any other MCP server, and supports the full range of [transports](https://gofastmcp.com/docs/clients/transports.md): in-memory, STDIO, Streamable HTTP, and SSE.

This page shows how to point `FastMCPToolset` at a FastMCP server, with examples for each transport. For the toolset's full API, see the [Pydantic AI documentation](https://ai.pydantic.dev/mcp/fastmcp-client/).

> [!TIP]
>
> The `FastMCPToolset` currently exposes **tools** to the agent. Other MCP features such as elicitation and sampling are not yet supported through this toolset; use Pydantic AI's standard [`MCPServer`](https://ai.pydantic.dev/mcp/client/) client if you need them.

## Install

`FastMCPToolset` lives in `pydantic-ai-slim` behind the `fastmcp` optional group:

```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
pip install "pydantic-ai-slim[fastmcp]"
```

## Create a Server

Create a FastMCP server with the tools you want to expose. We'll use a single dice-rolling tool throughout this guide.

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

## In-Memory

If your FastMCP server lives in the same process as your agent, pass the `FastMCP` instance directly. The toolset reuses an [in-memory transport](https://gofastmcp.com/docs/clients/transports.md#in-memory-transport), which avoids a network round trip and is the fastest option for tests and embedded use.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
import asyncio
import random
from fastmcp import FastMCP
from pydantic_ai import Agent
from pydantic_ai.toolsets.fastmcp import FastMCPToolset

mcp = FastMCP(name="Dice Roller")

@mcp.tool
def roll_dice(n_dice: int) -> list[int]:
    return [random.randint(1, 6) for _ in range(n_dice)]

toolset = FastMCPToolset(mcp)
agent = Agent("openai:gpt-4.1", toolsets=[toolset])

async def main():
    result = await agent.run("Roll 3 dice!")
    print(result.output)

if __name__ == "__main__":
    asyncio.run(main())
```

## Streamable HTTP

For a remote FastMCP server reachable over HTTP, pass the URL as a string. The toolset infers the [Streamable HTTP transport](https://gofastmcp.com/docs/clients/transports.md#http-transport) from the URL.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from pydantic_ai import Agent
from pydantic_ai.toolsets.fastmcp import FastMCPToolset

toolset = FastMCPToolset("https://your-server-url.com/mcp")
agent = Agent("openai:gpt-4.1", toolsets=[toolset])
```

For [SSE](https://gofastmcp.com/docs/clients/transports.md#sse-transport), use a `/sse` URL instead.

## STDIO

To launch a FastMCP server as a subprocess, pass a script path and the toolset will use the [STDIO transport](https://gofastmcp.com/docs/clients/transports.md#stdio-transport).

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from pydantic_ai import Agent
from pydantic_ai.toolsets.fastmcp import FastMCPToolset

toolset = FastMCPToolset("server.py")
agent = Agent("openai:gpt-4.1", toolsets=[toolset])
```

You can also pass a [`StdioTransport`](https://gofastmcp.com/docs/clients/transports#stdio-transport) directly when you need control over the command, args, or environment.

## MCP Configuration

To wire up multiple servers at once, pass an [MCP configuration](https://gofastmcp.com/docs/integrations/mcp-json-configuration.md) dictionary. The toolset opens one client per server and exposes all of their tools to the agent.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from pydantic_ai import Agent
from pydantic_ai.toolsets.fastmcp import FastMCPToolset

mcp_config = {
    "mcpServers": {
        "dice": {"command": "python", "args": ["server.py"]},
        "weather": {"url": "https://weather.example.com/mcp"},
    }
}

toolset = FastMCPToolset(mcp_config)
agent = Agent("openai:gpt-4.1", toolsets=[toolset])
```

## Authentication

Because `FastMCPToolset` wraps a [FastMCP `Client`](https://gofastmcp.com/docs/clients/client), it inherits the client's full [authentication](https://gofastmcp.com/docs/clients/auth/bearer.md) story. To pass credentials such as a bearer token to a remote server, build a `Client` (or `StreamableHttpTransport`) yourself and hand it to the toolset.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport
from pydantic_ai import Agent
from pydantic_ai.toolsets.fastmcp import FastMCPToolset

transport = StreamableHttpTransport(
    url="https://your-server-url.com/mcp",
    headers={"Authorization": "Bearer your-access-token"},
)

toolset = FastMCPToolset(Client(transport))
agent = Agent("openai:gpt-4.1", toolsets=[toolset])
```

For OAuth flows, use FastMCP's [`OAuth` helper](https://gofastmcp.com/docs/clients/auth/oauth) when constructing the `Client`. For server-side token verification, see [Token Verification](https://gofastmcp.com/docs/servers/auth/token-verification.md).


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.