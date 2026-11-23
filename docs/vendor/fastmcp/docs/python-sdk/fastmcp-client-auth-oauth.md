> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# oauth

# `fastmcp.client.auth.oauth`

## Functions

### `check_if_auth_required` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/auth/oauth.py#L58](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/auth/oauth.py#L58)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
check_if_auth_required(mcp_url: str, httpx_kwargs: dict[str, Any] | None = None) -> bool
```

Check if the MCP endpoint requires authentication by making a test request.

**Returns:**

* True if auth appears to be required, False otherwise

## Classes

### `ClientNotFoundError` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/auth/oauth.py#L50](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/auth/oauth.py#L50)</sup>

Raised when OAuth client credentials are not found on the server.

### `ExpiredClientRegistrationError` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/auth/oauth.py#L54](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/auth/oauth.py#L54)</sup>

Raised when dynamic registration returns an expired client secret.

### `TokenStorageAdapter` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/auth/oauth.py#L88](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/auth/oauth.py#L88)</sup>

**Methods:**

#### `clear` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/auth/oauth.py#L135](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/auth/oauth.py#L135)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
clear(self) -> None
```

#### `get_tokens` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/auth/oauth.py#L144](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/auth/oauth.py#L144)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_tokens(self) -> OAuthToken | None
```

#### `set_tokens` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/auth/oauth.py#L148](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/auth/oauth.py#L148)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
set_tokens(self, tokens: OAuthToken) -> None
```

#### `get_token_expiry` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/auth/oauth.py#L168](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/auth/oauth.py#L168)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_token_expiry(self) -> float | None
```

#### `get_client_info` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/auth/oauth.py#L178](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/auth/oauth.py#L178)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_client_info(self) -> OAuthClientInformationFull | None
```

#### `set_client_info` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/auth/oauth.py#L184](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/auth/oauth.py#L184)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
set_client_info(self, client_info: OAuthClientInformationFull) -> None
```

### `OAuth` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/auth/oauth.py#L202](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/auth/oauth.py#L202)</sup>

OAuth client provider for MCP servers with browser-based authentication.

This class provides OAuth authentication for FastMCP clients by opening
a browser for user authorization and running a local callback server.

**Methods:**

#### `redirect_handler` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/auth/oauth.py#L390](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/auth/oauth.py#L390)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
redirect_handler(self, authorization_url: str) -> None
```

Open browser for authorization, with pre-flight check for invalid client.

#### `callback_handler` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/auth/oauth.py#L411](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/auth/oauth.py#L411)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
callback_handler(self) -> AuthorizationCodeResult
```

Handle OAuth callback and return the authorization code result.

#### `async_auth_flow` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/auth/oauth.py#L466](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/auth/oauth.py#L466)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
async_auth_flow(self, request: httpx2.Request) -> AsyncGenerator[httpx2.Request, httpx2.Response]
```

HTTPX auth flow with automatic retry on stale cached credentials.

If the OAuth flow fails due to invalid/stale client credentials,
clears the cache and retries once with fresh registration.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.