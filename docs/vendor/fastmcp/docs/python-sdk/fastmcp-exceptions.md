> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# exceptions

# `fastmcp.exceptions`

Custom exceptions for FastMCP.

## Functions

### `to_mcp_error` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/exceptions.py#L117](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/exceptions.py#L117)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
to_mcp_error(exc: Exception) -> MCPError
```

Translate a FastMCP exception into a wire-format `MCPError`.

Central mapping from FastMCP's public exception types to the JSON-RPC error
codes defined by the MCP spec (imported from `mcp_types`). Request-handler
adapters call this instead of hand-rolling `MCPError(code=..., ...)` per
call site, so the wire codes stay spec-correct and consistent across
resources, prompts, and tools.

`NotFoundError` and `DisabledError` map to `INVALID_PARAMS` (-32602):
per SEP-2164 a request naming a component that does not exist (or is
disabled) is an invalid-params error, which matches the SDK's own
`ResourceNotFoundError -> INVALID_PARAMS` mapping in `mcp.server.mcpserver`.
`ValidationError` is also an invalid-params error. Everything else falls
back to `default_code` (`INTERNAL_ERROR` by default).

If `exc` is already an `MCPError`, it is returned unchanged so an
explicit code chosen upstream survives translation.

## Classes

### `FastMCPError` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/exceptions.py#L38](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/exceptions.py#L38)</sup>

Base error for FastMCP.

### `ValidationError` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/exceptions.py#L46](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/exceptions.py#L46)</sup>

Error in validating parameters or return values.

### `ResourceError` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/exceptions.py#L50](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/exceptions.py#L50)</sup>

Error in resource operations.

### `ToolError` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/exceptions.py#L54](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/exceptions.py#L54)</sup>

Error in tool operations.

### `PromptError` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/exceptions.py#L58](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/exceptions.py#L58)</sup>

Error in prompt operations.

### `InvalidSignature` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/exceptions.py#L62](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/exceptions.py#L62)</sup>

Invalid signature for use with FastMCP.

### `ClientError` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/exceptions.py#L66](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/exceptions.py#L66)</sup>

Error in client operations.

### `NotFoundError` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/exceptions.py#L70](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/exceptions.py#L70)</sup>

Object not found.

### `DisabledError` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/exceptions.py#L74](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/exceptions.py#L74)</sup>

Object is disabled.

### `ResourceSecurityError` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/exceptions.py#L78](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/exceptions.py#L78)</sup>

A templated resource parameter failed path-security screening.

Subclasses `NotFoundError` so the read handler surfaces a
non-leaky `INVALID_PARAMS` (-32602) "resource not found" error to
the client — a traversal attempt is indistinguishable from a request
for a resource that does not exist, and never reveals which parameter
or policy tripped.

### `AuthorizationError` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/exceptions.py#L89](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/exceptions.py#L89)</sup>

Error when authorization check fails.

### `InsufficientScopeError` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/exceptions.py#L93](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/exceptions.py#L93)</sup>

Authorization failed because the token is missing required OAuth scopes.

Unlike a bare `AuthorizationError`, this carries the specific scopes the
caller must obtain. A component-level scope shortfall can then be signalled
as a spec-correct `insufficient_scope` step-up (SEP-2350 / RFC 6750 §3),
naming exactly what to re-authorize for instead of an opaque denial. The
named scopes are only the *unmet* ones, so an existing grant is accumulated
rather than replaced when the caller re-authorizes.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.