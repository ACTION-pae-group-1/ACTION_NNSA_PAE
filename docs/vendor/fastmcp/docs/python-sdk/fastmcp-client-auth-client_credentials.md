> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# client_credentials

# `fastmcp.client.auth.client_credentials`

Machine-to-machine (M2M) OAuth client authentication for FastMCP.

These providers authenticate a FastMCP client to a protected MCP server without
a browser, using the OAuth 2.0 `client_credentials` grant:

* `ClientCredentialsOAuthProvider` authenticates with a `client_id` and
  `client_secret` (the common M2M case).
* `PrivateKeyJWTOAuthProvider` authenticates with an RFC 7523 `private_key_jwt`
  client assertion (workload identity federation, or a locally signed JWT).

Both are thin wrappers over the MCP SDK's client-credentials providers. Like the
interactive `OAuth` provider, they can be constructed without an `mcp_url` and
bound to the server URL automatically when passed to `Client(auth=...)`.

## Classes

### `ClientCredentialsOAuthProvider` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/auth/client\_credentials.py#L166](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/auth/client_credentials.py#L166)</sup>

OAuth `client_credentials` provider using a client ID and secret.

This is the standard machine-to-machine flow: the client exchanges its
`client_id` and `client_secret` at the authorization server's token
endpoint for an access token, which is then attached to every request. The
token endpoint is discovered from the MCP server's OAuth metadata, so callers
provide the MCP server URL rather than a raw token endpoint.

**Methods:**

#### `async_auth_flow` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/auth/client\_credentials.py#L273](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/auth/client_credentials.py#L273)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
async_auth_flow(self, request: httpx2.Request) -> AsyncGenerator[httpx2.Request, httpx2.Response]
```

### `PrivateKeyJWTOAuthProvider` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/auth/client\_credentials.py#L296](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/auth/client_credentials.py#L296)</sup>

OAuth `client_credentials` provider using `private_key_jwt` (RFC 7523).

Instead of a shared client secret, the client authenticates to the token
endpoint with a signed JWT assertion. The `assertion_provider` callback
receives the authorization server's issuer identifier (the required JWT
audience) and returns the assertion. Use
`SignedJWTParameters.create_assertion_provider()` to sign locally with a
private key, `static_assertion_provider()` for a pre-built JWT, or supply your
own callback for workload identity federation.

**Methods:**

#### `async_auth_flow` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/auth/client\_credentials.py#L412](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/auth/client_credentials.py#L412)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
async_auth_flow(self, request: httpx2.Request) -> AsyncGenerator[httpx2.Request, httpx2.Response]
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.