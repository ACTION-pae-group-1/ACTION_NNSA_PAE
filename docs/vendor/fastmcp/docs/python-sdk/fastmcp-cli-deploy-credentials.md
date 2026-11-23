> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# credentials

# `fastmcp.cli.deploy.credentials`

Restricted Horizon credential storage and resolution.

## Functions

### `resolve_credential` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/credentials.py#L130](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/credentials.py#L130)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
resolve_credential(store: CredentialStore) -> ResolvedCredential
```

Resolve environment, stored, then interactive credentials.

### `revoke_and_clear_credential` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/credentials.py#L161](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/credentials.py#L161)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
revoke_and_clear_credential(client: HorizonClient, store: CredentialStore) -> None
```

Attempt remote revocation and always remove the stored credential.

## Classes

### `AuthenticationRequiredError` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/credentials.py#L33](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/credentials.py#L33)</sup>

No Horizon credential is available without interactive authorization.

### `AuthState` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/credentials.py#L37](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/credentials.py#L37)</sup>

**Methods:**

#### `require_nonempty_api_key` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/credentials.py#L45](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/credentials.py#L45)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
require_nonempty_api_key(cls, value: SecretStr) -> SecretStr
```

### `ResolvedCredential` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/credentials.py#L52](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/credentials.py#L52)</sup>

### `CredentialStore` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/credentials.py#L57](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/credentials.py#L57)</sup>

Persist the active personal Horizon API key.

**Methods:**

#### `load` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/credentials.py#L67](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/credentials.py#L67)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
load(self) -> SecretStr | None
```

#### `save` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/credentials.py#L71](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/credentials.py#L71)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
save(self, api_key: SecretStr | str) -> None
```

#### `save_for_origin` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/credentials.py#L84](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/credentials.py#L84)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
save_for_origin(self, api_key: SecretStr | str) -> None
```

Save a key only while its issuing Horizon origin is active.

#### `clear_if_matches` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/credentials.py#L100](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/credentials.py#L100)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
clear_if_matches(self, api_key: SecretStr | str) -> None
```

Clear a key only while its Horizon origin and value are active.

#### `clear` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/deploy/credentials.py#L126](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/deploy/credentials.py#L126)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
clear(self) -> None
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.