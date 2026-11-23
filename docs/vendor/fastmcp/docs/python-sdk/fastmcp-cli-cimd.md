> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# cimd

# `fastmcp.cli.cimd`

CIMD (Client ID Metadata Document) CLI commands.

## Functions

### `create_command` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/cimd.py#L32](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/cimd.py#L32)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
create_command() -> None
```

Generate a CIMD document for hosting.

Create a Client ID Metadata Document that you can host at an HTTPS URL.
The URL where you host this document becomes your client\_id.

After creating the document, host it at an HTTPS URL with a non-root path,
for example: [https://myapp.example.com/oauth/client.json](https://myapp.example.com/oauth/client.json)

### `validate_command` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/cimd.py#L144](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/cimd.py#L144)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
validate_command(url: Annotated[str, cyclopts.Parameter(help='URL of the CIMD document to validate')]) -> None
```

Validate a hosted CIMD document.

Fetches the document from the given URL and validates:

* URL is valid CIMD URL (HTTPS, non-root path)
* Document is valid JSON
* Document conforms to CIMD schema
* client\_id in document matches the URL


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.