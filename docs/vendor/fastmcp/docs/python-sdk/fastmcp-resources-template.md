> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# template

# `fastmcp.resources.template`

Resource template functionality.

## Functions

### `extract_query_params` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/template.py#L44](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/template.py#L44)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
extract_query_params(uri_template: str) -> set[str]
```

Extract query parameter names from RFC 6570 `{?param1,param2}` syntax.

The explode modifier is stripped, so `{?tags*}` yields `{"tags"}`. Use
`extract_exploded_query_params` to find which names carried it.

### `extract_exploded_query_params` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/template.py#L92](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/template.py#L92)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
extract_exploded_query_params(uri_template: str) -> set[str]
```

Extract query parameter names declared with the RFC 6570 explode modifier.

`{?tags*}` marks `tags` as repeatable — `?tags=a&tags=b` collects into a
list rather than collapsing to the first value.

### `encode_literal` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/template.py#L110](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/template.py#L110)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
encode_literal(text: str) -> str
```

Percent-encode literal template text per RFC 6570 section 3.1.

A template may be written with characters the URI grammar does not allow —
a non-ASCII `ucschar` (`file:///docs/café/`) or a space — and section 3.1
requires those to be UTF-8 percent-encoded in the expanded URI. Reserved
and unreserved characters are structural and stay as written, and existing
`%XX` triplets pass through so an already-encoded literal is not encoded
twice.

A resource URI reaches the server as an `AnyUrl`, which percent-encodes it,
so the encoded form is what matching has to line up with.

### `build_regex` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/template.py#L164](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/template.py#L164)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
build_regex(template: str) -> re.Pattern[str] | None
```

Build regex pattern for URI template, handling RFC 6570 syntax.

Supports:

* `{var}` - simple path parameter
* `{var*}` - wildcard path parameter (captures multiple segments)
* `{?var1,var2}` - query parameters (ignored in path matching)

Hyphens in parameter names are normalized to underscores in regex group
names so that matched groups are valid Python identifiers.

Returns None if the template produces an invalid regex (e.g. parameter
names with leading digits or duplicates from a remote server).

### `match_uri_template` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/template.py#L201](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/template.py#L201)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
match_uri_template(uri: str, uri_template: str) -> dict[str, Any] | None
```

Match URI against template and extract both path and query parameters.

Supports RFC 6570 URI templates:

* Path params: `{var}`, `{var*}`
* Query params: `{?var1,var2}`, `{?list*}` (repeated keys)

`list_params` names non-exploded query params that hold lists. Per RFC 6570
section 3.2.8 their value is comma-joined, with literal commas separating
items and `%2C` inside an item, so they are split before decoding.

`regex` is the template's compiled path pattern when the caller already
holds it; otherwise it is built from `uri_template` through a bounded cache.

### `expand_uri_template` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/template.py#L276](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/template.py#L276)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
expand_uri_template(uri_template: str, params: dict[str, Any]) -> str
```

Expand a URI template with parameters — inverse of `match_uri_template`.

Supports the same RFC 6570 subset:

* Path params: `{var}`, `{var*}`
* Query params: `{?var1,var2}`

### `forward_uri` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/template.py#L348](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/template.py#L348)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
forward_uri(uri_template: str, params: dict[str, Any], uri: str) -> str
```

Build the URI a forwarding layer (mount or proxy) sends to the server behind it.

The path is expanded from `uri_template` with `params`, but the query string
is carried over from the incoming `uri` byte for byte. Re-expanding it would
decode and re-encode values, and the forwarding layer does not know which
`{?name}` params hold comma-joined lists, so `?tags=a%2Cb,c` would arrive as
one item instead of two.

## Classes

### `ResourceTemplate` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/template.py#L363](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/template.py#L363)</sup>

A template for dynamically creating resources.

**Methods:**

