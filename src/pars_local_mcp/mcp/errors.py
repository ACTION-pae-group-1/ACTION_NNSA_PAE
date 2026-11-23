"""Client-safe error responses for PARS tools.

Tool errors go back to the MCP client. Exception text can contain database
paths, SQL fragments, or data values, so an unexpected exception returns a fixed
message only. The server log records the exception class name, never its message.

Raise PublicError for a validation message that is safe to show the client as written.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("pars_local_mcp")

GENERIC_MESSAGE = "The operation failed. The server log has the details."


class PublicError(Exception):
    """An error whose message is safe to return to the client unchanged."""


def tool_error(exc: BaseException) -> dict[str, Any]:
    """Map an exception to the error dict a tool returns to the client."""
    if isinstance(exc, PublicError):
        return {"error": str(exc)}
    logger.error("tool_failed error_type=%s", type(exc).__name__)
    return {"error": GENERIC_MESSAGE}


def require_range(name: str, value: int | float, low: int | float, high: int | float):
    """Return value if low <= value <= high, otherwise raise PublicError."""
    if not low <= value <= high:
        raise PublicError(f"{name} must be between {low} and {high}")
    return value
