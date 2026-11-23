> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# settings

# `fastmcp.settings`

## Classes

### `Settings` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/settings.py#L34](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/settings.py#L34)</sup>

FastMCP settings.

**Methods:**

#### `get_setting` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/settings.py#L46](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/settings.py#L46)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_setting(self, attr: str) -> Any
```

Get a setting. If the setting contains one or more `__`, it will be
treated as a nested setting.

#### `set_setting` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/settings.py#L59](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/settings.py#L59)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
set_setting(self, attr: str, value: Any) -> None
```

Set a setting. If the setting contains one or more `__`, it will be
treated as a nested setting.

#### `normalize_log_level` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/settings.py#L83](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/settings.py#L83)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
normalize_log_level(cls, v)
```

#### `parse_disabled_session_idle_timeout` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/settings.py#L304](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/settings.py#L304)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
parse_disabled_session_idle_timeout(cls, v)
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.