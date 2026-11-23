> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# filesystem

# `fastmcp.utilities.mcp_server_config.v1.sources.filesystem`

## Classes

### `FileSystemSource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/mcp\_server\_config/v1/sources/filesystem.py#L16](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/mcp_server_config/v1/sources/filesystem.py#L16)</sup>

Source for local Python files.

**Methods:**

#### `parse_path_with_object` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/mcp\_server\_config/v1/sources/filesystem.py#L29](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/mcp_server_config/v1/sources/filesystem.py#L29)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
parse_path_with_object(cls, v: str) -> str
```

Parse path:object syntax and extract the object name.

This validator runs before the model is created, allowing us to
handle the "file.py:object" syntax at the model boundary.

#### `load_server` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/mcp\_server\_config/v1/sources/filesystem.py#L64](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/mcp_server_config/v1/sources/filesystem.py#L64)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
load_server(self) -> Any
```

Load server from filesystem.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.