> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# function_prompt

# `fastmcp.prompts.function_prompt`

Standalone @prompt decorator for FastMCP.

## Functions

### `prompt` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/prompts/function\_prompt.py#L407](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/prompts/function_prompt.py#L407)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
prompt(name_or_fn: str | Callable[..., Any] | None = None) -> Any
```

Standalone decorator to mark a function as an MCP prompt.

Returns the original function with metadata attached. Register with a server
using mcp.add\_prompt().

## Classes

### `DecoratedPrompt` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/prompts/function\_prompt.py#L44](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/prompts/function_prompt.py#L44)</sup>

Protocol for functions decorated with @prompt.

### `PromptMeta` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/prompts/function\_prompt.py#L53](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/prompts/function_prompt.py#L53)</sup>

Metadata attached to functions by the @prompt decorator.

### `FunctionPrompt` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/prompts/function\_prompt.py#L68](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/prompts/function_prompt.py#L68)</sup>

A prompt that is a function.

**Methods:**

#### `from_function` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/prompts/function\_prompt.py#L74](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/prompts/function_prompt.py#L74)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from_function(cls, fn: Callable[..., Any]) -> FunctionPrompt
```

Create a Prompt from a function.

**Args:**

* `fn`: The function to wrap
* `metadata`: PromptMeta object with all configuration. If provided,
  individual parameters must not be passed.
* `name, title, etc.`: Individual parameters for backwards compatibility.
  Cannot be used together with metadata parameter.

The function can return:

* str: wrapped as single user Message
* list\[Message | str]: converted to list\[Message]
* PromptResult: used directly

#### `render` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/prompts/function\_prompt.py#L322](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/prompts/function_prompt.py#L322)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
render(self, arguments: dict[str, Any] | None = None) -> PromptResult
```

Render the prompt with arguments.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.