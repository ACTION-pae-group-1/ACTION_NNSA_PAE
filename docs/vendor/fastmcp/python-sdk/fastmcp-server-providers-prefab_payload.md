> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# prefab_payload

# `fastmcp.server.providers.prefab_payload`

Late-bound tool names in Prefab UI payloads.

A Prefab UI is serialized during the entry tool's call, deep inside whatever
composition the server happens to have. At that moment nothing knows what the
backend tools will be *called* by the time the payload reaches a host: every
layer above may rename them, and the outermost layer's names are the only ones
a client can actually invoke.

So the payload leaves the app addressed by identity — `<hash>_<local_name>`,
stable everywhere — and every FastMCP server rewrites those references on the
way out to whatever it lists that tool as. Servers rewrite innermost-first, so
the edge writes last and wins.

Rewriting a name in place would destroy the identity for the next layer up, so
the payload carries a name-to-identity map under `_meta.fastmcp.toolNames`.
Each layer resolves through the map and updates it. The action objects keep the
exact shape `prefab_ui` defines — only the value of `tool` changes, and only
ever to another valid tool name.

Renderers read `_meta` already and ignore keys they don't recognize, so this
needs no renderer change.

## Functions

### `payload_has_identities` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/prefab\_payload.py#L83](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/prefab_payload.py#L83)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
payload_has_identities(payload: Any) -> bool
```

Cheap guard: does this payload carry tool references worth rewriting?

Runs on every tool result, so it must not walk the tree.

### `annotate_payload_identities` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/prefab\_payload.py#L91](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/prefab_payload.py#L91)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
annotate_payload_identities(payload: dict[str, Any]) -> dict[str, Any]
```

Record the identity-addressed form of each reference, at serialization.

References start out as `<hash>_<local_name>`, so the map begins as an
identity map to itself. Once a later layer rewrites a name, this is the
only remaining route back: it carries both what the reference points at
and the address any server can fall back to.

### `rewrite_payload_tool_names` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/prefab\_payload.py#L115](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/prefab_payload.py#L115)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
rewrite_payload_tool_names(payload: Any, resolve: IdentityResolver) -> Any
```

Re-address a payload's tool references to this server's own names.

Mutates in place and returns the payload.

A reference this server cannot resolve is restored to its
identity-addressed form rather than left as-is. Leaving it would strand
whatever name an inner server chose — a name that is correct there and
meaningless here — and, unlike the identity form, a stranded name has no
route back. Restoring keeps the reference resolvable by the dispatcher,
or by any server further out with a better view.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.