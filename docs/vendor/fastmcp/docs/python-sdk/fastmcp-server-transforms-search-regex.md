> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# regex

# `fastmcp.server.transforms.search.regex`

Regex-based search transform.

## Classes

### `RegexSearchTransform` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/server/transforms/search/regex.py#L20](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/transforms/search/regex.py#L20)</sup>

Search transform using regex pattern matching.

Tools are matched against their name, description, and parameter
information using Pydantic's Rust regex engine with case-insensitive
matching. Lookarounds and backreferences are not supported.

A search stops after about a second and returns the matches found so
far, so a costly pattern cannot hold the worker for long.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.