> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# messages

# `fastmcp.client.messages`

## Classes

### `MessageHandler` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/messages.py#L11](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/messages.py#L11)</sup>

This class is used to handle MCP messages sent to the client: notifications
and transport-level exceptions. Users can override any of the hooks.

Server-initiated *requests* (ping, sampling, roots) never reach this
handler: the stable MCP SDK v2's `message_handler` contract only delivers
`ServerNotification | Exception`, so a request has no wire path here.
Those are answered through the `Client`'s dedicated callbacks instead —
`sampling_handler=`, `roots=`, and `elicitation_handler=`.

**Methods:**

#### `dispatch` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/messages.py#L26](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/messages.py#L26)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
dispatch(self, message: Message) -> None
```

#### `on_message` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/messages.py#L54](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/messages.py#L54)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_message(self, message: Message) -> None
```

#### `on_notification` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/messages.py#L57](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/messages.py#L57)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_notification(self, message: mcp_types.ServerNotification) -> None
```

#### `on_exception` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/messages.py#L60](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/messages.py#L60)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_exception(self, message: Exception) -> None
```

#### `on_progress` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/messages.py#L63](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/messages.py#L63)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_progress(self, message: mcp_types.ProgressNotification) -> None
```

#### `on_logging_message` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/messages.py#L66](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/messages.py#L66)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_logging_message(self, message: mcp_types.LoggingMessageNotification) -> None
```

#### `on_tool_list_changed` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/messages.py#L71](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/messages.py#L71)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_tool_list_changed(self, message: mcp_types.ToolListChangedNotification) -> None
```

#### `on_resource_list_changed` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/messages.py#L76](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/messages.py#L76)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_resource_list_changed(self, message: mcp_types.ResourceListChangedNotification) -> None
```

#### `on_prompt_list_changed` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/messages.py#L81](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/messages.py#L81)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_prompt_list_changed(self, message: mcp_types.PromptListChangedNotification) -> None
```

#### `on_resource_updated` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/messages.py#L86](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/messages.py#L86)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_resource_updated(self, message: mcp_types.ResourceUpdatedNotification) -> None
```

#### `on_cancelled` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/messages.py#L91](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/messages.py#L91)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
on_cancelled(self, message: mcp_types.CancelledNotification) -> None
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.