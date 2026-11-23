> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# oidc_proxy

# `fastmcp.server.auth.oidc_proxy`

OIDC Proxy Provider for FastMCP.

This provider acts as a transparent proxy to an upstream OIDC compliant Authorization
Server. It leverages the OAuthProxy class to handle Dynamic Client Registration and
forwarding of all OAuth flows.

This implementation is based on:
OpenID Connect Discovery 1.0 - [https://openid.net/specs/openid-connect-discovery-1\_0.html](https://openid.net/specs/openid-connect-discovery-1_0.html)
OAuth 2.0 Authorization Server Metadata - [https://datatracker.ietf.org/doc/html/rfc8414](https://datatracker.ietf.org/doc/html/rfc8414)

## Classes

### `OIDCConfiguration` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/oidc\_proxy.py#L58](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/oidc_proxy.py#L58)</sup>

OIDC Configuration.

**Methods:**

#### `get_oidc_configuration` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/oidc\_proxy.py#L173](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/oidc_proxy.py#L173)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_oidc_configuration(cls, config_url: AnyHttpUrl) -> Self
```

Get the OIDC configuration for the specified config URL.

Successful discovery responses are cached briefly to avoid repeatedly hitting
the issuer for identical provider construction. Cached data is copied and
revalidated for every caller so mutable model instances are never shared.

**Args:**

* `config_url`: The OIDC config URL
* `strict`: The strict flag for the configuration
* `timeout_seconds`: HTTP request timeout in seconds

### `OIDCProxy` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/oidc\_proxy.py#L239](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/oidc_proxy.py#L239)</sup>

OAuth provider that wraps OAuthProxy to provide configuration via an OIDC configuration URL.

This provider makes it easier to add OAuth protection for any upstream provider
that is OIDC compliant.

**Methods:**

#### `get_oidc_configuration` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/oidc\_proxy.py#L571](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/oidc_proxy.py#L571)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_oidc_configuration(self, config_url: AnyHttpUrl, strict: bool | None, timeout_seconds: int | None) -> OIDCConfiguration
```

Gets the OIDC configuration for the specified configuration URL.

**Args:**

* `config_url`: The OIDC configuration URL
* `strict`: The strict flag for the configuration
* `timeout_seconds`: HTTP request timeout in seconds

#### `get_token_verifier` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/oidc\_proxy.py#L588](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/oidc_proxy.py#L588)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_token_verifier(self) -> TokenVerifier
```

Creates the token verifier for the specified OIDC configuration and arguments.

**Args:**

* `algorithm`: Optional token verifier algorithm
* `audience`: Optional token verifier audience
* `required_scopes`: Optional token verifier required\_scopes
* `timeout_seconds`: HTTP request timeout in seconds


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.