#### `resolve_security` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/template.py#L400](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/template.py#L400)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
resolve_security(self, server_default: ResourceSecurity | None) -> ResourceSecurity | None
```

Resolve the effective security policy for this template.

A per-component `security` overrides the server default.
`INHERIT_SECURITY` (the field default) inherits `server_default`;
an explicit `None` disables screening for this template.

#### `from_function` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/template.py#L417](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/template.py#L417)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from_function(fn: Callable[..., Any], uri_template: str, name: str | None = None, version: str | int | None = None, title: str | None = None, description: str | None = None, icons: list[Icon] | None = None, mime_type: str | None = None, tags: set[str] | None = None, annotations: Annotations | None = None, meta: dict[str, Any] | None = None, auth: AuthCheck | list[AuthCheck] | None = None, security: ResourceSecurity | None | InheritSecurity = INHERIT_SECURITY) -> FunctionResourceTemplate
```

#### `set_default_mime_type` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/template.py#L450](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/template.py#L450)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
set_default_mime_type(cls, mime_type: str | None) -> str
```

Set default MIME type if not provided.

#### `matches` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/template.py#L456](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/template.py#L456)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
matches(self, uri: str) -> dict[str, Any] | None
```

Check if URI matches template and extract parameters.

#### `read` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/template.py#L482](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/template.py#L482)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
read(self, arguments: dict[str, Any]) -> str | bytes | ResourceResult
```

Read the resource content.

#### `convert_result` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/template.py#L488](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/template.py#L488)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
convert_result(self, raw_value: Any) -> ResourceResult
```

Convert a raw result to ResourceResult.

This is used in two contexts:

1. In \_read() to convert user function return values to ResourceResult
2. In tasks\_result\_handler() to convert Docket task results to ResourceResult

Handles ResourceResult passthrough and converts raw values using
ResourceResult's normalization. The template's own `mime_type` is
forwarded so that reads match the MIME type the template advertises
in `resources/templates/list`.

#### `create_resource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/template.py#L515](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/template.py#L515)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
create_resource(self, uri: str, params: dict[str, Any]) -> Resource
```

Create a resource from the template with the given parameters.

The base implementation does not support background tasks.
Use FunctionResourceTemplate for task support.

#### `to_mcp_template` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/template.py#L526](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/template.py#L526)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
to_mcp_template(self, **overrides: Any) -> SDKResourceTemplate
```

Convert the resource template to an SDKResourceTemplate.

#### `from_mcp_template` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/template.py#L546](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/template.py#L546)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from_mcp_template(cls, mcp_template: SDKResourceTemplate) -> ResourceTemplate
```

Creates a FastMCP ResourceTemplate from a raw MCP ResourceTemplate object.

#### `key` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/template.py#L559](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/template.py#L559)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
key(self) -> str
```

The globally unique lookup key for this template.

#### `get_span_attributes` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/template.py#L564](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/template.py#L564)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_span_attributes(self) -> dict[str, Any]
```

### `FunctionResourceTemplate` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/template.py#L571](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/template.py#L571)</sup>

A template for dynamically creating resources.

**Methods:**

#### `create_resource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/template.py#L586](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/template.py#L586)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
create_resource(self, uri: str, params: dict[str, Any]) -> Resource
```

Create a resource from the template with the given parameters.

#### `read` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/template.py#L608](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/template.py#L608)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
read(self, arguments: dict[str, Any]) -> str | bytes | ResourceResult
```

Read the resource content.

#### `from_function` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/template.py#L653](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/template.py#L653)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from_function(cls, fn: Callable[..., Any], uri_template: str, name: str | None = None, version: str | int | None = None, title: str | None = None, description: str | None = None, icons: list[Icon] | None = None, mime_type: str | None = None, tags: set[str] | None = None, annotations: Annotations | None = None, meta: dict[str, Any] | None = None, auth: AuthCheck | list[AuthCheck] | None = None, security: ResourceSecurity | None | InheritSecurity = INHERIT_SECURITY) -> FunctionResourceTemplate
```

Create a template from a function.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.