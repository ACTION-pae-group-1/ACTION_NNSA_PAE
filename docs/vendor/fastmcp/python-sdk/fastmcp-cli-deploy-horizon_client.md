> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# horizon_client

# `fastmcp.cli.deploy.horizon_client`

Typed HTTP client for the Horizon control plane.

## Functions

### `normalize_api_origin` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/horizon\_client.py#L129](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/horizon_client.py#L129)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
normalize_api_origin(value: str) -> str
```

Validate and normalize a Horizon API origin.

## Classes

### `HorizonError` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/horizon\_client.py#L33](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/horizon_client.py#L33)</sup>

A safe Horizon client error.

### `HorizonUnavailableError` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/horizon\_client.py#L37](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/horizon_client.py#L37)</sup>

The Horizon API could not be reached.

### `HorizonUnauthorizedError` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/horizon\_client.py#L41](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/horizon_client.py#L41)</sup>

The Horizon credential was rejected.

### `HorizonResponseError` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/horizon\_client.py#L45](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/horizon_client.py#L45)</sup>

Horizon returned an unexpected response.

### `DeviceAuthorization` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/horizon\_client.py#L60](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/horizon_client.py#L60)</sup>

### `DeviceAccessToken` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/horizon\_client.py#L69](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/horizon_client.py#L69)</sup>

**Methods:**

#### `require_nonempty_access_token` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/horizon\_client.py#L75](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/horizon_client.py#L75)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
require_nonempty_access_token(cls, value: SecretStr) -> SecretStr
```

### `HorizonUser` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/horizon\_client.py#L85](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/horizon_client.py#L85)</sup>

### `HorizonOrganization` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/horizon\_client.py#L95](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/horizon_client.py#L95)</sup>

### `DeviceMetadata` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/horizon\_client.py#L112](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/horizon_client.py#L112)</sup>

### `DeviceTokenPoll` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/horizon\_client.py#L120](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/horizon_client.py#L120)</sup>

### `HorizonClient` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/horizon\_client.py#L150](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/horizon_client.py#L150)</sup>

Call the Horizon routes used by FastMCP CLI authentication.

**Methods:**

#### `aclose` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/horizon\_client.py#L188](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/horizon_client.py#L188)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
aclose(self) -> None
```

#### `create_device_authorization` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/horizon\_client.py#L242](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/horizon_client.py#L242)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
create_device_authorization(self, metadata: DeviceMetadata | None = None) -> DeviceAuthorization
```

#### `exchange_device_authorization` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/horizon\_client.py#L262](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/horizon_client.py#L262)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
exchange_device_authorization(self, device_code: str) -> DeviceTokenPoll
```

#### `get_current_user` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/horizon\_client.py#L287](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/horizon_client.py#L287)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_current_user(self) -> HorizonUser
```

#### `list_organizations` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/horizon\_client.py#L297](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/horizon_client.py#L297)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
list_organizations(self) -> tuple[HorizonOrganization, ...]
```

#### `revoke_current_api_key` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/horizon\_client.py#L326](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/horizon_client.py#L326)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
revoke_current_api_key(self) -> None
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.