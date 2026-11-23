> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# prefab_synthesis

# `fastmcp.server.providers.prefab_synthesis`

On-demand Prefab renderer resource synthesis.

Tools marked as Prefab (via `app=True`, `PrefabAppConfig`, etc.) carry
a placeholder `meta.ui.resourceUri` and optionally a hash in
`meta.fastmcp.tool_hash`. This module synthesizes per-tool renderer
resources on demand at `list_resources` and `read_resource` time
without storing or materializing anything.

Each tool's resource URI is `ui://prefab/tool/<hash>/renderer.html`
where the hash comes from the tool's own meta (set at registration from
the app name + tool name). CSP on the resource is the tool's
`meta.ui.csp` merged with the renderer defaults across all four
`*_domains` fields.

## Functions

### `synthesize_prefab_resources` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/prefab\_synthesis.py#L213](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/prefab_synthesis.py#L213)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
synthesize_prefab_resources(server: FastMCP) -> list[Resource]
```

Return fresh synthetic Prefab resources for all prefab tools. Pure.

### `synthesize_prefab_resource_by_uri` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/prefab\_synthesis.py#L228](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/prefab_synthesis.py#L228)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
synthesize_prefab_resource_by_uri(server: FastMCP, uri: str) -> Resource | None
```

Intercept a Prefab renderer URI and synthesize on demand.

### `rewrite_tool_meta_for_wire` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/prefab\_synthesis.py#L241](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/prefab_synthesis.py#L241)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
rewrite_tool_meta_for_wire(tool: Tool) -> Tool
```

Return a model\_copy with the per-tool URI and resource-only fields stripped.

Reads the hash from the tool's own meta. If no hash is found,
returns the tool unchanged. Produces a fresh copy — the original
Tool object is untouched.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.