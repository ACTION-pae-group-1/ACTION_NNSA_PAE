> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# context

# `fastmcp.server.context`

## Functions

### `set_transport` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L97](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L97)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
set_transport(transport: TransportType) -> Token[TransportType | None]
```

Set the current transport type. Returns token for reset.

### `reset_transport` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L104](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L104)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
reset_transport(token: Token[TransportType | None]) -> None
```

Reset transport to previous value.

### `set_context` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L134](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L134)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
set_context(context: Context) -> Generator[Context, None, None]
```

## Classes

### `LogData` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L110](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L110)</sup>

Data object for passing log arguments to client-side handlers.

This provides an interface to match the Python standard library logging,
for compatibility with structured logging.

### `Context` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L143](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L143)</sup>

Context object providing access to MCP capabilities.

This provides a cleaner interface to MCP's RequestContext functionality.
It gets injected into tool and resource functions that request it via type hints.

To use context in a tool function, add a parameter with the Context type annotation:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
@server.tool
async def my_tool(x: int, ctx: Context) -> str:
    # Log messages to the client
    await ctx.info(f"Processing {x}")
    await ctx.debug("Debug info")
    await ctx.warning("Warning message")
    await ctx.error("Error message")

    # Report progress
    await ctx.report_progress(50, 100, "Processing")

    # Access resources
    data = await ctx.read_resource("resource://data")

    # Get request info
    request_id = ctx.request_id
    client_id = ctx.client_id

    # Manage state across the session (persists across requests)
    await ctx.set_state("key", "value")
    value = await ctx.get_state("key")

    # Store non-serializable values for the current request only
    await ctx.set_state("client", http_client, serializable=False)

    return str(x)
```

State Management:
Context provides session-scoped state that persists across requests within
the same MCP session. State is automatically keyed by session, ensuring
isolation between different clients.

State set during `on_initialize` middleware will persist to subsequent tool
calls when using the same session object (STDIO, SSE, single-server HTTP).
For distributed/serverless HTTP deployments where different machines handle
the init and tool calls, state is isolated by the mcp-session-id header.

The context parameter name can be anything as long as it's annotated with Context.
The context is optional - tools that don't need it can omit the parameter.

**Methods:**

#### `is_background_task` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L224](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L224)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
is_background_task(self) -> bool
```

True when this context is running in a background task (Docket worker).

When True, certain operations like elicit() will use task-aware
implementations that can pause the task and wait for client input.

#### `task_id` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L242](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L242)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
task_id(self) -> str | None
```

Get the background task ID if running in a background task.

Returns None if not running in a background task context.

#### `origin_request_id` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L250](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L250)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
origin_request_id(self) -> str | None
```

Get the request ID that originated this execution, if available.

In foreground request mode, this is the current request\_id.
In background task mode, this is the request\_id captured when the task
was submitted, if one was available.

#### `fastmcp` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L262](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L262)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
fastmcp(self) -> FastMCP
```

Get the FastMCP instance.

#### `request_context` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L312](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L312)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
request_context(self) -> FastMCPRequestContext | None
```

Access to the underlying request context.

Returns None when the MCP session has not been established yet.
Returns the FastMCPRequestContext wrapper once the MCP session is available.

For HTTP request access in middleware, use `get_http_request()` from fastmcp.server.dependencies,
which works whether or not the MCP session is available.

Example in middleware:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
async def on_request(self, context, call_next):
    ctx = context.fastmcp_context
    if ctx.request_context:
        # MCP session available - can access session_id, request_id, etc.
        session_id = ctx.session_id
    else:
        # MCP session not available yet - use HTTP helpers
        from fastmcp.server.dependencies import get_http_request
        request = get_http_request()
    return await call_next(context)
```

#### `client_extension_settings` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L337](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L337)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
client_extension_settings(self, identifier: str) -> dict[str, Any] | None
```

This request's per-request opt-in settings for an MCP extension.

SEP-2133 extensions negotiate per request: the client repeats its
extension capabilities in each request's `_meta` under
`io.modelcontextprotocol/clientCapabilities` → `extensions` →
`identifier`. Returns the declared settings dict (possibly empty) when
the extension was opted in for this request, or `None` when it was
not (or there is no active request). This bridges an extension's
`tools/call` interceptor — which receives a FastMCP `Context` — to
the request's declared client capabilities.

#### `input_responses` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L378](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L378)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
input_responses(self) -> mcp_types.InputResponses | None
```

