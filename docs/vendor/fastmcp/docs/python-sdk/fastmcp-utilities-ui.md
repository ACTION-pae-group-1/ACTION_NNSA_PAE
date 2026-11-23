> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# ui

# `fastmcp.utilities.ui`

Shared UI utilities for FastMCP HTML pages.

This module provides reusable HTML/CSS components for OAuth callbacks,
consent pages, and other user-facing interfaces.

## Functions

### `create_page` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/ui.py#L453](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/ui.py#L453)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
create_page(content: str, title: str = 'FastMCP', additional_styles: str = '', csp_policy: str = "default-src 'none'; style-src 'unsafe-inline'; img-src https: data:; base-uri 'none'") -> str
```

Create a complete HTML page with FastMCP styling.

**Args:**

* `content`: HTML content to place inside the page
* `title`: Page title
* `additional_styles`: Extra CSS to include
* `csp_policy`: Content Security Policy header value.
  If empty string "", the CSP meta tag is omitted entirely.

**Returns:**

* Complete HTML page as string

### `create_logo` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/ui.py#L501](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/ui.py#L501)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
create_logo(icon_url: str | None = None, alt_text: str = 'FastMCP') -> str
```

Create logo HTML.

**Args:**

* `icon_url`: Optional custom icon URL. If not provided, uses the FastMCP logo.
* `alt_text`: Alt text for the logo image.

**Returns:**

* HTML for logo image tag.

### `create_status_message` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/ui.py#L516](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/ui.py#L516)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
create_status_message(message: str, is_success: bool = True) -> str
```

Create a status message with icon.

**Args:**

* `message`: Status message text
* `is_success`: True for success (✓), False for error (✕)

**Returns:**

* HTML for status message

### `create_info_box` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/ui.py#L539](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/ui.py#L539)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
create_info_box(content: str, is_error: bool = False, centered: bool = False, monospace: bool = False) -> str
```

Create an info box.

**Args:**

* `content`: HTML content for the info box
* `is_error`: True for error styling, False for normal
* `centered`: True to center the text, False for left-aligned
* `monospace`: True to use gray monospace font styling instead of blue

**Returns:**

* HTML for info box

### `create_detail_box` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/ui.py#L568](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/ui.py#L568)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
create_detail_box(rows: list[tuple[str, str]]) -> str
```

Create a detail box with key-value pairs.

**Args:**

* `rows`: List of (label, value) tuples

**Returns:**

* HTML for detail box

### `create_button_group` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/ui.py#L591](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/ui.py#L591)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
create_button_group(buttons: list[tuple[str, str, str]]) -> str
```

Create a group of buttons.

**Args:**

* `buttons`: List of (text, value, css\_class) tuples

**Returns:**

* HTML for button group

### `create_secure_html_response` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/utilities/ui.py#L609](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/utilities/ui.py#L609)</sup>

```python theme={"theme":{"light":"snazzy-light","dark":"dark-plus"}}
create_secure_html_response(html: str, status_code: int = 200) -> HTMLResponse
```

Create an HTMLResponse with security headers.

Adds X-Frame-Options: DENY to prevent clickjacking attacks per MCP security best practices.

**Args:**

* `html`: HTML content to return
* `status_code`: HTTP status code

**Returns:**

* HTMLResponse with security headers


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.