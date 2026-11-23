> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# claude_desktop

# `fastmcp.cli.install.claude_desktop`

Claude Desktop integration for FastMCP install using Cyclopts.

## Functions

### `get_claude_config_path` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/install/claude\_desktop.py#L20](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/install/claude_desktop.py#L20)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_claude_config_path(config_path: Path | None = None) -> Path | None
```

Get the Claude config directory based on platform.

**Args:**

* `config_path`: Optional custom path to the Claude Desktop config directory

### `install_claude_desktop` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/install/claude\_desktop.py#L49](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/install/claude_desktop.py#L49)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
install_claude_desktop(file: Path, server_object: str | None, name: str) -> bool
```

Install FastMCP server in Claude Desktop.

**Args:**

* `file`: Path to the server file
* `server_object`: Optional server object name (for :object suffix)
* `name`: Name for the server in Claude's config
* `with_editable`: Optional list of directories to install in editable mode
* `with_packages`: Optional list of additional packages to install
* `env_vars`: Optional dictionary of environment variables
* `python_version`: Optional Python version to use
* `with_requirements`: Optional requirements file to install from
* `project`: Optional project directory to run within
* `config_path`: Optional custom path to Claude Desktop config directory

**Returns:**

* True if installation was successful, False otherwise

### `claude_desktop_command` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/install/claude\_desktop.py#L139](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/install/claude_desktop.py#L139)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
claude_desktop_command(server_spec: str) -> None
```

Install an MCP server in Claude Desktop.

**Args:**

* `server_spec`: Python file to install, optionally with :object suffix


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.