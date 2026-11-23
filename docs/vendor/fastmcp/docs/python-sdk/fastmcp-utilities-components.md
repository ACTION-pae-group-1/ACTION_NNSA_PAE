> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# components

# `fastmcp.utilities.components`

## Functions

### `get_fastmcp_metadata` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/components.py#L22](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/components.py#L22)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_fastmcp_metadata(meta: dict[str, Any] | None) -> FastMCPMeta
```

Extract FastMCP metadata from a component's meta dict.

Handles both the current `fastmcp` namespace and the legacy `_fastmcp`
namespace for compatibility with older FastMCP servers.

### `public_result_meta` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/components.py#L39](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/components.py#L39)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
public_result_meta(meta: dict[str, Any] | None) -> dict[str, Any] | None
```

Strip FastMCP's internal bookkeeping out of component meta.

Component `meta` carries private entries under the `fastmcp` namespace
(e.g. `_internal.visibility`) that must never reach the wire. Listings
already filter these via `FastMCPComponent.get_meta()`; results that
carry component meta (resource contents, prompt results) need the same
treatment.

Returns None when nothing public remains, so components without user
metadata keep an absent `_meta` rather than an empty object.

## Classes

### `FastMCPMeta` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/components.py#L16](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/components.py#L16)</sup>

### `FastMCPComponent` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/components.py#L99](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/components.py#L99)</sup>

Base class for FastMCP tools, prompts, resources, and resource templates.

**Methods:**

#### `make_key` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/components.py#L154](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/components.py#L154)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
make_key(cls, identifier: str) -> str
```

Construct the lookup key for this component type.

**Args:**

* `identifier`: The raw identifier (name for tools/prompts, uri for resources)

**Returns:**

* A prefixed key like "tool:name" or "resource:uri"

#### `key` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/components.py#L168](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/components.py#L168)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
key(self) -> str
```

The globally unique lookup key for this component.

Format: "{key_prefix}:{identifier}@{version}" or "{key_prefix}:{identifier}@"
e.g. "tool:my\_tool\@v2", "tool:my\_tool@", "resource:file://x.txt@"

The @ suffix is ALWAYS present to enable unambiguous parsing of keys
(URIs may contain @ characters, so we always include the delimiter).

Subclasses should override this to use their specific identifier.
Base implementation uses name.

Prefer `.key` over ad-hoc `name or uri or uri_template` logic for any
cross-component identity work (dedupe, grouping, collision detection,
lookup tables). It encodes type, identifier, and version, so variants
of the same component don't falsely collide with each other, and
cross-type identifiers (e.g. a tool and a resource both named "foo")
can't clash.

#### `get_meta` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/components.py#L190](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/components.py#L190)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_meta(self) -> dict[str, Any]
```

Get the meta information about the component.

Returns a dict that always includes a `fastmcp` key containing:

* `tags`: sorted list of component tags
* `version`: component version (only if set)

Internal keys (prefixed with `_`) are stripped from the fastmcp namespace.

#### `enable` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/components.py#L238](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/components.py#L238)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
enable(self) -> None
```

Removed in 3.0. Use server.enable(keys=\[...]) instead.

#### `disable` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/components.py#L245](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/components.py#L245)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
disable(self) -> None
```

Removed in 3.0. Use server.disable(keys=\[...]) instead.

#### `copy` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/components.py#L252](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/components.py#L252)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
copy(self) -> Self
```

Create a copy of the component.

#### `get_span_attributes` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/components.py#L256](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/components.py#L256)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_span_attributes(self) -> dict[str, Any]
```

Return span attributes for telemetry.

Subclasses should call super() and merge their specific attributes.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.