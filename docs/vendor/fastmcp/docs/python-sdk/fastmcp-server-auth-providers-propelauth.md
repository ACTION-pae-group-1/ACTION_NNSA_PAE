> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# propelauth

# `fastmcp.server.auth.providers.propelauth`

PropelAuth authentication provider for FastMCP.

Example:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import FastMCP
from fastmcp.server.auth.providers.propelauth import PropelAuthProvider

auth = PropelAuthProvider(
    auth_url="https://auth.yourdomain.com",
    introspection_client_id="your-client-id",
    introspection_client_secret="your-client-secret",
    base_url="https://your-fastmcp-server.com",
    required_scopes=["read:user_data"],
)

mcp = FastMCP("My App", auth=auth)
```

## Classes

### `PropelAuthTokenIntrospectionOverrides` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/providers/propelauth.py#L36](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/providers/propelauth.py#L36)</sup>

### `PropelAuthProvider` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/providers/propelauth.py#L43](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/providers/propelauth.py#L43)</sup>

PropelAuth resource server provider using OAuth 2.1 token introspection.

This provider validates access tokens via PropelAuth's introspection endpoint
and forwards authorization server metadata for OAuth discovery.

For detailed setup instructions, see:
[https://docs.propelauth.com/mcp-authentication/overview](https://docs.propelauth.com/mcp-authentication/overview)

**Methods:**

#### `get_routes` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/providers/propelauth.py#L141](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/providers/propelauth.py#L141)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_routes(self, mcp_path: str | None = None) -> list[Route]
```

Get routes for this provider.

Includes the standard routes from the RemoteAuthProvider (protected resource metadata routes (RFC 9728)),
and creates an authorization server metadata route that forwards to PropelAuth's route

**Args:**

* `mcp_path`: The path where the MCP endpoint is mounted (e.g., "/mcp")
  This is used to advertise the resource URL in metadata.

#### `verify_token` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/providers/propelauth.py#L185](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/providers/propelauth.py#L185)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
verify_token(self, token: str) -> AccessToken | None
```

Verify token and check the `aud` claim against the configured resource.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.