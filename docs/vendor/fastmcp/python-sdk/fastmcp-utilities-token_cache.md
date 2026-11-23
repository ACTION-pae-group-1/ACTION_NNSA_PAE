> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# token_cache

# `fastmcp.utilities.token_cache`

In-memory cache for token verification results.

Provides a generic TTL-based cache for `AccessToken` objects, designed to
reduce repeated network calls during opaque-token verification.  Only
*successful* verifications should be cached; errors and failures must be
retried on every request.

Example:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp.utilities.token_cache import TokenCache

cache = TokenCache(ttl_seconds=300, max_size=10000)

# On cache miss, call the upstream verifier and store the result.
hit, token = cache.get(raw_token)
if not hit:
    token = await _call_upstream(raw_token)
    if token is not None:
        cache.set(raw_token, token)
```

## Classes

### `TokenCache` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/token\_cache.py#L46](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/token_cache.py#L46)</sup>

TTL-based in-memory cache for `AccessToken` objects.

Features:

* SHA-256 hashed cache keys (fixed size, regardless of token length).
* Per-entry TTL that respects both the configured `ttl_seconds` and the
  token's own `expires_at` claim (whichever is sooner).
* Bounded size with FIFO eviction when the cache is full.
* Periodic cleanup of expired entries to prevent unbounded growth.
* Defensive deep copies on both store and retrieve to prevent
  callers from mutating cached values.

Caching is disabled when `ttl_seconds` is `None` or `0`, or
when `max_size` is `0`.  Negative values raise `ValueError`.

**Methods:**

#### `enabled` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/token\_cache.py#L89](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/token_cache.py#L89)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
enabled(self) -> bool
```

Return whether caching is active.

#### `get` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/token\_cache.py#L95](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/token_cache.py#L95)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get(self, token: str) -> tuple[bool, AccessToken | None]
```

Look up a cached verification result.

**Returns:**

* `(True, AccessToken)` on a cache hit, `(False, None)` on a miss
* or when caching is disabled.  The returned `AccessToken` is a deep
* copy that is safe to mutate.

#### `set` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/token\_cache.py#L118](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/token_cache.py#L118)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
set(self, token: str, result: AccessToken) -> None
```

Store a *successful* verification result.

Only successful verifications should be cached.  Failures (inactive
tokens, missing scopes, HTTP errors, timeouts) must **not** be cached
so that transient problems do not produce sticky false negatives.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.