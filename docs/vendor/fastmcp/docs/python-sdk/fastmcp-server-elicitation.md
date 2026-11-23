> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# elicitation

# `fastmcp.server.elicitation`

## Functions

### `parse_elicit_response_type` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/elicitation.py#L168](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/elicitation.py#L168)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
parse_elicit_response_type(response_type: Any, response_title: str | None = None, response_description: str | None = None) -> ElicitConfig
```

Parse response\_type into schema and handling configuration.

A response type is required; `None` raises `TypeError`. Supports
multiple syntaxes:

* dict: `{"low": {"title": "..."}}` -> single-select titled enum
* list patterns:
  * `[["a", "b"]]` -> multi-select untitled
  * `[{"low": {...}}]` -> multi-select titled
  * `["a", "b"]` -> single-select untitled
* `list\[X]` type annotation: multi-select with type
* Scalar types (bool, int, float, str, Literal, Enum): single value
* Other types (dataclass, BaseModel): use directly

The `response_title` and `response_description` arguments customize the
label and description of the wrapped `value` property for the scalar/dict/list
shorthand forms. They are only valid when FastMCP is wrapping the response
type; passing them with a full BaseModel/dataclass raises `TypeError`,
because in those cases the user already controls field metadata via
`Field(title=..., description=...)`.

### `handle_elicit_accept` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/elicitation.py#L337](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/elicitation.py#L337)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
handle_elicit_accept(config: ElicitConfig, content: Any) -> AcceptedElicitation[Any]
```

Handle an accepted elicitation response.

**Args:**

* `config`: The elicitation configuration from parse\_elicit\_response\_type
* `content`: The response content from the client

**Returns:**

* AcceptedElicitation with the extracted/validated data

### `get_elicitation_schema` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/elicitation.py#L400](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/elicitation.py#L400)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_elicitation_schema(response_type: type[T]) -> dict[str, Any]
```

Get the schema for an elicitation response.

**Args:**

* `response_type`: The type of the response

### `validate_elicitation_json_schema` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/elicitation.py#L426](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/elicitation.py#L426)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
validate_elicitation_json_schema(schema: dict[str, Any]) -> None
```

Validate that a JSON schema follows MCP elicitation requirements.

This ensures the schema is compatible with MCP elicitation requirements:

* Must be an object schema
* Must only contain primitive field types (string, number, integer, boolean)
* Must be flat (no nested objects or arrays of objects)
* Allows const fields (for Literal types) and enum fields (for Enum types)
* Only primitive types and their nullable variants are allowed

**Args:**

* `schema`: The JSON schema to validate

**Raises:**

* `TypeError`: If the schema doesn't meet MCP elicitation requirements

## Classes

### `ElicitationJsonSchema` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/elicitation.py#L37](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/elicitation.py#L37)</sup>

Custom JSON schema generator for MCP elicitation that always inlines enums.

MCP elicitation requires inline enum schemas without $ref/$defs references.
This generator ensures enums are always generated inline for compatibility.
Optionally adds enumNames for better UI display when available.

**Methods:**

#### `definitions_schema` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/elicitation.py#L50](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/elicitation.py#L50)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
definitions_schema(self, schema: core_schema.DefinitionsSchema) -> JsonSchemaValue
```

Record shared enum definitions so references to them can be inlined.

#### `definition_ref_schema` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/elicitation.py#L59](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/elicitation.py#L59)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
definition_ref_schema(self, schema: core_schema.DefinitionReferenceSchema) -> JsonSchemaValue
```

Inline references to shared enums; enum definitions are never emitted.

#### `generate_inner` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/elicitation.py#L68](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/elicitation.py#L68)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
generate_inner(self, schema: core_schema.CoreSchema) -> JsonSchemaValue
```

Override to prevent ref generation for enums and handle list schemas.

#### `list_schema` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/elicitation.py#L81](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/elicitation.py#L81)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
list_schema(self, schema: core_schema.ListSchema) -> JsonSchemaValue
```

Generate schema for list types, detecting enum items for multi-select.

#### `enum_schema` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/elicitation.py#L118](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/elicitation.py#L118)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
enum_schema(self, schema: core_schema.EnumSchema) -> JsonSchemaValue
```

Generate inline enum schema.

Always generates enum pattern: `{"enum": [value, ...]}`
Titled enums are handled separately via dict-based syntax in ctx.elicit().

### `AcceptedElicitation` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/elicitation.py#L129](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/elicitation.py#L129)</sup>

Result when user accepts the elicitation.

### `ScalarElicitationType` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/elicitation.py#L137](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/elicitation.py#L137)</sup>

### `ElicitConfig` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/elicitation.py#L142](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/elicitation.py#L142)</sup>

Configuration for an elicitation request.

**Attributes:**

* `schema`: The JSON schema to send to the client
* `response_type`: The type to validate responses with. For raw schemas,
  it validates the extracted "value".
* `is_raw`: True if schema was built directly (extract "value" from response)


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.