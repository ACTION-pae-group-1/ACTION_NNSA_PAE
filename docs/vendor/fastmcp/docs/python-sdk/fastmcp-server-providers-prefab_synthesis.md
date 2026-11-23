> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# prefab_synthesis

# `fastmcp.server.providers.prefab_synthesis`

On-demand Prefab renderer resources shared by effective configuration.

Tools carry a placeholder UI resource URI. Listings rewrite it to a stable
renderer URI derived from the Prefab version, delivery mode, and effective
resource metadata. Matching tools share a resource; different CSP, permissions,
domains, and border preferences stay distinct. HTML is loaded only on read.
Legacy per-tool URIs remain readable independently of backend tool identity.

## Functions

### `synthesize_prefab_resources` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/prefab\_synthesis.py#L254](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/prefab_synthesis.py#L254)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
synthesize_prefab_resources(server: FastMCP) -> list[Resource]
```

Return one lazy resource per effective renderer configuration.

### `synthesize_prefab_resource_by_uri` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/prefab\_synthesis.py#L266](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/prefab_synthesis.py#L266)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
synthesize_prefab_resource_by_uri(server: FastMCP, uri: str) -> Resource | None
```

Intercept a Prefab renderer URI and synthesize on demand.

### `rewrite_tool_meta_for_wire` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/prefab\_synthesis.py#L288](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/prefab_synthesis.py#L288)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
rewrite_tool_meta_for_wire(tool: Tool) -> Tool
```

Return a copy with the shared URI and resource-only fields stripped.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.