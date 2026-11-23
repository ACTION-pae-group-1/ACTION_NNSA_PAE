> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# LLM Sampling

> Handle server-initiated LLM sampling requests.

New in version `2.0.0`

MCP servers can request LLM completions from clients. The client handles these requests through a sampling handler callback.

## Sampling Handler

Provide a `sampling_handler` function when creating the client:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import Client
from fastmcp.client.sampling import (
    SamplingMessage,
    SamplingParams,
    RequestContext,
)

async def sampling_handler(
    messages: list[SamplingMessage],
    params: SamplingParams,
    context: RequestContext
) -> str:
    # Your LLM integration logic here
    # Extract text from messages and generate a response
    return "Generated response based on the messages"

client = Client(
    "my_mcp_server.py",
    sampling_handler=sampling_handler,
)
```

### Handler Parameters

The sampling handler receives three parameters:

> [card] Sampling Handler Parameters
>
> **SamplingMessage** `Sampling Message Object`
>
> **attributes**
>
> **role** `Literal["user", "assistant"]`
>
> The role of the message.
>
> **content** `TextContent | ImageContent | AudioContent`
>
> The content of the message.
>
> TextContent is most common, and has a `.text` attribute.
>
> **SamplingParams** `Sampling Parameters Object`
>
> **attributes**
>
> **messages** `list[SamplingMessage]`
>
> The messages to sample from
>
> **modelPreferences** `ModelPreferences | None`
>
> The server's preferences for which model to select. The client MAY ignore
> these preferences.
>
> **attributes**
>
> **hints** `list[ModelHint] | None`
>
> The hints to use for model selection.
>
> **costPriority** `float | None`
>
> The cost priority for model selection.
>
> **speedPriority** `float | None`
>
> The speed priority for model selection.
>
> **intelligencePriority** `float | None`
>
> The intelligence priority for model selection.
>
> **systemPrompt** `str | None`
>
> An optional system prompt the server wants to use for sampling.
>
> **includeContext** `IncludeContext | None`
>
> A request to include context from one or more MCP servers (including the caller), to
> be attached to the prompt.
>
> **temperature** `float | None`
>
> The sampling temperature.
>
> **maxTokens** `int`
>
> The maximum number of tokens to sample.
>
> **stopSequences** `list[str] | None`
>
> The stop sequences to use for sampling.
>
> **metadata** `dict[str, Any] | None`
>
> Optional metadata to pass through to the LLM provider.
>
> **tools** `list[Tool] | None`
>
> Optional list of tools the LLM can use during sampling. See [Using the OpenAI Handler](#using-the-openai-handler).
>
> **toolChoice** `ToolChoice | None`
>
> Optional control over tool usage behavior (`auto`, `required`, or `none`).
>
> **RequestContext** `Request Context Object`
>
> **attributes**
>
> **request\_id** `RequestId`
>
> Unique identifier for the MCP request

## Basic Example

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import Client
from fastmcp.client.sampling import SamplingMessage, SamplingParams, RequestContext

async def basic_sampling_handler(
    messages: list[SamplingMessage],
    params: SamplingParams,
    context: RequestContext
) -> str:
    # Extract message content
    conversation = []
    for message in messages:
        content = message.content.text if hasattr(message.content, 'text') else str(message.content)
        conversation.append(f"{message.role}: {content}")

    # Use the system prompt if provided
    system_prompt = params.systemPrompt or "You are a helpful assistant."

    # Here you would integrate with your preferred LLM service
    # This is just a placeholder response
    return f"Response based on conversation: {' | '.join(conversation)}"

client = Client(
    "my_mcp_server.py",
    sampling_handler=basic_sampling_handler
)
```

> [!NOTE]
>
> If the client doesn't provide a sampling handler, servers can optionally configure a fallback handler. See [Server Sampling](https://gofastmcp.com/docs/v2/servers/sampling.md#sampling-fallback-handler) for details.

## Sampling Capabilities

When you provide a `sampling_handler`, FastMCP automatically advertises full sampling capabilities to the server, including tool support. To disable tool support (for simpler handlers that don't support tools), pass `sampling_capabilities` explicitly:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from mcp.types import SamplingCapability

client = Client(
    "my_mcp_server.py",
    sampling_handler=basic_handler,
    sampling_capabilities=SamplingCapability(),  # No tool support
)
```

## Built-in Handlers

FastMCP provides built-in sampling handlers for OpenAI and Anthropic APIs. These handlers support the full sampling API including tool use, handling message conversion and response formatting automatically.

### OpenAI Handler

New in version `2.11.0`

The OpenAI handler works with OpenAI's API and any OpenAI-compatible provider:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import Client
from fastmcp.client.sampling.handlers.openai import OpenAISamplingHandler

client = Client(
    "my_mcp_server.py",
    sampling_handler=OpenAISamplingHandler(default_model="gpt-4o"),
)
```

For OpenAI-compatible APIs (like local models), pass a custom client:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from openai import AsyncOpenAI

client = Client(
    "my_mcp_server.py",
    sampling_handler=OpenAISamplingHandler(
        default_model="llama-3.1-70b",
        client=AsyncOpenAI(base_url="http://localhost:8000/v1"),
    ),
)
```

> [!NOTE]
>
> Install the OpenAI handler with `pip install 'fastmcp[openai]'`.

### Anthropic Handler

New in version `2.14.1`

The Anthropic handler uses Claude models via the Anthropic API:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import Client
from fastmcp.client.sampling.handlers.anthropic import AnthropicSamplingHandler

client = Client(
    "my_mcp_server.py",
    sampling_handler=AnthropicSamplingHandler(default_model="claude-sonnet-4-5"),
)
```

You can pass a custom client for advanced configuration:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from anthropic import AsyncAnthropic

client = Client(
    "my_mcp_server.py",
    sampling_handler=AnthropicSamplingHandler(
        default_model="claude-sonnet-4-5",
        client=AsyncAnthropic(),  # Uses ANTHROPIC_API_KEY env var
    ),
)
```

> [!NOTE]
>
> Install the Anthropic handler with `pip install 'fastmcp[anthropic]'`.

### Tool Execution

Tool execution happens on the server side. The client's role is to pass tools to the LLM and return the LLM's response (which may include tool use requests). The server then executes the tools and may send follow-up sampling requests with tool results.

> [!TIP]
>
> To implement a custom sampling handler, see the [handler source code](https://github.com/PrefectHQ/fastmcp/tree/main/fastmcp_slim/fastmcp/client/sampling/handlers) as a reference.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.