> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# CLI

> The fastmcp command-line interface

The `fastmcp` CLI is installed automatically with FastMCP. It's the primary way to run, test, install, and interact with MCP servers from your terminal.

```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
fastmcp --help
```

## Commands at a Glance

| Command | What it does |
| - | - |
| [`run`](https://gofastmcp.com/cli/running) | Run a server (local file, factory function, remote URL, or config file) |
| [`dev apps`](https://gofastmcp.com/cli/running#previewing-apps) | Launch a browser-based preview UI for Prefab App tools |
| [`dev inspector`](https://gofastmcp.com/cli/running#development-with-the-inspector) | Launch a server inside the MCP Inspector for interactive testing |
| [`install`](https://gofastmcp.com/cli/install-mcp) | Install a server into Claude Code, Claude Desktop, Cursor, Gemini CLI, or Goose |
| [`inspect`](https://gofastmcp.com/cli/inspecting) | Print a server's tools, resources, and prompts as a summary or JSON report |
| [`list`](https://gofastmcp.com/cli/client) | List a server's tools (and optionally resources and prompts) |
| [`call`](https://gofastmcp.com/cli/client#calling-tools) | Call a tool, read a resource, or get a prompt |
| [`discover`](https://gofastmcp.com/cli/client#discovering-configured-servers) | Find MCP servers configured in your editors and tools |
| [`generate-cli`](https://gofastmcp.com/cli/generate-cli) | Scaffold a standalone typed CLI from a server's tool schemas |
| [`project prepare`](https://gofastmcp.com/cli/running#pre-building-environments) | Pre-install dependencies into a reusable uv project |
| [`auth cimd`](https://gofastmcp.com/cli/auth) | Create and validate CIMD documents for OAuth |
| `login` | Sign in to Prefect Horizon with a browser device flow |
| `whoami` | Show the current Horizon account |
| `logout` | Revoke the current Horizon key and remove the local credential |
| `version` | Print version info (`--copy` to copy to clipboard) |

## Server Targets

Most commands need to know *which server* to talk to. You pass a "server spec" as the first argument, and FastMCP resolves the right transport automatically.

**URLs** connect to a running HTTP server:

```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
fastmcp list http://localhost:8000/mcp
fastmcp call http://localhost:8000/mcp get_forecast city=London
```

**Python files** are loaded directly — no `mcp.run()` boilerplate needed. FastMCP finds a server instance named `mcp`, `server`, or `app` in the file, or you can specify one explicitly:

```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
fastmcp list server.py
fastmcp run server.py:my_custom_server
```

**Config files** work too — both FastMCP's own `fastmcp.json` format and standard MCP config files with an `mcpServers` key:

```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
fastmcp run fastmcp.json
fastmcp list mcp-config.json
```

**Stdio commands** connect to any MCP server that speaks over standard I/O. Use `--command` instead of a positional argument:

```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
fastmcp list --command 'npx -y @modelcontextprotocol/server-github'
```

### Name-Based Resolution

If your servers are already configured in an editor or tool, you can refer to them by name. FastMCP scans configs from Claude Desktop, Claude Code, Cursor, Gemini CLI, and Goose:

```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
fastmcp list weather
fastmcp call weather get_forecast city=London
```

When the same name appears in multiple configs, use the `source:name` form to be specific:

```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
fastmcp list claude-code:my-server
fastmcp call cursor:weather get_forecast city=London
```

Run [`fastmcp discover`](https://gofastmcp.com/cli/client#discovering-configured-servers) to see what's available on your machine.

## Authentication

### Prefect Horizon Account

Use the top-level account commands to manage the credential for Prefect Horizon.

```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
fastmcp login
fastmcp whoami
fastmcp logout
```

`fastmcp login` first uses `HORIZON_API_KEY` or a valid stored key when one is available.
When login needs a new key, it shows a verification URL and code.
It opens a browser when the terminal supports it.
If the browser does not open, use the shown URL and code on another device.
To switch accounts, run `fastmcp logout` before you run `fastmcp login` again.

Login stores only the personal Horizon API key.
It does not select or store a deployment organization.
`fastmcp whoami` gets the current user from Horizon.
`fastmcp logout` attempts to revoke the stored key and always removes its local credential.

Set `HORIZON_API_KEY` to use an environment credential instead.
The CLI gives that value first precedence and never stores it.
When this variable controls the session, logout does not revoke or remove any credential.
Remove the variable from your environment to sign out.

Use `--json` for stable command results.
During JSON login, the verification challenge goes to stderr and the final result goes to stdout.
JSON mode does not open a browser or ask a question.

### MCP Server Authentication

When targeting an HTTP URL, the CLI enables OAuth authentication by default. If the server requires it, you'll be guided through the flow (typically opening a browser). If it doesn't, the setup is a silent no-op.

OAuth tokens are kept in memory by default and discarded when the command exits. To reuse authentication across `fastmcp list` and `fastmcp call`, generate a Fernet key once and save it as `FASTMCP_OAUTH_ENCRYPTION_KEY` in your environment or `.env` file:

```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

With that setting, the CLI encrypts tokens and client registration details on disk under `FASTMCP_HOME`. Keep the key secret and reuse the same value across invocations. Changing it starts a separate cache and requires signing in again. This applies to HTTP and SSE URLs and discovered servers that connect directly over HTTP or SSE; MCPConfig files retain their per-server authentication configuration. The Python SDK's storage defaults are unchanged.

To skip authentication entirely — useful for local development servers — pass `--auth none`:

```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
fastmcp call http://localhost:8000/mcp my_tool --auth none
```

You can also pass a bearer token directly. Give the token value on its own; FastMCP adds the `Bearer` prefix when it builds the `Authorization` header.

```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
fastmcp list http://localhost:8000/mcp --auth "sk-..."
```

## Transport Override

FastMCP defaults to Streamable HTTP for URL targets. If the server only supports Server-Sent Events (SSE), force the older transport:

```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
fastmcp list http://localhost:8000 --transport sse
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.