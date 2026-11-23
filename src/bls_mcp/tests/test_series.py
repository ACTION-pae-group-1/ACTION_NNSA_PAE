"""Validation tests for BLS series search requests."""

import pytest
from pydantic import ValidationError

from bls_mcp.models.series import SeriesSearchRequest


@pytest.mark.parametrize("program", ["pc", "ci", "pd", "wp"])
def test_valid_program_codes(program):
    request = SeriesSearchRequest(programs=[program])
    assert request.programs == [program]


@pytest.mark.parametrize("program", ["PC", "CI", "PPI", "invalid"])
def test_invalid_program_codes(program):
    with pytest.raises(ValidationError):
        SeriesSearchRequest(programs=[program])


def test_default_search_request():
    request = SeriesSearchRequest()

    assert request.query == ""
    assert request.programs is None
    assert request.active_only is True
    assert request.limit == 25


@pytest.mark.parametrize("limit", [0, 101])
def test_invalid_search_limits(limit):
    with pytest.raises(ValidationError):
        SeriesSearchRequest(limit=limit)
