> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Calling Tools

> Execute server-side tools and handle structured results.

New in version `2.0.0`

Use this when you need to execute server-side functions and process their results.

Tools are executable functions exposed by MCP servers. The client's `list_tools()` method discovers what a server offers, and `call_tool()` executes a tool by name with arguments and returns structured results.

## Discovering Tools

`list_tools()` returns every tool the server advertises as a list of `mcp_types.Tool` objects, each carrying the tool's name, description, and JSON `input_schema`. It follows pagination automatically, so the result is the complete catalog.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
async with client:
    tools = await client.list_tools()
    for tool in tools:
        print(tool.name, tool.description)
        print(tool.input_schema)
```

Servers can change their catalog while the connection is open and notify the client with a `notifications/tools/list_changed` notification; a fresh `list_tools()` call reflects the new set. See [Notifications](https://gofastmcp.com/docs/clients/notifications.md) for reacting to that notification.

For page-by-page control over large catalogs, `list_tools_mcp()` returns one raw `ListToolsResult` at a time and accepts the `cursor` from the previous page's `next_cursor`.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
async with client:
    page = await client.list_tools_mcp()
    while page.next_cursor is not None:
        page = await client.list_tools_mcp(cursor=page.next_cursor)
```

Both methods accept a `cache_mode` argument when the client was built with a [response cache](https://gofastmcp.com/docs/clients/client.md#response-caching).

## Basic Execution

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
async with client:
    result = await client.call_tool("add", {"a": 5, "b": 3})
    # result -> CallToolResult with structured and unstructured data

    # Access structured data (automatically deserialized)
    print(result.data)  # 8

    # Access traditional content blocks
    print(result.content[0].text)  # "8"
```

Arguments are passed as a dictionary. For multi-server clients, tool names are automatically prefixed with the server name (e.g., `weather_get_forecast` for a tool named `get_forecast` on the `weather` server).

## Execution Options

The `call_tool()` method supports timeout control and progress monitoring:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
async with client:
    # With timeout (aborts if execution takes longer than 2 seconds)
    result = await client.call_tool(
        "long_running_task",
        {"param": "value"},
        timeout=2.0
    )

    # With progress handler
    result = await client.call_tool(
        "long_running_task",
        {"param": "value"},
        progress_handler=my_progress_handler
    )
```

## Structured Results

New in version `2.10.0`

Tool execution returns a `CallToolResult` object. The `.data` property provides fully hydrated Python objects including complex types like datetimes and UUIDs, reconstructed from the server's output schema.

Pydantic models can combine named fields with typed additional properties. The client retains those additional fields in `.data` and hydrates their values using the advertised schema, including inside nested objects and lists.

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from datetime import datetime
from uuid import UUID

async with client:
    result = await client.call_tool("get_weather", {"city": "London"})

    # FastMCP reconstructs complete Python objects
    weather = result.data
    print(f"Temperature: {weather.temperature}C at {weather.timestamp}")

    # Complex types are properly deserialized
    assert isinstance(weather.timestamp, datetime)
    assert isinstance(weather.station_id, UUID)

    # Raw structured JSON is also available
    print(f"Raw JSON: {result.structured_content}")
```

> [card] CallToolResult Properties
>
> **.data** `Any`
>
> Fully hydrated Python objects with complex type support (datetimes, UUIDs, custom classes). FastMCP exclusive.
>
> **.content** `list[mcp_types.ContentBlock]`
>
> Standard MCP content blocks (`TextContent`, `ImageContent`, `AudioContent`, etc.).
>
> **.structured\_content** `dict[str, Any] | None`
>
> Standard MCP structured JSON data as sent by the server.
>
> **.is\_error** `bool`
>
> Boolean indicating if the tool execution failed.
>
> **.meta** `dict[str, Any] | None`
>
> The `_meta` object the server attached to the result, if any.

Structured content without an output schema is returned as a dictionary in `.data`, including an empty object (`{}`). When structured content is absent or deserialization fails, `.data` is `None`. Fall back to content blocks in that case:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
async with client:
    result = await client.call_tool("legacy_tool", {"param": "value"})

    if result.data is not None:
        print(f"Structured: {result.data}")
    else:
        for content in result.content:
            if hasattr(content, 'text'):
                print(f"Text result: {content.text}")
```

> [!TIP]
>
> FastMCP servers automatically wrap primitive results (like `int`, `str`, `bool`) in a `{"result": value}` structure. FastMCP clients automatically unwrap this, so you get the original value in `.data`.

## Error Handling

By default, `call_tool()` raises a `ToolError` if the tool execution fails:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from fastmcp.exceptions import ToolError

async with client:
    try:
        result = await client.call_tool("potentially_failing_tool", {"param": "value"})
        print("Tool succeeded:", result.data)
    except ToolError as e:
        print(f"Tool failed: {e}")
```

To handle errors manually instead of catching exceptions, disable automatic error raising:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
async with client:
    result = await client.call_tool(
        "potentially_failing_tool",
        {"param": "value"},
        raise_on_error=False
    )

    if result.is_error:
        print(f"Tool failed: {result.content[0].text}")
    else:
        print(f"Tool succeeded: {result.data}")
```

## Sending Metadata

New in version `2.13.1`

The `meta` parameter sends ancillary information alongside tool calls for observability, debugging, or client identification:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
async with client:
    result = await client.call_tool(
        name="send_email",
        arguments={
            "to": "user@example.com",
            "subject": "Hello",
            "body": "Welcome!"
        },
        meta={
            "trace_id": "abc-123",
            "request_source": "mobile_app"
        }
    )
```

See [Client Metadata](https://gofastmcp.com/docs/servers/context.md#client-metadata) to learn how servers access this data.

## Version Selection

New in version `3.0.0`

When a server exposes multiple versions of a tool, `call_tool()` runs the highest by default. Pass `version` to call a specific one:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
async with client:
    result = await client.call_tool("calculate", {"x": 1, "y": 2}, version="1.0")
```

See [Version Discovery](https://gofastmcp.com/docs/servers/versioning.md#version-discovery) for how to discover available versions.

## Raw Protocol Access

For complete control, use `call_tool_mcp()` which returns the raw MCP protocol object:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
async with client:
    result = await client.call_tool_mcp("my_tool", {"param": "value"})
    # result -> mcp_types.CallToolResult

    if result.is_error:
        print(f"Tool failed: {result.content}")
    else:
        print(f"Tool succeeded: {result.content}")
        # Note: No automatic deserialization with call_tool_mcp()
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.