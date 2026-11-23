> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# auth

# `fastmcp.server.auth.auth`

## Classes

### `AccessToken` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L61](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L61)</sup>

AccessToken that includes all JWT claims.

### `TokenHandler` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L69](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L69)</sup>

TokenHandler that returns MCP-compliant error responses.

This handler addresses two SDK issues:

1. Error code: The SDK returns `unauthorized_client` for client authentication
   failures, but RFC 6749 Section 5.2 requires `invalid_client` with HTTP 401.
   This distinction matters for client re-registration behavior.

2. Status code: The SDK returns HTTP 400 for all token errors including
   `invalid_grant` (expired/invalid tokens). However, the MCP spec requires:
   "Invalid or expired tokens MUST receive a HTTP 401 response."

This handler transforms responses to be compliant with both OAuth 2.1 and MCP specs.

**Methods:**

#### `handle` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L85](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L85)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
handle(self, request: Any)
```

Wrap SDK handle() and transform auth error responses.

The SEP-990 jwt-bearer (ID-JAG) grant is dispatched here rather than by
the SDK. The SDK requires a confidential client (a stored client\_secret)
before it will call `exchange_identity_assertion`. FastMCP OAuth-proxy
clients are always public (`token_endpoint_auth_method="none"`, no stored
secret), and in the proxy trust model the ID-JAG — validated against a
trusted issuer — is the authoritative grant, not a per-client secret.
So when identity assertion is enabled we authenticate the client and
dispatch the grant ourselves, without the SDK's confidential precondition.

### `PrivateKeyJWTClientAuthenticator` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L224](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L224)</sup>

Client authenticator with private\_key\_jwt support for CIMD clients.

Extends the SDK's ClientAuthenticator to add support for the `private_key_jwt`
authentication method per RFC 7523. This is required for CIMD (Client ID Metadata
Document) clients that use asymmetric keys for authentication.

The authenticator:

1. Delegates to SDK for standard methods (client\_secret\_basic, client\_secret\_post, none)
2. Adds private\_key\_jwt handling for CIMD clients
3. Validates JWT assertions against client's JWKS

**Methods:**

#### `authenticate_request` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L254](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L254)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
authenticate_request(self, request: Request) -> OAuthClientInformationFull
```

Authenticate a client from an HTTP request.

Extends SDK authentication to support private\_key\_jwt for CIMD clients.
Delegates to SDK for client\_secret\_basic (Authorization header) and
client\_secret\_post (form body) authentication.

### `AuthProvider` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L305](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L305)</sup>

Base class for all FastMCP authentication providers.

This class provides a unified interface for all authentication providers,
whether they are simple token verifiers or full OAuth authorization servers.
All providers must be able to verify tokens and can optionally provide
custom authentication routes.

**Methods:**

#### `verify_token` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L345](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L345)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
verify_token(self, token: str) -> AccessToken | None
```

Verify a bearer token and return access info if valid.

All auth providers must implement token verification.

**Args:**

* `token`: The token string to validate

**Returns:**

* AccessToken object if valid, None if invalid or expired

#### `scopes_supported` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L359](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L359)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
scopes_supported(self) -> list[str]
```

Scopes advertised in protected resource metadata.

#### `challenge_scopes` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L364](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L364)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
challenge_scopes(self) -> list[str]
```

Scopes clients must request to access this resource.

#### `get_challenge_scopes` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L368](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L368)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_challenge_scopes(self, required_scopes: list[str] | None = None) -> list[str]
```

Select the scopes a `WWW-Authenticate` challenge asks clients to request.

Called without arguments for the server-wide challenge, which defaults to
`required_scopes`. Override this method to translate scopes for an
authorization server that uses a different format, or to request
optional scopes up front.

#### `set_mcp_path` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L380](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L380)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
set_mcp_path(self, mcp_path: str | None) -> None
```

Set the MCP endpoint path and compute resource URL.

This method is called by get\_routes() to configure the expected
resource URL before route creation. Subclasses can override to
perform additional initialization that depends on knowing the
MCP endpoint path.

**Args:**

* `mcp_path`: The path where the MCP endpoint is mounted (e.g., "/mcp")

#### `get_routes` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L394](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L394)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_routes(self, mcp_path: str | None = None) -> list[Route]
```

Get all routes for this authentication provider.

This includes both well-known discovery routes and operational routes.
Each provider is responsible for creating whatever routes it needs:

* TokenVerifier: typically no routes (default implementation)
* RemoteAuthProvider: protected resource metadata routes
* OAuthProvider: full OAuth authorization server routes
* Custom providers: whatever routes they need

**Args:**

* `mcp_path`: The path where the MCP endpoint is mounted (e.g., "/mcp")
  This is used to advertise the resource URL in metadata, but the
  provider does not create the actual MCP endpoint route.

**Returns:**

* List of all routes for this provider (excluding the MCP endpoint itself)

#### `get_well_known_routes` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L417](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L417)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_well_known_routes(self, mcp_path: str | None = None) -> list[Route]
```

Get well-known discovery routes for this authentication provider.

This is a utility method that filters get\_routes() to return only
well-known discovery routes (those starting with /.well-known/).

Well-known routes provide OAuth metadata and discovery endpoints that
clients use to discover authentication capabilities. These routes should
be mounted at the root level of the application to comply with RFC 8414
and RFC 9728.

Common well-known routes:

* /.well-known/oauth-authorization-server (authorization server metadata)
* /.well-known/oauth-protected-resource/\* (protected resource metadata)

**Args:**

* `mcp_path`: The path where the MCP endpoint is mounted (e.g., "/mcp")
  This is used to construct path-scoped well-known URLs.

**Returns:**

* List of well-known discovery routes (typically mounted at root level)

#### `get_middleware` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L449](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L449)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_middleware(self) -> list
```

