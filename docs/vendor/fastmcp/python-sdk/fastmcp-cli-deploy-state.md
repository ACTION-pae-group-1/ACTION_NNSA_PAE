> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# state

# `fastmcp.cli.deploy.state`

Versioned JSON state helpers for the FastMCP CLI.

## Functions

### `state_lock` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/state.py#L97](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/state.py#L97)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
state_lock(directory: Path) -> Iterator[None]
```

Lock related CLI state changes across processes.

### `read_state` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/state.py#L146](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/state.py#L146)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
read_state(path: Path, model: type[ModelT]) -> ModelT | None
```

Read and validate a versioned JSON state file.

### `write_state` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/state.py#L170](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/state.py#L170)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
write_state(path: Path, data: dict[str, Any]) -> None
```

Write JSON through a restricted temporary file and atomic replacement.

### `remove_state` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/state.py#L222](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/state.py#L222)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
remove_state(path: Path) -> None
```

Remove a state file when it exists.

## Classes

### `StateFileError` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/state.py#L20](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/state.py#L20)</sup>

A CLI state file could not be read or written safely.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.