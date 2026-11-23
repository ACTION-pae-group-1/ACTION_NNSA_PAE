> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# output

# `fastmcp.cli.deploy.output`

Stable terminal and JSON output for Horizon CLI commands.

## Functions

### `emit_device_challenge` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/output.py#L84](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/output.py#L84)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
emit_device_challenge(authorization: DeviceAuthorization) -> None
```

Show a device challenge before polling starts.

### `start_device_approval_status` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/output.py#L129](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/output.py#L129)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
start_device_approval_status() -> Status | None
```

Start the terminal spinner while the browser approval is pending.

### `stop_device_approval_status` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/output.py#L142](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/output.py#L142)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
stop_device_approval_status(status: Status | None) -> None
```

Stop a device approval spinner when one is active.

### `emit_identity` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/output.py#L148](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/output.py#L148)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
emit_identity(command: Literal['login', 'whoami'], user: HorizonUser) -> None
```

Show the authenticated user.

### `emit_environment_logout` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/output.py#L182](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/output.py#L182)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
emit_environment_logout() -> None
```

Explain why logout cannot change an environment credential.

### `emit_logout` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/output.py#L216](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/output.py#L216)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
emit_logout() -> None
```

Show a successful local logout result.

### `emit_error` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/output.py#L257](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/output.py#L257)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
emit_error(command: CommandName, category: ErrorCategory, message: str) -> None
```

Show a stable expected command failure.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.