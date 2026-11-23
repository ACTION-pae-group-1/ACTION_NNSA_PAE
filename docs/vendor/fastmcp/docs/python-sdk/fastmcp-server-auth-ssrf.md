> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# ssrf

# `fastmcp.server.auth.ssrf`

SSRF-safe HTTP utilities for FastMCP.

This module provides SSRF-protected HTTP fetching with:

* DNS resolution and IP validation before requests
* DNS pinning to prevent rebinding TOCTOU attacks
* Support for both CIMD and JWKS fetches

When `FASTMCP_SSRF_TRUST_PROXY` is set, DNS resolution and the IP blocklist are
skipped and a single request is made to the hostname URL through the configured
HTTPS\_PROXY/ALL\_PROXY, delegating DNS and egress to that trusted proxy (the scheme
and hostname checks still apply). The proxy URL is read from the environment and
passed to httpx2 explicitly with `trust_env` disabled, so the request is provably
routed through the proxy rather than predicted to be — NO\_PROXY is not evaluated in
this mode. If no proxy is configured, the fetch is refused rather than sent direct
with the blocklist disabled.

Proxy-trust mode removes FastMCP's DNS/IP checks and pinning. SSRF protection
then depends on the proxy's destination restrictions, which FastMCP does not
verify; configuring a proxy alone does not establish equivalent protection.

## Functions

### `format_ip_for_url` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/ssrf.py#L59](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/ssrf.py#L59)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
format_ip_for_url(ip_str: str) -> str
```

Format IP address for use in URL (bracket IPv6 addresses).

IPv6 addresses must be bracketed in URLs to distinguish the address from
the port separator. For example: https\://\[2001:db8::1]:443/path

**Args:**

* `ip_str`: IP address string

**Returns:**

* IP string suitable for URL (IPv6 addresses are bracketed)

### `is_ip_allowed` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/ssrf.py#L141](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/ssrf.py#L141)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
is_ip_allowed(ip_str: str) -> bool
```

Check if an IP address is allowed (must be globally routable unicast).

Uses ip.is\_global which catches:

* Private (10.x, 172.16-31.x, 192.168.x)
* Loopback (127.x, ::1)
* Link-local (169.254.x, fe80::) - includes AWS metadata!
* Reserved, unspecified
* RFC6598 Carrier-Grade NAT (100.64.0.0/10) - can point to internal networks
* IPv6 transition forms that embed blocked IPv4 targets

Additionally blocks multicast addresses (not caught by is\_global).

**Args:**

* `ip_str`: IP address string to check

**Returns:**

* True if the IP is allowed (public unicast internet), False if blocked

### `resolve_hostname` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/ssrf.py#L179](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/ssrf.py#L179)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
resolve_hostname(hostname: str, port: int = 443) -> list[str]
```

Resolve hostname to IP addresses using DNS.

**Args:**

* `hostname`: Hostname to resolve
* `port`: Port number (used for getaddrinfo)

**Returns:**

* List of resolved IP addresses

**Raises:**

* `SSRFError`: If resolution fails

### `validate_url` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/ssrf.py#L278](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/ssrf.py#L278)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
validate_url(url: str, require_path: bool = False) -> ValidatedURL
```

Validate URL for SSRF and resolve to IPs.

**Args:**

* `url`: URL to validate
* `require_path`: If True, require non-root path (for CIMD)

**Returns:**

* ValidatedURL with resolved IPs

**Raises:**

* `SSRFError`: If the URL is invalid, resolves to blocked IPs, or proxy-trust
  mode is enabled but no configured proxy will route the request.

### `ssrf_safe_fetch` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/ssrf.py#L374](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/ssrf.py#L374)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
ssrf_safe_fetch(url: str) -> bytes
```

Fetch URL with comprehensive SSRF protection and DNS pinning.

Security measures:

1. HTTPS only
2. DNS resolution with IP validation
3. Connects to validated IP directly (DNS pinning prevents rebinding)
4. Response size limit
5. Redirects disabled
6. Overall timeout

**Args:**

* `url`: URL to fetch
* `require_path`: If True, require non-root path
* `max_size`: Maximum response size in bytes (default 5KB)
* `timeout`: Per-operation timeout in seconds
* `overall_timeout`: Overall timeout for entire operation

**Returns:**

* Response body as bytes

**Raises:**

* `SSRFError`: If SSRF validation fails
* `SSRFFetchError`: If fetch fails

### `ssrf_safe_fetch_response` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/ssrf.py#L417](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/ssrf.py#L417)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
ssrf_safe_fetch_response(url: str) -> SSRFFetchResponse
```

Fetch URL with SSRF protection and return response metadata.

This is equivalent to :func:`ssrf_safe_fetch` but returns response headers
and status code, and supports conditional request headers.

## Classes

### `SSRFError` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/ssrf.py#L100](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/ssrf.py#L100)</sup>

Raised when an SSRF protection check fails.

### `SSRFFetchError` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/ssrf.py#L104](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/ssrf.py#L104)</sup>

Raised when SSRF-safe fetch fails.

### `ValidatedURL` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/ssrf.py#L209](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/ssrf.py#L209)</sup>

A URL that has been validated for SSRF with resolved IPs.

### `SSRFFetchResponse` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/auth/ssrf.py#L221](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/auth/ssrf.py#L221)</sup>

Response payload from an SSRF-safe fetch.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.