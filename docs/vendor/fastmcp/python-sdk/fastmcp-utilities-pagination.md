> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# pagination

# `fastmcp.utilities.pagination`

Pagination utilities for MCP list operations.

## Functions

### `paginate_sequence` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/pagination.py#L60](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/pagination.py#L60)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
paginate_sequence(items: Sequence[T], cursor: str | None, page_size: int) -> tuple[list[T], str | None]
```

Paginate a sequence of items.

**Args:**

* `items`: The full sequence to paginate.
* `cursor`: Optional cursor from a previous request. None for first page.
* `page_size`: Maximum number of items per page.

**Returns:**

* Tuple of (page\_items, next\_cursor). next\_cursor is None if no more pages.

**Raises:**

* `ValueError`: If the cursor is invalid.

## Classes

### `CursorState` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/pagination.py#L16](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/pagination.py#L16)</sup>

Internal representation of pagination cursor state.

The cursor encodes the offset into the result set. This is opaque to clients
per the MCP spec - they should not parse or modify cursors.

**Methods:**

#### `encode` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/pagination.py#L25](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/pagination.py#L25)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
encode(self) -> str
```

Encode cursor state to an opaque string.

#### `decode` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/pagination.py#L31](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/pagination.py#L31)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
decode(cls, cursor: str) -> CursorState
```

Decode cursor from an opaque string.

**Raises:**

* `ValueError`: If the cursor is invalid or malformed.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.