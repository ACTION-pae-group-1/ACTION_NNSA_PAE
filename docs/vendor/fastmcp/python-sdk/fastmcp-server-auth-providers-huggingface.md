> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# huggingface

# `fastmcp.server.auth.providers.huggingface`

Hugging Face OAuth provider for FastMCP.

## Classes

### `HuggingFaceTokenVerifier` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/providers/huggingface.py#L56](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/providers/huggingface.py#L56)</sup>

Token verifier for Hugging Face OAuth access tokens.

Hugging Face OAuth access tokens are opaque, so validation is performed by
calling Hugging Face's userinfo endpoint.

**Methods:**

#### `verify_token` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/providers/huggingface.py#L74](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/providers/huggingface.py#L74)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
verify_token(self, token: str) -> AccessToken | None
```

Verify a Hugging Face OAuth token using the userinfo endpoint.

### `HuggingFaceProvider` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/providers/huggingface.py#L175](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/providers/huggingface.py#L175)</sup>

Complete Hugging Face OAuth provider for FastMCP.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.