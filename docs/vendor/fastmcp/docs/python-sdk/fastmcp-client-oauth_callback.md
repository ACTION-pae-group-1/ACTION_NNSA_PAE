> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# oauth_callback

# `fastmcp.client.oauth_callback`

OAuth callback server for handling authorization code flows.

This module provides a reusable callback server that can handle OAuth redirects
and display styled responses to users.

## Functions

### `create_callback_html` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/oauth\_callback.py#L34](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/oauth_callback.py#L34)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
create_callback_html(message: str, is_success: bool = True, title: str = 'FastMCP OAuth', server_url: str | None = None) -> str
```

Create a styled HTML response for OAuth callbacks.

### `create_oauth_callback_server` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/oauth\_callback.py#L114](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/oauth_callback.py#L114)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
create_oauth_callback_server(port: int, host: str = '127.0.0.1', callback_path: str = '/callback', server_url: str | None = None, result_container: OAuthCallbackResult | None = None, result_ready: anyio.Event | None = None) -> Server
```

Create an OAuth callback server.

**Args:**

* `port`: The port to run the server on
* `callback_path`: The path to listen for OAuth redirects on
* `server_url`: Optional server URL to display in success messages
* `result_container`: Optional container to store callback results
* `result_ready`: Optional event to signal when callback is received

**Returns:**

* Configured uvicorn Server instance (not yet running)

## Classes

### `CallbackResponse` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/oauth\_callback.py#L80](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/oauth_callback.py#L80)</sup>

**Methods:**

#### `from_dict` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/oauth\_callback.py#L92](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/oauth_callback.py#L92)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from_dict(cls, data: dict[str, str]) -> CallbackResponse
```

#### `to_dict` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/oauth\_callback.py#L95](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/oauth_callback.py#L95)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
to_dict(self) -> dict[str, str]
```

### `OAuthCallbackResult` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/oauth\_callback.py#L100](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/oauth_callback.py#L100)</sup>

Container for OAuth callback results, used with anyio.Event for async coordination.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.