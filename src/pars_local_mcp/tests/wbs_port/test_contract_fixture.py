"""Tests for wbs_port.contract_fixture, the labeled test fixture for the WBS pipeline.

Every output is written under pytest's tmp_path. The fixture is built from the default
CAEF and mock inputs in pars_local_mcp/data.
"""

from __future__ import annotations

import re

import duckdb
import pytest

from pars_local_mcp.data.generate_full_mock import PROJECT_PARSIDS
from pars_local_mcp.wbs_port import pipeline as P
from pars_local_mcp.wbs_port.contract_fixture import (
    CAEF_DB,
    FIXTURE_MARKER,
    SAMPLE_PROJECTS,
    build_contract_fixture,
)

SUPPORTING_TABLES = {
    "bronze_abbreviations",
    "silver_stop_words",
    "bronze_stop_phrases",
    "silver_project_descriptions",
}
FIXTURE_TABLES = {
    "gold_corrections",
    "silver_spae_data",
    "silver_corrections",
    "_fixture_marker",
} | SUPPORTING_TABLES
CAEF_SOURCE_ROWS = 16680
ROWS_PER_PROJECT = 834
ALL_PARSIDS = {str(p) for p in PROJECT_PARSIDS}
SAMPLE_PARSIDS = {str(p) for p in sorted(PROJECT_PARSIDS)[:SAMPLE_PROJECTS]}
# All CAEF rows for each sample project.
SAMPLE_ROWS = SAMPLE_PROJECTS * ROWS_PER_PROJECT
INTEGER_TEXT = re.compile(r"[0-9]+")


@pytest.fixture(scope="module")
def fixture_db(tmp_path_factory):
    return build_contract_fixture(
        tmp_path_factory.mktemp("contract_fixture") / "contract_fixture.duckdb"
    )


@pytest.fixture
def fixture_con(fixture_db):
    con = duckdb.connect(str(fixture_db), read_only=True)
    try:
        yield con
    finally:
        con.close()


def _table_names(con):
    rows = con.execute("SELECT table_name FROM information_schema.tables").fetchall()
    return {r[0] for r in rows}


def _count(con, table):
    return con.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]


def _distinct(con, table, column):
    rows = con.execute(f'SELECT DISTINCT "{column}" FROM "{table}"').fetchall()
    return {r[0] for r in rows}


def test_build_writes_a_file_that_duckdb_opens_read_only(tmp_path):
    out = tmp_path / "nested" / "contract_fixture.duckdb"

    returned = build_contract_fixture(out)

    assert returned == out
    assert out.is_file()
    con = duckdb.connect(str(out), read_only=True)
    try:
        assert con.execute("SELECT count(*) FROM _fixture_marker").fetchone() == (1,)
    finally:
        con.close()


def test_fixture_contains_exactly_the_contract_tables(fixture_con):
    assert _table_names(fixture_con) == FIXTURE_TABLES


def test_row_counts_are_sample_projects_and_all_spae_rows(fixture_con):
    caef = duckdb.connect(str(CAEF_DB), read_only=True)
    try:
        assert _count(caef, "labeled_wbs") == CAEF_SOURCE_ROWS
        source_per_project = dict(
            caef.execute(
                "SELECT parsid, count(*) FROM labeled_wbs GROUP BY parsid"
            ).fetchall()
        )
    finally:
        caef.close()
    assert source_per_project == {p: ROWS_PER_PROJECT for p in ALL_PARSIDS}

    assert _count(fixture_con, "gold_corrections") == SAMPLE_ROWS
    assert _count(fixture_con, "silver_spae_data") == CAEF_SOURCE_ROWS
    gold_per_project = dict(
        fixture_con.execute(
            "SELECT parsid, count(*) FROM gold_corrections GROUP BY parsid"
        ).fetchall()
    )
    assert gold_per_project == {p: ROWS_PER_PROJECT for p in SAMPLE_PARSIDS}


def test_silver_corrections_equals_gold_corrections_row_for_row(fixture_con):
    gold = fixture_con.execute("SELECT * FROM gold_corrections").fetchall()
    corrections = fixture_con.execute("SELECT * FROM silver_corrections").fetchall()

    assert len(corrections) == len(gold) == SAMPLE_ROWS
    assert sorted(corrections) == sorted(gold)


def test_marker_table_holds_the_fixture_marker_text(fixture_con):
    rows = fixture_con.execute("SELECT note FROM _fixture_marker").fetchall()

    assert rows == [(FIXTURE_MARKER,)]


def test_parsid_is_integer_text_for_spae_and_gold(fixture_con):
    spae = _distinct(fixture_con, "silver_spae_data", "parsid")
    gold = _distinct(fixture_con, "gold_corrections", "parsid")

    assert spae == ALL_PARSIDS
    assert gold == SAMPLE_PARSIDS
    assert all(INTEGER_TEXT.fullmatch(value) for value in spae | gold)


@pytest.mark.parametrize("table", ["gold_corrections", "silver_spae_data"])
def test_wbs_level_is_integer_text_equal_to_wbs_code_depth(fixture_con, table):
    rows = fixture_con.execute(f'SELECT wbs, wbs_level FROM "{table}"').fetchall()

    assert rows
    mismatches = [
        (wbs, level)
        for wbs, level in rows
        if not INTEGER_TEXT.fullmatch(level) or level != str(len(wbs.split(".")))
    ]
    assert mismatches == []


def test_fixture_passes_validate_source(fixture_db):
    report = P.validate_source(fixture_db)

    assert report["ok"] is True, report["problems"]
    assert report["problems"] == []
    assert report["data_origin"] == "labeled_test_fixture"
