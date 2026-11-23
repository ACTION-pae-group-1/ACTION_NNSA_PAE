> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# jwt

# `fastmcp.server.auth.providers.jwt`

TokenVerifier implementations for FastMCP.

## Classes

### `JWKData` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/providers/jwt.py#L76](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/providers/jwt.py#L76)</sup>

JSON Web Key data structure.

### `JWKSData` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/providers/jwt.py#L91](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/providers/jwt.py#L91)</sup>

JSON Web Key Set data structure.

### `RSAKeyPair` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/providers/jwt.py#L98](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/providers/jwt.py#L98)</sup>

RSA key pair for JWT testing.

**Methods:**

#### `generate` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/providers/jwt.py#L105](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/providers/jwt.py#L105)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
generate(cls) -> RSAKeyPair
```

Generate an RSA key pair for testing.

**Returns:**

* Generated key pair

#### `create_token` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/providers/jwt.py#L140](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/providers/jwt.py#L140)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
create_token(self, subject: str = 'fastmcp-user', issuer: str = 'https://fastmcp.example.com', audience: str | list[str] | None = None, scopes: list[str] | None = None, expires_in_seconds: int = 3600, additional_claims: dict[str, Any] | None = None, kid: str | None = None) -> str
```

Generate a test JWT token for testing purposes.

**Args:**

* `subject`: Subject claim (usually user ID)
* `issuer`: Issuer claim
* `audience`: Audience claim - can be a string or list of strings (optional)
* `scopes`: List of scopes to include
* `expires_in_seconds`: Token expiration time in seconds
* `additional_claims`: Any additional claims to include
* `kid`: Key ID to include in header

### `JWTVerifier` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/providers/jwt.py#L207](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/providers/jwt.py#L207)</sup>

JWT token verifier supporting asymmetric (RSA/ECDSA/EdDSA) and symmetric (HMAC) algorithms.

This verifier validates JWT tokens using various signing algorithms:

* **Asymmetric algorithms** (RS256/384/512, ES256/384/512, PS256/384/512,
  Ed25519, Ed448, and legacy EdDSA):
  Uses public/private key pairs. Ideal for external clients and services where
  only the authorization server has the private key.
* **Symmetric algorithms** (HS256/384/512): Uses a shared secret for both
  signing and verification. Perfect for internal microservices and trusted
  environments where the secret can be securely shared.

Use this when:

* You have JWT tokens issued by an external service (asymmetric)
* You need JWKS support for automatic key rotation (asymmetric)
* You have internal microservices sharing a secret key (symmetric)
* Your tokens contain standard OAuth scopes and claims

**Methods:**

#### `load_access_token` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/providers/jwt.py#L534](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/providers/jwt.py#L534)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
load_access_token(self, token: str) -> AccessToken | None
```

Validate a JWT bearer token and return an AccessToken when the token is valid.

**Args:**

* `token`: The JWT bearer token string to validate.

**Returns:**

* AccessToken | None: An AccessToken populated from token claims if the token is valid; `None` if the token is expired, has an invalid signature or format, fails issuer/audience/scope validation, or any other validation error occurs.

#### `verify_token` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/providers/jwt.py#L668](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/providers/jwt.py#L668)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
verify_token(self, token: str) -> AccessToken | None
```

Verify a bearer token and return access info if valid.

This method implements the TokenVerifier protocol by delegating
to our existing load\_access\_token method.

**Args:**

* `token`: The JWT token string to validate

**Returns:**

* AccessToken object if valid, None if invalid or expired

### `StaticTokenVerifier` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/providers/jwt.py#L684](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/providers/jwt.py#L684)</sup>

Simple static token verifier for testing and development.

This verifier validates tokens against a predefined dictionary of valid token
strings and their associated claims. When a token string matches a key in the
dictionary, the verifier returns the corresponding claims as if the token was
validated by a real authorization server.

Use this when:

* You're developing or testing locally without a real OAuth server
* You need predictable tokens for automated testing
* You want to simulate different users/scopes without complex setup
* You're prototyping and need simple API key-style authentication

WARNING: Never use this in production - tokens are stored in plain text!

**Methods:**

#### `verify_token` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/providers/jwt.py#L718](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/providers/jwt.py#L718)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
verify_token(self, token: str) -> AccessToken | None
```

Verify token against static token dictionary.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.