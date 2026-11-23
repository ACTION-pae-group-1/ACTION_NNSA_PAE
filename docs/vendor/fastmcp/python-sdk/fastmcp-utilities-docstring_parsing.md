> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/llms.txt
> Use this file to discover all available pages before exploring further.

# docstring_parsing

# `fastmcp.utilities.docstring_parsing`

Extract descriptions from function docstrings.

Uses griffelib to parse Google, NumPy, and Sphinx-style docstrings. The
interface is intentionally narrow — a single function returning a
`ParsedDocstring` — so the implementation can be swapped without touching
callers.

## Functions

### `parse_docstring` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/docstring\_parsing.py#L33](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/docstring_parsing.py#L33)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
parse_docstring(fn: Callable[..., Any]) -> ParsedDocstring
```

Parse a function's docstring into a summary and parameter descriptions.

Tries Google, NumPy, and Sphinx parsers in order, using the first one that
recognizes a structured section (parameters, returns, raises, and so on).
The description is the free-form text before the first such section. If no
parser recognizes a section, returns the full docstring as the description
with no parameter descriptions.

## Classes

### `ParsedDocstring` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/docstring\_parsing.py#L26](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/docstring_parsing.py#L26)</sup>

The extracted description and per-parameter descriptions from a docstring.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.