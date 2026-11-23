"""Tests for the full mock database generator."""

import json

import duckdb
import pytest

from pars_local_mcp.data.generate_full_mock import (
    DATA_DIR,
    MARKER_TABLE,
    PROJECT_NAMES,
    SCHEMA_FILE,
    build_mock_database,
    element_titles,
)


@pytest.fixture
def small_db(tmp_path, monkeypatch):

    target = DATA_DIR / "_test_mock_pars_full.duckdb"
    counts = build_mock_database(output_path=target, fact_rows=40, reference_rows=5)
    yield target, counts
    if target.exists():
        target.unlink()


def test_every_schema_table_is_created(small_db):
    target, counts = small_db
    expected = set(json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))["tables"])
    assert set(counts) == expected
    con = duckdb.connect(str(target), read_only=True)
    try:
        present = {
            r[0]
            for r in con.execute(
                "select table_name from information_schema.tables where "
                "table_schema='main'"
            ).fetchall()
        }
    finally:
        con.close()
    assert expected <= present


def test_columns_match_schema(small_db):
    target, _ = small_db
    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))["tables"]
    con = duckdb.connect(str(target), read_only=True)
    try:
        for table, columns in schema.items():
            actual = [
                r[0]
                for r in con.execute(
                    "select column_name from information_schema.columns "
                    "where table_schema='main' and table_name=? "
                    "order by ordinal_position",
                    [table],
                ).fetchall()
            ]
            assert actual == [c["name"] for c in columns], table
    finally:
        con.close()


def test_marker_table_marks_data_as_synthetic(small_db):
    target, _ = small_db
    con = duckdb.connect(str(target), read_only=True)
    try:
        note = con.execute(f'select note from "{MARKER_TABLE}"').fetchone()[0]
    finally:
        con.close()
    assert "SYNTHETIC MOCK DATA" in note


def test_row_counts_follow_fact_and_reference_sizes(small_db):
    _, counts = small_db
    assert counts["silver_spae_data"] == 40
    assert counts["bronze_abbreviations"] == 5


def test_output_outside_data_directory_is_refused(tmp_path):
    with pytest.raises(ValueError, match="inside"):
        build_mock_database(output_path=tmp_path / "x.duckdb", fact_rows=1)


def test_stadium_names_and_faker_titles_are_reproducible():
    assert len(PROJECT_NAMES) == 20
    assert len(set(PROJECT_NAMES)) == 20
    assert all(
        "stadium" in name.lower()
        or any(
            word in name.lower()
            for word in ("ballpark", "arena", "athletics", "aquatics", "grandstand")
        )
        for name in PROJECT_NAMES
    )
    titles = element_titles(250, seed=42)
    assert titles == element_titles(250, seed=42)
    assert len(set(titles)) == 250
    assert any("roof" in title.lower() for title in titles)
    assert not any("nuclear" in title.lower() for title in titles)


def test_mock_stadium_description_and_costs_preserve_schema(small_db):
    target, _ = small_db
    with duckdb.connect(str(target), read_only=True) as con:
        descriptions = con.execute(
            "SELECT project_name, project_description, nuclear_non_nuclear "
            "FROM silver_project_descriptions"
        ).fetchall()
        assert all(name in description for name, description, _ in descriptions)
        assert all(
            "stadium" in description.lower() for _, description, _ in descriptions
        )
        assert {flag for _, _, flag in descriptions} == {"Non-Nuclear"}
        costs = con.execute(
            'SELECT "INC_BCWS_Dollars" FROM bronze_spae_data LIMIT 5'
        ).fetchall()
        assert all(float(row[0]) >= 2_500_000 for row in costs)
