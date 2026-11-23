> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# base

# `fastmcp.utilities.mcp_server_config.v1.sources.base`

## Classes

### `Source` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/mcp\_server\_config/v1/sources/base.py#L7](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/mcp_server_config/v1/sources/base.py#L7)</sup>

Abstract base class for all source types.

**Methods:**

#### `prepare` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/mcp\_server\_config/v1/sources/base.py#L12](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/mcp_server_config/v1/sources/base.py#L12)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
prepare(self) -> None
```

Prepare the source (download, clone, install, etc).

For sources that need preparation (e.g., git clone, download),
this method performs that preparation. For sources that don't
need preparation (e.g., local files), this is a no-op.

#### `load_server` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/mcp\_server\_config/v1/sources/base.py#L22](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/mcp_server_config/v1/sources/base.py#L22)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
load_server(self) -> Any
```

Load and return the FastMCP server instance.

Must be called after prepare() if the source requires preparation.
All information needed to load the server should be available
as attributes on the source instance.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.