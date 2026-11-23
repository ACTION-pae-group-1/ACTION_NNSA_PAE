> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# version_check

# `fastmcp.utilities.version_check`

Version checking utilities for FastMCP.

## Functions

### `get_latest_version` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/version\_check.py#L106](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/version_check.py#L106)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_latest_version(include_prereleases: bool = False) -> str | None
```

Get the latest version of FastMCP from PyPI, using cache when available.

**Args:**

* `include_prereleases`: If True, include pre-release versions.

**Returns:**

* The latest version string, or None if unavailable.

### `check_for_newer_version` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/version\_check.py#L132](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/version_check.py#L132)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
check_for_newer_version() -> str | None
```

Check if a newer version of FastMCP is available.

**Returns:**

* The latest version string if newer than current, None otherwise.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.