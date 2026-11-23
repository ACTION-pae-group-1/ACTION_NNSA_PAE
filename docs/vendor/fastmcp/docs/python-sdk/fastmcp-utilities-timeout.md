> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# timeout

# `fastmcp.utilities.timeout`

Timeout normalization utilities.

## Functions

### `normalize_timeout_to_timedelta` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/timeout.py#L8](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/timeout.py#L8)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
normalize_timeout_to_timedelta(value: int | float | datetime.timedelta | None) -> datetime.timedelta | None
```

Normalize a timeout value to a timedelta.

**Args:**

* `value`: Timeout value as int/float (seconds), timedelta, or None

**Returns:**

* timedelta if value provided, None otherwise

### `normalize_timeout_to_seconds` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/timeout.py#L28](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/timeout.py#L28)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
normalize_timeout_to_seconds(value: int | float | datetime.timedelta | None) -> float | None
```

Normalize a timeout value to seconds (float).

**Args:**

* `value`: Timeout value as int/float (seconds), timedelta, or None.
  Zero values are treated as "disabled" and return None.

**Returns:**

* float seconds if value provided and non-zero, None otherwise


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.