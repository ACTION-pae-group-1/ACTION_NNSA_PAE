> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# types

# `fastmcp.utilities.types`

Common types used across FastMCP.

## Functions

### `get_fn_name` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/types.py#L41](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/types.py#L41)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_fn_name(fn: Callable[..., Any]) -> str
```

### `get_function_type_hints` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/types.py#L51](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/types.py#L51)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_function_type_hints(fn: Callable[..., Any]) -> dict[str, Any]
```

Resolve a function's type hints, keeping `Annotated` metadata.

Before Python 3.11, `typing.get_type_hints` wraps the hint of every
parameter that defaults to `None` in `Optional[...]`. For
`Annotated[int | None, Field(title="Limit")] = None` that produces
`Optional[Annotated[...]]`, which buries the `Field` metadata in a nested
union branch of the JSON schema. Hints are resolved here without that
wrapping, so every supported Python version yields the same schema.

### `get_cached_typeadapter` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/types.py#L75](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/types.py#L75)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_cached_typeadapter(cls: T) -> TypeAdapter[T]
```

TypeAdapters are heavy objects, and in an application context we'd typically
create them once in a global scope and reuse them as often as possible.
However, this isn't feasible for user-generated functions. Instead, we use a
cache to minimize the cost of creating them as much as possible.

### `issubclass_safe` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/types.py#L153](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/types.py#L153)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
issubclass_safe(cls: type, base: type) -> bool
```

Check if cls is a subclass of base, even if cls is a type variable.

### `is_class_member_of_type` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/types.py#L163](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/types.py#L163)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
is_class_member_of_type(cls: Any, base: type) -> bool
```

Check if cls is a member of base, even if cls is a type variable.

Base can be a type, a UnionType, or an Annotated type. Generic types are not
considered members (e.g. T is not a member of list\[T]).

### `find_kwarg_by_type` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/types.py#L185](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/types.py#L185)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
find_kwarg_by_type(fn: Callable, kwarg_type: type) -> str | None
```

Find the name of the kwarg that is of type kwarg\_type.

Includes union types that contain the kwarg\_type, as well as Annotated types.

### `create_function_without_params` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/types.py#L211](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/types.py#L211)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
create_function_without_params(fn: Callable[..., Any], exclude_params: list[str]) -> Callable[..., Any]
```

Create a new function with the same code but without the specified parameters in annotations.

This is used to exclude parameters from type adapter processing when they can't be serialized.
The excluded parameters are removed from the function's **annotations** dictionary.

### `replace_type` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/types.py#L519](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/types.py#L519)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
replace_type(type_, type_map: dict[type, type])
```

Given a (possibly generic, nested, or otherwise complex) type, replaces all
instances of keys in type\_map with their corresponding values.

This is useful for transforming types when creating tools.

**Args:**

* `type_`: The type to transform.
* `type_map`: A mapping of types to replace (keys are replaced by values).

Examples:

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
>>> replace_type(list[int | bool], {int: str})
list[str | bool]

>>> replace_type(list[list[int]], {int: str})
list[list[str]]
```

## Classes

### `FastMCPBaseModel` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/types.py#L45](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/types.py#L45)</sup>

Base model for FastMCP models.

### `Image` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/types.py#L268](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/types.py#L268)</sup>

Helper class for returning images from tools.

**Methods:**

#### `to_image_content` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/types.py#L325](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/types.py#L325)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
to_image_content(self, mime_type: str | None = None, annotations: Annotations | None = None) -> mcp_types.ImageContent
```

Convert to MCP ImageContent.

#### `to_data_uri` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/types.py#L340](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/types.py#L340)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
to_data_uri(self, mime_type: str | None = None) -> str
```

Get image as a data URI.

### `Audio` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/types.py#L346](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/types.py#L346)</sup>

Helper class for returning audio from tools.

**Methods:**

#### `to_audio_content` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/types.py#L391](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/types.py#L391)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
to_audio_content(self, mime_type: str | None = None, annotations: Annotations | None = None) -> mcp_types.AudioContent
```

### `File` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/types.py#L412](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/types.py#L412)</sup>

Helper class for returning file data from tools.

**Methods:**

#### `to_resource_content` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/types.py#L460](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/types.py#L460)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
to_resource_content(self, mime_type: str | None = None, annotations: Annotations | None = None) -> mcp_types.EmbeddedResource
```

### `ContextSamplingFallbackProtocol` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/types.py#L555](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/types.py#L555)</sup>


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.