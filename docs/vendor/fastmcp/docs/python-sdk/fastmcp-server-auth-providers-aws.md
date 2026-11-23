> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# aws

# `fastmcp.server.auth.providers.aws`

AWS Cognito OAuth provider for FastMCP.

This module provides a complete AWS Cognito OAuth integration that's ready to use
with a user pool ID, domain prefix, client ID and client secret. It handles all
the complexity of AWS Cognito's OAuth flow, token validation, and user management.

Example:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import FastMCP
from fastmcp.server.auth.providers.aws_cognito import AWSCognitoProvider

# Simple AWS Cognito OAuth protection
auth = AWSCognitoProvider(
    user_pool_id="your-user-pool-id",
    aws_region="eu-central-1",
    client_id="your-cognito-client-id",
    client_secret="your-cognito-client-secret"
)

mcp = FastMCP("My Protected Server", auth=auth)
```

## Classes

### `AWSCognitoTokenVerifier` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/providers/aws.py#L44](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/providers/aws.py#L44)</sup>

Token verifier for Cognito access tokens.

Cognito access tokens use a `client_id` claim instead of the
standard `aud` claim.  This subclass passes `audience=None`
to the parent (skipping the `aud` check) and validates the
`client_id` claim directly.

**Methods:**

#### `verify_token` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/providers/aws.py#L57](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/providers/aws.py#L57)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
verify_token(self, token: str) -> AccessToken | None
```

Verify token and filter claims to Cognito-specific subset.

### `AWSCognitoProvider` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/providers/aws.py#L95](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/providers/aws.py#L95)</sup>

Complete AWS Cognito OAuth provider for FastMCP.

This provider makes it trivial to add AWS Cognito OAuth protection to any
FastMCP server using OIDC Discovery. Just provide your Cognito User Pool details,
client credentials, and a base URL, and you're ready to go.

Features:

* Automatic OIDC Discovery from AWS Cognito User Pool
* Automatic JWT token validation via Cognito's public keys
* Cognito-specific claim filtering (sub, username, cognito:groups)
* Support for Cognito User Pools

**Methods:**

#### `get_token_verifier` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/providers/aws.py#L244](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/providers/aws.py#L244)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_token_verifier(self) -> AWSCognitoTokenVerifier
```

Creates a Cognito-specific token verifier with claim filtering.

**Args:**

* `algorithm`: Optional token verifier algorithm
* `audience`: Optional token verifier audience
* `required_scopes`: Optional token verifier required\_scopes
* `timeout_seconds`: HTTP request timeout in seconds


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.