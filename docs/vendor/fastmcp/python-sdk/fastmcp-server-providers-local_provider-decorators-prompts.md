> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# prompts

# `fastmcp.server.providers.local_provider.decorators.prompts`

Prompt decorator mixin for LocalProvider.

This module provides the PromptDecoratorMixin class that adds prompt
registration functionality to LocalProvider.

## Classes

### `PromptDecoratorMixin` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/local\_provider/decorators/prompts.py#L27](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/local_provider/decorators/prompts.py#L27)</sup>

Mixin class providing prompt decorator functionality for LocalProvider.

This mixin contains all methods related to:

* Prompt registration via add\_prompt()
* Prompt decorator (@provider.prompt)

**Methods:**

#### `add_prompt` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/local\_provider/decorators/prompts.py#L35](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/local_provider/decorators/prompts.py#L35)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
add_prompt(self: LocalProvider, prompt: Prompt | Callable[..., Any]) -> Prompt
```

Add a prompt to this provider's storage.

Accepts either a Prompt object or a decorated function with **fastmcp** metadata.

#### `prompt` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/local\_provider/decorators/prompts.py#L73](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/local_provider/decorators/prompts.py#L73)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
prompt(self: LocalProvider, name_or_fn: F) -> F
```

#### `prompt` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/local\_provider/decorators/prompts.py#L89](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/local_provider/decorators/prompts.py#L89)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
prompt(self: LocalProvider, name_or_fn: str | None = None) -> Callable[[F], F]
```

#### `prompt` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/local\_provider/decorators/prompts.py#L104](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/local_provider/decorators/prompts.py#L104)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
prompt(self: LocalProvider, name_or_fn: str | AnyFunction | None = None) -> Callable[[AnyFunction], FunctionPrompt] | FunctionPrompt | partial[Callable[[AnyFunction], FunctionPrompt] | FunctionPrompt]
```

Decorator to register a prompt.

This decorator supports multiple calling patterns:

* @provider.prompt (without parentheses)
* @provider.prompt() (with empty parentheses)
* @provider.prompt("custom\_name") (with name as first argument)
* @provider.prompt(name="custom\_name") (with name as keyword argument)
* provider.prompt(function, name="custom\_name") (direct function call)

**Args:**

* `name_or_fn`: Either a function (when used as @prompt), a string name, or None
* `name`: Optional name for the prompt (keyword-only, alternative to name\_or\_fn)
* `title`: Optional title for the prompt
* `description`: Optional description of what the prompt does
* `icons`: Optional icons for the prompt
* `tags`: Optional set of tags for categorizing the prompt
* `enabled`: Whether the prompt is enabled (default True). If False, adds to blocklist.
* `meta`: Optional meta information about the prompt
* `auth`: Optional authorization checks for the prompt

**Returns:**

* The registered FunctionPrompt or a decorator function.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.