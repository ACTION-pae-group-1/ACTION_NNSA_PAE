> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# generate

# `fastmcp.cli.generate`

Generate a standalone CLI script and agent skill from an MCP server.

## Functions

### `serialize_transport` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/generate.py#L122](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/generate.py#L122)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
serialize_transport(resolved: str | dict[str, Any] | ClientTransport) -> tuple[str, set[str]]
```

Serialize a resolved transport to a Python expression string.

Returns `(expression, extra_imports)` where *extra\_imports* is a set of
import lines needed by the expression.

### `generate_cli_script` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/generate.py#L288](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/generate.py#L288)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
generate_cli_script(server_name: str, server_spec: str, transport_code: str, extra_imports: set[str], tools: list[mcp_types.Tool]) -> str
```

Generate the full CLI script source code.

### `generate_skill_content` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/generate.py#L624](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/generate.py#L624)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
generate_skill_content(server_name: str, cli_filename: str, tools: list[mcp_types.Tool]) -> str
```

Generate a SKILL.md file for a generated CLI script.

### `generate_cli_command` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/generate.py#L675](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/generate.py#L675)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
generate_cli_command(server_spec: Annotated[str, cyclopts.Parameter(help='Server URL, Python file, MCPConfig JSON, discovered name, or .js file')], output: Annotated[str, cyclopts.Parameter(help='Output file path (default: cli.py)')] = 'cli.py') -> None
```

Generate a standalone CLI script from an MCP server.

Connects to the server, reads its tools/resources/prompts, and writes
a Python script that can invoke them directly. Also generates a SKILL.md
agent skill file unless --no-skill is passed.

**Examples:**

fastmcp generate-cli weather
fastmcp generate-cli weather my\_cli.py
fastmcp generate-cli [http://localhost:8000/mcp](http://localhost:8000/mcp)
fastmcp generate-cli server.py output.py -f
fastmcp generate-cli weather --no-skill


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.