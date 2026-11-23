> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# json_schema_converter

# `fastmcp.utilities.openapi.json_schema_converter`

Clean OpenAPI 3.0 to JSON Schema converter for the experimental parser.

This module provides a systematic approach to converting OpenAPI 3.0 schemas
to JSON Schema, inspired by py-openapi-schema-to-json-schema but optimized
for our specific use case.

## Functions

### `convert_openapi_schema_to_json_schema` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/openapi/json\_schema\_converter.py#L42](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/openapi/json_schema_converter.py#L42)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
convert_openapi_schema_to_json_schema(schema: dict[str, Any], openapi_version: str | None = None, remove_read_only: bool = False, remove_write_only: bool = False, convert_one_of_to_any_of: bool = True, definitions: dict[str, Any] | None = None) -> dict[str, Any]
```

Convert an OpenAPI schema to JSON Schema format.

This is a clean, systematic approach that:

1. Removes OpenAPI-specific fields
2. Converts nullable fields to type arrays (for OpenAPI 3.0 only)
3. Converts oneOf to anyOf for overlapping union handling
4. Recursively processes nested schemas
5. Optionally removes readOnly/writeOnly properties (see
   `_filter_properties_by_access` for the exact semantics)

**Args:**

* `schema`: OpenAPI schema dictionary
* `openapi_version`: OpenAPI version for optimization
* `remove_read_only`: Whether to remove readOnly properties
* `remove_write_only`: Whether to remove writeOnly properties
* `convert_one_of_to_any_of`: Whether to convert oneOf to anyOf
* `definitions`: Unconverted schemas that local `#/$defs/...` references
  resolve against when deciding which properties to remove. Defaults
  to the schema's own `$defs`.

**Returns:**

* JSON Schema-compatible dictionary

### `convert_schema_definitions` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/openapi/json\_schema\_converter.py#L404](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/openapi/json_schema_converter.py#L404)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
convert_schema_definitions(schema_definitions: dict[str, Any] | None, openapi_version: str | None = None, **kwargs) -> dict[str, Any]
```

Convert a dictionary of OpenAPI schema definitions to JSON Schema.

**Args:**

* `schema_definitions`: Dictionary of schema definitions
* `openapi_version`: OpenAPI version for optimization
* `**kwargs`: Additional arguments passed to convert\_openapi\_schema\_to\_json\_schema

**Returns:**

* Dictionary of converted schema definitions


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.