> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# tool_transform

# `fastmcp.server.transforms.tool_transform`

Transform for applying tool transformations.

## Classes

### `ToolTransform` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/tool\_transform.py#L16](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/tool_transform.py#L16)</sup>

Applies tool transformations to modify tool schemas.

Wraps ToolTransformConfig to apply argument renames, schema changes,
hidden arguments, and other transformations at the transform level.

**Methods:**

#### `list_tools` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/tool\_transform.py#L64](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/tool_transform.py#L64)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
list_tools(self, tools: Sequence[Tool]) -> Sequence[Tool]
```

Apply transforms to matching tools.

#### `get_tool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/tool\_transform.py#L75](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/tool_transform.py#L75)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_tool(self, name: str, call_next: GetToolNext) -> Tool | None
```

Get tool by transformed name.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.