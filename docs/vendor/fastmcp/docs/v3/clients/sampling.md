> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# LLM Sampling

> Handle server-initiated LLM completion requests.

New in version `2.0.0`

Use this when you need to respond to server requests for LLM completions.

MCP servers can request LLM completions from clients during tool execution. This enables servers to delegate AI reasoning to the client, which controls which LLM is used and how requests are made.

## Handler Template

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import Client
from fastmcp.client.sampling import SamplingMessage, SamplingParams, RequestContext

async def sampling_handler(
    messages: list[SamplingMessage],
    params: SamplingParams,
    context: RequestContext
) -> str:
    """
    Handle server requests for LLM completions.

    Args:
        messages: Conversation messages to send to the LLM
        params: Sampling parameters (temperature, max_tokens, etc.)
        context: Request context with metadata

    Returns:
        Generated text response from your LLM
    """
    # Extract message content
    conversation = []
    for message in messages:
        content = message.content.text if hasattr(message.content, 'text') else str(message.content)
        conversation.append(f"{message.role}: {content}")

    # Use the system prompt if provided
    system_prompt = params.systemPrompt or "You are a helpful assistant."

    # Integrate with your LLM service here
    return "Generated response based on the messages"

client = Client(
    "my_mcp_server.py",
    sampling_handler=sampling_handler,
)
```

## Handler Parameters

> [card] SamplingMessage
>
> **role** `Literal["user", "assistant"]`
>
> The role of the message
>
> **content** `TextContent | ImageContent | AudioContent`
>
> The content of the message. TextContent has a `.text` attribute.

> [card] SamplingParams
>
> **systemPrompt** `str | None`
>
> Optional system prompt the server wants to use
>
> **modelPreferences** `ModelPreferences | None`
>
> Server preferences for model selection (hints, cost/speed/intelligence priorities)
>
> **temperature** `float | None`
>
> Sampling temperature
>
> **maxTokens** `int`
>
> Maximum tokens to generate
>
> **stopSequences** `list[str] | None`
>
> Stop sequences for sampling
>
> **tools** `list[Tool] | None`
>
> Tools the LLM can use during sampling
>
> **toolChoice** `ToolChoice | None`
>
> Tool usage behavior (`auto`, `required`, or `none`)

## Built-in Handlers

FastMCP provides built-in handlers for OpenAI, Anthropic, and Google Gemini APIs that support the full sampling API including tool use.

### OpenAI Handler

New in version `2.11.0`

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import Client
from fastmcp.client.sampling.handlers.openai import OpenAISamplingHandler

client = Client(
    "my_mcp_server.py",
    sampling_handler=OpenAISamplingHandler(default_model="gpt-4o"),
)
```

For OpenAI-compatible APIs (like local models):

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
> Install the OpenAI handler with `pip install fastmcp[openai]`.

### Anthropic Handler

New in version `2.14.1`

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import Client
from fastmcp.client.sampling.handlers.anthropic import AnthropicSamplingHandler

client = Client(
    "my_mcp_server.py",
    sampling_handler=AnthropicSamplingHandler(default_model="claude-sonnet-4-5"),
)
```

> [!NOTE]
>
> Install the Anthropic handler with `pip install fastmcp[anthropic]`.

### Google Gemini Handler

New in version `3.1.0`

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import Client
from fastmcp.client.sampling.handlers.google_genai import GoogleGenaiSamplingHandler

client = Client(
    "my_mcp_server.py",
    sampling_handler=GoogleGenaiSamplingHandler(default_model="gemini-2.0-flash"),
)
```

> [!NOTE]
>
> Install the Google Gemini handler with `pip install fastmcp[gemini]`.

## Sampling Capabilities

When you provide a `sampling_handler`, FastMCP automatically advertises full sampling capabilities to the server, including tool support. To disable tool support for simpler handlers:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from mcp.types import SamplingCapability

client = Client(
    "my_mcp_server.py",
    sampling_handler=basic_handler,
    sampling_capabilities=SamplingCapability(),  # No tool support
)
```

## Tool Execution

Tool execution happens on the server side. The client's role is to pass tools to the LLM and return the LLM's response (which may include tool use requests). The server then executes the tools and may send follow-up sampling requests with tool results.

> [!TIP]
>
> To implement a custom sampling handler, see the [handler source code](https://github.com/PrefectHQ/fastmcp/tree/main/fastmcp_slim/fastmcp/client/sampling/handlers) as a reference.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.