> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# base

# `fastmcp.client.transports.base`

## Classes

### `ClientSessionKwargs` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/base.py#L24](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/base.py#L24)</sup>

Keyword arguments for the MCP ClientSession constructor.

### `TransportOptions` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/base.py#L42](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/base.py#L42)</sup>

How one client wants its connection built.

These belong to the client rather than to the transport, so a transport
shared between clients doesn't leak one client's settings to another.
Different client layers may own different fields; a layer that adds its
settings must preserve the existing options rather than replace the bundle.

**Attributes:**

* `session_class`: The ClientSession class to instantiate. Proxies supply a
  session that skips output-schema validation, since they relay
  results rather than consume them.
* `forward_incoming_headers`: Whether to forward eligible inbound HTTP
  headers upstream, including authorization. Hop-specific HTTP headers
  and MCP transport, routing, and event-stream state are excluded
  because each backend connection owns that state. Only appropriate
  for proxies; honored by the HTTP and SSE transports and ignored by
  the others.
* `backend_mode`: The connect `mode` to give backend clients that a wrapping
  transport builds on this client's behalf, so a chain of connections
  speaks one protocol era end to end. `None` leaves each backend
  client at its own default. Honored by `MCPConfigTransport`, whose
  multi-server form mounts a proxy per configured server and resolves
  one shared era for the aggregate; ignored by transports that connect
  to a single backend directly, since those carry the connecting
  client's own session and era.

### `ClientTransport` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/base.py#L80](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/base.py#L80)</sup>

Abstract base class for different MCP client transport mechanisms.

A Transport is responsible for establishing and managing connections
to an MCP server, and providing a ClientSession within an async context.

**Methods:**

#### `connect_session` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/base.py#L98](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/base.py#L98)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
connect_session(self, **session_kwargs: Unpack[SessionKwargs]) -> AsyncGenerator[ClientSession, None]
```

Establishes a connection and yields an active ClientSession.

The ClientSession is *not* expected to be initialized in this context manager.

The session is guaranteed to be valid only within the scope of the
async context manager. Connection setup and teardown are handled
within this context.

**Args:**

* `transport_options`: How the connecting client wants this connection
  built. Defaults apply when omitted. A transport
  that wraps others must pass this along.
* `**session_kwargs`: Keyword arguments to pass to the ClientSession
  constructor (e.g., callbacks, timeouts).

#### `close` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/base.py#L130](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/base.py#L130)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
close(self)
```

Close the transport.

#### `get_session_id` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/transports/base.py#L133](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/transports/base.py#L133)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_session_id(self) -> str | None
```

Get the session ID for this transport, if available.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.