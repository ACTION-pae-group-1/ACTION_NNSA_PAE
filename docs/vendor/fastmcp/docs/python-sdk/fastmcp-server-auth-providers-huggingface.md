> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# huggingface

# `fastmcp.server.auth.providers.huggingface`

Hugging Face OAuth provider for FastMCP.

## Classes

### `HuggingFaceTokenVerifier` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/providers/huggingface.py#L57](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/providers/huggingface.py#L57)</sup>

Token verifier for Hugging Face OAuth access tokens.

Hugging Face OAuth access tokens are opaque, so validation is performed by
calling Hugging Face's userinfo endpoint.

**Methods:**

#### `verify_token` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/providers/huggingface.py#L75](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/providers/huggingface.py#L75)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
verify_token(self, token: str) -> AccessToken | None
```

Verify a Hugging Face OAuth token using the userinfo endpoint.

### `HuggingFaceProvider` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/providers/huggingface.py#L176](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/providers/huggingface.py#L176)</sup>

Complete Hugging Face OAuth provider for FastMCP.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.