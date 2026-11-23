> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# base

# `fastmcp.prompts.base`

Base classes for FastMCP prompts.

## Classes

### `Message` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/prompts/base.py#L38](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/prompts/base.py#L38)</sup>

Wrapper for prompt message with auto-serialization.

Accepts any content - strings pass through, other types
(dict, list, BaseModel) are JSON-serialized to text.

**Methods:**

#### `to_mcp_prompt_message` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/prompts/base.py#L93](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/prompts/base.py#L93)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
to_mcp_prompt_message(self) -> PromptMessage
```

Convert to MCP PromptMessage.

### `PromptArgument` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/prompts/base.py#L98](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/prompts/base.py#L98)</sup>

An argument that can be passed to a prompt.

### `PromptResult` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/prompts/base.py#L110](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/prompts/base.py#L110)</sup>

Canonical result type for prompt rendering.

Provides explicit control over prompt responses: multiple messages,
roles, and metadata at both the message and result level.

**Methods:**

#### `to_mcp_prompt_result` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/prompts/base.py#L182](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/prompts/base.py#L182)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
to_mcp_prompt_result(self) -> GetPromptResult
```

Convert to MCP GetPromptResult.

### `InputRequiredPromptResult` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/prompts/base.py#L192](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/prompts/base.py#L192)</sup>

The full result of a single multi-round-trip prompt leg (SEP-2322).

`InputRequiredResult` is a result type, not a `tools/call` feature: any
request may resolve to one. When a prompt returns an `InputRequiredResult`
from its body to ask the client for input, that ask is the legitimate
result of this `prompts/get` — so FastMCP wraps it in this `PromptResult`
subclass, mirroring `InputRequiredToolResult`, and it flows through the
middleware chain as an ordinary return value.

Invariant: the wrapped `InputRequiredResult` is never rendered as prompt
messages. `messages` is always empty; the wire handler (`_on_get_prompt`)
reads `.input_required` and returns it to the runner.

### `Prompt` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/prompts/base.py#L224](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/prompts/base.py#L224)</sup>

A prompt template that can be rendered with parameters.

**Methods:**

#### `to_mcp_prompt` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/prompts/base.py#L236](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/prompts/base.py#L236)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
to_mcp_prompt(self, **overrides: Any) -> SDKPrompt
```

Convert the prompt to an MCP prompt.

#### `from_function` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/prompts/base.py#L262](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/prompts/base.py#L262)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from_function(cls, fn: Callable[..., Any]) -> FunctionPrompt
```

Create a Prompt from a function.

The function can return:

* str: wrapped as single user Message
* list\[Message | str]: converted to list\[Message]
* PromptResult: used directly

#### `render` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/prompts/base.py#L296](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/prompts/base.py#L296)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
render(self, arguments: dict[str, Any] | None = None) -> str | list[Message | str] | PromptResult
```

Render the prompt with arguments.

Subclasses must implement this method. Return one of:

* str: Wrapped as single user Message
* list\[Message | str]: Converted to list\[Message]
* PromptResult: Used directly

#### `convert_result` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/prompts/base.py#L309](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/prompts/base.py#L309)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
convert_result(self, raw_value: Any) -> PromptResult
```

Convert a raw return value to PromptResult.

**Raises:**

* `TypeError`: for unsupported types

#### `get_span_attributes` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/prompts/base.py#L372](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/prompts/base.py#L372)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_span_attributes(self) -> dict[str, Any]
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.