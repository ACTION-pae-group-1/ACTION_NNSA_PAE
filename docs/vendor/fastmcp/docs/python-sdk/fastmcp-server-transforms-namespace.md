> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# namespace

# `fastmcp.server.transforms.namespace`

Namespace transform for prefixing component names.

## Classes

### `Namespace` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/namespace.py#L28](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/namespace.py#L28)</sup>

Prefixes component names with a namespace.

* Tools: name → namespace\_name
* Prompts: name → namespace\_name
* Resources: protocol://path → protocol://namespace/path
* Resource Templates: same as resources

**Methods:**

#### `list_tools` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/namespace.py#L99](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/namespace.py#L99)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
list_tools(self, tools: Sequence[Tool]) -> Sequence[Tool]
```

Prefix tool names with namespace.

#### `get_tool` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/namespace.py#L105](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/namespace.py#L105)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_tool(self, name: str, call_next: GetToolNext) -> Tool | None
```

Get tool by namespaced name.

#### `list_resources` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/namespace.py#L121](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/namespace.py#L121)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
list_resources(self, resources: Sequence[Resource]) -> Sequence[Resource]
```

Add namespace path segment to resource URIs.

#### `get_resource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/namespace.py#L128](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/namespace.py#L128)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_resource(self, uri: str, call_next: GetResourceNext) -> Resource | None
```

Get resource by namespaced URI.

#### `list_resource_templates` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/namespace.py#L148](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/namespace.py#L148)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
list_resource_templates(self, templates: Sequence[ResourceTemplate]) -> Sequence[ResourceTemplate]
```

Add namespace path segment to template URIs.

#### `get_resource_template` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/namespace.py#L157](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/namespace.py#L157)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_resource_template(self, uri: str, call_next: GetResourceTemplateNext) -> ResourceTemplate | None
```

Get resource template by namespaced URI.

#### `list_prompts` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/namespace.py#L179](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/namespace.py#L179)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
list_prompts(self, prompts: Sequence[Prompt]) -> Sequence[Prompt]
```

Prefix prompt names with namespace.

#### `get_prompt` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/namespace.py#L185](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/namespace.py#L185)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_prompt(self, name: str, call_next: GetPromptNext) -> Prompt | None
```

Get prompt by namespaced name.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.