> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# skill_provider

# `fastmcp.server.providers.skills.skill_provider`

Basic skill provider for handling a single skill folder.

## Classes

### `SkillResource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/skills/skill\_provider.py#L55](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/skills/skill_provider.py#L55)</sup>

A resource representing a skill's main file or manifest.

**Methods:**

#### `get_meta` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/skills/skill\_provider.py#L61](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/skills/skill_provider.py#L61)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_meta(self) -> dict[str, Any]
```

#### `read` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/skills/skill\_provider.py#L70](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/skills/skill_provider.py#L70)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
read(self) -> str | bytes | ResourceResult
```

Read the resource content.

### `SkillFileTemplate` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/skills/skill\_provider.py#L96](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/skills/skill_provider.py#L96)</sup>

A template for accessing files within a skill.

**Methods:**

#### `read` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/skills/skill\_provider.py#L101](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/skills/skill_provider.py#L101)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
read(self, arguments: dict[str, Any]) -> str | bytes | ResourceResult
```

Read a file from the skill directory.

#### `create_resource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/skills/skill\_provider.py#L127](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/skills/skill_provider.py#L127)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
create_resource(self, uri: str, params: dict[str, Any]) -> Resource
```

Create a resource for the given URI and parameters.

Note: This is not typically used since \_read() handles file reading directly.
Provided for compatibility with the ResourceTemplate interface.

### `SkillFileResource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/skills/skill\_provider.py#L150](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/skills/skill_provider.py#L150)</sup>

A resource representing a specific file within a skill.

**Methods:**

#### `get_meta` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/skills/skill\_provider.py#L156](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/skills/skill_provider.py#L156)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_meta(self) -> dict[str, Any]
```

#### `read` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/skills/skill\_provider.py#L164](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/skills/skill_provider.py#L164)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
read(self) -> str | bytes | ResourceResult
```

Read the file content.

### `SkillProvider` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/skills/skill\_provider.py#L181](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/skills/skill_provider.py#L181)</sup>

Provider that exposes a single skill folder as MCP resources.

Each skill folder must contain a main file (default: SKILL.md) and may
contain additional supporting files.

Exposes:

* A Resource for the main file (skill://{name}/SKILL.md)
* A Resource for the synthetic manifest (skill://{name}/\_manifest)
* Supporting files via ResourceTemplate or Resources (configurable)

**Args:**

* `skill_path`: Path to the skill directory.
* `main_file_name`: Name of the main skill file. Defaults to "SKILL.md".
* `supporting_files`: How supporting files (everything except main file and
  manifest) are exposed to clients:
* "template": Accessed via ResourceTemplate, hidden from list\_resources().
  Clients discover files by reading the manifest first.
* "resources": Each file exposed as individual Resource in list\_resources().
  Full enumeration upfront.

**Methods:**

#### `skill_info` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/skills/skill\_provider.py#L283](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/skills/skill_provider.py#L283)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
skill_info(self) -> SkillInfo
```

Get the loaded skill info.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.