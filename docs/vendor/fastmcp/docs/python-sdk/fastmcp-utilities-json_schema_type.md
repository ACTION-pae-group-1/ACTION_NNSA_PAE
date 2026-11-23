> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# json_schema_type

# `fastmcp.utilities.json_schema_type`

Convert JSON Schema to Python types with validation.

The json\_schema\_to\_type function converts a JSON Schema into a Python type that can be used
for validation with Pydantic. It supports:

* Basic types (string, number, integer, boolean, null)
* Complex types (arrays, objects)
* Format constraints (date-time, date, time, duration, uuid, email, uri)
* Numeric constraints (minimum, maximum, multipleOf)
* String constraints (minLength, maxLength, pattern)
* Array constraints (minItems, maxItems, uniqueItems)
* Object properties with defaults
* References and recursive schemas
* Enums and constants
* Union types

## Unsupported regex patterns

Pydantic uses a Rust-based regex engine that does not support all regex
features found in real-world JSON Schemas (particularly those from AWS,
Azure, and other large OpenAPI providers). Unsupported constructs include
lookahead/lookbehind assertions (`(?!...)`, `(?<=...)`), Unicode property
escapes (`\p{Graph}`, `\p{Print}`), and very large compiled patterns.

When a `pattern` constraint cannot be compiled, `json_schema_to_type`
degrades gracefully:

1. The pattern is **dropped** from the Pydantic `StringConstraints` so
   the type will not raise a `SchemaError`.
2. A `UserWarning` is emitted with the unsupported pattern.
3. The original pattern is preserved in the type metadata as
   `x-unsupported-pattern` (visible via `TypeAdapter(T).json_schema()`).
4. Other constraints (`minLength`, `maxLength`) are still enforced.

Example:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "age": {"type": "integer", "minimum": 0},
        "email": {"type": "string", "format": "email"}
    },
    "required": ["name", "age"]
}

# Name is optional and will be inferred from schema's "title" property if not provided
Person = json_schema_to_type(schema)
# Creates a validated dataclass with name, age, and optional email fields
```

## Functions

### `json_schema_to_type` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/json\_schema\_type.py#L280](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/json_schema_type.py#L280)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
json_schema_to_type(schema: Mapping[str, Any] | bool, name: str | None = None) -> type
```

Convert JSON schema to appropriate Python type with validation.

**Args:**

* `schema`: A JSON Schema dictionary defining the type structure and validation rules.
  Boolean schemas are also accepted (`True` = any type, `False` = unsatisfiable).
* `name`: Optional name for object schemas. Only allowed when schema type is "object".
  If not provided for objects, name will be inferred from schema's "title"
  property or default to "Root".

**Returns:**

* A Python type (typically a dataclass for objects) with Pydantic validation

**Raises:**

* `ValueError`: If a name is provided for a non-object schema, or if the
  schema is too deeply nested or too large to convert.

**Examples:**

Create a dataclass from an object schema:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
schema = {
    "type": "object",
    "title": "Person",
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "age": {"type": "integer", "minimum": 0},
        "email": {"type": "string", "format": "email"}
    },
    "required": ["name", "age"]
}

Person = json_schema_to_type(schema)
# Creates a dataclass with name, age, and optional email fields:
# @dataclass
# class Person:
#     name: str
#     age: int
#     email: str | None = None
```

Person(name="John", age=30)

Create a scalar type with constraints:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
schema = {
    "type": "string",
    "minLength": 3,
    "pattern": "^[A-Z][a-z]+$"
}

NameType = json_schema_to_type(schema)
# Creates Annotated[str, StringConstraints(min_length=3, pattern="^[A-Z][a-z]+$")]

@dataclass
class Name:
    name: NameType
```

### `json_schema_to_type_adapter` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/json\_schema\_type.py#L368](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/json_schema_type.py#L368)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
json_schema_to_type_adapter(schema: Mapping[str, Any] | bool) -> TypeAdapter[Any]
```

Return a cached `TypeAdapter` for `json_schema_to_type(schema)`.

Adapters are cached by schema content in a bounded cache, so the classes
they hold are released when they are evicted.

### `safe_create_model` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/json\_schema\_type.py#L944](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/json_schema_type.py#L944)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
safe_create_model(name: str, field_definitions: Mapping[str, tuple[Any, Any]]) -> type[BaseModel]
```

Create a Pydantic model whose field names come from untrusted input.

Each property name only ever becomes a field. A reserved name is stored
under a generated field name with the original name as its alias, so it
validates and dumps (with `by_alias=True`) under its original name.

**Args:**

* `name`: The model class name.
* `field_definitions`: Maps each property name to `(annotation, default)`,
  where `default` may be a `FieldInfo` or `...` for required fields.
* `config`: Optional model configuration.

## Classes

### `JSONSchema` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/json\_schema\_type.py#L247](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/json_schema_type.py#L247)</sup>


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.