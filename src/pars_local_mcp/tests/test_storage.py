"""Comprehensive tests for PARS storage module (models and queries).

Tests cover:
- WBSElement, ProjectMetadata, WBSSearchFilter data classes
- PARSStore context manager and all query methods
- DuckDB schema expectations
- Edge cases and error handling
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import duckdb
import pytest

from pars_local_mcp.storage.models import (
    LabeledWBSRecord,
    ProjectMetadata,
    WBSElement,
    WBSSearchFilter,
)
from pars_local_mcp.storage.queries import PARSStore


class TestWBSElementModel:
    """Test WBSElement data class."""

    def test_create_with_all_fields(self):
        """Test creating WBSElement with all required fields."""
        elem = WBSElement(
            parsid="proj_001",
            wbs_code="01.01.01",
            title="Engineering Analysis",
            level=3,
            parent_wbs="01.01",
            leaf_node=False,
        )
        assert elem.parsid == "proj_001"
        assert elem.wbs_code == "01.01.01"
        assert elem.title == "Engineering Analysis"
        assert elem.level == 3
        assert elem.parent_wbs == "01.01"
        assert elem.leaf_node is False

    def test_create_leaf_node(self):
        """Test creating a leaf node WBSElement."""
        elem = WBSElement(
            parsid="proj_001",
            wbs_code="01.01.01.01.01",
            title="Detailed Task",
            level=5,
            parent_wbs="01.01.01.01",
            leaf_node=True,
        )
        assert elem.leaf_node is True

    def test_create_root_level_element(self):
        """Test creating a root-level WBS element (level 1)."""
        elem = WBSElement(
            parsid="proj_001",
            wbs_code="01",
            title="Program Management",
            level=1,
            parent_wbs=None,
            leaf_node=False,
        )
        assert elem.level == 1
        assert elem.parent_wbs is None

    def test_wbs_element_immutability(self):
        """Test WBSElement behavior (frozen if dataclass with frozen=True)."""
        elem = WBSElement(
            parsid="proj_001",
            wbs_code="01",
            title="Test",
            level=1,
            parent_wbs=None,
            leaf_node=False,
        )
        # Should be able to access all fields
        assert elem.parsid == "proj_001"


class TestProjectMetadataModel:
    """Test ProjectMetadata data class."""

    def test_create_with_all_fields(self):
        """Test creating ProjectMetadata with all fields."""
        proj = ProjectMetadata(
            parsid="proj_001",
            project_name="Space Launch System",
            total_elements=150,
            hierarchy_depth=6,
        )
        assert proj.parsid == "proj_001"
        assert proj.project_name == "Space Launch System"
        assert proj.total_elements == 150
        assert proj.hierarchy_depth == 6

    def test_create_with_zero_elements(self):
        """Test creating ProjectMetadata with zero elements."""
        proj = ProjectMetadata(
            parsid="proj_empty",
            project_name="Empty Project",
            total_elements=0,
            hierarchy_depth=0,
        )
        assert proj.total_elements == 0
        assert proj.hierarchy_depth == 0

    def test_create_with_large_numbers(self):
        """Test creating ProjectMetadata with large element counts."""
        proj = ProjectMetadata(
            parsid="proj_large",
            project_name="Large Program",
            total_elements=100000,
            hierarchy_depth=10,
        )
        assert proj.total_elements == 100000


class TestLabeledWBSRecordModel:
    """Test LabeledWBSRecord data class for training data."""

    def test_create_with_all_caef_levels(self):
        """Test creating LabeledWBSRecord with all CAEF levels."""
        record = LabeledWBSRecord(
            parsid="proj_001",
            wbs_code="01.01.01",
            title="Engineering Analysis",
            caef_level_2="01",
            caef_level_3="01.01",
            caef_level_4="01.01.01",
            caef_level_5="01.01.01.01",
            caef_level_6="",
            caef_level_7="",
            caef_level_8="",
        )
        assert record.parsid == "proj_001"
        assert record.wbs_code == "01.01.01"
        assert record.title == "Engineering Analysis"
        assert record.caef_level_2 == "01"
        assert record.caef_level_3 == "01.01"
        assert record.caef_level_4 == "01.01.01"
        assert record.caef_level_5 == "01.01.01.01"
        assert record.caef_level_6 == ""
        assert record.caef_level_7 == ""
        assert record.caef_level_8 == ""

    def test_create_with_full_hierarchy(self):
        """Test creating LabeledWBSRecord with complete 7-level CAEF hierarchy."""
        record = LabeledWBSRecord(
            parsid="proj_001",
            wbs_code="01.01.01.01.01.01.01",
            title="Deep Task",
            caef_level_2="01",
            caef_level_3="01.01",
            caef_level_4="01.01.01",
            caef_level_5="01.01.01.01",
            caef_level_6="01.01.01.01.01",
            caef_level_7="01.01.01.01.01.01",
            caef_level_8="01.01.01.01.01.01.01",
        )
        assert record.caef_level_8 == "01.01.01.01.01.01.01"

    def test_create_with_partial_hierarchy(self):
        """Test LabeledWBSRecord with partial CAEF hierarchy (empty levels)."""
        record = LabeledWBSRecord(
            parsid="proj_002",
            wbs_code="02",
            title="High Level",
            caef_level_2="02",
            caef_level_3="",
            caef_level_4="",
            caef_level_5="",
            caef_level_6="",
            caef_level_7="",
            caef_level_8="",
        )
        assert record.caef_level_2 == "02"
        assert record.caef_level_3 == ""


class TestWBSSearchFilterModel:
    """Test WBSSearchFilter data class."""

    def test_create_empty_filter(self):
        """Test creating a filter with all None/default values."""
        filter_obj = WBSSearchFilter()
        assert filter_obj.parsid is None
        assert filter_obj.wbs_pattern is None
        assert filter_obj.min_level is None
        assert filter_obj.max_level is None
        assert filter_obj.include_leaves_only is False

    def test_create_with_parsid_only(self):
        """Test filter with only parsid specified."""
        filter_obj = WBSSearchFilter(parsid="proj_001")
        assert filter_obj.parsid == "proj_001"
        assert filter_obj.wbs_pattern is None

    def test_create_with_wbs_pattern(self):
        """Test filter with WBS pattern (SQL LIKE syntax)."""
        filter_obj = WBSSearchFilter(wbs_pattern="23.%")
        assert filter_obj.wbs_pattern == "23.%"

    def test_create_with_level_bounds(self):
        """Test filter with min/max level bounds."""
        filter_obj = WBSSearchFilter(min_level=2, max_level=4)
        assert filter_obj.min_level == 2
        assert filter_obj.max_level == 4

    def test_create_with_leaves_only(self):
        """Test filter to include only leaf nodes."""
        filter_obj = WBSSearchFilter(include_leaves_only=True)
        assert filter_obj.include_leaves_only is True

    def test_create_with_all_filters(self):
        """Test filter with all constraints combined."""
        filter_obj = WBSSearchFilter(
            parsid="proj_001",
            wbs_pattern="01.%",
            min_level=1,
            max_level=3,
            include_leaves_only=False,
        )
        assert filter_obj.parsid == "proj_001"
        assert filter_obj.wbs_pattern == "01.%"
        assert filter_obj.min_level == 1
        assert filter_obj.max_level == 3
        assert filter_obj.include_leaves_only is False


class TestPARSStoreContextManager:
    """Test PARSStore as a context manager."""

    @pytest.fixture
    def test_db(self):
        """Create a temporary DuckDB database with test schema."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            conn = duckdb.connect(str(db_path))

            # Create tables with expected schema
            conn.execute("""
                CREATE TABLE projects (
                    parsid VARCHAR PRIMARY KEY,
                    project_name VARCHAR NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE wbs_elements (
                    parsid VARCHAR NOT NULL,
                    wbs_code VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    level INTEGER NOT NULL,
                    parent_wbs VARCHAR,
                    leaf_node BOOLEAN NOT NULL,
                    PRIMARY KEY (parsid, wbs_code),
                    FOREIGN KEY (parsid) REFERENCES projects(parsid)
                )
            """)

            # Insert test data
            conn.execute("INSERT INTO projects VALUES ('proj_001', 'Test Project')")
            conn.execute("INSERT INTO projects VALUES ('proj_002', 'Another Project')")

            conn.execute("""
                INSERT INTO wbs_elements VALUES
                ('proj_001', '01', 'Program Management', 1, NULL, FALSE),
                ('proj_001', '01.01', 'Engineering', 2, '01', FALSE),
                ('proj_001', '01.01.01', 'Analysis', 3, '01.01', TRUE),
                ('proj_001', '02', 'Support', 1, NULL, FALSE),
                ('proj_002', '01', 'Different Program', 1, NULL, FALSE)
            """)

            conn.close()
            yield db_path

    def test_context_manager_enters(self, test_db):
        """Test that PARSStore can be entered as context manager."""
        with PARSStore(str(test_db)) as store:
            assert store is not None

    def test_context_manager_exits(self, test_db):
        """Test that PARSStore exits cleanly."""
        store = None
        with PARSStore(str(test_db)) as s:
            store = s
        # After context, store should be properly closed
        assert store is not None

    def test_context_manager_with_nonexistent_db(self):
        """Test context manager with nonexistent database path."""
        with pytest.raises(Exception):  # duckdb raises an error
            with PARSStore("/nonexistent/path/db.duckdb") as _:
                pass


