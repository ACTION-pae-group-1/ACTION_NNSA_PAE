> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# function_parsing

# `fastmcp.tools.function_parsing`

Function introspection and schema generation for FastMCP tools.

## Classes

### `ParsedFunction` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/tools/function\_parsing.py#L268](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/tools/function_parsing.py#L268)</sup>

**Methods:**

#### `from_function` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/tools/function\_parsing.py#L277](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/tools/function_parsing.py#L277)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from_function(cls, fn: Callable[..., Any], validate: bool = True, wrap_non_object_output_schema: bool = True) -> ParsedFunction
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.