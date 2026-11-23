> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Welcome to FastMCP

> The fast, Pythonic way to build MCP servers, clients, and applications.

<video autoPlay muted loop playsInline src="https://mintcdn.com/fastmcp/-fU9AuXWlaP61Fuq/assets/brand/f-watercolor-waves-4-animated.mp4?fit=max&auto=format&n=-fU9AuXWlaP61Fuq&q=85&s=5eb68c6916a4c338185cae8b742f144d" />

**FastMCP is the standard framework for building MCP applications.** The [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) connects LLMs to tools and data. FastMCP gives you everything you need to go from prototype to production — build servers that expose capabilities, connect clients to any MCP service, and give your tools interactive UIs:

```python {1} theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import FastMCP

mcp = FastMCP("Demo 🚀")

@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

if __name__ == "__main__":
    mcp.run()
```

## Move Fast and Make Things

The [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) lets you give agents access to your tools and data. But building an effective MCP application is harder than it looks.

FastMCP handles all of it. Declare a tool with a Python function, and the schema, validation, and documentation are generated automatically. Connect to a server with a URL, and transport negotiation, authentication, and protocol lifecycle are managed for you. You focus on your logic, and the MCP part just works: **with FastMCP, best practices are built in.**

**That's why FastMCP is the standard framework for working with MCP.** FastMCP 1.0 was incorporated into the official MCP Python SDK in 2024. Today, the actively maintained standalone project is downloaded a million times a day, and some version of FastMCP powers 70% of MCP servers across all languages.

FastMCP has three pillars:

> [card] [Servers](https://gofastmcp.com/docs/servers/server.md)
>
> Expose tools, resources, and prompts to LLMs.

> [card] [Apps](https://gofastmcp.com/docs/apps/overview.md)
>
> Give your tools interactive UIs rendered directly in the conversation.

> [card] [Clients](https://gofastmcp.com/docs/clients/client.md)
>
> Connect to any MCP server — local or remote, programmatic or CLI.

**[Servers](https://gofastmcp.com/docs/servers/server.md)** wrap your Python functions into MCP-compliant tools, resources, and prompts. **[Clients](https://gofastmcp.com/docs/clients/client.md)** connect to any server with full protocol support. And **[Apps](https://gofastmcp.com/docs/apps/overview.md)** give your tools interactive UIs rendered directly in the conversation.

Ready to build? Start with the [installation guide](https://gofastmcp.com/docs/getting-started/installation.md) or jump straight to the [quickstart](https://gofastmcp.com/docs/getting-started/quickstart.md).

FastMCP is made with 💙 by [Prefect](https://www.prefect.io/).

## Run FastMCP in production with Horizon

FastMCP is the standard way to build MCP servers. **[Prefect Horizon](https://www.prefect.io/horizon?utm_source=gofastmcp\&utm_medium=docs\&utm_campaign=docs_welcome\&utm_content=welcome_body)** is the enterprise MCP gateway for running them safely.

Built by the FastMCP team, Horizon packages the best practices we've learned shipping the world's most popular MCP framework.

Deploy FastMCP servers from GitHub with branch previews and instant rollback. Create a private registry of every MCP your company uses. Secure access with SSO and tool-level RBAC. Get audit logs, observability, and governance across your MCP stack. Remix approved tools into purpose-built endpoints for teams and agents.

Start with FastMCP. [Scale with Horizon →](https://www.prefect.io/horizon?utm_source=gofastmcp\&utm_medium=docs\&utm_campaign=docs_welcome\&utm_content=welcome_cta)

> [!TIP]
>
> **This documentation reflects FastMCP's `main` branch**, meaning it always reflects the latest development version. Features are generally marked with version badges (e.g. `New in version: 3.0.0`) to indicate when they were introduced. Note that this may include features that are not yet released.

## LLM-Friendly Docs

The FastMCP documentation is available in multiple LLM-friendly formats:

### MCP Server

The FastMCP docs are accessible via MCP! The server URL is `https://gofastmcp.com/mcp`.

In fact, you can use FastMCP to search the FastMCP docs:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
import asyncio
from fastmcp import Client

async def main():
    async with Client("https://gofastmcp.com/mcp") as client:
        result = await client.call_tool(
            name="search_fast_mcp",
            arguments={"query": "deploy a FastMCP server"}
        )
    print(result)

asyncio.run(main())
```

### Text Formats

The docs are also available in [llms.txt format](https://llmstxt.org/):

* [llms.txt](https://gofastmcp.com/llms.txt) - A sitemap listing all documentation pages
* [llms-full.txt](https://gofastmcp.com/llms-full.txt) - The entire documentation in one file (may exceed context windows)

Any page can be accessed as markdown by appending `.md` to the URL. For example, this page becomes `https://gofastmcp.com/getting-started/welcome.md`.

You can also copy any page as markdown by pressing "Cmd+C" (or "Ctrl+C" on Windows) on your keyboard.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.