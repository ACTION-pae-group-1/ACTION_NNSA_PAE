> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# claude_code

# `fastmcp.cli.install.claude_code`

Claude Code integration for FastMCP install using Cyclopts.

## Functions

### `find_claude_command` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/install/claude\_code.py#L20](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/install/claude_code.py#L20)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
find_claude_command() -> str | None
```

Find the Claude Code CLI command.

Checks common installation locations since 'claude' is often a shell alias
that doesn't work with subprocess calls.

### `check_claude_code_available` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/install/claude\_code.py#L68](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/install/claude_code.py#L68)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
check_claude_code_available() -> bool
```

Check if Claude Code CLI is available.

### `install_claude_code` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/install/claude\_code.py#L73](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/install/claude_code.py#L73)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
install_claude_code(file: Path, server_object: str | None, name: str) -> bool
```

Install FastMCP server in Claude Code.

**Args:**

* `file`: Path to the server file
* `server_object`: Optional server object name (for :object suffix)
* `name`: Name for the server in Claude Code
* `with_editable`: Optional list of directories to install in editable mode
* `with_packages`: Optional list of additional packages to install
* `env_vars`: Optional dictionary of environment variables
* `python_version`: Optional Python version to use
* `with_requirements`: Optional requirements file to install from
* `project`: Optional project directory to run within

**Returns:**

* True if installation was successful, False otherwise

### `claude_code_command` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/install/claude\_code.py#L155](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/install/claude_code.py#L155)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
claude_code_command(server_spec: str) -> None
```

Install an MCP server in Claude Code.

**Args:**

* `server_spec`: Python file to install, optionally with :object suffix


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.