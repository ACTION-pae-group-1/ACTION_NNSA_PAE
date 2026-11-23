"""Offline schema checks against small scratch DuckDB databases."""

from pathlib import Path

import pytest

duckdb = pytest.importorskip("duckdb")

from bls_mcp.storage.connection import build_connection  # noqa: E402
from bls_mcp.storage.schema import SCHEMA_VERSION, initialize_schema  # noqa: E402


@pytest.fixture
def conn(tmp_path: Path):
    with build_connection(tmp_path / "build.duckdb") as writer:
        initialize_schema(writer)
        yield writer


def test_initialization_creates_program_and_provenance_tables(conn):
    actual = {
        row[0]
        for row in conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()
    }
    assert {
        "snapshot_info",
        "source_files",
        "series_catalog",
        "observations",
        "pc_series",
        "pc_industry",
        "pc_product",
        "cu_series",
        "cu_area",
        "cu_item",
        "ci_series",
        "ci_dimension",
        "wp_series",
        "wp_group",
        "wp_item",
    } <= actual
    assert SCHEMA_VERSION == 5
    cols = {
        row[1]: row[2]
        for row in conn.execute("PRAGMA table_info('observations')").fetchall()
    }
    assert cols["year"] == "SMALLINT"
    assert cols["value"] == "DOUBLE"
    assert "source_file_id" in cols
    assert "footnote_codes" in cols
    cu_columns = {
        row[1]: row[2]
        for row in conn.execute("PRAGMA table_info('cu_series')").fetchall()
    }
    assert cu_columns["periodicity_code"] == "VARCHAR"
    assert cu_columns["base_code"] == "VARCHAR"
    assert cu_columns["base_period"] == "VARCHAR"
    area_columns = {
        row[1]: row[2]
        for row in conn.execute("PRAGMA table_info('cu_area')").fetchall()
    }
    assert area_columns["selectable"] == "BOOLEAN"
    item_columns = {
        row[1]: row[2]
        for row in conn.execute("PRAGMA table_info('cu_item')").fetchall()
    }
    assert item_columns["selectable"] == "BOOLEAN"
    initialize_schema(conn)  # No changes to existing tables or data.


def test_empty_schema_defers_art_index_and_rejects_nonfinite_values(conn):
    # Milestone 3 creates the explicit ART index *after* PC bulk insertion.
    assert (
        conn.execute(
            "SELECT COUNT(*) FROM duckdb_indexes() WHERE table_name = 'observations'"
        ).fetchone()[0]
        == 0
    )
    conn.execute(
        """
        INSERT INTO observations VALUES
          ('CIU1010000000000I', 2025, 'Q01', 141.5, NULL, 1),
          ('CIU1010000000000I', 2025, 'Q04', 150.0, NULL, 1),
          ('PCU_TEST', 2025, 'M13', 130.0, 'P', 2)
        """
    )
    assert conn.execute(
        "SELECT period FROM observations ORDER BY series_id, year, period"
    ).fetchall() == [("Q01",), ("Q04",), ("M13",)]
    for value in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(duckdb.ConstraintException):
            conn.execute(
                "INSERT INTO observations VALUES ('XX', 2025, 'M01', ?, NULL, 1)",
                [value],
            )


def test_pc_product_is_keyed_by_industry_and_product(conn):
    conn.execute(
        """
        INSERT INTO pc_product VALUES
          ('111', '01', 'Industry A product'),
          ('222', '01', 'Industry B product')
        """
    )
    assert conn.execute(
        "SELECT product_name FROM pc_product "
        "WHERE industry_code = ? AND product_code = ?",
        ["222", "01"],
    ).fetchone() == ("Industry B product",)
    with pytest.raises(duckdb.ConstraintException):
        conn.execute("INSERT INTO pc_product VALUES ('222', '01', 'duplicate')")
