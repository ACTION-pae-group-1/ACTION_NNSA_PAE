> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# version_filter

# `fastmcp.server.transforms.version_filter`

Version filter transform for filtering components by version range.

## Classes

### `VersionFilter` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/version\_filter.py#L24](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/version_filter.py#L24)</sup>

Filters components by version range.

When applied to a provider or server, components within the version range
are visible, and unversioned components are included by default. Within
that filtered set, the highest version of each component is exposed to
clients (standard deduplication behavior). Set
`include_unversioned=False` to exclude unversioned components.

Parameters mirror comparison operators for clarity:

# Versions \< 3.0 (v1 and v2)

server.add\_transform(VersionFilter(version\_lt="3.0"))

# Versions >= 2.0 and \< 3.0 (only v2.x)

server.add\_transform(VersionFilter(version\_gte="2.0", version\_lt="3.0"))

Works with any version string - PEP 440 (1.0, 2.0) or dates (2025-01-01).

**Args:**

* `version_gte`: Versions >= this value pass through.
* `version_lt`: Versions \< this value pass through.
* `include_unversioned`: Whether unversioned components (`version=None`)
  should pass through the filter. Defaults to True.

**Methods:**

#### `list_tools` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/version\_filter.py#L80](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/version_filter.py#L80)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
list_tools(self, tools: Sequence[Tool]) -> Sequence[Tool]
```

#### `get_tool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/version\_filter.py#L87](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/version_filter.py#L87)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_tool(self, name: str, call_next: GetToolNext) -> Tool | None
```

#### `list_resources` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/version\_filter.py#L101](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/version_filter.py#L101)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
list_resources(self, resources: Sequence[Resource]) -> Sequence[Resource]
```

#### `get_resource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/version\_filter.py#L108](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/version_filter.py#L108)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_resource(self, uri: str, call_next: GetResourceNext) -> Resource | None
```

#### `list_resource_templates` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/version\_filter.py#L126](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/version_filter.py#L126)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
list_resource_templates(self, templates: Sequence[ResourceTemplate]) -> Sequence[ResourceTemplate]
```

#### `get_resource_template` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/version\_filter.py#L135](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/version_filter.py#L135)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_resource_template(self, uri: str, call_next: GetResourceTemplateNext) -> ResourceTemplate | None
```

#### `list_prompts` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/version\_filter.py#L153](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/version_filter.py#L153)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
list_prompts(self, prompts: Sequence[Prompt]) -> Sequence[Prompt]
```

#### `get_prompt` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/version\_filter.py#L160](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/version_filter.py#L160)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_prompt(self, name: str, call_next: GetPromptNext) -> Prompt | None
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.