> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# session_scoped_event_store

# `fastmcp.server.session_scoped_event_store`

Lightweight session scoping for Streamable HTTP event stores.

## Classes

### `SessionScopedEventStore` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/session\_scoped\_event\_store.py#L19](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/session_scoped_event_store.py#L19)</sup>

EventStore adapter that isolates stream IDs to one transport session.

**Methods:**

#### `store_event` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/session\_scoped\_event\_store.py#L34](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/session_scoped_event_store.py#L34)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
store_event(self, stream_id: StreamId, message: JSONRPCMessage | None) -> EventId
```

#### `replay_events_after` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/session\_scoped\_event\_store.py#L41](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/session_scoped_event_store.py#L41)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
replay_events_after(self, last_event_id: EventId, send_callback: EventCallback) -> StreamId | None
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.