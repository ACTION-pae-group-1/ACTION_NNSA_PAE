> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# OIDC Proxy

> Bridge OIDC providers to work seamlessly with MCP's authentication flow.

New in version `2.12.4`

The OIDC proxy enables FastMCP servers to authenticate with OIDC providers that **don't support Dynamic Client Registration (DCR)** out of the box. This includes OAuth providers like: Auth0, Google, Azure, AWS, etc. For providers that do support DCR (like WorkOS AuthKit), use [`RemoteAuthProvider`](https://gofastmcp.com/servers/auth/remote-oauth) instead.

The OIDC proxy is built upon [`OAuthProxy`](https://gofastmcp.com/servers/auth/oauth-proxy) so it has all the same functionality under the covers.

## Implementation

### Provider Setup Requirements

Before using the OIDC proxy, you need to register your application with your OAuth provider:

1. **Register your application** in the provider's developer console (Auth0 Applications, Google Cloud Console, Azure Portal, etc.)
2. **Configure the redirect URI** as your FastMCP server URL plus your chosen callback path:
   * Default: `https://your-server.com/auth/callback`
   * Custom: `https://your-server.com/your/custom/path` (if you set `redirect_path`)
   * Development: `http://localhost:8000/auth/callback`
3. **Obtain your credentials**: Client ID and Client Secret

> [!WARNING]
>
> The redirect URI you configure with your provider must exactly match your
> FastMCP server's URL plus the callback path. If you customize `redirect_path`
> in the OIDC proxy, update your provider's redirect URI accordingly.

### Basic Setup

Here's how to implement the OIDC proxy with any provider:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import FastMCP
from fastmcp.server.auth.oidc_proxy import OIDCProxy

# Create the OIDC proxy
auth = OIDCProxy(
    # Provider's configuration URL
    config_url="https://provider.com/.well-known/openid-configuration",

    # Your registered app credentials
    client_id="your-client-id",
    client_secret="your-client-secret",

    # Your FastMCP server's public URL
    base_url="https://your-server.com",

    # Optional: customize the callback path (default is "/auth/callback")
    # redirect_path="/custom/callback",
)

mcp = FastMCP(name="My Server", auth=auth)
```

### Configuration Parameters

> **OIDCProxy Parameters**
>
> **config\_url** `str` *required*
>
> URL of your OAuth provider's OIDC configuration
>
> **client\_id** `str` *required*
>
> Client ID from your registered OAuth application
>
> **client\_secret** `str | None`
>
> Client secret from your registered OAuth application. Optional for PKCE public
> clients. When omitted, `jwt_signing_key` must be provided.
>
> **base\_url** `AnyHttpUrl | str` *required*
>
> Public URL of your FastMCP server (e.g., `https://your-server.com`)
>
> **resource\_base\_url** `AnyHttpUrl | str | None`
>
> Optional public base URL for the protected resource metadata and token audience.
>
> Use this when your OAuth callbacks and operational endpoints need to live under one public URL, but the protected MCP resource should be advertised under another. FastMCP will still append the MCP mount path (for example, `/mcp`) to this base URL.
>
> **strict** `bool | None`
>
> Strict flag for configuration validation. When True, requires all OIDC
> mandatory fields.
>
> **audience** `str | None`
>
> Audience parameter for OIDC providers that require it (e.g., Auth0). This is
> typically your API identifier.
>
> **timeout\_seconds** `int | None` (default: 10)
>
> HTTP request timeout in seconds for fetching OIDC configuration
>
> **token\_verifier** `TokenVerifier | None`
>
> New in version `2.13.1`
>
> Custom token verifier for validating tokens. When provided, FastMCP uses your custom verifier instead of creating a default `JWTVerifier`.
>
> Cannot be used with `algorithm` or `required_scopes` parameters - configure these on your verifier instead. The verifier's `required_scopes` are automatically loaded and advertised.
>
> **algorithm** `str | None`
>
> JWT algorithm to use for token verification (e.g., "RS256"). If not specified,
> uses the provider's default. Only used when `token_verifier` is not provided.
>
> **required\_scopes** `list[str] | None`
>
> List of OAuth scopes for token validation. These are automatically
> included in authorization requests. Only used when `token_verifier` is not provided.
>
> **redirect\_path** `str` (default: /auth/callback)
>
> Path for OAuth callbacks. Must match the redirect URI configured in your OAuth
> application
>
> **allowed\_client\_redirect\_uris** `list[str] | None`
>
> List of allowed redirect URI patterns for MCP clients. Patterns support wildcards (e.g., `"http://localhost:*"`, `"https://*.example.com/*"`).
>
> * `None` (default): DCR clients use registered redirect URIs, with loopback ports allowed to vary for MCP compatibility. Unsafe browser schemes such as `javascript:`, `data:`, `file:`, and `vbscript:` are rejected.
> * Empty list `[]`: No redirect URIs allowed
> * Custom list: Only matching patterns allowed
>
> These patterns apply to MCP client loopback redirects. Configure the upstream OAuth app redirect URI separately with `redirect_path`.
>
> **valid\_scopes** `list[str] | None`
>
> The complete set of scopes clients are allowed to request — the full set of
> available scopes (a superset of `required_scopes`). These are advertised to
> clients through the `/.well-known` endpoints (as `scopes_supported`) and
> enforced at Dynamic Client Registration: a client registering with a scope
> outside this set is rejected. Defaults to `required_scopes` from your token
> verifier if not specified.
>
> **token\_endpoint\_auth\_method** `str | None`
>
> Token endpoint authentication method for the upstream OAuth server. Controls how the proxy authenticates when exchanging authorization codes and refresh tokens with the upstream provider.
>
> * `"client_secret_basic"`: Send credentials in Authorization header (most common)
> * `"client_secret_post"`: Send credentials in request body (required by some providers)
> * `"none"`: No authentication (for public clients)
> * `None` (default): `"client_secret_basic"` when a client secret is configured, `"none"` otherwise
>
> Set this if your provider requires a specific authentication method and the default doesn't work.
>
> **jwt\_signing\_key** `str | bytes | None`
>
> New in version `2.13.0`
>
> Secret used to sign FastMCP JWT tokens issued to clients. **`bytes`** are used as-is, with no stretching, so supply at least 32 bytes of high-entropy key material. With the default file-backed client storage, the bytes must also decode as UTF-8; use `secrets.token_urlsafe(32).encode()` instead of raw `secrets.token_bytes()`, or configure `client_storage` explicitly. **A string** is stretched into a 32-byte key with PBKDF2 (1,000,000 iterations), since a supplied string may be low-entropy.
>
> **Default behavior (`None`):**
> The key is deterministically derived from `client_secret` using HKDF, on every platform. Because the derivation is deterministic, the same key is produced across restarts as long as `client_secret` doesn't change, so tokens remain valid without any extra configuration. This convenience makes it **only** suitable for development and local testing.
>
> **For production:**
> Provide an explicit `jwt_signing_key` (e.g., from an environment variable) rather than relying on the auto-derived key.
>
> **client\_storage** `AsyncKeyValue | None`
>
> New in version `2.13.0`
>
> Storage backend for persisting OAuth client registrations and upstream tokens.
>
> **Default behavior:**
> Encrypted disk store in your platform's data directory (derived from `platformdirs`), on every platform including Linux. The encryption key is itself derived from `jwt_signing_key`.
>
> By default, clients are automatically persisted to encrypted disk storage, allowing them to survive server restarts as long as the filesystem remains accessible. This means MCP clients only need to register once and can reconnect seamlessly.
>
> For production deployments with multiple servers or cloud deployments, use a network-accessible storage backend rather than local disk storage. **Wrap your storage in `FernetEncryptionWrapper` to encrypt sensitive OAuth tokens at rest.** See [Storage Backends](https://gofastmcp.com/servers/storage-backends.md) for available options.
>
> Testing with in-memory storage (unencrypted):
>
> ```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
> from key_value.aio.stores.memory import MemoryStore
>
> # Use in-memory storage for testing (clients lost on restart)
> auth = OIDCProxy(..., client_storage=MemoryStore())
> ```
>
> Production with encrypted Redis storage:
>
> ```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
> from key_value.aio.stores.redis import RedisStore
> from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
> from cryptography.fernet import Fernet
> import os
>
> auth = OIDCProxy(
>     ...,
>     jwt_signing_key=os.environ["JWT_SIGNING_KEY"],
>     client_storage=FernetEncryptionWrapper(
>         key_value=RedisStore(host="redis.example.com", port=6379),
>         fernet=Fernet(os.environ["STORAGE_ENCRYPTION_KEY"])
>     )
> )
> ```
>
> **require\_authorization\_consent** `bool | Literal["remember", "external"]` (default: True)
>
> Consent screen behavior for authorization requests. Accepts `True` (default; always prompt — strongest protection), `"remember"` (silent consent on return visits via signed cookie, gated by `Sec-Fetch-Site` to block AS-in-the-middle attacks), `"external"` (same authorization path as `False`, but the warning is suppressed because the operator asserts that equivalent protections are enforced externally), or `False` (disable entirely; local/testing only). See the [OAuthProxy documentation](https://gofastmcp.com/servers/auth/oauth-proxy.md) for full details on each mode and the security trade-offs.
>
> `False` and `"external"` disable FastMCP's consent and browser-binding checks, reducing protection against confused deputy and AS-in-the-middle attacks unless equivalent checks are enforced elsewhere. FastMCP does not provide or verify external enforcement. `"remember"` is also weaker than the default `True`, since its cross-site detection is a browser heuristic.
>
> **consent\_csp\_policy** `str | None` (default: None)
>
> Content Security Policy for the consent page.
>
> Disabling or weakening this policy reduces browser protections against content injection unless your deployment supplies an equivalent CSP header; FastMCP does not verify that header.
>
> * `None` (default): Uses the built-in CSP policy with appropriate directives for form submission
> * Empty string `""`: Disables CSP entirely (no meta tag rendered)
> * Custom string: Uses the provided value as the CSP policy
>
> This is useful for organizations that have their own CSP policies and need to override or disable FastMCP's built-in CSP directives.

### Using Built-in Providers

FastMCP includes pre-configured OIDC providers for common services:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp.server.auth.providers.auth0 import Auth0Provider

auth = Auth0Provider(
    config_url="https://.../.well-known/openid-configuration",
    client_id="your-auth0-client-id",
    client_secret="your-auth0-client-secret",
    audience="https://...",
    base_url="https://localhost:8000"
)

mcp = FastMCP(name="My Server", auth=auth)
```

Available providers include `Auth0Provider` at present.

### Scope Configuration

OAuth scopes are configured with `required_scopes` to automatically request the permissions your application needs.

Dynamic clients created by the proxy will automatically include these scopes in their authorization requests.

## CIMD Support

New in version `3.0.0`

The OIDC proxy inherits full CIMD (Client ID Metadata Document) support from `OAuthProxy`. Clients can use HTTPS URLs as their `client_id` instead of registering dynamically, and the proxy will fetch and validate their metadata document.

See the [OAuth Proxy CIMD documentation](https://gofastmcp.com/servers/auth/oauth-proxy.md#cimd-support) for complete details on how CIMD works, including private key JWT authentication and security considerations.

The CIMD-related parameters available on `OIDCProxy` are:

> **CIMD Parameters**
>
> **enable\_cimd** `bool` (default: True)
>
> Whether to accept CIMD URLs as client identifiers.

## Production Configuration

For production deployments, load sensitive credentials from environment variables:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
import os
from fastmcp import FastMCP
from fastmcp.server.auth.providers.auth0 import Auth0Provider

# Load secrets from environment variables
auth = Auth0Provider(
    config_url=os.environ.get("AUTH0_CONFIG_URL"),
    client_id=os.environ.get("AUTH0_CLIENT_ID"),
    client_secret=os.environ.get("AUTH0_CLIENT_SECRET"),
    audience=os.environ.get("AUTH0_AUDIENCE"),
    base_url=os.environ.get("BASE_URL", "https://localhost:8000")
)

mcp = FastMCP(name="My Server", auth=auth)

@mcp.tool
def protected_tool(data: str) -> str:
    """This tool is now protected by OAuth."""
    return f"Processed: {data}"

if __name__ == "__main__":
    mcp.run(transport="http", port=8000)
```

This keeps secrets out of your codebase while maintaining explicit configuration.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.