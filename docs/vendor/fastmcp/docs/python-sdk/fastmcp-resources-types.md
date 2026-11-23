> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# types

# `fastmcp.resources.types`

Concrete resource implementations.

## Classes

### `TextResource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/types.py#L22](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/types.py#L22)</sup>

A resource that reads from a string.

**Methods:**

#### `read` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/types.py#L27](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/types.py#L27)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
read(self) -> ResourceResult
```

Read the text content.

### `BinaryResource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/types.py#L40](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/types.py#L40)</sup>

A resource that reads from bytes.

**Methods:**

#### `read` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/types.py#L45](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/types.py#L45)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
read(self) -> ResourceResult
```

Read the binary content.

### `FileResource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/types.py#L58](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/types.py#L58)</sup>

A resource that reads from a file.

Set is\_binary=True to read file as binary data instead of text.

**Methods:**

#### `validate_absolute_path` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/types.py#L88](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/types.py#L88)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
validate_absolute_path(cls, path: Path) -> Path
```

Ensure path is absolute.

#### `set_binary_from_mime_type` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/types.py#L95](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/types.py#L95)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
set_binary_from_mime_type(self) -> Self
```

Set is\_binary based on mime\_type if not explicitly set.

#### `read` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/types.py#L102](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/types.py#L102)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
read(self) -> ResourceResult
```

Read the file content.

### `HttpResource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/types.py#L122](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/types.py#L122)</sup>

A resource that reads from an HTTP endpoint.

**Methods:**

#### `read` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/types.py#L131](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/types.py#L131)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
read(self) -> ResourceResult
```

Read the HTTP content.

### `DirectoryResource` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/types.py#L147](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/types.py#L147)</sup>

A resource that lists files in a directory.

**Methods:**

#### `validate_absolute_path` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/types.py#L167](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/types.py#L167)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
validate_absolute_path(cls, path: Path) -> Path
```

Ensure path is absolute.

#### `list_files` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/types.py#L173](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/types.py#L173)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
list_files(self) -> list[Path]
```

List files in the directory.

#### `read` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/resources/types.py#L189](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/resources/types.py#L189)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
read(self) -> ResourceResult
```

Read the directory listing.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.