> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# function_prompt

# `fastmcp.prompts.function_prompt`

Standalone @prompt decorator for FastMCP.

## Functions

### `prompt` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/prompts/function\_prompt.py#L403](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/prompts/function_prompt.py#L403)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
prompt(name_or_fn: str | Callable[..., Any] | None = None) -> Any
```

Standalone decorator to mark a function as an MCP prompt.

Returns the original function with metadata attached. Register with a server
using mcp.add\_prompt().

## Classes

### `DecoratedPrompt` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/prompts/function\_prompt.py#L43](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/prompts/function_prompt.py#L43)</sup>

Protocol for functions decorated with @prompt.

### `PromptMeta` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/prompts/function\_prompt.py#L52](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/prompts/function_prompt.py#L52)</sup>

Metadata attached to functions by the @prompt decorator.

### `FunctionPrompt` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/prompts/function\_prompt.py#L67](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/prompts/function_prompt.py#L67)</sup>

A prompt that is a function.

**Methods:**

#### `from_function` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/prompts/function\_prompt.py#L73](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/prompts/function_prompt.py#L73)</sup>

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

#### `render` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/prompts/function\_prompt.py#L321](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/prompts/function_prompt.py#L321)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
render(self, arguments: dict[str, Any] | None = None) -> PromptResult
```

Render the prompt with arguments.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.