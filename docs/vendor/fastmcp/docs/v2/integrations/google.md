> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Google OAuth 🤝 FastMCP

> Secure your FastMCP server with Google OAuth

New in version `2.12.0`

This guide shows you how to secure your FastMCP server using **Google OAuth**. Since Google doesn't support Dynamic Client Registration, this integration uses the [**OAuth Proxy**](https://gofastmcp.com/docs/v2/servers/auth/oauth-proxy.md) pattern to bridge Google's traditional OAuth with MCP's authentication requirements.

## Configuration

### Prerequisites

Before you begin, you will need:

1. A **[Google Cloud Account](https://console.cloud.google.com/)** with access to create OAuth 2.0 Client IDs
2. Your FastMCP server's URL (can be localhost for development, e.g., `http://localhost:8000`)

### Step 1: Create a Google OAuth 2.0 Client ID

Create an OAuth 2.0 Client ID in your Google Cloud Console to get the credentials needed for authentication:

**1. Navigate to OAuth Consent Screen**

Go to the [Google Cloud Console](https://console.cloud.google.com/apis/credentials) and select your project (or create a new one).

First, configure the OAuth consent screen by navigating to **APIs & Services → OAuth consent screen**. Choose "External" for testing or "Internal" for G Suite organizations.

**2. Create OAuth 2.0 Client ID**

Navigate to **APIs & Services → Credentials** and click **"+ CREATE CREDENTIALS"** → **"OAuth client ID"**.

Configure your OAuth client:

* **Application type**: Web application
* **Name**: Choose a descriptive name (e.g., "FastMCP Server")
* **Authorized JavaScript origins**: Add your server's base URL (e.g., `http://localhost:8000`)
* **Authorized redirect URIs**: Add your server URL + `/auth/callback` (e.g., `http://localhost:8000/auth/callback`)

> [!WARNING]
>
> The redirect URI must match exactly. The default path is `/auth/callback`, but you can customize it using the `redirect_path` parameter. For local development, Google allows `http://localhost` URLs with various ports. For production, you must use HTTPS.

> [!TIP]
>
> If you want to use a custom callback path (e.g., `/auth/google/callback`), make sure to set the same path in both your Google OAuth Client settings and the `redirect_path` parameter when configuring the GoogleProvider.

**3. Save Your Credentials**

After creating the client, you'll receive:

* **Client ID**: A string ending in `.apps.googleusercontent.com`
* **Client Secret**: A string starting with `GOCSPX-`

Download the JSON credentials or copy these values securely.

> [!TIP]
>
> Store these credentials securely. Never commit them to version control. Use environment variables or a secrets manager in production.

### Step 2: FastMCP Configuration

Create your FastMCP server using the `GoogleProvider`, which handles Google's OAuth flow automatically:

```python server.py theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import FastMCP
from fastmcp.server.auth.providers.google import GoogleProvider

# The GoogleProvider handles Google's token format and validation
auth_provider = GoogleProvider(
    client_id="123456789.apps.googleusercontent.com",  # Your Google OAuth Client ID
    client_secret="GOCSPX-abc123...",                  # Your Google OAuth Client Secret
    base_url="http://localhost:8000",                  # Must match your OAuth configuration
    required_scopes=[                                  # Request user information
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
    ],
    # redirect_path="/auth/callback"                  # Default value, customize if needed
)

mcp = FastMCP(name="Google Secured App", auth=auth_provider)

# Add a protected tool to test authentication
@mcp.tool
async def get_user_info() -> dict:
    """Returns information about the authenticated Google user."""
    from fastmcp.server.dependencies import get_access_token
    
    token = get_access_token()
    # The GoogleProvider stores user data in token claims
    return {
        "google_id": token.claims.get("sub"),
        "email": token.claims.get("email"),
        "name": token.claims.get("name"),
        "picture": token.claims.get("picture"),
        "locale": token.claims.get("locale")
    }
```

## Testing

### Running the Server

Start your FastMCP server with HTTP transport to enable OAuth flows:

```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
fastmcp run server.py --transport http --port 8000
```

Your server is now running and protected by Google OAuth authentication.

### Testing with a Client

Create a test client that authenticates with your Google-protected server:

```python test_client.py theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import Client
import asyncio

async def main():
    # The client will automatically handle Google OAuth
    async with Client("http://localhost:8000/mcp", auth="oauth") as client:
        # First-time connection will open Google login in your browser
        print("✓ Authenticated with Google!")
        
        # Test the protected tool
        result = await client.call_tool("get_user_info")
        print(f"Google user: {result['email']}")
        print(f"Name: {result['name']}")

if __name__ == "__main__":
    asyncio.run(main())
```

When you run the client for the first time:

1. Your browser will open to Google's authorization page
2. Sign in with your Google account and grant the requested permissions
3. After authorization, you'll be redirected back
4. The client receives the token and can make authenticated requests

> [!NOTE]
>
> The client caches tokens locally, so you won't need to re-authenticate for subsequent runs unless the token expires or you explicitly clear the cache.

## Production Configuration

New in version `2.13.0`

For production deployments with persistent token management across server restarts, configure `jwt_signing_key` and `client_storage`:

```python server.py theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
import os
from fastmcp import FastMCP
from fastmcp.server.auth.providers.google import GoogleProvider
from key_value.aio.stores.redis import RedisStore
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from cryptography.fernet import Fernet

# Production setup with encrypted persistent token storage
auth_provider = GoogleProvider(
    client_id="123456789.apps.googleusercontent.com",
    client_secret="GOCSPX-abc123...",
    base_url="https://your-production-domain.com",
    required_scopes=["openid", "https://www.googleapis.com/auth/userinfo.email"],

    # Production token management
    jwt_signing_key=os.environ["JWT_SIGNING_KEY"],
    client_storage=FernetEncryptionWrapper(
        key_value=RedisStore(
            host=os.environ["REDIS_HOST"],
            port=int(os.environ["REDIS_PORT"])
        ),
        fernet=Fernet(os.environ["STORAGE_ENCRYPTION_KEY"])
    )
)

mcp = FastMCP(name="Production Google App", auth=auth_provider)
```

> [!NOTE]
>
> Parameters (`jwt_signing_key` and `client_storage`) work together to ensure tokens and client registrations survive server restarts. **Wrap your storage in `FernetEncryptionWrapper` to encrypt sensitive OAuth tokens at rest** - without it, tokens are stored in plaintext. Store secrets in environment variables and use a persistent storage backend like Redis for distributed deployments.
>
> For complete details on these parameters, see the [OAuth Proxy documentation](https://gofastmcp.com/docs/v2/servers/auth/oauth-proxy.md#configuration-parameters).

## Environment Variables

New in version `2.12.1`

For production deployments, use environment variables instead of hardcoding credentials.

### Provider Selection

Setting this environment variable allows the Google provider to be used automatically without explicitly instantiating it in code.

> [card]
>
> **FASTMCP\_SERVER\_AUTH** (default: Not set)
>
> Set to `fastmcp.server.auth.providers.google.GoogleProvider` to use Google authentication.

### Google-Specific Configuration

These environment variables provide default values for the Google provider, whether it's instantiated manually or configured via `FASTMCP_SERVER_AUTH`.

> [card]
>
> **FASTMCP\_SERVER\_AUTH\_GOOGLE\_CLIENT\_ID** *required*
>
> Your Google OAuth 2.0 Client ID (e.g., `123456789.apps.googleusercontent.com`)
>
> **FASTMCP\_SERVER\_AUTH\_GOOGLE\_CLIENT\_SECRET** *required*
>
> Your Google OAuth 2.0 Client Secret (e.g., `GOCSPX-abc123...`)
>
> **FASTMCP\_SERVER\_AUTH\_GOOGLE\_BASE\_URL** (default: [http://localhost:8000](http://localhost:8000))
>
> Public URL where OAuth endpoints will be accessible (includes any mount path)
>
> **FASTMCP\_SERVER\_AUTH\_GOOGLE\_ISSUER\_URL** (default: Uses BASE\_URL)
>
> Issuer URL for OAuth metadata (defaults to `BASE_URL`). Set to root-level URL when mounting under a path prefix to avoid 404 logs. See [HTTP Deployment guide](https://gofastmcp.com/docs/v2/deployment/http.md#mounting-authenticated-servers) for details.
>
> **FASTMCP\_SERVER\_AUTH\_GOOGLE\_REDIRECT\_PATH** (default: /auth/callback)
>
> Redirect path configured in your Google OAuth Client
>
> **FASTMCP\_SERVER\_AUTH\_GOOGLE\_REQUIRED\_SCOPES** (default: \[])
>
> Comma-, space-, or JSON-separated list of required Google scopes (e.g., `"openid,https://www.googleapis.com/auth/userinfo.email"` or `["openid", "https://www.googleapis.com/auth/userinfo.email"]`)
>
> **FASTMCP\_SERVER\_AUTH\_GOOGLE\_TIMEOUT\_SECONDS** (default: 10)
>
> HTTP request timeout for Google API calls

Example `.env` file:

```bash theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
# Use the Google provider
FASTMCP_SERVER_AUTH=fastmcp.server.auth.providers.google.GoogleProvider

# Google OAuth credentials
FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID=123456789.apps.googleusercontent.com
FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET=GOCSPX-abc123...
FASTMCP_SERVER_AUTH_GOOGLE_BASE_URL=https://your-server.com
FASTMCP_SERVER_AUTH_GOOGLE_REQUIRED_SCOPES=openid,https://www.googleapis.com/auth/userinfo.email
```

With environment variables set, your server code simplifies to:

```python server.py theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import FastMCP

# Authentication is automatically configured from environment
mcp = FastMCP(name="Google Secured App")

@mcp.tool
async def protected_tool(query: str) -> str:
    """A tool that requires Google authentication to access."""
    # Your tool implementation here
    return f"Processing authenticated request: {query}"
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.