Client responses to a prior `InputRequiredResult.input_requests`.

The multi-round-trip guard channel (SEP-2322). A guard tool inspects
this to decide what to do on each round: `None` on the initial round
(nothing has been asked yet, or the client retried without responses),
so the tool returns an `InputRequiredResult` to ask; present on a later
round, so the tool reads the answers and proceeds. It is a mapping whose
keys match the `input_requests` map the tool minted; each value is the
client's result for that request (an `ElicitResult`, `CreateMessageResult`,
or `ListRootsResult`).

In a background task there is no wire request, so this falls back to the
responses the in-task guard loop delivered (see the tasks extension).

#### `request_state` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L399](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L399)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
request_state(self) -> str | None
```

Opaque state echoed from a prior `InputRequiredResult.request_state`.

The multi-round-trip guard channel (SEP-2322): whatever a tool put in
`InputRequiredResult.request_state` on an earlier round is handed back
here (as plaintext — the framework seals it on the wire and unseals it
before the tool runs, so tampering is rejected before this is read).
`None` on the initial round. Use it to carry a small amount of computed
state across rounds without re-deriving it.

In a background task there is no wire request, so this falls back to the
state the in-task guard loop re-injected (see the tasks extension).

#### `lifespan_context` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L418](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L418)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
lifespan_context(self) -> dict[str, Any]
```

Access the server's lifespan context.

Returns the context dict yielded by *this* server's lifespan function.
For a mounted child this is the child's own lifespan, not the parent's
— the MCP session always belongs to the parent, so reading from the
request context would return the parent's. We read directly from the
server's cached lifespan result instead, which is set by the
per-server `_lifespan_manager` regardless of mount position.

Returns an empty dict if no lifespan was configured.

Example:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
@server.tool
def my_tool(ctx: Context) -> str:
    db = ctx.lifespan_context.get("db")
    if db:
        return db.query("SELECT 1")
    return "No database connection"
```

#### `report_progress` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L453](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L453)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
report_progress(self, progress: float, total: float | None = None, message: str | None = None) -> None
```

Report progress for the current operation.

Works in both foreground (MCP progress notifications) and background
(Docket task execution) contexts.

**Args:**

* `progress`: Current progress value e.g. 24
* `total`: Optional total value e.g. 100
* `message`: Optional status message describing current progress

#### `list_resources` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L552](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L552)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
list_resources(self) -> list[SDKResource]
```

List all available resources from the server.

**Returns:**

* List of Resource objects available on the server

#### `list_prompts` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L563](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L563)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
list_prompts(self) -> list[SDKPrompt]
```

List all available prompts from the server.

**Returns:**

* List of Prompt objects available on the server

#### `get_prompt` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L574](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L574)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_prompt(self, name: str, arguments: dict[str, Any] | None = None) -> GetPromptResult
```

Get a prompt by name with optional arguments.

**Args:**

* `name`: The name of the prompt to get
* `arguments`: Optional arguments to pass to the prompt

**Returns:**

* The prompt result

#### `read_resource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L593](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L593)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
read_resource(self, uri: str | AnyUrl) -> ResourceResult
```

Read a resource by URI.

**Args:**

* `uri`: Resource URI to read

**Returns:**

* ResourceResult with contents

#### `log` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L609](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L609)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
log(self, message: str, level: LoggingLevel | None = None, logger_name: str | None = None, extra: Mapping[str, Any] | None = None) -> None
```

Send a log message to the client.

Messages sent to Clients are also logged to the `fastmcp.server.context.to_client` logger with a level of `DEBUG`.

**Args:**

* `message`: Log message
* `level`: Optional log level. One of "debug", "info", "notice", "warning", "error", "critical",
  "alert", or "emergency". Default is "info".
* `logger_name`: Optional logger name
* `extra`: Optional mapping for additional arguments

#### `transport` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L650](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L650)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
transport(self) -> TransportType | None
```

Get the current transport type.

Returns the transport type used to run this server: "stdio", "sse",
or "streamable-http". Returns None if called outside of a server context.

#### `client_supports_extension` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L658](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L658)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
client_supports_extension(self, extension_id: str) -> bool
```

Check whether the connected client supports a given MCP extension.

Inspects the `extensions` capability the client declared, read from
the session's `client_capabilities`. The session is available in
request mode and in background-task mode, where the snapshot session
preserves the declared capabilities. Returns `False` when no session
is available (e.g., a distributed worker with no live session, or
outside any context) or when the client did not advertise the
extension.

