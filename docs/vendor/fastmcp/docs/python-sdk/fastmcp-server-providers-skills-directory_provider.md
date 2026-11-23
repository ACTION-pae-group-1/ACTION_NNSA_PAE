> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# directory_provider

# `fastmcp.server.providers.skills.directory_provider`

Directory scanning provider for discovering multiple skills.

## Classes

### `SkillsDirectoryProvider` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/skills/directory\_provider.py#L40](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/skills/directory_provider.py#L40)</sup>

Provider that scans directories and creates a SkillProvider per skill folder.

This extends AggregateProvider to combine multiple SkillProviders into one.
Each subdirectory containing a main file (default: SKILL.md) becomes a skill.
Can scan multiple root directories - if a skill name appears in multiple roots,
the first one found wins.

**Args:**

* `roots`: Root directory(ies) containing skill folders. Can be a single path
  or a sequence of paths.
* `experimental_skills`: Opt into experimental SEP-2640 discovery, strict
  manifests, nested skills, and live byte-preserving reads. Defaults to False.
* `reload`: If True, re-discover skills on each request. Defaults to False.
* `main_file_name`: Name of the main skill file. Defaults to "SKILL.md".
* `supporting_files`: How supporting files are exposed in child SkillProviders:
* "template": Accessed via ResourceTemplate, hidden from list\_resources().
* "resources": Each file exposed as individual Resource in list\_resources().

**Methods:**

#### `required_extensions` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/providers/skills/directory\_provider.py#L442](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/providers/skills/directory_provider.py#L442)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
required_extensions(self) -> Sequence[ServerExtension]
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.