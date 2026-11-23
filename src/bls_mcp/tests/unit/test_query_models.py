"""Query request validation does not depend on the native DuckDB wheel."""

import pytest

from bls_mcp.storage.query_models import (
    MAX_SERIES_IDS,
    SeriesSearchFilters,
    validate_max_rows,
    validate_normalization,
    validate_series_ids,
    validate_window,
)


def test_search_filters_validate_bounded_inputs():
    assert SeriesSearchFilters(programs=("pc", "cu"), offset=10).limit == 50
    for filters in (
        {"limit": 0},
        {"limit": 1_001},
        {"offset": -1},
        {"offset": 1_000_001},
        {"query": "a" * 257},
        {"programs": ()},
        {"programs": ("pc", "pc")},
        {"programs": ("PC",)},
        {"industry_code": ""},
        {"active_only": "yes"},
        {"seasonal_adjustment": 1},
    ):
        with pytest.raises(ValueError):
            SeriesSearchFilters(**filters)


def test_series_ids_reject_strings_duplicates_and_oversized_batches():
    assert validate_series_ids(["A", "B"]) == ("A", "B")
    for ids in (
        [],
        ["A", "A"],
        [""],
        [" space "],
        ["a" * 129],
        [str(i) for i in range(MAX_SERIES_IDS + 1)],
    ):
        with pytest.raises(ValueError):
            validate_series_ids(ids)
    with pytest.raises(TypeError):
        validate_series_ids("A")


def test_year_bounds_target_base_and_row_cap_are_strict():
    for start, end in ((2026, 2025), (0, None), (None, 32768), (True, None)):
        with pytest.raises(ValueError):
            validate_window(start, end)
    for year, period, target in (
        (2025, "M14", 100.0),
        (2025, "Q05", 100.0),
        (2025, "S00", 100.0),
        (0, "M01", 100.0),
        (2025, "M01", 0.0),
        (2025, "M01", float("nan")),
        (2025, "M01", float("inf")),
        (2025, "M01", True),
    ):
        with pytest.raises(ValueError):
            validate_normalization(year, period, target)
    for invalid in (0, -1, 1_000_001, True):
        with pytest.raises(ValueError):
            validate_max_rows(invalid)
    validate_normalization(2025, "M13", 100.0)
    validate_normalization(2025, "Q04", 100.0)
    validate_normalization(2025, "S03", 100.0)
