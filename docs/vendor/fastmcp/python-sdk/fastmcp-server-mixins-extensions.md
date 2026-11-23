> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# extensions

# `fastmcp.server.mixins.extensions`

Server-owned extension registration and provider composition.

## Classes

### `ExtensionsMixin` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/mixins/extensions.py#L25](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/mixins/extensions.py#L25)</sup>

Manage explicit and provider-bundled server extensions.

**Methods:**

#### `add_extension` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/mixins/extensions.py#L47](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/mixins/extensions.py#L47)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
add_extension(self: FastMCP, extension: ServerExtension) -> None
```

Register a server extension (SEP-2133).

Extensions contribute capabilities, additive request methods, tool-call
interception, and optional lifespans. The instance is bound to this
server. Explicit registration replaces a provider-bundled extension
with the same identifier, even when providers were added first.
Two explicit registrations with the same identifier are an error.

Register before serving. Mounted servers contribute separate instances
of extensions that opt in with `auto_register = True`; other extensions
must be registered on the server you run.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.