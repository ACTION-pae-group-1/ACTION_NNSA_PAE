"""Tests for decimal-safe display formatting used by every screen."""

from decimal import Decimal

import pytest

from cost_intel_ui.formatting import fixed, percent_of_fraction, signed, to_decimal


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1.126250052151", Decimal("1.126250052151")),
        (15, Decimal("15")),
        (0.1, Decimal("0.1")),
        (Decimal("2.5"), Decimal("2.5")),
    ],
)
def test_to_decimal_accepts_strings_ints_floats_and_decimals(value, expected):
    assert to_decimal(value) == expected


@pytest.mark.parametrize("value", [None, "", "abc", "NaN", "Infinity", float("nan")])
def test_to_decimal_rejects_non_finite_or_missing_values(value):
    with pytest.raises(ValueError):
        to_decimal(value)


def test_fixed_rounds_half_up_like_the_intended_decimal_display():
    assert fixed("1.126250052151", 4) == "1.1263"
    assert fixed("0.125", 2) == "0.13"
    assert fixed(100, 2) == "100.00"


def test_fixed_defaults_to_two_places():
    assert fixed("12.625005215100") == "12.63"


def test_signed_prefixes_plus_for_zero_and_positive_values():
    assert signed("12.6250052151", 2) == "+12.63"
    assert signed("0", 2) == "+0.00"
    assert signed("-11.2097710371", 2) == "-11.21"


def test_percent_of_fraction_scales_by_one_hundred():
    assert percent_of_fraction("0.450000000000") == "45.00"
    assert percent_of_fraction("-0.046348499519", 8) == "-4.63484995"
