"""Tool errors must not leak exception text (paths, SQL, data values) to clients."""

from __future__ import annotations

import logging

import pytest

from pars_local_mcp.mcp.errors import (
    GENERIC_MESSAGE,
    PublicError,
    require_range,
    tool_error,
)


def test_unexpected_exception_text_is_not_returned(caplog) -> None:
    exc = RuntimeError("cannot open /secret/path/mock.duckdb near SELECT secret_value")
    with caplog.at_level(logging.ERROR, logger="pars_local_mcp"):
        result = tool_error(exc)
    assert result == {"error": GENERIC_MESSAGE}
    assert "/secret/path" not in str(result)
    assert "secret_value" not in str(result)
    # Server logs record the exception class only, never its message.
    assert "error_type=RuntimeError" in caplog.text
    assert "/secret/path" not in caplog.text
    assert "secret_value" not in caplog.text


def test_public_error_message_is_returned_as_written() -> None:
    result = tool_error(PublicError("level must be between 1 and 8"))
    assert result == {"error": "level must be between 1 and 8"}


def test_public_error_is_an_exception() -> None:
    assert issubclass(PublicError, Exception)


def test_require_range_accepts_inclusive_bounds() -> None:
    assert require_range("level", 1, 1, 8) == 1
    assert require_range("level", 8, 1, 8) == 8


@pytest.mark.parametrize("value", [0, 9, -1])
def test_require_range_rejects_values_outside_the_bounds(value: int) -> None:
    with pytest.raises(PublicError, match="level must be between 1 and 8"):
        require_range("level", value, 1, 8)
