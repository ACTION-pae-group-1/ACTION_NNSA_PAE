> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# authentication

# `fastmcp.cli.deploy.authentication`

Horizon device authorization workflow.

## Functions

### `poll_device_authorization` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/authentication.py#L32](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/authentication.py#L32)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
poll_device_authorization(client: HorizonClient, authorization: DeviceAuthorization) -> SecretStr
```

Poll at the server interval until the device request completes.

### `authorize_device` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/authentication.py#L77](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/authentication.py#L77)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
authorize_device(client: HorizonClient) -> SecretStr
```

Create, present, and complete a Horizon device authorization.

## Classes

### `DeviceAuthorizationError` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/authentication.py#L20](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/authentication.py#L20)</sup>

Device authorization did not complete.

### `DeviceAuthorizationDeniedError` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/authentication.py#L24](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/authentication.py#L24)</sup>

The user denied the device authorization request.

### `DeviceAuthorizationExpiredError` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/authentication.py#L28](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/authentication.py#L28)</sup>

The device authorization request expired.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.