Example::

from fastmcp.apps.config import UI\_EXTENSION\_ID

@mcp.tool
async def my\_tool(ctx: Context) -> str:
if ctx.client\_supports\_extension(UI\_EXTENSION\_ID):
return "UI-capable client"
return "text-only client"

#### `client_id` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L686](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L686)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
client_id(self) -> str | None
```

Get the client ID if available.

#### `request_id` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L694](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L694)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
request_id(self) -> str
```

Get the unique ID for this request.

Raises RuntimeError if MCP request context is not available.

#### `session_id` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L707](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L707)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
session_id(self) -> str
```

Get the MCP session ID for ALL transports.

Returns the session ID that can be used as a key for session-based
data storage (e.g., Redis) to share data between tool calls within
the same client session.

**Returns:**

* The session ID for StreamableHTTP transports, or a generated ID
* for other transports.

#### `session` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L792](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L792)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
session(self) -> ServerSession
```

Access to the underlying session for advanced usage.

In request mode: Returns the session from the active request context.
In background task mode: Returns the session stored at Context creation.

Raises RuntimeError if no session is available.

#### `debug` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L818](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L818)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
debug(self, message: str, logger_name: str | None = None, extra: Mapping[str, Any] | None = None) -> None
```

Send a `DEBUG`-level message to the connected MCP Client.

Messages sent to Clients are also logged to the `fastmcp.server.context.to_client` logger with a level of `DEBUG`.

#### `info` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L834](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L834)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
info(self, message: str, logger_name: str | None = None, extra: Mapping[str, Any] | None = None) -> None
```

Send a `INFO`-level message to the connected MCP Client.

Messages sent to Clients are also logged to the `fastmcp.server.context.to_client` logger with a level of `DEBUG`.

#### `warning` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L850](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L850)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
warning(self, message: str, logger_name: str | None = None, extra: Mapping[str, Any] | None = None) -> None
```

Send a `WARNING`-level message to the connected MCP Client.

Messages sent to Clients are also logged to the `fastmcp.server.context.to_client` logger with a level of `DEBUG`.

#### `error` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L866](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L866)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
error(self, message: str, logger_name: str | None = None, extra: Mapping[str, Any] | None = None) -> None
```

Send a `ERROR`-level message to the connected MCP Client.

Messages sent to Clients are also logged to the `fastmcp.server.context.to_client` logger with a level of `DEBUG`.

#### `send_notification` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L882](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L882)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
send_notification(self, notification: mcp_types.ServerNotification) -> None
```

Send a notification to the client immediately.

**Args:**

* `notification`: An MCP notification instance (e.g., ToolListChangedNotification())

#### `close_sse_stream` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L902](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L902)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
close_sse_stream(self) -> None
```

Close the current response stream to trigger client reconnection.

When using StreamableHTTP transport with an EventStore configured, this
method gracefully closes the HTTP connection for the current request.
The client will automatically reconnect (after `retry_interval` milliseconds)
and resume receiving events from where it left off via the EventStore.

This is useful for long-running operations to avoid load balancer timeouts.
Instead of holding a connection open for minutes, you can periodically close
and let the client reconnect.

#### `elicit` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L956](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L956)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
elicit(self, message: str, response_type: type[T]) -> AcceptedElicitation[T] | DeclinedElicitation | CancelledElicitation
```

The accepted elicitation will contain the response data

#### `elicit` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L967](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L967)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
elicit(self, message: str, response_type: list[str]) -> AcceptedElicitation[str] | DeclinedElicitation | CancelledElicitation
```

When response\_type is a list of strings, the accepted elicitation will
contain the selected string response

#### `elicit` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L979](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L979)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
elicit(self, message: str, response_type: dict[str, dict[str, str]]) -> AcceptedElicitation[str] | DeclinedElicitation | CancelledElicitation
```

When response\_type is a dict mapping keys to title dicts, the accepted
elicitation will contain the selected key

#### `elicit` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L991](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L991)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
elicit(self, message: str, response_type: list[list[str]]) -> AcceptedElicitation[list[str]] | DeclinedElicitation | CancelledElicitation
```

When response\_type is a list containing a list of strings (multi-select),
the accepted elicitation will contain a list of selected strings

