> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# code_mode

# `fastmcp.experimental.transforms.code_mode`

## Classes

### `SandboxProvider` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/experimental/transforms/code\_mode.py#L138](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/experimental/transforms/code_mode.py#L138)</sup>

Interface for executing LLM-generated Python code in a sandbox.

WARNING: The `code` parameter passed to `run` contains untrusted,
LLM-generated Python.  Implementations MUST execute it in an isolated
sandbox — never with plain `exec()`.  Use `MontySandboxProvider`
(backed by `pydantic-monty`) for production workloads.

**Methods:**

#### `run` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/experimental/transforms/code\_mode.py#L147](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/experimental/transforms/code_mode.py#L147)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
run(self, code: str) -> Any
```

### `MontySandboxProvider` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/experimental/transforms/code\_mode.py#L175](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/experimental/transforms/code_mode.py#L175)</sup>

Sandbox provider backed by `pydantic-monty`.

**Args:**

* `limits`: Resource limits for sandbox execution. Supported keys:
  `max_feed_duration_secs` (float), `max_turn_duration_secs` (float),
  `max_memory` (int),
  `max_recursion_depth` (int), and `gc_interval` (int).
  Time, memory, and GC limits are optional; omit a key to disable
  it. Recursion depth defaults to Monty's standard maximum of 1,000.
  Duration limits measure sandbox execution time, excluding time
  waiting on host callbacks. The feed limit covers the whole execution;
  the turn limit resets after each host round trip.
  Unsupported keys raise `ValueError` rather than being silently
  ignored.

When the argument is omitted entirely, a conservative baseline
is applied (`max_feed_duration_secs=30`, `max_memory=100 MB`) so
the out-of-box configuration is not unbounded. Pass
`limits=None` to disable configurable time, memory, and GC
limits, or a dict to set your own. Monty's standard recursion
limit still applies.

**Methods:**

#### `run` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/experimental/transforms/code\_mode.py#L211](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/experimental/transforms/code_mode.py#L211)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
run(self, code: str) -> Any
```

### `Search` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/experimental/transforms/code\_mode.py#L352](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/experimental/transforms/code_mode.py#L352)</sup>

Discovery tool factory that searches the catalog by query.

**Args:**

* `search_fn`: Async callable `(tools, query) -> matching_tools`.
  Defaults to BM25 ranking.
* `name`: Name of the synthetic tool exposed to the LLM.
* `default_detail`: Default detail level for search results.
  `"brief"` returns tool names and descriptions only.
  `"detailed"` returns compact markdown with parameter schemas.
  `"full"` returns complete JSON tool definitions.
* `default_limit`: Maximum number of results to return.
  The LLM can override this per call.  `None` means no limit.

### `GetSchemas` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/experimental/transforms/code\_mode.py#L434](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/experimental/transforms/code_mode.py#L434)</sup>

Discovery tool factory that returns schemas for tools by name.

**Args:**

* `name`: Name of the synthetic tool exposed to the LLM.
* `default_detail`: Default detail level for schema results.
  `"brief"` returns tool names and descriptions only.
  `"detailed"` renders compact markdown with parameter names,
  types, and required markers.
  `"full"` returns the complete JSON schema.

### `GetTags` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/experimental/transforms/code\_mode.py#L495](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/experimental/transforms/code_mode.py#L495)</sup>

Discovery tool factory that lists tool tags from the catalog.

Reads `tool.tags` from the catalog and groups tools by tag. Tools
without tags appear under `"untagged"`.

**Args:**

* `name`: Name of the synthetic tool exposed to the LLM.
* `default_detail`: Default detail level.
  `"brief"` returns tag names with tool counts.
  `"full"` lists all tools under each tag.

### `ListTools` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/experimental/transforms/code\_mode.py#L562](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/experimental/transforms/code_mode.py#L562)</sup>

Discovery tool factory that lists all tools in the catalog.

**Args:**

* `name`: Name of the synthetic tool exposed to the LLM.
* `default_detail`: Default detail level.
  `"brief"` returns tool names and one-line descriptions.
  `"detailed"` returns compact markdown with parameter schemas.
  `"full"` returns the complete JSON schema.

### `CodeMode` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/experimental/transforms/code\_mode.py#L611](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/experimental/transforms/code_mode.py#L611)</sup>

Transform that collapses all tools into discovery + execute meta-tools.

Discovery tools are composable via the `discovery_tools` parameter.
Each is a callable that receives catalog access and returns a `Tool`.
By default, `Search` and `GetSchemas` are included for
progressive disclosure: search finds candidates, get\_schema retrieves
parameter details, and execute runs code.

The `execute` tool is always present and provides a sandboxed Python
environment with `call_tool(name, params)` in scope.

**Methods:**

#### `transform_tools` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/experimental/transforms/code\_mode.py#L663](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/experimental/transforms/code_mode.py#L663)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
transform_tools(self, tools: Sequence[Tool]) -> Sequence[Tool]
```

#### `get_tool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/experimental/transforms/code\_mode.py#L666](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/experimental/transforms/code_mode.py#L666)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_tool(self, name: str, call_next: GetToolNext) -> Tool | None
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.