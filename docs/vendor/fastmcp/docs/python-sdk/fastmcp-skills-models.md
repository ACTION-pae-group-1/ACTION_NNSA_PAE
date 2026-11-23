> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# models

# `fastmcp.skills.models`

Wire models for the MCP Skills extension (SEP-2640).

## Classes

### `SkillFrontmatter` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/models.py#L41](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/models.py#L41)</sup>

Agent Skills frontmatter carried verbatim as JSON-compatible values.

**Methods:**

#### `validate_agent_skills_fields` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/models.py#L45](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/models.py#L45)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
validate_agent_skills_fields(self) -> SkillFrontmatter
```

#### `name` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/models.py#L87](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/models.py#L87)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
name(self) -> str
```

#### `description` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/models.py#L91](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/models.py#L91)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
description(self) -> str
```

#### `license` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/models.py#L95](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/models.py#L95)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
license(self) -> str | None
```

#### `compatibility` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/models.py#L99](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/models.py#L99)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
compatibility(self) -> str | None
```

#### `metadata` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/models.py#L103](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/models.py#L103)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
metadata(self) -> dict[str, str] | None
```

#### `allowed_tools` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/models.py#L107](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/models.py#L107)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
allowed_tools(self) -> str | None
```

### `SkillResource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/models.py#L122](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/models.py#L122)</sup>

One file in a static skill manifest.

**Methods:**

#### `validate_size_type` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/models.py#L133](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/models.py#L133)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
validate_size_type(cls, value: object) -> object
```

### `MCPSkill` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/models.py#L143](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/models.py#L143)</sup>

A complete SEP-2640 skill entry.

**Methods:**

#### `validate_entry` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/models.py#L154](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/models.py#L154)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
validate_entry(self) -> MCPSkill
```

### `ListSkillsParams` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/models.py#L188](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/models.py#L188)</sup>

Parameters for `skills/list`.

### `GetSkillParams` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/models.py#L192](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/models.py#L192)</sup>

Parameters for `skills/get`.

### `ListSkillsResult` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/models.py#L198](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/models.py#L198)</sup>

Result from `skills/list`.

### `GetSkillResult` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/models.py#L205](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/models.py#L205)</sup>

Result from `skills/get`.

### `ListSkillsRequest` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/models.py#L212](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/models.py#L212)</sup>

Client request envelope for `skills/list`.

### `GetSkillRequest` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/models.py#L219](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/models.py#L219)</sup>

Client request envelope for `skills/get`.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.