#### `elicit` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L1003](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L1003)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
elicit(self, message: str, response_type: list[dict[str, dict[str, str]]]) -> AcceptedElicitation[list[str]] | DeclinedElicitation | CancelledElicitation
```

When response\_type is a list containing a dict mapping keys to title dicts
(multi-select with titles), the accepted elicitation will contain a list of
selected keys

#### `elicit` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L1015](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L1015)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
elicit(self, message: str, response_type: type[T] | list[str] | dict[str, dict[str, str]] | list[list[str]] | list[dict[str, dict[str, str]]]) -> AcceptedElicitation[T] | AcceptedElicitation[dict[str, Any]] | AcceptedElicitation[str] | AcceptedElicitation[list[str]] | DeclinedElicitation | CancelledElicitation
```

Send an elicitation request to the client and await the response.

Call this method at any time to request additional information from
the user through the client. The client must support elicitation,
or the request will error.

Note that the MCP protocol only supports simple object schemas with
primitive types. You can provide a dataclass, TypedDict, or BaseModel to
comply. If you provide a primitive type, an object schema with a single
"value" field will be generated for the MCP interaction and
automatically deconstructed into the primitive type upon response.

`response_type` is required. Pass `bool` when all you need is a
confirmation; an empty schema leaves some clients rendering an empty,
non-functional form.

**Args:**

* `message`: A human-readable message explaining what information is needed
* `response_type`: The type of the response, which should be a primitive
  type or dataclass or BaseModel. If it is a primitive type, an
  object schema with a single "value" field will be generated.
* `response_title`: Optional label to display for the wrapped `value`
  field when `response_type` is a scalar, Literal, Enum, or one
  of the dict/list shorthand forms. Overrides the auto-generated
  "Value" label. Raises `TypeError` if passed with a BaseModel,
  dataclass, or `None` response type (use `Field(title=...)`
  on the model instead).
* `response_description`: Optional description to attach to the wrapped
  `value` field. Same scope rules as `response_title`.

#### `set_state` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L1108](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L1108)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
set_state(self, key: str, value: Any) -> None
```

Set a value in the state store.

By default, values are stored in the session-scoped state store and
persist across requests within the same MCP session. Values must be
JSON-serializable (dicts, lists, strings, numbers, etc.).

For non-serializable values (e.g., HTTP clients, database connections),
pass `serializable=False`. These values are stored in a request-scoped
dict and only live for the current MCP request (tool call, resource
read, or prompt render). They will not be available in subsequent
requests.

The key is automatically prefixed with the session identifier.

#### `get_state` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L1162](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L1162)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_state(self, key: str) -> Any
```

Get a value from the state store.

Checks request-scoped state first (set with `serializable=False`),
then falls back to the session-scoped state store.

Returns None if the key is not found.

#### `delete_state` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L1176](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L1176)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
delete_state(self, key: str) -> None
```

Delete a value from the state store.

Removes from both request-scoped and session-scoped stores.

#### `enable_components` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L1197](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L1197)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
enable_components(self) -> None
```

Enable components matching criteria for this session only.

Session rules override global transforms. Rules accumulate - each call
adds a new rule to the session. Later marks override earlier ones
(Visibility transform semantics).

Sends notifications to this session only: ToolListChangedNotification,
ResourceListChangedNotification, and PromptListChangedNotification.

**Args:**

* `names`: Component names or URIs to match.
* `keys`: Component keys to match (e.g., tool:my\_tool\@v1).
* `version`: Component version spec to match.
* `tags`: Tags to match (component must have at least one).
* `components`: Component types to match (e.g., {"tool", "prompt"}).
* `match_all`: If True, matches all components regardless of other criteria.

#### `disable_components` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L1235](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L1235)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
disable_components(self) -> None
```

Disable components matching criteria for this session only.

Session rules override global transforms. Rules accumulate - each call
adds a new rule to the session. Later marks override earlier ones
(Visibility transform semantics).

Sends notifications to this session only: ToolListChangedNotification,
ResourceListChangedNotification, and PromptListChangedNotification.

**Args:**

* `names`: Component names or URIs to match.
* `keys`: Component keys to match (e.g., tool:my\_tool\@v1).
* `version`: Component version spec to match.
* `tags`: Tags to match (component must have at least one).
* `components`: Component types to match (e.g., {"tool", "prompt"}).
* `match_all`: If True, matches all components regardless of other criteria.

#### `reset_visibility` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/context.py#L1273](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/context.py#L1273)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
reset_visibility(self) -> None
```

Clear all session visibility rules.

Use this to reset session visibility back to global defaults.

Sends notifications to this session only: ToolListChangedNotification,
ResourceListChangedNotification, and PromptListChangedNotification.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.