> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# cli

# `fastmcp.utilities.cli`

## Functions

### `is_already_in_uv_subprocess` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/cli.py#L28](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/cli.py#L28)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
is_already_in_uv_subprocess() -> bool
```

Check if we're already running in a FastMCP uv subprocess.

### `load_and_merge_config` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/cli.py#L33](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/cli.py#L33)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
load_and_merge_config(server_spec: str | None, **cli_overrides) -> tuple[MCPServerConfig, str]
```

Load config from server\_spec and apply CLI overrides.

This consolidates the config parsing logic that was duplicated across
run, inspect, and dev commands.

**Args:**

* `server_spec`: Python file, config file, URL, or None to auto-detect
* `cli_overrides`: CLI arguments that override config values

**Returns:**

* Tuple of (MCPServerConfig, resolved\_server\_spec)

### `log_server_banner` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/cli.py#L207](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/cli.py#L207)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
log_server_banner(server: FastMCP[Any]) -> None
```

Creates and logs a formatted banner with server information and logo.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.