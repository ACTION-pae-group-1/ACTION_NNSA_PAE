> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# OAuth Authentication

> Authenticate your FastMCP client via OAuth 2.1.

New in version `2.6.0`

> [!TIP]
>
> OAuth authentication is only relevant for HTTP-based transports and requires user interaction via a web browser.

When your FastMCP client needs to access an MCP server protected by OAuth 2.1, and the process requires user interaction (like logging in and granting consent), you should use the Authorization Code Flow. FastMCP provides the `fastmcp.client.auth.OAuth` helper to simplify this entire process.

This flow is common for user-facing applications where the application acts on behalf of the user.

## Client Usage

### Default Configuration

The simplest way to use OAuth is to pass the string `"oauth"` to the `auth` parameter of the `Client` or transport instance. FastMCP will automatically configure the client to use OAuth with default settings:

```python {4} theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import Client

# Uses default OAuth settings
async with Client("https://your-server.fastmcp.app/mcp", auth="oauth") as client:
    await client.list_tools()
```

### `OAuth` Helper

To fully configure the OAuth flow, use the `OAuth` helper and pass it to the `auth` parameter of the `Client` or transport instance. `OAuth` manages the complexities of the OAuth 2.1 Authorization Code Grant with PKCE (Proof Key for Code Exchange) for enhanced security, and implements the full `httpx2.Auth` interface.

```python {2, 4, 6} theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import Client
from fastmcp.client.auth import OAuth

oauth = OAuth(scopes=["user"])

async with Client("https://your-server.fastmcp.app/mcp", auth=oauth) as client:
    await client.list_tools()
```

> [!NOTE]
>
> You don't need to pass `mcp_url` when using `OAuth` with `Client(auth=...)` — the transport provides the server URL automatically.

#### `OAuth` Parameters

