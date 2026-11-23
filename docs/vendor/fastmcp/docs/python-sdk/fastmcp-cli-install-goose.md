> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# goose

# `fastmcp.cli.install.goose`

Goose integration for FastMCP install using Cyclopts.

## Functions

### `generate_goose_deeplink` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/install/goose.py#L29](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/install/goose.py#L29)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
generate_goose_deeplink(name: str, command: str, args: list[str]) -> str
```

Generate a Goose deeplink for installing an MCP extension.

**Args:**

* `name`: Human-readable display name for the extension.
* `command`: The executable command (e.g. "uv").
* `args`: Arguments to the command.
* `description`: Short description shown in Goose.

**Returns:**

* A goose://extension?... deeplink URL.

### `install_goose` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/install/goose.py#L85](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/install/goose.py#L85)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
install_goose(file: Path, server_object: str | None, name: str) -> bool
```

Install FastMCP server in Goose via deeplink.

**Args:**

* `file`: Path to the server file.
* `server_object`: Optional server object name (for :object suffix).
* `name`: Name for the extension in Goose.
* `with_packages`: Optional list of additional packages to install.
* `python_version`: Optional Python version to use.

**Returns:**

* True if installation was successful, False otherwise.

### `goose_command` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/install/goose.py#L135](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/install/goose.py#L135)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
goose_command(server_spec: str) -> None
```

Install an MCP server in Goose.

Uses uvx to run the server. Environment variables are not included
in the deeplink; use `fastmcp install mcp-json` to generate a full
config for manual installation.

**Args:**

* `server_spec`: Python file to install, optionally with :object suffix


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.