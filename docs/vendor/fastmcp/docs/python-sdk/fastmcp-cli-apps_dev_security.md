> ## Documentation Index
> Fetch the complete documentation index at: https://gofastmcp.com/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# apps_dev_security

# `fastmcp.cli.apps_dev_security`

Browser session, Host, and Origin checks for the `fastmcp dev apps` host.

## Classes

### `DevSessionMiddleware` <sup>[https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp\_slim/fastmcp/cli/apps\_dev\_security.py#L38](https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/cli/apps_dev_security.py#L38)</sup>

Require a browser session started from the private startup URL.

`GET /?token=...` with the startup token sets an HttpOnly, SameSite=Strict
cookie and redirects to `/`. Every other request needs that cookie. The
cookie holds a separate session secret: browsers send cookies to every
port on the host, and the startup token must not reach other services. Every
request must also name this server in its Host header, and browser
requests must come from this origin: cookies do not distinguish ports on
the same host, so the Origin and Fetch Metadata headers are checked too.


This documentation is built and hosted on [Mintlify](https://mintlify.com), a developer documentation platform.