* **`scopes`** (`str | list[str]`, optional): OAuth scopes to request. Can be space-separated string or list of strings
* **`client_name`** (`str`, optional): Client name for dynamic registration. Defaults to `"FastMCP Client"`
* **`client_id`** (`str`, optional): Pre-registered OAuth client ID. When provided, skips Dynamic Client Registration entirely. See [Pre-Registered Clients](#pre-registered-clients)
* **`client_secret`** (`str`, optional): OAuth client secret for pre-registered clients, sent to the token endpoint with `client_secret_post` unless `additional_client_metadata` sets `token_endpoint_auth_method`. Public clients that rely on PKCE can omit it
* **`client_metadata_url`** (`str`, optional): URL-based client identity (CIMD). See [CIMD Authentication](https://gofastmcp.com/docs/clients/auth/cimd.md) for details
* **`token_storage`** (`AsyncKeyValue`, optional): Storage backend for persisting OAuth tokens. Defaults to in-memory storage, which loses tokens on restart and emits a warning. See [Token Storage](#token-storage) for encrypted storage options
* **`additional_client_metadata`** (`dict[str, Any]`, optional): Extra metadata for client registration
* **`callback_port`** (`int`, optional): Fixed port for OAuth callback server. If not specified, uses a random available port
* **`callback_host`** (`str`, optional): Hostname for the callback server and the `redirect_uri`. Defaults to `"localhost"`
* **`callback_timeout`** (`float`, optional): Seconds to wait for the browser callback before raising `TimeoutError`. Defaults to `300.0`
* **`httpx_client_factory`** (`McpHttpClientFactory`, optional): Factory for creating httpx2 clients

## OAuth Flow

The OAuth flow is triggered when you use a FastMCP `Client` configured to use OAuth.

**1. Token Check**

The client first checks the configured `token_storage` backend for existing, valid tokens for the target server. If one is found, it will be used to authenticate the client.

**2. OAuth Server Discovery**

If no valid tokens exist, the client reads the MCP server's protected resource metadata (`/.well-known/oauth-protected-resource`) to find its authorization server, then fetches that server's metadata (`/.well-known/oauth-authorization-server` or OpenID Connect discovery) to learn its endpoints.

**3. Client Registration**

If a `client_id` is provided, the client uses those pre-registered credentials directly and skips this step entirely. Otherwise, if a `client_metadata_url` is configured and the server supports CIMD, the client uses its metadata URL as its identity. As a fallback, the client performs Dynamic Client Registration (RFC 7591) if the server supports it.

**4. Local Callback Server**

A temporary local HTTP server is started on an available port (or the port specified via `callback_port`). This server's address (by default `http://localhost:<port>/callback`, set by `callback_host`) acts as the `redirect_uri` for the OAuth flow.

**5. Browser Interaction**

The user's default web browser is automatically opened, directing them to the OAuth server's authorization endpoint. The user logs in and grants (or denies) the requested `scopes`.

**6. Authorization Code & Token Exchange**

Upon approval, the OAuth server redirects the user's browser to the local callback server with an `authorization_code`. The client captures this code and exchanges it with the OAuth server's token endpoint for an `access_token` (and often a `refresh_token`) using PKCE for security.

**7. Token Caching**

The obtained tokens are saved to the configured `token_storage` backend for future use, eliminating the need for repeated browser interactions.

**8. Authenticated Requests**

The access token is automatically included in the `Authorization` header for requests to the MCP server.

**9. Refresh Token**

If the access token expires, the client will automatically use the refresh token to get a new access token.

## Token Storage

New in version `2.13.0`

By default, tokens are stored in memory and lost when your application restarts. For persistent storage, pass an `AsyncKeyValue`-compatible storage backend to the `token_storage` parameter.

> [!WARNING]
>
> **Security Consideration**: Use encrypted storage for production. MCP clients can accumulate OAuth credentials for many servers over time, and a compromised token store could expose access to multiple services.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
import os
from pathlib import Path

from cryptography.fernet import Fernet
from fastmcp import Client
from fastmcp.client.auth import OAuth
from key_value.aio.stores.filetree import (
    FileTreeStore,
    FileTreeV1CollectionSanitizationStrategy,
    FileTreeV1KeySanitizationStrategy,
)
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper

token_dir = Path("~/.fastmcp/oauth-tokens").expanduser()
token_dir.mkdir(parents=True, exist_ok=True)

file_store = FileTreeStore(
    data_directory=token_dir,
    key_sanitization_strategy=FileTreeV1KeySanitizationStrategy(token_dir),
    collection_sanitization_strategy=FileTreeV1CollectionSanitizationStrategy(token_dir),
)

encrypted_storage = FernetEncryptionWrapper(
    key_value=file_store,
    fernet=Fernet(os.environ["OAUTH_STORAGE_ENCRYPTION_KEY"]),
)

oauth = OAuth(token_storage=encrypted_storage)

async with Client("https://your-server.fastmcp.app/mcp", auth=oauth) as client:
    await client.list_tools()
```

You can use any `AsyncKeyValue`-compatible backend from the [key-value library](https://github.com/strawgate/py-key-value) including Redis, DynamoDB, and more. Wrap your storage in `FernetEncryptionWrapper` for encryption.

> [!NOTE]
>
> When selecting a storage backend, review the [py-key-value documentation](https://github.com/strawgate/py-key-value) to understand the maturity level and limitations of your chosen backend. Some backends may be in preview or have constraints that affect production suitability.

## CIMD Authentication

New in version `3.0.0`

Client ID Metadata Documents (CIMD) provide an alternative to Dynamic Client Registration. Instead of registering with each server, your client hosts a static JSON document at an HTTPS URL. That URL becomes your client's identity, and servers can verify who you are through your domain ownership.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import Client
from fastmcp.client.auth import OAuth

async with Client(
    "https://mcp-server.example.com/mcp",
    auth=OAuth(
        client_metadata_url="https://myapp.example.com/oauth/client.json",
    ),
) as client:
    await client.list_tools()
```

See the [CIMD Authentication](https://gofastmcp.com/docs/clients/auth/cimd.md) page for complete documentation on creating, hosting, and validating CIMD documents.

## Pre-Registered Clients

New in version `3.0.0`

Some OAuth servers don't support Dynamic Client Registration — the MCP spec explicitly makes DCR optional. If your client has been pre-registered with the server (you already have a `client_id` and optionally a `client_secret`), you can provide them directly to skip DCR entirely.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import Client
from fastmcp.client.auth import OAuth

async with Client(
    "https://mcp-server.example.com/mcp",
    auth=OAuth(
        client_id="my-registered-client-id",
        client_secret="my-client-secret",
    ),
) as client:
    await client.list_tools()
```

Public clients that rely on PKCE for security can omit `client_secret`:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp.client.auth import OAuth

oauth = OAuth(client_id="my-public-client-id")
```

> [!NOTE]
>
> When using pre-registered credentials, the client will not attempt Dynamic Client Registration. If the server rejects the credentials, the error is surfaced immediately rather than falling back to DCR.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.