Get HTTP application-level middleware for this auth provider.

**Returns:**

* List of Starlette Middleware instances to apply to the HTTP app

### `TokenVerifier` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L486](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L486)</sup>

Base class for token verifiers (Resource Servers).

This class provides token verification capability without OAuth server functionality.
Token verifiers typically don't provide authentication routes by default.

**Methods:**

#### `verify_token` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L517](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L517)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
verify_token(self, token: str) -> AccessToken | None
```

Verify a bearer token and return access info if valid.

### `RemoteAuthProvider` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L522](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L522)</sup>

Authentication provider for resource servers that verify tokens from known authorization servers.

This provider composes a TokenVerifier with authorization server metadata to create
standardized OAuth 2.0 Protected Resource endpoints (RFC 9728). Perfect for:

* JWT verification with known issuers
* Remote token introspection services
* Any resource server that knows where its tokens come from

Use this when you have token verification logic and want to advertise
the authorization servers that issue valid tokens.

**Methods:**

#### `scopes_supported` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L582](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L582)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
scopes_supported(self) -> list[str]
```

Scopes advertised in protected resource metadata.

#### `get_challenge_scopes` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L588](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L588)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_challenge_scopes(self, required_scopes: list[str] | None = None) -> list[str]
```

Translate effective validation scopes for the authorization server.

#### `verify_token` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L605](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L605)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
verify_token(self, token: str) -> AccessToken | None
```

Verify token using the configured token verifier.

#### `get_routes` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L609](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L609)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_routes(self, mcp_path: str | None = None) -> list[Route]
```

Get routes for this provider.

Creates protected resource metadata routes (RFC 9728).

### `MultiAuth` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L643](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L643)</sup>

Composes an optional auth server with additional token verifiers.

Use this when a single server needs to accept tokens from multiple sources.
For example, an OAuth proxy for interactive clients combined with a JWT
verifier for machine-to-machine tokens.

Token verification tries the server first (if present), then each verifier
in order, returning the first successful result. Routes and OAuth metadata
come from the server; verifiers contribute only token verification.

**Methods:**

#### `scopes_supported` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L818](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L818)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
scopes_supported(self) -> list[str]
```

Scopes advertised by the delegated auth server.

#### `get_challenge_scopes` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L824](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L824)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_challenge_scopes(self, required_scopes: list[str] | None = None) -> list[str]
```

Select challenge scopes through an unambiguous auth source.

Without a `required_scopes` override, the server or sole verifier selects
its own default challenge, including any customization of this hook.

#### `verify_token` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L845](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L845)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
verify_token(self, token: str) -> AccessToken | None
```

Verify a token by trying the server, then each verifier in order.

Each source is tried independently. If a source raises an exception,
it is logged and treated as a non-match so that remaining sources
still get a chance to verify the token.

#### `set_mcp_path` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L888](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L888)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
set_mcp_path(self, mcp_path: str | None) -> None
```

Propagate MCP path to the server and all verifiers.

#### `get_routes` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L896](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L896)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_routes(self, mcp_path: str | None = None) -> list[Route]
```

Delegate route creation to the server.

#### `get_well_known_routes` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L902](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L902)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_well_known_routes(self, mcp_path: str | None = None) -> list[Route]
```

Delegate well-known route creation to the server.

This ensures that server-specific well-known route logic (e.g.,
OAuthProvider's RFC 8414 path-aware discovery) is preserved.

### `OAuthProvider` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L913](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L913)</sup>

OAuth Authorization Server provider.

This class provides full OAuth server functionality including client registration,
authorization flows, token issuance, and token verification.

**Methods:**

#### `verify_token` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L985](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L985)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
verify_token(self, token: str) -> AccessToken | None
```

Verify a bearer token and return access info if valid.

This method implements the TokenVerifier protocol by delegating
to our existing load\_access\_token method.

**Args:**

* `token`: The token string to validate

**Returns:**

* AccessToken object if valid, None if invalid or expired

#### `scopes_supported` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L1001](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L1001)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
scopes_supported(self) -> list[str]
```

Scopes advertised by this authorization server.

#### `get_routes` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L1010](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L1010)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_routes(self, mcp_path: str | None = None) -> list[Route]
```

Get OAuth authorization server routes and optional protected resource routes.

This method creates the full set of OAuth routes including:

* Standard OAuth authorization server routes (/.well-known/oauth-authorization-server, /authorize, /token, etc.)
* Optional protected resource routes

**Returns:**

* List of OAuth routes

#### `get_well_known_routes` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/auth.py#L1112](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/auth.py#L1112)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_well_known_routes(self, mcp_path: str | None = None) -> list[Route]
```

Get well-known discovery routes with RFC 8414 path-aware support.

Overrides the base implementation to support path-aware authorization
server metadata discovery per RFC 8414. If issuer\_url has a path component,
the authorization server metadata route is adjusted to include that path.

For example, if issuer\_url is "[http://example.com/api](http://example.com/api)", the discovery
endpoint will be at "/.well-known/oauth-authorization-server/api" instead
of just "/.well-known/oauth-authorization-server".

**Args:**

* `mcp_path`: The path where the MCP endpoint is mounted (e.g., "/mcp")

**Returns:**

* List of well-known discovery routes


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.