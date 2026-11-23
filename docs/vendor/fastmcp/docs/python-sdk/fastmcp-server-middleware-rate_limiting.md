> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# rate_limiting

# `fastmcp.server.middleware.rate_limiting`

Rate limiting middleware for protecting FastMCP servers from abuse.

## Classes

### `RateLimitError` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/rate\_limiting.py#L18](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/rate_limiting.py#L18)</sup>

Error raised when rate limit is exceeded.

### `TokenBucketRateLimiter` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/rate\_limiting.py#L25](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/rate_limiting.py#L25)</sup>

Token bucket implementation for rate limiting.

**Methods:**

#### `consume` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/rate\_limiting.py#L41](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/rate_limiting.py#L41)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
consume(self, tokens: int = 1) -> bool
```

Try to consume tokens from the bucket.

**Args:**

* `tokens`: Number of tokens to consume

**Returns:**

* True if tokens were available and consumed, False otherwise

### `SlidingWindowRateLimiter` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/rate\_limiting.py#L64](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/rate_limiting.py#L64)</sup>

Sliding window rate limiter implementation.

**Methods:**

#### `is_allowed` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/rate\_limiting.py#L79](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/rate_limiting.py#L79)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
is_allowed(self) -> bool
```

Check if a request is allowed.

### `RateLimitingMiddleware` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/rate\_limiting.py#L95](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/rate_limiting.py#L95)</sup>

Middleware that implements rate limiting to prevent server abuse.

Uses a token bucket algorithm by default, allowing for burst traffic
while maintaining a sustainable long-term rate.

**Methods:**

#### `on_request` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/rate\_limiting.py#L186](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/rate_limiting.py#L186)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_request(self, context: MiddlewareContext, call_next: CallNext) -> Any
```

Apply rate limiting to requests.

### `SlidingWindowRateLimitingMiddleware` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/rate\_limiting.py#L204](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/rate_limiting.py#L204)</sup>

Middleware that implements sliding window rate limiting.

Uses a sliding window approach which provides more precise rate limiting
but uses more memory to track individual request timestamps.

**Methods:**

#### `on_request` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/middleware/rate\_limiting.py#L259](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/middleware/rate_limiting.py#L259)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_request(self, context: MiddlewareContext, call_next: CallNext) -> Any
```

Apply sliding window rate limiting to requests.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.