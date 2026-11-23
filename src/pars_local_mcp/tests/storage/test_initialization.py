"""Tests for database initialization module."""

from __future__ import annotations

import duckdb
import pytest

from pars_local_mcp.mcp.errors import PublicError
from pars_local_mcp.storage.initialization import (
    SYNTHETIC_MARKER_TABLE,
    generate_labeled_wbs_training_data,
    generate_synthetic_wbs_elements,
    initialize_database,
)


def _tables(db) -> set[str]:
    conn = duckdb.connect(str(db), read_only=True)
    try:
        return {row[0] for row in conn.execute("SHOW TABLES").fetchall()}
    finally:
        conn.close()


class TestResetGuard:
    """Startup never drops tables in a database not known to be synthetic."""

    def test_new_database_is_created_and_marked_synthetic(self, tmp_path):
        db = tmp_path / "fresh.duckdb"
        initialize_database(db, synthetic_root=tmp_path / "data")
        assert {"wbs_elements", "projects", SYNTHETIC_MARKER_TABLE} <= _tables(db)

    def test_marked_database_is_regenerated_on_restart(self, tmp_path):
        db = tmp_path / "again.duckdb"
        initialize_database(db, synthetic_root=tmp_path / "data")
        initialize_database(db, synthetic_root=tmp_path / "data")
        assert SYNTHETIC_MARKER_TABLE in _tables(db)

    def test_unmarked_database_outside_synthetic_root_is_not_reset(self, tmp_path):
        db = tmp_path / "shared.duckdb"
        conn = duckdb.connect(str(db))
        conn.execute("CREATE TABLE wbs_elements (x INTEGER)")
        conn.execute("INSERT INTO wbs_elements VALUES (42)")
        conn.close()

        with pytest.raises(PublicError, match="not marked as synthetic"):
            initialize_database(db, synthetic_root=tmp_path / "data")

        conn = duckdb.connect(str(db), read_only=True)
        try:
            assert conn.execute("SELECT count(*) FROM wbs_elements").fetchone()[0] == 1
        finally:
            conn.close()

    def test_unmarked_database_under_synthetic_root_is_regenerated(self, tmp_path):
        root = tmp_path / "data"
        root.mkdir()
        db = root / "legacy_mock.duckdb"
        conn = duckdb.connect(str(db))
        conn.execute("CREATE TABLE wbs_elements (x INTEGER)")
        conn.close()

        initialize_database(db, synthetic_root=root)

        assert SYNTHETIC_MARKER_TABLE in _tables(db)


class TestGenerateLabeledWBSData:
    """Test labeled WBS training data generation."""

    def test_generate_labeled_wbs_returns_tuples(self):
        """Test that generate_labeled_wbs_training_data returns list of tuples."""
        data = generate_labeled_wbs_training_data()
        assert isinstance(data, list)
        assert len(data) > 0
        assert all(isinstance(item, tuple) for item in data)

    def test_labeled_data_tuple_format(self):
        """Test that each tuple has correct format and length."""
        data = generate_labeled_wbs_training_data()
        for item in data:
            assert len(item) == 10  # parsid, wbs_code, title, caef_L2-L8
            # All elements should be strings
            assert all(isinstance(x, str) for x in item)

    def test_labeled_data_contains_59_records(self):
        """Test that labeled training data contains 59 records."""
        data = generate_labeled_wbs_training_data()
        assert len(data) == 59

    def test_labeled_data_parsid_values(self):
        """Test that records have proj_001 or proj_002 parsid."""
        data = generate_labeled_wbs_training_data()
        parsids = {item[0] for item in data}
        assert parsids.issubset({"proj_001", "proj_002"})
        # Should have both projects
        assert len(parsids) == 2

    def test_labeled_data_caef_codes_format(self):
        """Test that CAEF codes follow expected format (e.g., E1, E1.1, etc.)."""
        data = generate_labeled_wbs_training_data()
        for parsid, wbs_code, title, l2, l3, l4, l5, l6, l7, l8 in data:
            # Level 2 should always have a code for training data
            assert l2, f"Level 2 CAEF code missing for {wbs_code}"
            # Higher levels can be empty
            for level_code in [l3, l4, l5, l6, l7, l8]:
                # Should be either empty or match pattern (E + digits/dots)
                if level_code:
                    assert level_code[0] == "E", f"Invalid CAEF code: {level_code}"


def test_stadium_titles_match_across_startup_wbs_tables():
    labeled = {(row[0], row[1]): row[2] for row in generate_labeled_wbs_training_data()}
    hierarchy = {(row[0], row[1]): row[2] for row in generate_synthetic_wbs_elements()}
    assert labeled == hierarchy
    assert all(
        len(title.split(" - ", 1)) == 2
        and all(part.strip() for part in title.split(" - ", 1))
        for title in labeled.values()
    )


def test_initialized_project_names_are_sports_venues(tmp_path):
    db = tmp_path / "stadiums.duckdb"
    initialize_database(db)
    with duckdb.connect(str(db), read_only=True) as conn:
        names = [
            row[0]
            for row in conn.execute("SELECT project_name FROM projects").fetchall()
        ]
    assert len(names) == 2
    assert all("Stadium" in name for name in names)
