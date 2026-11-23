> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# provider

# `fastmcp.skills.provider`

Provider that serves `Skill` objects defined in code or loaded from any source.

## Classes

### `SkillFileResource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/provider.py#L36](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/provider.py#L36)</sup>

One file of a `Skill`, served with its exact bytes.

**Methods:**

#### `read` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/provider.py#L45](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/provider.py#L45)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
read(self) -> ResourceResult
```

### `SkillManifestResource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/provider.py#L54](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/provider.py#L54)</sup>

The resource-mode `_manifest` listing used by `sync_skills` and `download_skill`.

**Methods:**

#### `read` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/provider.py#L61](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/provider.py#L61)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
read(self) -> str
```

### `SkillCatalogProvider` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/provider.py#L73](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/provider.py#L73)</sup>

Serve `Skill` objects as MCP resources and Skills extension entries.

Each skill's files are served under `skill://{path}/`, where `path` defaults
to the skill's name. Pass a mapping to choose paths; the last path segment
must equal the skill's name. Every client can read the files as resources,
and the provider registers `SkillsExtension` so discovery clients can use
`skills/list` and `skills/get`.

For skills that change at runtime, such as rows in a database, subclass and
override `load_skills()`. It is called once per MCP request.

**Methods:**

#### `required_extensions` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/provider.py#L107](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/provider.py#L107)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
required_extensions(self) -> Sequence[ServerExtension]
```

#### `load_skills` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/provider.py#L112](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/provider.py#L112)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
load_skills(self) -> SkillCatalog
```

Return the skills to serve. Override to load them from another source.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.