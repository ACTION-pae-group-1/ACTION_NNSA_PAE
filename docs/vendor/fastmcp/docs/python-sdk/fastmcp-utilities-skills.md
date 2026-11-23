> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# skills

# `fastmcp.utilities.skills`

Client utilities for discovering and downloading skills from MCP servers.

## Functions

### `list_skill_summaries` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/skills.py#L48](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/skills.py#L48)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
list_skill_summaries(client: Client) -> list[SkillSummary]
```

List the skills a server publishes as resources.

Discovers skills by finding resources with URIs matching the
`skill://{name}/SKILL.md` pattern, so it works with any server that
serves skills as resources. For the Skills extension's `skills/list`,
use `Client.list_skills()` with `SkillsClientExtension` instead.

**Args:**

* `client`: Connected FastMCP client

**Returns:**

* List of SkillSummary objects with name, description, and URI

### `list_skills` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/skills.py#L94](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/skills.py#L94)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
list_skills(client: Client) -> list[SkillSummary]
```

Deprecated alias for `list_skill_summaries`.

The name collided with `Client.list_skills()`, which sends the Skills
extension's `skills/list` request and returns different results.

### `get_skill_manifest` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/skills.py#L110](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/skills.py#L110)</sup>

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

### `download_skill` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/skills.py#L150](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/skills.py#L150)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
download_skill(client: Client, skill_name: str, target_dir: str | Path) -> Path
```

Read a skill from the server and write it to a local directory.

Creates a subdirectory named after the skill containing all files. A
skill served at a nested path, such as a mounted server's `ops/deploy`,
is installed as `deploy`, since agents look for skill folders one level
deep. Every file is checked against the server's manifest before it is
written; see `Client.read_skill`.

**Args:**

* `client`: Connected FastMCP client
* `skill_name`: Name or path of the skill to download
* `target_dir`: Directory where skill folder will be created
* `overwrite`: If True, replace an existing skill directory. If False
  (default), raise FileExistsError if directory exists.

**Returns:**

* Path to the downloaded skill directory

**Raises:**

* `ValueError`: If the skill cannot be found, fails verification, or is
  not a valid skill
* `FileExistsError`: If skill directory exists and overwrite=False

### `sync_skills` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/skills.py#L214](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/skills.py#L214)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
sync_skills(client: Client, target_dir: str | Path) -> list[Path]
```

Download all available skills from a server.

Each skill is installed in a folder named after it. When two skills share
a name, such as `ops/deploy` and `web/deploy`, only the first is
installed.

**Args:**

* `client`: Connected FastMCP client
* `target_dir`: Directory where skill folders will be created
* `overwrite`: If True, overwrite existing files

**Returns:**

* List of paths to downloaded skill directories

## Classes

### `SkillSummary` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/skills.py#L23](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/skills.py#L23)</sup>

Summary information about a skill available on a server.

### `SkillFile` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/skills.py#L32](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/skills.py#L32)</sup>

Information about a file within a skill.

### `SkillManifest` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/skills.py#L41](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/skills.py#L41)</sup>

Full manifest of a skill including all files.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.