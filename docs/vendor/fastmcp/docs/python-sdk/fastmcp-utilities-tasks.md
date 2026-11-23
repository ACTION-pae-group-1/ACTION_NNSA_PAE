> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# tasks

# `fastmcp.utilities.tasks`

Task configuration primitives for FastMCP components.

## Classes

### `TaskMeta` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/tasks.py#L29](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/tasks.py#L29)</sup>

Metadata for task-augmented execution requests.

**Attributes:**

* `ttl`: Client-requested TTL in milliseconds. If None, uses server default.
* `fn_key`: Docket routing key. Auto-derived from component name if None.

### `TaskConfig` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/tasks.py#L42](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/tasks.py#L42)</sup>

Configuration for MCP background task execution.

Controls how a component handles task-augmented requests:

* `forbidden`: Component does not support task execution.
* `optional`: Component supports both synchronous and task execution.
* `required`: Component requires task execution.

**Methods:**

#### `from_bool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/tasks.py#L56](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/tasks.py#L56)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from_bool(cls, value: bool) -> TaskConfig
```

Convert a boolean task flag to a TaskConfig.

#### `supports_tasks` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/tasks.py#L60](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/tasks.py#L60)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
supports_tasks(self) -> bool
```

Check if this component supports task execution.

#### `validate_function` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/tasks.py#L64](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/tasks.py#L64)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
validate_function(self, fn: Callable[..., Any], name: str) -> None
```

Validate that a function is compatible with this task config.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.