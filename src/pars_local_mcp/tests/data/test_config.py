from __future__ import annotations

import pandas as pd
import polars as pl

from pars_local_mcp.data.config import (
    clean_text,
    clean_wbs,
    concatenate_data,
    input_reshaper,
    normalize_title,
    normalize_wbs,
    text_cleaning_function,
    transform,
)


def _elements():
    return pl.DataFrame(
        {
            "wbs": ["e1", "e2", "e3", "e4"],
            "wbs_title": ["Alpha", "Beta", "Gamma", "Delta"],
            "wbs_level": [2, 3, 4, 3],
        }
    )


def test_concatenate_builds_full_ancestor_chain_in_text_field():
    out = concatenate_data(
        _elements(),
        text_field="wbs_title",
        level_field="wbs_level",
        starting_level=2,
        with_dates=False,
    )

    chain = dict(zip(out["wbs"].to_list(), out["wbs_title"].to_list()))
    assert chain["e3"] == "Alpha | Beta | Gamma"
    assert chain["e4"] == "Alpha | Delta"


def test_concatenate_fills_each_level_column_with_ancestor_title():
    out = concatenate_data(
        _elements(),
        text_field="wbs_title",
        level_field="wbs_level",
        starting_level=2,
        with_dates=False,
    )

    row = out.filter(pl.col("wbs") == "e3").row(0, named=True)
    assert row["wbs_level_2"] == "Alpha"
    assert row["wbs_level_3"] == "Beta"
    assert row["wbs_level_4"] == "Gamma"


def test_concatenate_ignores_levels_below_starting_level():
    frame = pl.DataFrame(
        {
            "wbs": ["root", "e1", "e2"],
            "wbs_title": ["Root", "Alpha", "Beta"],
            "wbs_level": [1, 2, 3],
        }
    )
    out = concatenate_data(
        frame,
        text_field="wbs_title",
        level_field="wbs_level",
        starting_level=2,
        with_dates=False,
    )

    assert "root" not in out["wbs"].to_list()
    assert set(out["wbs"].to_list()) == {"e1", "e2"}


def test_transform_lowercases_level_columns_and_strips_leading_codes():
    frame = pl.DataFrame(
        {
            "wbs": ["1.2"],
            "parent_wbs": ["1"],
            "level_2": ["1.1 Project Management"],
        }
    )
    out = transform(frame)

    # Canon regex leaves a leading space after stripping the code prefix; kept verbatim.
    assert out["level_2"].to_list() == [" project management"]
    assert out["wbs"].to_list() == ["01.2"]


def test_normalize_wbs_pads_single_digit_codes():
    series = pd.Series(["1", "2.3", "Ab"])

    assert normalize_wbs(series).tolist() == ["01", "02.3", "ab"]


def test_normalize_title_lowercases_and_strips():
    series = pd.Series(["  Hello World  "])

    assert normalize_title(series).tolist() == ["hello world"]


def test_clean_wbs_removes_sentinel_suffix():
    series = pd.Series(["1.1.00000000000001"])

    assert clean_wbs(series).tolist() == ["01.1."]


def test_clean_text_collapses_costs_and_whitespace():
    series = pd.Series(["Labor-Costs   and  Commisioning "])

    assert clean_text(series).tolist() == ["Labor costs and commissioning"]


def test_text_cleaning_function_strips_punctuation_and_lowercases():
    assert text_cleaning_function("Hello, World! 42") == "hello world 42"


def test_input_reshaper_is_identity():
    data = [1, 2, 3]

    assert input_reshaper(data) is data
