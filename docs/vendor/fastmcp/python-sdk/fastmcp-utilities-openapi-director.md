> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# director

# `fastmcp.utilities.openapi.director`

Request director using openapi-core for stateless HTTP request building.

## Classes

### `RequestDirector` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/openapi/director.py#L78](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/openapi/director.py#L78)</sup>

Builds httpx2.Request objects from HTTPRoute and arguments using openapi-core.

**Methods:**

#### `build` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/openapi/director.py#L85](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/openapi/director.py#L85)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
build(self, route: HTTPRoute, flat_args: dict[str, Any], base_url: str = 'http://localhost') -> httpx2.Request
```

Constructs a final httpx2.Request object, handling all OpenAPI serialization.

**Args:**

* `route`: HTTPRoute containing OpenAPI operation details
* `flat_args`: Flattened arguments from LLM (may include suffixed parameters)
* `base_url`: Base URL for the request

**Returns:**

* httpx2.Request: Properly formatted HTTP request


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.