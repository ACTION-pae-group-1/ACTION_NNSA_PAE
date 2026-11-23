> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# uv

# `fastmcp.utilities.mcp_server_config.v1.environments.uv`

## Classes

### `UVEnvironment` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/mcp\_server\_config/v1/environments/uv.py#L14](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/mcp_server_config/v1/environments/uv.py#L14)</sup>

Configuration for Python environment setup.

**Methods:**

#### `build_command` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/mcp\_server\_config/v1/environments/uv.py#L49](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/mcp_server_config/v1/environments/uv.py#L49)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
build_command(self, command: list[str]) -> list[str]
```

Build complete uv run command with environment args and command to execute.

**Args:**

* `command`: Command to execute (e.g., \["fastmcp", "run", "server.py"])

**Returns:**

* Complete command ready for subprocess.run, including "uv" prefix if needed.
* If no environment configuration is set, returns the command unchanged.

#### `prepare` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/mcp\_server\_config/v1/environments/uv.py#L109](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/mcp_server_config/v1/environments/uv.py#L109)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
prepare(self, output_dir: Path | None = None) -> None
```

Prepare the Python environment using uv.

**Args:**

* `output_dir`: Directory where the persistent uv project will be created.
  If None, creates a temporary directory for ephemeral use.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.