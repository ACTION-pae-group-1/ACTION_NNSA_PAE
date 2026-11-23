> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# skills

# `fastmcp.utilities.skills`

Client utilities for discovering and downloading skills from MCP servers.

## Functions

### `list_skills` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/skills.py#L43](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/skills.py#L43)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
list_skills(client: Client) -> list[SkillSummary]
```

List all available skills from an MCP server.

Discovers skills by finding resources with URIs matching the
`skill://{name}/SKILL.md` pattern.

**Args:**

* `client`: Connected FastMCP client

**Returns:**

* List of SkillSummary objects with name, description, and URI

### `get_skill_manifest` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/skills.py#L87](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/skills.py#L87)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_skill_manifest(client: Client, skill_name: str) -> SkillManifest
```

Get the manifest for a specific skill.

**Args:**

* `client`: Connected FastMCP client
* `skill_name`: Name of the skill

**Returns:**

* SkillManifest with file listing

**Raises:**

* `ValueError`: If manifest cannot be read or parsed

### `download_skill` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/skills.py#L127](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/skills.py#L127)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
download_skill(client: Client, skill_name: str, target_dir: str | Path) -> Path
```

Download a skill and all its files to a local directory.

Creates a subdirectory named after the skill containing all files.

**Args:**

* `client`: Connected FastMCP client
* `skill_name`: Name of the skill to download
* `target_dir`: Directory where skill folder will be created
* `overwrite`: If True, overwrite existing skill directory. If False
  (default), raise FileExistsError if directory exists.

**Returns:**

* Path to the downloaded skill directory

**Raises:**

* `ValueError`: If skill cannot be found or downloaded
* `FileExistsError`: If skill directory exists and overwrite=False

### `sync_skills` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/skills.py#L218](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/skills.py#L218)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
sync_skills(client: Client, target_dir: str | Path) -> list[Path]
```

Download all available skills from a server.

**Args:**

* `client`: Connected FastMCP client
* `target_dir`: Directory where skill folders will be created
* `overwrite`: If True, overwrite existing files

**Returns:**

* List of paths to downloaded skill directories

## Classes

### `SkillSummary` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/skills.py#L18](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/skills.py#L18)</sup>

Summary information about a skill available on a server.

### `SkillFile` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/skills.py#L27](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/skills.py#L27)</sup>

Information about a file within a skill.

### `SkillManifest` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/skills.py#L36](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/skills.py#L36)</sup>

Full manifest of a skill including all files.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.