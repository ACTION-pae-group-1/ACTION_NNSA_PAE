> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# parser

# `fastmcp.utilities.openapi.parser`

OpenAPI parsing logic for converting OpenAPI specs to HTTPRoute objects.

## Functions

### `parse_openapi_to_http_routes` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/openapi/parser.py#L56](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/openapi/parser.py#L56)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
parse_openapi_to_http_routes(openapi_dict: dict[str, Any]) -> list[HTTPRoute]
```

Parses an OpenAPI schema dictionary into a list of HTTPRoute objects
using the openapi-pydantic library.

Supports both OpenAPI 3.0.x and 3.1.x versions.

## Classes

### `OpenAPIParser` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/openapi/parser.py#L110](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/openapi/parser.py#L110)</sup>

Unified parser for OpenAPI schemas with generic type parameters to handle both 3.0 and 3.1.

**Methods:**

#### `parse` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/openapi/parser.py#L702](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/openapi/parser.py#L702)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
parse(self) -> list[HTTPRoute]
```

Parse the OpenAPI schema into HTTP routes.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.