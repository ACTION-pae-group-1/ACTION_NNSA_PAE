> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# base

# `fastmcp.resources.base`

Base classes and interfaces for FastMCP resources.

## Functions

### `convert_raw_to_resource_result` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/base.py#L242](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/base.py#L242)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
convert_raw_to_resource_result(raw_value: Any) -> ResourceResult
```

Wrap a user function's return value in a ResourceResult.

Shared by `Resource` and `ResourceTemplate` so both honor the MIME type
the component declares in listings. A component that advertises
`text/csv` must not serve `text/plain` on read.

**Args:**

* `raw_value`: The value returned by the user's function.
* `mime_type`: The component's declared MIME type, forwarded to content items.
* `meta`: Component-level meta (e.g. `ui` metadata for MCP Apps CSP/permissions)
  propagated to each content item. For `list[ResourceContent]` returns
  it is merged into every item, with item-level keys taking precedence.

## Classes

### `ResourceContent` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/base.py#L34](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/base.py#L34)</sup>

Wrapper for resource content with optional MIME type and metadata.

Accepts any value for content - strings and bytes pass through directly,
other types (dict, list, BaseModel, etc.) are automatically JSON-serialized.

**Methods:**

#### `to_mcp_resource_contents` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/base.py#L89](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/base.py#L89)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
to_mcp_resource_contents(self, uri: AnyUrl | str) -> mcp_types.TextResourceContents | mcp_types.BlobResourceContents
```

Convert to MCP resource contents type.

**Args:**

* `uri`: The URI of the resource (required by MCP types)

**Returns:**

* TextResourceContents for str content, BlobResourceContents for bytes

### `ResourceResult` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/base.py#L116](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/base.py#L116)</sup>

Canonical result type for resource reads.

Provides explicit control over resource responses: multiple content items,
per-item MIME types, and metadata at both the item and result level.

**Methods:**

#### `to_mcp_result` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/base.py#L197](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/base.py#L197)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
to_mcp_result(self, uri: AnyUrl | str) -> mcp_types.ReadResourceResult
```

Convert to MCP ReadResourceResult.

**Args:**

* `uri`: The URI of the resource (required by MCP types)

**Returns:**

* MCP ReadResourceResult with converted contents

### `InputRequiredResourceResult` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/base.py#L213](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/base.py#L213)</sup>

The full result of a single multi-round-trip resource read (SEP-2322).

`InputRequiredResult` is a result type, not a `tools/call` feature: any
request may resolve to one. When a resource or resource template returns an
`InputRequiredResult` from its body to ask the client for input, that ask is
the legitimate result of this `resources/read` — so FastMCP wraps it in this
`ResourceResult` subclass, mirroring `InputRequiredToolResult` and
`InputRequiredPromptResult`, and it flows through the middleware chain as an
ordinary return value.

Invariant: the wrapped `InputRequiredResult` is never serialized as resource
contents. `contents` is always empty; the wire handler (`_on_read_resource`)
reads `.input_required` and returns it to the runner.

### `Resource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/base.py#L322](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/base.py#L322)</sup>

Base class for all resources.

**Methods:**

#### `from_function` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/base.py#L347](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/base.py#L347)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from_function(cls, fn: Callable[..., Any], uri: str | AnyUrl) -> FunctionResource
```

#### `set_default_mime_type` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/base.py#L384](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/base.py#L384)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
set_default_mime_type(cls, mime_type: str | None) -> str
```

Set default MIME type if not provided.

#### `set_default_name` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/base.py#L391](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/base.py#L391)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
set_default_name(self) -> Self
```

Set default name from URI if not provided.

#### `read` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/base.py#L401](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/base.py#L401)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
read(self) -> str | bytes | ResourceResult
```

Read the resource content.

Subclasses implement this to return resource data. Supported return types:

* str: Text content
* bytes: Binary content
* ResourceResult: Full control over contents and result-level meta

#### `convert_result` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/base.py#L413](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/base.py#L413)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
convert_result(self, raw_value: Any) -> ResourceResult
```

Convert a raw result to ResourceResult.

This is used in two contexts:

1. In \_read() to convert user function return values to ResourceResult
2. In tasks\_result\_handler() to convert Docket task results to ResourceResult

Handles ResourceResult passthrough and converts raw values using
ResourceResult's normalization.  When the raw value is a plain
string or bytes, the resource's own `mime_type` is forwarded so
that `ui://` resources (and others with non-default MIME types)
don't fall back to `text/plain`.

The resource's component-level `meta` (e.g. `ui` metadata for
MCP Apps CSP/permissions) is propagated to each content item so
that hosts can read it from the `resources/read` response.

#### `to_mcp_resource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/base.py#L445](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/base.py#L445)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
to_mcp_resource(self, **overrides: Any) -> SDKResource
```

Convert the resource to an SDKResource.

#### `key` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/base.py#L468](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/base.py#L468)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
key(self) -> str
```

The globally unique lookup key for this resource.

#### `get_span_attributes` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/base.py#L473](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/base.py#L473)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_span_attributes(self) -> dict[str, Any]
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.