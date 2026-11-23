> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# prefab

# `fastmcp.utilities.prefab`

Lazy helpers for FastMCP's optional Prefab UI integration.

## Functions

### `prefab_available` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/prefab.py#L12](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/prefab.py#L12)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
prefab_available() -> bool
```

Return whether Prefab UI is installed without importing it.

### `is_prefab_type` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/prefab.py#L42](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/prefab.py#L42)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
is_prefab_type(candidate: Any) -> bool
```

Return whether a type is a Prefab app or component type.

### `is_prefab_app` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/prefab.py#L51](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/prefab.py#L51)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
is_prefab_app(value: Any) -> bool
```

Return whether a value is a Prefab app.

### `is_prefab_component` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/prefab.py#L60](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/prefab.py#L60)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
is_prefab_component(value: Any) -> bool
```

Return whether a value is a Prefab component.

### `prefab_app_from_component` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/prefab.py#L69](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/prefab.py#L69)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
prefab_app_from_component(component: Any) -> Any
```

Wrap a Prefab component in a Prefab app.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.