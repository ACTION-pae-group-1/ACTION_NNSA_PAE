"""Companion tests for the series models agents send to search_series."""

from __future__ import annotations

import re

import pydantic
import pytest

from bls_mcp.models.series import ProgramCode, SeriesSearchRequest

SUPPORTED_PROGRAMS: list[ProgramCode] = ["pc", "pd", "wp", "ci", "cu", "oe"]


def test_each_supported_program_code_is_accepted() -> None:
    request = SeriesSearchRequest(programs=SUPPORTED_PROGRAMS)
    assert request.programs == SUPPORTED_PROGRAMS


@pytest.mark.parametrize("bad", ["PPI", "ECI", "CPI", "OEWS", "PC", "xx"])
def test_unknown_program_error_names_the_valid_codes(bad: str) -> None:
    with pytest.raises(pydantic.ValidationError) as error:
        SeriesSearchRequest.model_validate({"programs": [bad]})

    message = str(error.value)
    for code in SUPPORTED_PROGRAMS:
        assert f"'{code}'" in message


def test_program_description_keeps_each_code_in_its_own_sentence() -> None:
    """The description is model-facing; codes must not run into each other."""
    description = SeriesSearchRequest.model_fields["programs"].description or ""

    for code in SUPPORTED_PROGRAMS:
        assert f" {code}: " in description
    assert re.search(r"[.:;][a-z]{2}:", description) is None


def test_program_description_names_cpi_and_oews() -> None:
    description = SeriesSearchRequest.model_fields["programs"].description or ""

    assert "Consumer Price Index" in description
    assert "Occupational Employment and Wage Statistics" in description


@pytest.mark.parametrize("limit", [0, 101])
def test_limit_outside_bounds_is_rejected(limit: int) -> None:
    with pytest.raises(pydantic.ValidationError):
        SeriesSearchRequest(limit=limit)
