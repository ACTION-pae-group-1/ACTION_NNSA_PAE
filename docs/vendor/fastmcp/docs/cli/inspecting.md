> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Inspecting Servers

> View a server's components and metadata

New in version `2.9.0`

`fastmcp inspect` loads a server and reports what it contains — its tools, resources, prompts, version, and metadata. The default output is a human-readable summary:

```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
fastmcp inspect server.py
```

```text theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
Server
  Name:         MyServer
  Version:      1.0.0
  Generation:   2
  Instructions: A helpful MCP server

Components
  Tools:        5
  Prompts:      2
  Resources:    3
  Templates:    1

Environment
  FastMCP:      4.2.0
  MCP:          2.3.0

Use --format [fastmcp|mcp] for complete JSON output
```

## JSON Output

For programmatic use, two JSON formats are available:

**FastMCP format** (`--format fastmcp`) includes everything FastMCP knows about the server — component keys, tags, output schemas, annotations, custom metadata, and the server's capabilities. Field names use `snake_case`. This is the format for debugging and introspecting FastMCP servers.

**MCP protocol format** (`--format mcp`) shows exactly what MCP clients see through the protocol — only standard MCP fields, `camelCase` names, no FastMCP-specific extensions. This is the format for verifying client compatibility and debugging what clients actually receive.

```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
# Full FastMCP metadata to stdout
fastmcp inspect server.py --format fastmcp

# MCP protocol view saved to file
fastmcp inspect server.py --format mcp -o manifest.json
```

## Options

| Option | Flag | Description |
| - | - | - |
| Format | `--format`, `-f` | `fastmcp` or `mcp` (required when using `-o`) |
| Output File | `--output`, `-o` | Save to file instead of stdout |
| Python | `--python` | Python version to use when running via `uv` |
| Extra Packages | `--with` | Additional packages to install (repeatable) |
| Project | `--project` | Run within a specific uv project directory |
| Requirements | `--with-requirements` | Install from a requirements file |
| Skip Env | `--skip-env` | Do not set up a uv environment |

## Entrypoints

The `inspect` command supports the same local entrypoints as [`fastmcp run`](https://gofastmcp.com/docs/cli/running): inferred instances, explicit entrypoints, factory functions, and `fastmcp.json` configs.

```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
fastmcp inspect server.py                  # inferred instance
fastmcp inspect server.py:my_server        # explicit entrypoint
fastmcp inspect server.py:create_server    # factory function
fastmcp inspect fastmcp.json               # config file
```

> [!WARNING]
>
> `inspect` only works with local files and `fastmcp.json` — it doesn't connect to remote URLs or standard MCP config files.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.