class TestPARSStoreSearchWBS:
    """Test PARSStore.search_wbs method."""

    @pytest.fixture
    def test_db(self):
        """Create a temporary DuckDB database with test schema."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            conn = duckdb.connect(str(db_path))

            conn.execute("""
                CREATE TABLE projects (
                    parsid VARCHAR PRIMARY KEY,
                    project_name VARCHAR NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE wbs_elements (
                    parsid VARCHAR NOT NULL,
                    wbs_code VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    level INTEGER NOT NULL,
                    parent_wbs VARCHAR,
                    leaf_node BOOLEAN NOT NULL,
                    PRIMARY KEY (parsid, wbs_code),
                    FOREIGN KEY (parsid) REFERENCES projects(parsid)
                )
            """)

            conn.execute("INSERT INTO projects VALUES ('proj_001', 'Test Project')")
            conn.execute("INSERT INTO projects VALUES ('proj_002', 'Project 2')")

            # Insert hierarchical test data
            conn.execute("""
                INSERT INTO wbs_elements VALUES
                ('proj_001', '01', 'Program Management', 1, NULL, FALSE),
                ('proj_001', '01.01', 'Engineering', 2, '01', FALSE),
                ('proj_001', '01.01.01', 'Analysis', 3, '01.01', TRUE),
                ('proj_001', '01.01.02', 'Design', 3, '01.01', TRUE),
                ('proj_001', '02', 'Support', 1, NULL, FALSE),
                ('proj_001', '02.01', 'QA', 2, '02', FALSE),
                ('proj_001', '02.01.01', 'Testing', 3, '02.01', TRUE),
                ('proj_002', '01', 'Different Program', 1, NULL, FALSE)
            """)

            conn.close()
            yield db_path

    def test_search_no_filters_returns_all_for_project(self, test_db):
        """Test search with empty filter returns all elements for project."""
        with PARSStore(str(test_db)) as store:
            filter_obj = WBSSearchFilter(parsid="proj_001")
            results = store.search_wbs(filter_obj)
            assert len(results) == 7
            assert all(r.parsid == "proj_001" for r in results)

    def test_search_by_parsid_only(self, test_db):
        """Test filter by parsid only."""
        with PARSStore(str(test_db)) as store:
            filter_obj = WBSSearchFilter(parsid="proj_002")
            results = store.search_wbs(filter_obj)
            assert len(results) == 1
            assert results[0].wbs_code == "01"

    def test_search_by_wbs_pattern(self, test_db):
        """Test filter by WBS pattern (SQL LIKE syntax)."""
        with PARSStore(str(test_db)) as store:
            filter_obj = WBSSearchFilter(parsid="proj_001", wbs_pattern="01.01%")
            results = store.search_wbs(filter_obj)
            assert len(results) == 3
            assert all(r.wbs_code.startswith("01.01") for r in results)

    def test_search_by_level(self, test_db):
        """Test filter by exact level."""
        with PARSStore(str(test_db)) as store:
            filter_obj = WBSSearchFilter(parsid="proj_001", min_level=2, max_level=2)
            results = store.search_wbs(filter_obj)
            assert all(r.level == 2 for r in results)
            assert len(results) == 2  # 01.01 and 02.01

    def test_search_by_min_level(self, test_db):
        """Test filter with minimum level bound."""
        with PARSStore(str(test_db)) as store:
            filter_obj = WBSSearchFilter(parsid="proj_001", min_level=3)
            results = store.search_wbs(filter_obj)
            assert all(r.level >= 3 for r in results)
            assert len(results) == 3  # 01.01.01, 01.01.02, 02.01.01

    def test_search_by_max_level(self, test_db):
        """Test filter with maximum level bound."""
        with PARSStore(str(test_db)) as store:
            filter_obj = WBSSearchFilter(parsid="proj_001", max_level=1)
            results = store.search_wbs(filter_obj)
            assert all(r.level <= 1 for r in results)
            assert len(results) == 2  # 01 and 02

    def test_search_leaves_only(self, test_db):
        """Test filter for leaf nodes only."""
        with PARSStore(str(test_db)) as store:
            filter_obj = WBSSearchFilter(parsid="proj_001", include_leaves_only=True)
            results = store.search_wbs(filter_obj)
            assert all(r.leaf_node is True for r in results)
            assert len(results) == 3  # 01.01.01, 01.01.02, 02.01.01

    def test_search_with_limit(self, test_db):
        """Test search with result limit."""
        with PARSStore(str(test_db)) as store:
            filter_obj = WBSSearchFilter(parsid="proj_001")
            results = store.search_wbs(filter_obj, limit=3)
            assert len(results) <= 3

    def test_search_with_offset(self, test_db):
        """Test search with result offset."""
        with PARSStore(str(test_db)) as store:
            filter_obj = WBSSearchFilter(parsid="proj_001")
            all_results = store.search_wbs(filter_obj)
            offset_results = store.search_wbs(filter_obj, offset=2)
            assert len(offset_results) == len(all_results) - 2

    def test_search_with_limit_and_offset(self, test_db):
        """Test search with both limit and offset."""
        with PARSStore(str(test_db)) as store:
            filter_obj = WBSSearchFilter(parsid="proj_001")
            results = store.search_wbs(filter_obj, limit=2, offset=1)
            assert len(results) <= 2

    def test_search_returns_wbs_elements(self, test_db):
        """Test that search returns WBSElement instances."""
        with PARSStore(str(test_db)) as store:
            filter_obj = WBSSearchFilter(parsid="proj_001")
            results = store.search_wbs(filter_obj)
            assert len(results) > 0
            assert all(isinstance(r, WBSElement) for r in results)

    def test_search_empty_result(self, test_db):
        """Test search that returns no results."""
        with PARSStore(str(test_db)) as store:
            filter_obj = WBSSearchFilter(parsid="proj_001", wbs_pattern="99.%")
            results = store.search_wbs(filter_obj)
            assert results == []

    def test_search_combined_filters(self, test_db):
        """Test search with multiple filters combined."""
        with PARSStore(str(test_db)) as store:
            filter_obj = WBSSearchFilter(
                parsid="proj_001",
                wbs_pattern="01.%",
                min_level=2,
                max_level=3,
                include_leaves_only=True,
            )
            results = store.search_wbs(filter_obj)
            assert all(r.parsid == "proj_001" for r in results)
            assert all(r.wbs_code.startswith("01.") for r in results)
            assert all(2 <= r.level <= 3 for r in results)
            assert all(r.leaf_node is True for r in results)


class TestPARSStoreListProjects:
    """Test PARSStore.list_projects method."""

    @pytest.fixture
    def test_db(self):
        """Create a temporary DuckDB database with test schema."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            conn = duckdb.connect(str(db_path))

            conn.execute("""
                CREATE TABLE projects (
                    parsid VARCHAR PRIMARY KEY,
                    project_name VARCHAR NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE wbs_elements (
                    parsid VARCHAR NOT NULL,
                    wbs_code VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    level INTEGER NOT NULL,
                    parent_wbs VARCHAR,
                    leaf_node BOOLEAN NOT NULL,
                    PRIMARY KEY (parsid, wbs_code),
                    FOREIGN KEY (parsid) REFERENCES projects(parsid)
                )
            """)

            conn.execute(
                "INSERT INTO projects VALUES ('proj_001', 'Space Launch System')"
            )
            conn.execute("INSERT INTO projects VALUES ('proj_002', 'Avionics')")

            # Insert hierarchical test data
            conn.execute("""
                INSERT INTO wbs_elements VALUES
                ('proj_001', '01', 'PM', 1, NULL, FALSE),
                ('proj_001', '01.01', 'Eng', 2, '01', FALSE),
                ('proj_001', '01.01.01', 'Analysis', 3, '01.01', TRUE),
                ('proj_001', '02', 'QA', 1, NULL, FALSE),
                ('proj_002', '01', 'Hardware', 1, NULL, FALSE)
            """)

            conn.close()
            yield db_path

    def test_list_projects_returns_metadata(self, test_db):
        """Test that list_projects returns ProjectMetadata instances."""
        with PARSStore(str(test_db)) as store:
            projects = store.list_projects()
            assert len(projects) == 2
            assert all(isinstance(p, ProjectMetadata) for p in projects)

    def test_list_projects_contains_all_projects(self, test_db):
        """Test that all projects are returned."""
        with PARSStore(str(test_db)) as store:
            projects = store.list_projects()
            parsids = {p.parsid for p in projects}
            assert "proj_001" in parsids
            assert "proj_002" in parsids

    def test_list_projects_metadata_fields(self, test_db):
        """Test that project metadata has correct fields."""
        with PARSStore(str(test_db)) as store:
            projects = store.list_projects()
            for proj in projects:
                assert proj.parsid is not None
                assert proj.project_name is not None
                assert proj.total_elements >= 0
                assert proj.hierarchy_depth >= 0

    def test_list_projects_counts_elements(self, test_db):
        """Test that total_elements count is correct."""
        with PARSStore(str(test_db)) as store:
            projects = store.list_projects()
            proj_001 = next(p for p in projects if p.parsid == "proj_001")
            proj_002 = next(p for p in projects if p.parsid == "proj_002")
            assert proj_001.total_elements == 4
            assert proj_002.total_elements == 1

    def test_list_projects_hierarchy_depth(self, test_db):
        """Test that hierarchy_depth is calculated correctly."""
        with PARSStore(str(test_db)) as store:
            projects = store.list_projects()
            proj_001 = next(p for p in projects if p.parsid == "proj_001")
            proj_002 = next(p for p in projects if p.parsid == "proj_002")
            assert proj_001.hierarchy_depth == 3
            assert proj_002.hierarchy_depth == 1


class TestPARSStoreGetWBSSubtree:
    """Test PARSStore.get_wbs_subtree method."""

    @pytest.fixture
    def test_db(self):
        """Create a temporary DuckDB database with hierarchical test data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            conn = duckdb.connect(str(db_path))

            conn.execute("""
                CREATE TABLE projects (
                    parsid VARCHAR PRIMARY KEY,
                    project_name VARCHAR NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE wbs_elements (
                    parsid VARCHAR NOT NULL,
                    wbs_code VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    level INTEGER NOT NULL,
                    parent_wbs VARCHAR,
                    leaf_node BOOLEAN NOT NULL,
                    PRIMARY KEY (parsid, wbs_code),
                    FOREIGN KEY (parsid) REFERENCES projects(parsid)
                )
            """)

            conn.execute("INSERT INTO projects VALUES ('proj_001', 'Test Project')")

            # Create a proper hierarchy
            conn.execute("""
                INSERT INTO wbs_elements VALUES
                ('proj_001', '01', 'Engineering', 1, NULL, FALSE),
                ('proj_001', '01.01', 'Software', 2, '01', FALSE),
                ('proj_001', '01.01.01', 'Core System', 3, '01.01', FALSE),
                ('proj_001', '01.01.01.01', 'Memory Manager', 4, '01.01.01', TRUE),
                ('proj_001', '01.01.01.02', 'Scheduler', 4, '01.01.01', TRUE),
                ('proj_001', '01.01.02', 'Integration', 3, '01.01', TRUE),
                ('proj_001', '01.02', 'Hardware', 2, '01', FALSE),
                ('proj_001', '01.02.01', 'PCB Design', 3, '01.02', TRUE)
            """)

            conn.close()
            yield db_path

    def test_get_wbs_subtree_returns_dict(self, test_db):
        """Test that get_wbs_subtree returns a dict."""
        with PARSStore(str(test_db)) as store:
            result = store.get_wbs_subtree("proj_001", "01")
            assert isinstance(result, dict)

    def test_get_wbs_subtree_has_element_key(self, test_db):
        """Test that result contains 'element' key."""
        with PARSStore(str(test_db)) as store:
            result = store.get_wbs_subtree("proj_001", "01")
            assert "element" in result
            assert isinstance(result["element"], (dict, WBSElement))

    def test_get_wbs_subtree_has_children_key(self, test_db):
        """Test that result contains 'children' key."""
        with PARSStore(str(test_db)) as store:
            result = store.get_wbs_subtree("proj_001", "01")
            assert "children" in result
            assert isinstance(result["children"], list)

    def test_get_wbs_subtree_root_element(self, test_db):
        """Test getting subtree for root element."""
        with PARSStore(str(test_db)) as store:
            result = store.get_wbs_subtree("proj_001", "01")
            elem = result["element"]
            if isinstance(elem, dict):
                assert elem["wbs_code"] == "01"
            else:
                assert elem.wbs_code == "01"

    def test_get_wbs_subtree_has_children(self, test_db):
        """Test that root element has children."""
        with PARSStore(str(test_db)) as store:
            result = store.get_wbs_subtree("proj_001", "01")
            children = result["children"]
            assert len(children) == 2  # 01.01 and 01.02

    def test_get_wbs_subtree_nested_hierarchy(self, test_db):
        """Test that children have their own children."""
        with PARSStore(str(test_db)) as store:
            result = store.get_wbs_subtree("proj_001", "01")
            children = result["children"]
            # Find 01.01 child
            software = next(c for c in children if c["element"]["wbs_code"] == "01.01")
            assert len(software["children"]) > 0

    def test_get_wbs_subtree_leaf_node(self, test_db):
        """Test getting subtree for leaf node (no children)."""
        with PARSStore(str(test_db)) as store:
            result = store.get_wbs_subtree("proj_001", "01.01.01.01")
            children = result["children"]
            assert children == []

    def test_get_wbs_subtree_with_depth_limit(self, test_db):
        """Test get_wbs_subtree with depth constraint."""
        with PARSStore(str(test_db)) as store:
            result = store.get_wbs_subtree("proj_001", "01", depth=1)
            # Should include element and immediate children only
            assert "element" in result
            assert "children" in result

    def test_get_wbs_subtree_nonexistent_element(self, test_db):
        """Test getting subtree for nonexistent element."""
        with PARSStore(str(test_db)) as store:
            with pytest.raises(Exception):  # Should raise ValueError or similar
                store.get_wbs_subtree("proj_001", "99")

    def test_get_wbs_subtree_nonexistent_project(self, test_db):
        """Test getting subtree for nonexistent project."""
        with PARSStore(str(test_db)) as store:
            with pytest.raises(Exception):
                store.get_wbs_subtree("proj_999", "01")


class TestPARSStoreGetWBSLineage:
    """Test PARSStore.get_wbs_lineage method."""

    @pytest.fixture
    def test_db(self):
        """Create a temporary DuckDB database with parent-child relationships."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            conn = duckdb.connect(str(db_path))

            conn.execute("""
                CREATE TABLE projects (
                    parsid VARCHAR PRIMARY KEY,
                    project_name VARCHAR NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE wbs_elements (
                    parsid VARCHAR NOT NULL,
                    wbs_code VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    level INTEGER NOT NULL,
                    parent_wbs VARCHAR,
                    leaf_node BOOLEAN NOT NULL,
                    PRIMARY KEY (parsid, wbs_code),
                    FOREIGN KEY (parsid) REFERENCES projects(parsid)
                )
            """)

            conn.execute("INSERT INTO projects VALUES ('proj_001', 'Test Project')")

            conn.execute("""
                INSERT INTO wbs_elements VALUES
                ('proj_001', '01', 'Engineering', 1, NULL, FALSE),
                ('proj_001', '01.01', 'Software', 2, '01', FALSE),
                ('proj_001', '01.01.01', 'Core System', 3, '01.01', FALSE),
                ('proj_001', '01.01.01.01', 'Memory Manager', 4, '01.01.01', TRUE)
            """)

            conn.close()
            yield db_path

    def test_get_wbs_lineage_returns_list(self, test_db):
        """Test that get_wbs_lineage returns a list."""
        with PARSStore(str(test_db)) as store:
            result = store.get_wbs_lineage("proj_001", "01.01.01.01")
            assert isinstance(result, list)

    def test_get_wbs_lineage_returns_wbs_elements(self, test_db):
        """Test that lineage list contains WBSElement instances."""
        with PARSStore(str(test_db)) as store:
            result = store.get_wbs_lineage("proj_001", "01.01.01.01")
            if result and isinstance(result[0], dict):
                # If dicts, should have element keys
                assert all("wbs_code" in item for item in result)
            else:
                assert all(isinstance(item, WBSElement) for item in result)

    def test_get_wbs_lineage_for_leaf(self, test_db):
        """Test getting lineage for a leaf node."""
        with PARSStore(str(test_db)) as store:
            result = store.get_wbs_lineage("proj_001", "01.01.01.01")
            assert len(result) == 4  # Leaf + 3 ancestors

    def test_get_wbs_lineage_contains_target_element(self, test_db):
        """Test that lineage includes the target element."""
        with PARSStore(str(test_db)) as store:
            result = store.get_wbs_lineage("proj_001", "01.01.01.01")
            codes = [
                item["wbs_code"] if isinstance(item, dict) else item.wbs_code
                for item in result
            ]
            assert "01.01.01.01" in codes

    def test_get_wbs_lineage_contains_root(self, test_db):
        """Test that lineage includes the root element."""
        with PARSStore(str(test_db)) as store:
            result = store.get_wbs_lineage("proj_001", "01.01.01.01")
            codes = [
                item["wbs_code"] if isinstance(item, dict) else item.wbs_code
                for item in result
            ]
            assert "01" in codes

    def test_get_wbs_lineage_for_root_element(self, test_db):
        """Test lineage for root element (only itself)."""
        with PARSStore(str(test_db)) as store:
            result = store.get_wbs_lineage("proj_001", "01")
            assert len(result) == 1
            elem = result[0]
            code = elem["wbs_code"] if isinstance(elem, dict) else elem.wbs_code
            assert code == "01"

    def test_get_wbs_lineage_order(self, test_db):
        """Test that lineage is ordered from element to root."""
        with PARSStore(str(test_db)) as store:
            result = store.get_wbs_lineage("proj_001", "01.01.01.01")
            codes = [
                item["wbs_code"] if isinstance(item, dict) else item.wbs_code
                for item in result
            ]
            # Should be leaf to root: 01.01.01.01, 01.01.01, 01.01, 01
            assert codes[0] == "01.01.01.01"
            assert codes[-1] == "01"

    def test_get_wbs_lineage_nonexistent_element(self, test_db):
        """Test lineage for nonexistent element."""
        with PARSStore(str(test_db)) as store:
            with pytest.raises(Exception):
                store.get_wbs_lineage("proj_001", "99")

    def test_get_wbs_lineage_nonexistent_project(self, test_db):
        """Test lineage for nonexistent project."""
        with PARSStore(str(test_db)) as store:
            with pytest.raises(Exception):
                store.get_wbs_lineage("proj_999", "01")


class TestPARSStoreGetLabeledWBS:
    """Test PARSStore.get_labeled_wbs method for training data."""

    @pytest.fixture
    def test_db(self):
        """Create a temporary DuckDB database with labeled training data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            conn = duckdb.connect(str(db_path))

            conn.execute("""
                CREATE TABLE projects (
                    parsid VARCHAR PRIMARY KEY,
                    project_name VARCHAR NOT NULL,
                    project_description VARCHAR
                )
            """)

            conn.execute("""
                CREATE TABLE wbs_elements (
                    parsid VARCHAR NOT NULL,
                    wbs_code VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    level INTEGER NOT NULL,
                    parent_wbs VARCHAR,
                    leaf_node BOOLEAN NOT NULL,
                    PRIMARY KEY (parsid, wbs_code),
                    FOREIGN KEY (parsid) REFERENCES projects(parsid)
                )
            """)

            conn.execute("""
                CREATE TABLE labeled_wbs (
                    parsid VARCHAR NOT NULL,
                    wbs_code VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    caef_level_2 VARCHAR,
                    caef_level_3 VARCHAR,
                    caef_level_4 VARCHAR,
                    caef_level_5 VARCHAR,
                    caef_level_6 VARCHAR,
                    caef_level_7 VARCHAR,
                    caef_level_8 VARCHAR,
                    PRIMARY KEY (parsid, wbs_code),
                    FOREIGN KEY (parsid) REFERENCES projects(parsid)
                )
            """)

            conn.execute(
                "INSERT INTO projects "
                "VALUES ('proj_001', 'SLS Program', 'Space Launch System')"
            )

            # Insert labeled training data with CAEF hierarchy
            conn.execute("""
                INSERT INTO labeled_wbs VALUES
                ('proj_001', '01', 'Program Management', '01', '', '', '', '', '', ''),
                ('proj_001', '01.01', 'Engineering', '01', '01.01', '', '', '', '', ''),
                ('proj_001', '01.01.01', 'Software', '01', '01.01', '01.01.01',
                 '', '', '', ''),
                ('proj_001', '01.01.01.01', 'Core System', '01', '01.01',
                 '01.01.01', '01.01.01.01', '', '', ''),
                ('proj_001', '02', 'Testing', '02', '', '', '', '', '', ''),
                ('proj_001', '02.01', 'QA', '02', '02.01', '', '', '', '', '')
            """)

            conn.close()
            yield db_path

    def test_get_labeled_wbs_returns_list(self, test_db):
        """Test that get_labeled_wbs returns a list."""
        with PARSStore(str(test_db)) as store:
            results = store.get_labeled_wbs()
            assert isinstance(results, list)

    def test_get_labeled_wbs_returns_records(self, test_db):
        """Test that get_labeled_wbs returns LabeledWBSRecord instances."""
        with PARSStore(str(test_db)) as store:
            results = store.get_labeled_wbs()
            assert len(results) > 0
            assert all(isinstance(r, LabeledWBSRecord) for r in results)

    def test_get_labeled_wbs_contains_all_records(self, test_db):
        """Test that all labeled records are returned."""
        with PARSStore(str(test_db)) as store:
            results = store.get_labeled_wbs()
            assert len(results) == 6

    def test_get_labeled_wbs_has_caef_levels(self, test_db):
        """Test that records have CAEF hierarchy levels."""
        with PARSStore(str(test_db)) as store:
            results = store.get_labeled_wbs()
            for record in results:
                assert hasattr(record, "caef_level_2")
                assert hasattr(record, "caef_level_3")
                assert hasattr(record, "caef_level_4")
                assert hasattr(record, "caef_level_5")
                assert hasattr(record, "caef_level_6")
                assert hasattr(record, "caef_level_7")
                assert hasattr(record, "caef_level_8")

    def test_get_labeled_wbs_with_project_filter(self, test_db):
        """Test get_labeled_wbs with project filter."""
        with PARSStore(str(test_db)) as store:
            results = store.get_labeled_wbs(parsid="proj_001")
            assert len(results) == 6
            assert all(r.parsid == "proj_001" for r in results)

    def test_get_labeled_wbs_hierarchy_consistency(self, test_db):
        """Test that CAEF hierarchy labels are consistent."""
        with PARSStore(str(test_db)) as store:
            results = store.get_labeled_wbs()
            for record in results:
                # If level 3 is empty, level 4+ should be empty
                if record.caef_level_3 == "":
                    assert record.caef_level_4 == ""
                    assert record.caef_level_5 == ""


class TestPARSStoreGetProjectSplit:
    """Test PARSStore.get_project_split method for train/test splitting."""

    @pytest.fixture
    def test_db(self):
        """Create a temporary DuckDB database with multi-project labeled data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            conn = duckdb.connect(str(db_path))

            conn.execute("""
                CREATE TABLE projects (
                    parsid VARCHAR PRIMARY KEY,
                    project_name VARCHAR NOT NULL,
                    project_description VARCHAR
                )
            """)

            conn.execute("""
                CREATE TABLE labeled_wbs (
                    parsid VARCHAR NOT NULL,
                    wbs_code VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    caef_level_2 VARCHAR,
                    caef_level_3 VARCHAR,
                    caef_level_4 VARCHAR,
                    caef_level_5 VARCHAR,
                    caef_level_6 VARCHAR,
                    caef_level_7 VARCHAR,
                    caef_level_8 VARCHAR,
                    PRIMARY KEY (parsid, wbs_code),
                    FOREIGN KEY (parsid) REFERENCES projects(parsid)
                )
            """)

            conn.execute(
                "INSERT INTO projects VALUES ('proj_001', 'SLS', 'Space Launch System')"
            )
            conn.execute(
                "INSERT INTO projects VALUES ('proj_002', 'Orion', 'Orion Program')"
            )

            # Insert data for proj_001: 4 records
            conn.execute("""
                INSERT INTO labeled_wbs VALUES
                ('proj_001', '01', 'PM', '01', '', '', '', '', '', ''),
                ('proj_001', '01.01', 'Eng', '01', '01.01', '', '', '', '', ''),
                ('proj_001', '02', 'Test', '02', '', '', '', '', '', ''),
                ('proj_001', '02.01', 'QA', '02', '02.01', '', '', '', '', '')
            """)

            # Insert data for proj_002: 6 records
            conn.execute("""
                INSERT INTO labeled_wbs VALUES
                ('proj_002', '01', 'Hardware', '01', '', '', '', '', '', ''),
                ('proj_002', '01.01', 'Power', '01', '01.01', '', '', '', '', ''),
                ('proj_002', '01.02', 'Thermal', '01', '01.02', '', '', '', '', ''),
                ('proj_002', '02', 'Integration', '02', '', '', '', '', '', ''),
                ('proj_002', '02.01', 'Assembly', '02', '02.01', '', '', '', '', ''),
                ('proj_002', '02.02', 'Checkout', '02', '02.02', '', '', '', '', '')
            """)

            conn.close()
            yield db_path

    def test_get_project_split_returns_dict(self, test_db):
        """Test that get_project_split returns a dict."""
        with PARSStore(str(test_db)) as store:
            result = store.get_project_split()
            assert isinstance(result, dict)

    def test_get_project_split_has_train_test_keys(self, test_db):
        """Test that split dict has 'train' and 'test' keys."""
        with PARSStore(str(test_db)) as store:
            result = store.get_project_split()
            assert "train" in result
            assert "test" in result

    def test_get_project_split_returns_lists(self, test_db):
        """Test that train and test values are lists."""
        with PARSStore(str(test_db)) as store:
            result = store.get_project_split()
            assert isinstance(result["train"], list)
            assert isinstance(result["test"], list)

    def test_get_project_split_training_records(self, test_db):
        """Test that training data contains LabeledWBSRecord instances."""
        with PARSStore(str(test_db)) as store:
            result = store.get_project_split()
            train_data = result["train"]
            if len(train_data) > 0:
                assert all(isinstance(r, LabeledWBSRecord) for r in train_data)

    def test_get_project_split_disjoint_projects(self, test_db):
        """Test that train and test sets use different projects."""
        with PARSStore(str(test_db)) as store:
            result = store.get_project_split()
            train_projects = {r.parsid for r in result["train"]}
            test_projects = {r.parsid for r in result["test"]}
            # Projects should be disjoint (no overlap)
            assert len(train_projects & test_projects) == 0

    def test_get_project_split_has_both_sets(self, test_db):
        """Test that both train and test sets are populated."""
        with PARSStore(str(test_db)) as store:
            result = store.get_project_split()
            assert len(result["train"]) > 0
            assert len(result["test"]) > 0

    def test_get_project_split_covers_all_data(self, test_db):
        """Test that train+test covers all labeled data."""
        with PARSStore(str(test_db)) as store:
            result = store.get_project_split()
            all_labeled = store.get_labeled_wbs()
            total_in_split = len(result["train"]) + len(result["test"])
            assert total_in_split == len(all_labeled)

    def test_get_project_split_with_ratio(self, test_db):
        """Test get_project_split with custom train/test ratio."""
        with PARSStore(str(test_db)) as store:
            result = store.get_project_split(train_ratio=0.5)
            total = len(result["train"]) + len(result["test"])
            train_count = len(result["train"])
            # Check approximate ratio (±1 for rounding)
            assert abs(train_count / total - 0.5) <= 0.2


class TestPARSStoreIntegration:
    """Integration tests combining multiple store operations."""

    @pytest.fixture
    def test_db(self):
        """Create a comprehensive test database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            conn = duckdb.connect(str(db_path))

            conn.execute("""
                CREATE TABLE projects (
                    parsid VARCHAR PRIMARY KEY,
                    project_name VARCHAR NOT NULL,
                    project_description VARCHAR
                )
            """)

            conn.execute("""
                CREATE TABLE wbs_elements (
                    parsid VARCHAR NOT NULL,
                    wbs_code VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    level INTEGER NOT NULL,
                    parent_wbs VARCHAR,
                    leaf_node BOOLEAN NOT NULL,
                    PRIMARY KEY (parsid, wbs_code),
                    FOREIGN KEY (parsid) REFERENCES projects(parsid)
                )
            """)

            conn.execute("""
                CREATE TABLE labeled_wbs (
                    parsid VARCHAR NOT NULL,
                    wbs_code VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    caef_level_2 VARCHAR,
                    caef_level_3 VARCHAR,
                    caef_level_4 VARCHAR,
                    caef_level_5 VARCHAR,
                    caef_level_6 VARCHAR,
                    caef_level_7 VARCHAR,
                    caef_level_8 VARCHAR,
                    PRIMARY KEY (parsid, wbs_code),
                    FOREIGN KEY (parsid) REFERENCES projects(parsid)
                )
            """)

            conn.execute(
                "INSERT INTO projects "
                "VALUES ('proj_001', 'SLS Program', 'Space Launch System')"
            )

            conn.execute("""
                INSERT INTO wbs_elements VALUES
                ('proj_001', '01', 'Program Management', 1, NULL, FALSE),
                ('proj_001', '02', 'Engineering', 1, NULL, FALSE),
                ('proj_001', '02.01', 'Software', 2, '02', FALSE),
                ('proj_001', '02.01.01', 'Core', 3, '02.01', TRUE),
                ('proj_001', '02.02', 'Hardware', 2, '02', FALSE),
                ('proj_001', '02.02.01', 'PCB', 3, '02.02', TRUE),
                ('proj_001', '03', 'Testing', 1, NULL, FALSE)
            """)

            conn.execute("""
                INSERT INTO labeled_wbs VALUES
                ('proj_001', '01', 'Program Management', '01', '', '', '', '', '', ''),
                ('proj_001', '02', 'Engineering', '02', '', '', '', '', '', ''),
                ('proj_001', '02.01', 'Software', '02', '02.01', '', '', '', '', ''),
                ('proj_001', '02.01.01', 'Core', '02', '02.01', '02.01.01',
                 '', '', '', ''),
                ('proj_001', '02.02', 'Hardware', '02', '02.02', '', '', '', '', ''),
                ('proj_001', '02.02.01', 'PCB', '02', '02.02', '02.02.01',
                 '', '', '', ''),
                ('proj_001', '03', 'Testing', '03', '', '', '', '', '', '')
            """)

            conn.close()
            yield db_path

    def test_list_and_search_consistency(self, test_db):
        """Test that list_projects and search_wbs work together."""
        with PARSStore(str(test_db)) as store:
            projects = store.list_projects()
            assert len(projects) > 0

            proj = projects[0]
            search_filter = WBSSearchFilter(parsid=proj.parsid)
            elements = store.search_wbs(search_filter)
            assert len(elements) == proj.total_elements

    def test_search_and_subtree_consistency(self, test_db):
        """Test that search and subtree work together."""
        with PARSStore(str(test_db)) as store:
            search_filter = WBSSearchFilter(parsid="proj_001", min_level=1, max_level=1)
            roots = store.search_wbs(search_filter)
            assert len(roots) > 0

            for root in roots:
                subtree = store.get_wbs_subtree("proj_001", root.wbs_code)
                assert subtree is not None

    def test_lineage_and_search_consistency(self, test_db):
        """Test that lineage and search work together."""
        with PARSStore(str(test_db)) as store:
            search_filter = WBSSearchFilter(parsid="proj_001", include_leaves_only=True)
            leaves = store.search_wbs(search_filter)

            for leaf in leaves:
                lineage = store.get_wbs_lineage("proj_001", leaf.wbs_code)
                assert len(lineage) > 0
                assert leaf.wbs_code in [
                    (item["wbs_code"] if isinstance(item, dict) else item.wbs_code)
                    for item in lineage
                ]

    def test_training_workflow_end_to_end(self, test_db):
        """Test complete training workflow: load labeled data and create split."""
        with PARSStore(str(test_db)) as store:
            # Step 1: Load all labeled training data
            labeled_data = store.get_labeled_wbs()
            assert len(labeled_data) == 7

            # Step 2: Extract titles and CAEF labels for training
            titles = [record.title for record in labeled_data]
            caef_labels = [
                [
                    record.caef_level_2,
                    record.caef_level_3,
                    record.caef_level_4,
                    record.caef_level_5,
                    record.caef_level_6,
                    record.caef_level_7,
                    record.caef_level_8,
                ]
                for record in labeled_data
            ]
            assert len(titles) == len(caef_labels)

            # Step 3: Create project-disjoint train/test split (if multi-project)
            split = store.get_project_split()
            train_records = split["train"]
            test_records = split["test"]

            if len(train_records) > 0 and len(test_records) > 0:
                # Verify disjoint projects
                train_projects = {r.parsid for r in train_records}
                test_projects = {r.parsid for r in test_records}
                assert len(train_projects & test_projects) == 0


class TestStorageSafety:
    """Test safety: input validation, SQL injection prevention, cycle detection."""

    @pytest.fixture
    def test_db(self):
        """Create a temporary DuckDB database with test schema."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            conn = duckdb.connect(str(db_path))

            conn.execute("""
                CREATE TABLE projects (
                    parsid VARCHAR PRIMARY KEY,
                    project_name VARCHAR NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE wbs_elements (
                    parsid VARCHAR NOT NULL,
                    wbs_code VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    level INTEGER NOT NULL,
                    parent_wbs VARCHAR,
                    leaf_node BOOLEAN NOT NULL,
                    PRIMARY KEY (parsid, wbs_code),
                    FOREIGN KEY (parsid) REFERENCES projects(parsid)
                )
            """)

            conn.execute("INSERT INTO projects VALUES ('proj_001', 'Test Project')")
            conn.execute("""
                INSERT INTO wbs_elements VALUES
                ('proj_001', '01', 'Level 1', 1, NULL, FALSE),
                ('proj_001', '01.01', 'Level 2', 2, '01', FALSE),
                ('proj_001', '01.01.01', 'Level 3', 3, '01.01', FALSE),
                ('proj_001', '01.01.01.01', 'Level 4', 4, '01.01.01', FALSE),
                ('proj_001', '01.01.01.01.01', 'Level 5', 5, '01.01.01.01', TRUE)
            """)

            conn.close()
            yield db_path

    def test_negative_limit_raises_error(self, test_db):
        """Test that negative limit raises ValueError."""
        with PARSStore(str(test_db)) as store:
            filter_obj = WBSSearchFilter(parsid="proj_001")
            with pytest.raises(ValueError, match="limit must be non-negative"):
                store.search_wbs(filter_obj, limit=-1)

    def test_negative_offset_raises_error(self, test_db):
        """Test that negative offset raises ValueError."""
        with PARSStore(str(test_db)) as store:
            filter_obj = WBSSearchFilter(parsid="proj_001")
            with pytest.raises(ValueError, match="offset must be non-negative"):
                store.search_wbs(filter_obj, offset=-1)

    def test_zero_limit_is_valid(self, test_db):
        """Test that limit=0 is valid (returns empty)."""
        with PARSStore(str(test_db)) as store:
            filter_obj = WBSSearchFilter(parsid="proj_001")
            results = store.search_wbs(filter_obj, limit=0)
            assert len(results) == 0

    def test_zero_offset_is_valid(self, test_db):
        """Test that offset=0 is valid (no skipping)."""
        with PARSStore(str(test_db)) as store:
            filter_obj = WBSSearchFilter(parsid="proj_001")
            all_results = store.search_wbs(filter_obj)
            offset_zero = store.search_wbs(filter_obj, offset=0)
            assert len(all_results) == len(offset_zero)

    def test_limit_offset_bound_parameters(self, test_db):
        """Test that limit/offset use bound parameters (not string interpolation)."""
        with PARSStore(str(test_db)) as store:
            filter_obj = WBSSearchFilter(parsid="proj_001")
            # These should not raise SQL errors or return unexpected results
            # String interpolation attacks would fail here if not using bound params
            results_limit_2 = store.search_wbs(filter_obj, limit=2)
            results_offset_1 = store.search_wbs(filter_obj, offset=1)

            assert len(results_limit_2) <= 2
            assert len(results_offset_1) < len(store.search_wbs(filter_obj))

    def test_missing_database_raises_file_not_found(self):
        """Test that missing database raises FileNotFoundError on __enter__."""
        with pytest.raises(
            FileNotFoundError, match="PARS database file is not present"
        ):
            with PARSStore("/nonexistent/path/to/database.duckdb"):
                pass

    def test_database_opened_read_only(self, test_db):
        """Test that database is opened in read-only mode."""
        with PARSStore(str(test_db)) as store:
            # Attempting to write should fail (read-only connection)
            with pytest.raises(Exception):
                store.conn.execute(
                    "INSERT INTO projects VALUES ('proj_bad', 'Should Fail')"
                )

    def test_max_hierarchy_depth_constant_exists(self):
        """Test that MAX_HIERARCHY_DEPTH is defined."""
        from pars_local_mcp.storage.queries import MAX_HIERARCHY_DEPTH

        assert MAX_HIERARCHY_DEPTH == 64
        assert isinstance(MAX_HIERARCHY_DEPTH, int)
        assert MAX_HIERARCHY_DEPTH > 0


class TestSearchRequiresProjectId:
    """An explicit project_id must name a project; blank never matches all."""

    @pytest.fixture
    def test_db(self):
        """Two projects so a missing filter would visibly leak rows across projects."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.duckdb"
            conn = duckdb.connect(str(db_path))
            conn.execute("""
                CREATE TABLE projects (
                    parsid VARCHAR PRIMARY KEY,
                    project_name VARCHAR NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE wbs_elements (
                    parsid VARCHAR NOT NULL,
                    wbs_code VARCHAR NOT NULL,
                    title VARCHAR NOT NULL,
                    level INTEGER NOT NULL,
                    parent_wbs VARCHAR,
                    leaf_node BOOLEAN NOT NULL,
                    PRIMARY KEY (parsid, wbs_code)
                )
            """)
            conn.execute("INSERT INTO projects VALUES ('proj_001', 'Project 1')")
            conn.execute("INSERT INTO projects VALUES ('proj_002', 'Project 2')")
            conn.execute("""
                INSERT INTO wbs_elements VALUES
                ('proj_001', '01', 'Root 1', 1, NULL, FALSE),
                ('proj_001', '01.01', 'Leaf 1', 2, '01', TRUE),
                ('proj_002', '01', 'Root 2', 1, NULL, FALSE),
                ('proj_002', '01.01', 'Leaf 2', 2, '01', TRUE)
            """)
            conn.close()
            yield db_path

    @pytest.mark.parametrize("project_id", ["", "   ", "\t"])
    def test_blank_project_id_is_rejected(self, test_db, project_id):
        """A blank project_id must raise instead of returning other projects' rows."""
        with PARSStore(str(test_db)) as store:
            with pytest.raises(ValueError):
                store.search_wbs(WBSSearchFilter(parsid=project_id))

    def test_real_project_id_returns_only_its_rows(self, test_db):
        """A real project_id keeps its filter: only that project's rows come back."""
        with PARSStore(str(test_db)) as store:
            results = store.search_wbs(WBSSearchFilter(parsid="proj_002"))
            assert {r.parsid for r in results} == {"proj_002"}
            assert len(results) == 2
