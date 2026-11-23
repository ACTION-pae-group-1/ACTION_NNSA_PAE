> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# extension

# `fastmcp.skills.extension`

FastMCP server implementation of the MCP Skills extension.

## Classes

### `SkillsExtension` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/extension.py#L40](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/extension.py#L40)</sup>

Expose caller-scoped skill sources through SEP-2640 methods.

Skill providers register this extension automatically, so most servers
never construct it. With no `providers`, it serves every skill source
registered directly on the server, the backend skills of each
`ProxyProvider(..., skills=True)`, and the skills of mounted servers,
rewritten to the URIs the parent serves them at. Pass `providers` to limit
discovery to an explicit list of directly registered skill providers.

**Methods:**

#### `clone` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/extension.py#L62](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/extension.py#L62)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
clone(self) -> SkillsExtension
```

#### `methods` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/extension.py#L136](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/extension.py#L136)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
methods(self) -> Sequence[MethodBinding]
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.