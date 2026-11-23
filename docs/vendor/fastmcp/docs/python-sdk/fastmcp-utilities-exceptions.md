> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# exceptions

# `fastmcp.utilities.exceptions`

## Functions

### `is_http_status_error` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/exceptions.py#L19](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/exceptions.py#L19)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
is_http_status_error(exc: BaseException) -> bool
```

Return whether an exception is an httpx2 or legacy-httpx status error.

### `get_http_status_code` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/exceptions.py#L26](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/exceptions.py#L26)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_http_status_code(exc: BaseException) -> int | None
```

Return the response status code from a recognized HTTP status error.

### `is_timeout_error` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/exceptions.py#L34](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/exceptions.py#L34)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
is_timeout_error(exc: BaseException) -> bool
```

Return whether an exception is an httpx2 or legacy-httpx timeout.

### `is_request_error` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/exceptions.py#L41](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/exceptions.py#L41)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
is_request_error(exc: BaseException) -> bool
```

Return whether an exception is an httpx2 or legacy-httpx request error.

### `iter_exc` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/exceptions.py#L48](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/exceptions.py#L48)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
iter_exc(group: BaseExceptionGroup)
```

### `get_catch_handlers` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/exceptions.py#L76](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/exceptions.py#L76)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
get_catch_handlers() -> Mapping[type[BaseException] | Iterable[type[BaseException]], Callable[[BaseExceptionGroup[Any]], Any]]
```


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.