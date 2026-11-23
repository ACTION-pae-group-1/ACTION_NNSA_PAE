> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# dependencies

# `fastmcp.client.dependencies`

Client-side dependency helpers.

## Functions

### `get_http_headers` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/dependencies.py#L19](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/dependencies.py#L19)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_http_headers(include_all: bool = False, include: set[str] | None = None) -> dict[str, str]
```

Return HTTP headers from an ambient server request, when available.

The standalone client package has no server request context. When the full
FastMCP package is installed, delegate to its request-aware implementation.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.