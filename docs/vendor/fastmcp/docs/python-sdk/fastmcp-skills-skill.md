> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# skill

# `fastmcp.skills.skill`

Storage-neutral agent skills.

## Classes

### `Skill` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/skill.py#L51](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/skill.py#L51)</sup>

An agent skill: a `SKILL.md` plus supporting files, independent of storage.

A `Skill` holds exact file bytes. It doesn't know where it came from or which
URI it is served under; a provider decides that. Author one in Python with the
keyword constructor, or snapshot one from a directory, package, or mapping of
files.

**Methods:**

#### `from_files` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/skill.py#L132](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/skill.py#L132)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from_files(cls, files: Mapping[str, str | bytes]) -> Skill
```

Create a skill from relative paths mapped to text or bytes.

`files` must include `SKILL.md` with valid frontmatter.

#### `from_directory` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/skill.py#L142](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/skill.py#L142)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from_directory(cls, path: str | os.PathLike[str]) -> Skill
```

Read a skill folder once and return an immutable snapshot.

The folder name must match the `name` in its `SKILL.md`. Symlinks and
special files are rejected, so a snapshot never reaches outside the folder.

#### `from_package` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/skill.py#L162](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/skill.py#L162)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
from_package(cls, package: str, path: str) -> Skill
```

Load a skill folder shipped as package data, such as `("my_pkg", "skills/review")`.

#### `to_directory` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/skill.py#L188](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/skill.py#L188)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
to_directory(self, path: str | os.PathLike[str]) -> Path
```

Write the skill's files into `path`, a folder named after the skill.

The folder name must match the skill's `name`, so `from_directory` can
read it back. An existing folder raises `FileExistsError` unless
`overwrite` is set, in which case it is replaced: files that aren't
part of the skill are removed. Files are staged before replacing an
existing folder. If replacement and restoration both fail, the error
identifies where the previous folder has been retained.

#### `name` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/skill.py#L245](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/skill.py#L245)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
name(self) -> str
```

#### `description` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/skill.py#L249](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/skill.py#L249)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
description(self) -> str
```

#### `frontmatter` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/skill.py#L253](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/skill.py#L253)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
frontmatter(self) -> SkillFrontmatter
```

A copy of the parsed frontmatter; changing it does not change the skill.

#### `files` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/skill.py#L258](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/skill.py#L258)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
files(self) -> Mapping[str, bytes]
```

Every file in the skill, keyed by relative path, including `SKILL.md`.

#### `to_mcp_skill` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/skills/skill.py#L262](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/skills/skill.py#L262)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
to_mcp_skill(self, path: str | None = None) -> MCPSkill
```

Build the Skills extension entry for this skill served at `skill://{path}/`.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.