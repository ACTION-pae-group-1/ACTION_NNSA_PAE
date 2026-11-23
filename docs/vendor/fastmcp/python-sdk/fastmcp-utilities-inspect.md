> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# inspect

# `fastmcp.utilities.inspect`

Utilities for inspecting FastMCP instances.

## Functions

### `inspect_fastmcp_v2` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/inspect.py#L100](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/inspect.py#L100)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
inspect_fastmcp_v2(mcp: FastMCP[Any]) -> FastMCPInfo
```

Extract information from a FastMCP v2.x instance.

**Args:**

* `mcp`: The FastMCP v2.x instance to inspect

**Returns:**

* FastMCPInfo dataclass containing the extracted information

### `inspect_fastmcp_v1` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/inspect.py#L251](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/inspect.py#L251)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
inspect_fastmcp_v1(mcp: SDKServer) -> FastMCPInfo
```

Extract information from a FastMCP v1.x instance using a Client.

**Args:**

* `mcp`: The FastMCP v1.x instance to inspect

**Returns:**

* FastMCPInfo dataclass containing the extracted information

### `inspect_fastmcp` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/inspect.py#L413](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/inspect.py#L413)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
inspect_fastmcp(mcp: FastMCP[Any] | SDKServer) -> FastMCPInfo
```

Extract information from a FastMCP instance into a dataclass.

This function automatically detects whether the instance is FastMCP v1.x or v2.x
and uses the appropriate extraction method.

**Args:**

* `mcp`: The FastMCP instance to inspect (v1.x or v2.x)

**Returns:**

* FastMCPInfo dataclass containing the extracted information

### `format_fastmcp_info` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/inspect.py#L438](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/inspect.py#L438)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
format_fastmcp_info(info: FastMCPInfo) -> bytes
```

Format FastMCPInfo as FastMCP-specific JSON.

This includes FastMCP-specific fields like tags, enabled, annotations, etc.

### `format_mcp_info` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/inspect.py#L467](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/inspect.py#L467)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
format_mcp_info(mcp: FastMCP[Any] | SDKServer) -> bytes
```

Format server info as standard MCP protocol JSON.

Uses Client to get the standard MCP protocol format with camelCase fields.
Includes version metadata at the top level.

### `format_info` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/inspect.py#L503](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/inspect.py#L503)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
format_info(mcp: FastMCP[Any] | SDKServer, format: InspectFormat | Literal['fastmcp', 'mcp'], info: FastMCPInfo | None = None) -> bytes
```

Format server information according to the specified format.

**Args:**

* `mcp`: The FastMCP instance
* `format`: Output format ("fastmcp" or "mcp")
* `info`: Pre-extracted FastMCPInfo (optional, will be extracted if not provided)

**Returns:**

* JSON bytes in the requested format

## Classes

### `ToolInfo` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/inspect.py#L19](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/inspect.py#L19)</sup>

Information about a tool.

### `PromptInfo` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/inspect.py#L35](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/inspect.py#L35)</sup>

Information about a prompt.

### `ResourceInfo` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/inspect.py#L49](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/inspect.py#L49)</sup>

Information about a resource.

### `TemplateInfo` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/inspect.py#L65](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/inspect.py#L65)</sup>

Information about a resource template.

### `FastMCPInfo` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/inspect.py#L82](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/inspect.py#L82)</sup>

Information extracted from a FastMCP instance.

### `InspectFormat` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/inspect.py#L431](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/inspect.py#L431)</sup>

Output format for inspect command.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.