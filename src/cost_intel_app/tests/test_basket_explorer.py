"""Tests for the approved basket's explorer controls.

The component ribbon, the Normalized and Raw toggle, the source-year select, and
the period, component, and sort filters all go through ``explore_basket``. The
choices live in the basket state, so each request carries them back.
"""

import pytest

from cost_intel_app.basket_state import (
    META_CHIP_SLOTS,
    STAT_SLOTS,
    VIEW_ERROR,
    _slots,
    approve_basket,
    catalog_adjustment_years,
    catalog_periods,
    choose_preset,
    explore_basket,
    initial_basket,
)
from cost_intel_ui.fake_data import InMemoryDataSource
from cost_intel_ui.results_view import component_detail

NOW = "2026-11-13T00:00:00+00:00"
ALL_PERIODS = ("2021", "2022", "2023", "2024", "2025", "2026")


@pytest.fixture
def source():
    return InMemoryDataSource()


def _allocation(source, project_key="y12", scenario="recommended"):
    weights = source.scenario_weights(project_key)[scenario]
    return [{"enabled": True, "weight": str(w)} for w in weights]


def _approved(source, project_key="y12", scenario="recommended"):
    rows = _allocation(source, project_key, scenario)
    return approve_basket(source, project_key, rows, "review", NOW)


def _explore(source, locked, **choices):
    rows = [{"enabled": r["enabled"], "weight": r["weight"]} for r in locked["rows"]]
    return explore_basket(
        source, "y12", rows, "approved", locked["scenario"], **choices
    )


def _visible(slots):
    return [slot for slot in slots if slot["visible"]]


def test_default_selection_is_the_first_component_and_latest_year(source):
    selection = _approved(source)["results"]["selection"]
    assert selection == {
        "component": "electric",
        "mode": "normalized",
        "source_year": "2026",
        "table_year": "all",
        "table_comp": "all",
        "table_sort": "asc",
    }


def test_ribbon_marks_exactly_the_chosen_component(source):
    state = _explore(source, _approved(source), component="steel")
    ribbon = state["results"]["explorer"]["ribbon"]
    assert [s["component_id"] for s in ribbon if s["selected"]] == ["steel"]
    assert state["results"]["component"]["component_id"] == "steel"
    assert state["results"]["selection"]["component"] == "steel"


def test_raw_mode_shows_the_raw_ppi_series(source):
    state = _explore(source, _approved(source), component="electric", mode="raw")
    packet = source.get_result("y12", "recommended")
    raw = component_detail(packet, "electric", "raw")
    rows = state["results"]["component"]["rows"]
    assert [r["period"] for r in rows] == [str(y) for y in raw.years]
    assert [r["value"] for r in rows] == pytest.approx(list(raw.values))
    assert state["results"]["selection"]["mode"] == "raw"


def test_source_year_chooses_that_years_adjustment(source):
    state = _explore(source, _approved(source), source_year="2024")
    adjustment = state["results"]["adjustment"]
    assert adjustment["year"] == "2024"
    assert adjustment["source_year"] == "2024"
    assert len(_visible(adjustment["math_rows"])) == 4
    assert state["results"]["selection"]["source_year"] == "2024"


def test_base_year_does_not_invent_an_adjustment(source):
    state = _explore(source, _approved(source), source_year="2023")
    adjustment = state["results"]["adjustment"]
    assert adjustment["year"] == "2023"
    assert adjustment["message"]
    assert not _visible(adjustment["math_rows"])
    assert state["results"]["selection"]["source_year"] == "2023"


def test_table_filters_narrow_the_rows_and_count_them(source):
    state = _explore(
        source,
        _approved(source),
        table_comp="steel",
        table_sort="desc",
    )
    table = state["results"]["table"]
    assert len(table["rows"]) == 6
    assert {r["component_id"] for r in table["rows"]} == {"steel"}
    assert table["rows"][0]["period"] == "2026"
    assert table["rows"][-1]["period"] == "2021"
    assert table["count_label"] == "6 of 24 observations"


def test_period_filter_keeps_every_component_for_one_year(source):
    state = _explore(source, _approved(source), table_year="2024")
    table = state["results"]["table"]
    assert {r["period"] for r in table["rows"]} == {"2024"}
    assert len(table["rows"]) == 4
    assert table["count_label"] == "4 of 24 observations"


def test_default_table_count_is_every_observation(source):
    table = _approved(source)["results"]["table"]
    assert table["count_label"] == "24 of 24 observations"


def test_unknown_component_is_refused_and_the_locked_basket_stays(source):
    state = _explore(source, _approved(source), component="not-a-component")
    assert state["state"] == "error"
    assert state["error"] == VIEW_ERROR
    assert state["toast"] == VIEW_ERROR
    assert state["locked"] is True
    assert state["results"]["selection"]["component"] == "electric"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_year", "1999"),
        ("table_year", "1999"),
        ("table_comp", "not-a-component"),
        ("table_sort", "sideways"),
        ("mode", "bogus"),
    ],
)
def test_unknown_year_filter_sort_or_unit_is_refused(source, field, value):
    state = _explore(source, _approved(source), **{field: value})
    assert state["error"] == VIEW_ERROR
    assert state["locked"] is True


def test_an_empty_component_falls_back_to_the_first_component(source):
    state = _explore(source, _approved(source), component="")
    assert state["results"]["selection"]["component"] == "electric"


def test_choices_change_nothing_in_review(source):
    basket = initial_basket(source, "y12")
    rows = [{"enabled": r["enabled"], "weight": r["weight"]} for r in basket["rows"]]
    state = explore_basket(
        source, "y12", rows, "review", None, component="steel", mode="raw"
    )
    assert state["phase"] == "review"
    assert state["results"] is None


def test_a_new_approval_starts_from_the_default_selection(source):
    locked = _approved(source)
    _explore(source, locked, component="steel", mode="raw", table_sort="desc")
    reviewed = choose_preset(source, "y12", "materials", "approved")
    assert reviewed["phase"] == "review"
    again = approve_basket(source, "y12", _allocation(source), "review", NOW)
    assert again["results"]["selection"]["component"] == "electric"
    assert again["results"]["selection"]["mode"] == "normalized"
    assert again["results"]["selection"]["table_sort"] == "asc"


def test_every_result_fits_the_view_slots(source):
    for project in source.list_projects():
        for scenario in source.scenario_weights(project.key):
            locked = _approved(source, project.key, scenario)
            explorer = locked["results"]["explorer"]
            components = [
                c["component_id"]
                for c in source.get_result(project.key, scenario).result["components"]
            ]
            assert len(explorer["stats"]) == STAT_SLOTS
            assert len(_visible(explorer["stats"])) == STAT_SLOTS
            assert len(explorer["meta_chips"]) == META_CHIP_SLOTS
            assert len(_visible(explorer["ribbon"])) == len(components)
            adjustment = locked["results"]["adjustment"]
            assert len(_visible(adjustment["math_rows"])) == len(components)


def test_slots_pad_with_blanks_and_refuse_to_drop_entries():
    assert _slots(["a"], 3, str) == ["a", "", ""]
    assert _slots([], 2, str) == ["", ""]
    with pytest.raises(ValueError):
        _slots(["a", "b"], 1, str)


def test_the_catalog_offers_every_period_and_eligible_year(source):
    assert catalog_periods(source) == ALL_PERIODS
    assert catalog_adjustment_years(source) == ALL_PERIODS
