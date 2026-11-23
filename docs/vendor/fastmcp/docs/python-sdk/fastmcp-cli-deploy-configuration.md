> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# configuration

# `fastmcp.cli.deploy.configuration`

Global non-secret configuration for the FastMCP CLI.

## Classes

### `HorizonConfiguration` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/configuration.py#L18](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/configuration.py#L18)</sup>

**Methods:**

#### `validate_api_origin` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/configuration.py#L26](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/configuration.py#L26)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
validate_api_origin(cls, value: str) -> str
```

### `ConfigurationStore` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/configuration.py#L30](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/configuration.py#L30)</sup>

Persist the Horizon API origin without organization state.

**Methods:**

#### `load` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/configuration.py#L40](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/configuration.py#L40)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
load(self) -> HorizonConfiguration
```

#### `save` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/configuration.py#L49](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/configuration.py#L49)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
save(self, configuration: HorizonConfiguration) -> None
```

#### `set_api_origin` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/configuration.py#L55](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/configuration.py#L55)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
set_api_origin(self, api_origin: str) -> HorizonConfiguration
```

Set the origin and clear credentials before an origin change.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.