"""Decimal-safe display formatting.

The calculation contract transmits economic quantities as decimal strings. These
helpers format them for display without passing through binary floats.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

Number = str | int | float | Decimal


def to_decimal(value: Number | None) -> Decimal:
    """Convert a contract value to a finite Decimal, or raise ValueError."""
    if value is None or isinstance(value, bool):
        raise ValueError("A numeric value is required")
    try:
        result = Decimal(str(value)) if isinstance(value, float) else Decimal(value)
    except (InvalidOperation, TypeError) as exc:
        raise ValueError(f"Not a decimal value: {value!r}") from exc
    if not result.is_finite():
        raise ValueError(f"Not a finite decimal value: {value!r}")
    return result


def fixed(value: Number, places: int = 2) -> str:
    """Format with a fixed number of decimal places, rounding half up."""
    quantum = Decimal(1).scaleb(-places)
    return f"{to_decimal(value).quantize(quantum, rounding=ROUND_HALF_UP):f}"


def signed(value: Number, places: int = 2) -> str:
    """Format with an explicit sign; zero and positive values get a plus."""
    text = fixed(value, places)
    return text if text.startswith("-") else f"+{text}"


def percent_of_fraction(value: Number, places: int = 2) -> str:
    """Format a fraction (0.45) as a percent number (45.00) without the sign."""
    return fixed(to_decimal(value) * 100, places)
