> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# User Elicitation

> Handle server requests for structured user input.

New in version `2.10.0`

Use this when you need to respond to server requests for user input during tool execution.

Elicitation allows MCP servers to request structured input from users during operations. Instead of requiring all inputs upfront, servers can interactively ask for missing parameters, request clarification, or gather additional context.

> [!NOTE]
>
> **These sections show the server-initiated flow, which the handshake-era protocol uses.** On `2026-07-28` the server asks by returning a request instead — see [input-required rounds](#input-required-rounds). One `elicitation_handler` serves both, so the examples below pin `mode="legacy"` only to exercise the pushed form.

## Handler Template

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import Client
from fastmcp.client.elicitation import ElicitResult, ElicitRequestParams, RequestContext

async def elicitation_handler(
    message: str,
    response_type: type | None,
    params: ElicitRequestParams,
    context: RequestContext
) -> ElicitResult | object:
    """
    Handle server requests for user input.

    Args:
        message: The prompt to display to the user
        response_type: Python dataclass type for form responses (None for URL requests or empty schemas)
        params: Original MCP elicitation parameters
        context: Request context with metadata

    Returns:
        - Data directly (implicitly accepts the elicitation)
        - ElicitResult for explicit control over the action
    """
    # Present the message and collect input
    user_input = input(f"{message}: ")

    if not user_input:
        return ElicitResult(action="decline")

    # URL requests and empty-object schemas have no response type to construct,
    # so accepting is the whole response.
    if response_type is None:
        return ElicitResult(action="accept")

    # Create response using the provided dataclass type
    return response_type(value=user_input)

client = Client(
    "my_mcp_server.py",
    mode="legacy",
    elicitation_handler=elicitation_handler,
)
```

## How It Works

When a server needs user input, it sends an elicitation request with a message prompt. Form elicitation requests include a JSON schema describing the expected response structure, and FastMCP automatically converts that schema into a Python dataclass type. URL elicitation requests and empty-object schemas use `response_type=None`.

The handler receives four parameters:

> **Handler Parameters**
>
> **message** `str`
>
> The prompt message to display to the user
>
> **response\_type** `type | None`
>
> A Python dataclass type that FastMCP created from a form request's JSON schema. Use this to construct your response with proper typing. For URL requests or empty-object schemas, this will be `None`.
>
> **params** `ElicitRequestParams`
>
> The original MCP elicitation parameters. Form requests carry the raw JSON schema on `params.requested_schema`; URL requests carry `params.url` instead and have no schema.
>
> **context** `RequestContext`
>
> Request context containing metadata about the elicitation request

## Response Actions

You can return data directly, which implicitly accepts the elicitation:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
async def elicitation_handler(message, response_type, params, context):
    user_input = input(f"{message}: ")
    return response_type(value=user_input)  # Implicit accept
```

Or return an `ElicitResult` for explicit control over the action:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp.client.elicitation import ElicitResult

async def elicitation_handler(message, response_type, params, context):
    user_input = input(f"{message}: ")

    if not user_input:
        return ElicitResult(action="decline")  # User declined

    if user_input == "cancel":
        return ElicitResult(action="cancel")   # Cancel entire operation

    return ElicitResult(
        action="accept",
        content=response_type(value=user_input)
    )
```

**Action types:**

* **`accept`**: User provided valid input. Include the data in the `content` field.
* **`decline`**: User chose not to provide the requested information. Omit `content`.
* **`cancel`**: User cancelled the entire operation. Omit `content`.

## Example

A file management tool might ask which directory to create:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp import Client
from fastmcp.client.elicitation import ElicitResult

async def elicitation_handler(message, response_type, params, context):
    print(f"Server asks: {message}")

    user_response = input("Your response: ")

    if not user_response:
        return ElicitResult(action="decline")

    # Use the response_type dataclass to create a properly structured response
    return response_type(value=user_response)

client = Client(
    "my_mcp_server.py",
    mode="legacy",
    elicitation_handler=elicitation_handler
)
```

## Input-required rounds

New in version `4.0.0`

On protocol version `2026-07-28` and later, a server can ask for input before it returns a final result. Nothing is held open: the tool *returns* a description of what it needs, which completes that round as an ordinary response, and the client answers by issuing a **new** `call_tool`, `get_prompt`, or `read_resource` request carrying the answer. `fastmcp.Client` drives that loop for you — it fulfils each round's requests using the callbacks you already configured (your `elicitation_handler`, `sampling_handler`, and roots) and repeats until the call reaches a terminal result. No extra wiring is needed beyond the handlers described above.

The `input_required_max_rounds` parameter caps how many rounds the client will answer before giving up, guarding against a server that never terminates. It defaults to `10`.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
client = Client(
    "https://example.com/mcp",
    mode="auto",
    elicitation_handler=elicitation_handler,
    input_required_max_rounds=5,
)
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.