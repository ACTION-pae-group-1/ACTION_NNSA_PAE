> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# decorators

# `fastmcp.decorators`

Shared decorator utilities for FastMCP.

## Functions

### `resolve_task_config` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/decorators.py#L17](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/decorators.py#L17)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
resolve_task_config(task: bool | TaskConfig | None) -> bool | TaskConfig
```

Resolve task config, defaulting None to False.

### `get_fastmcp_meta` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/decorators.py#L29](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/decorators.py#L29)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_fastmcp_meta(fn: Any) -> Any | None
```

Extract FastMCP metadata from a function, handling bound methods and wrappers.

## Classes

### `HasFastMCPMeta` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/decorators.py#L23](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/decorators.py#L23)</sup>

Protocol for callables decorated with FastMCP metadata.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.