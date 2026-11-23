> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# skills

# `fastmcp.client.mixins.skills`

Skills-extension methods for the FastMCP client.

## Classes

### `ClientSkillsMixin` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/mixins/skills.py#L46](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/mixins/skills.py#L46)</sup>

Mixin providing SEP-2640 Skills methods for `Client`.

**Methods:**

#### `list_skills_mcp` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/mixins/skills.py#L77](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/mixins/skills.py#L77)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
list_skills_mcp(self: Client) -> ListSkillsResult
```

Send one `skills/list` request and return its protocol result.

**Args:**

* `cursor`: Optional pagination cursor from a previous result.
* `cache_mode`: Response-cache behavior for this call.

**Returns:**

* The complete protocol result, including cache and pagination fields.

**Raises:**

* `RuntimeError`: If the client is disconnected or Skills was not negotiated.
* `MCPError`: If the server rejects the request.

#### `list_skills` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/mixins/skills.py#L119](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/mixins/skills.py#L119)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
list_skills(self: Client, max_pages: int = AUTO_PAGINATION_MAX_PAGES) -> list[MCPSkill]
```

Retrieve every page returned by `skills/list`.

**Args:**

* `max_pages`: Maximum number of pages to fetch before raising.
* `cache_mode`: Response-cache behavior for the first page.

**Returns:**

* Every skill entry returned across the server's pages.

**Raises:**

* `RuntimeError`: If Skills was not negotiated or the page limit is reached.
* `MCPError`: If the server rejects a request.

#### `get_skill_mcp` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/mixins/skills.py#L166](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/mixins/skills.py#L166)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_skill_mcp(self: Client, uri: str) -> GetSkillResult
```

Send a `skills/get` request and return its protocol result.

**Args:**

* `uri`: URI of the skill's `SKILL.md` resource.
* `cache_mode`: Response-cache behavior for this call.

**Returns:**

* The complete protocol result, including cache fields.

**Raises:**

* `RuntimeError`: If the client is disconnected or Skills was not negotiated.
* `MCPError`: If the server rejects the request.

#### `get_skill` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/mixins/skills.py#L210](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/mixins/skills.py#L210)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_skill(self: Client, uri: str) -> MCPSkill
```

Retrieve one skill entry by its `SKILL.md` resource URI.

**Args:**

* `uri`: URI of the skill's `SKILL.md` resource.
* `cache_mode`: Response-cache behavior for this call.

**Returns:**

* The skill entry returned by the server.

**Raises:**

* `RuntimeError`: If the client is disconnected or Skills was not negotiated.
* `MCPError`: If the server rejects the request.

#### `read_skill` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/client/mixins/skills.py#L232](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/client/mixins/skills.py#L232)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
read_skill(self: Client, uri: str) -> Skill
```

Fetch every file of a skill, verify each one, and return a `Skill`.

The manifest comes from `skills/get` when the Skills extension was
negotiated, and otherwise from the `_manifest` resource that FastMCP
skill providers serve next to the files. Every file must match the
size and SHA-256 digest the manifest promised. When an extension entry
is available, the parsed frontmatter must also match that entry.

**Args:**

* `uri`: URI of the skill's `SKILL.md` resource.
* `cache_mode`: Response-cache behavior for the `skills/get` request.

**Returns:**

* The skill, with the exact bytes of every file.

**Raises:**

* `RuntimeError`: If the client is disconnected.
* `ValueError`: If the manifest is unusable, a file does not match it,
  or the files do not form a valid skill.
* `MCPError`: If the server rejects a request.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.