"""Tests for tools.py - verify MCP tool functionality and outputs."""

import tempfile
from pathlib import Path

import duckdb
import pytest
from fastmcp import Client, FastMCP

from pars_local_mcp.config import Settings
from pars_local_mcp.mcp.errors import PublicError
from pars_local_mcp.mcp.tools import register_tools
from pars_local_mcp.storage.models import WBSSearchFilter
from pars_local_mcp.storage.queries import PARSStore


def create_test_database(db_path: Path) -> None:
    """Create a test database with sample PARS data."""
    conn = duckdb.connect(str(db_path), read_only=False)
    try:
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
        conn.execute("""
            CREATE TABLE labeled_wbs (
                parsid VARCHAR NOT NULL,
                wbs_code VARCHAR NOT NULL,
                caef_level_1 VARCHAR,
                caef_level_2 VARCHAR,
                caef_level_3 VARCHAR,
                PRIMARY KEY (parsid, wbs_code),
                FOREIGN KEY (parsid, wbs_code) REFERENCES wbs_elements(parsid, wbs_code)
            )
        """)

        conn.execute(
            "INSERT INTO projects (parsid, project_name) VALUES (?, ?)",
            ("proj_001", "Test Project"),
        )

        test_elements = [
            ("proj_001", "01", "Engineering", 1, None, False),
            ("proj_001", "01.01", "Design", 2, "01", False),
            ("proj_001", "01.01.01", "Requirements", 3, "01.01", True),
            ("proj_001", "01.01.02", "Verification", 3, "01.01", True),
            ("proj_001", "01.02", "Implementation", 2, "01", False),
            ("proj_001", "01.02.01", "Development", 3, "01.02", True),
        ]

        for parsid, code, title, level, parent, leaf in test_elements:
            conn.execute(
                """
                INSERT INTO wbs_elements
                (parsid, wbs_code, title, level, parent_wbs, leaf_node)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (parsid, code, title, level, parent, leaf),
            )

        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def test_database():
    """Fixture providing a temporary test database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.duckdb"
        create_test_database(db_path)
        yield db_path


@pytest.fixture
def mcp_server(test_database):
    """Fixture providing a FastMCP server with test database."""
    settings = Settings(database_path=test_database)
    mcp = FastMCP("Test PARS Server", instructions="Test server")
    register_tools(mcp, settings)
    return mcp


class TestToolRegistration:
    """Test tool registration and structure."""

    def test_tools_register_without_error(self, mcp_server):
        """Test that tools can be registered without raising."""
        assert mcp_server is not None


class TestListProjectsTool:
    """Test list_projects tool."""

    def test_list_projects_returns_dict(self, test_database):
        """Test that list_projects returns correct structure."""
        with PARSStore(test_database) as store:
            projects = store.list_projects()
            assert len(projects) == 1
            assert projects[0].parsid == "proj_001"
            assert projects[0].total_elements == 6
            assert projects[0].hierarchy_depth == 3


class TestSearchWBSTool:
    """Test search_wbs tool."""

    def test_search_wbs_with_pattern(self, test_database):
        """Test search_wbs with WBS pattern filter."""
        with PARSStore(test_database) as store:
            filter_obj = WBSSearchFilter(parsid="proj_001", wbs_pattern="01%")
            results = store.search_wbs(filter_obj)
            assert len(results) == 6

    def test_search_wbs_with_level_bounds(self, test_database):
        """Test search_wbs with min/max level filters."""
        with PARSStore(test_database) as store:
            filter_obj = WBSSearchFilter(parsid="proj_001", min_level=2, max_level=2)
            results = store.search_wbs(filter_obj)
            assert len(results) == 2
            assert all(e.level == 2 for e in results)
            codes = {e.wbs_code for e in results}
            assert codes == {"01.01", "01.02"}

    def test_search_wbs_with_leaves_only(self, test_database):
        """Test search_wbs with include_leaves_only filter."""
        with PARSStore(test_database) as store:
            filter_obj = WBSSearchFilter(parsid="proj_001", include_leaves_only=True)
            results = store.search_wbs(filter_obj)
            assert len(results) == 3
            assert all(e.leaf_node is True for e in results)
            codes = {e.wbs_code for e in results}
            assert codes == {"01.01.01", "01.01.02", "01.02.01"}


class TestGetWBSHierarchyTool:
    """Test get_wbs_hierarchy tool."""

    def test_get_wbs_hierarchy_root_element(self, test_database):
        """Test get_wbs_hierarchy for root element."""
        with PARSStore(test_database) as store:
            result = store.get_wbs_subtree("proj_001", "01", depth=1)
            assert "element" in result
            assert result["element"]["wbs_code"] == "01"
            assert len(result["children"]) == 2
            children_codes = {c["element"]["wbs_code"] for c in result["children"]}
            assert children_codes == {"01.01", "01.02"}

    def test_get_wbs_hierarchy_nonexistent_element(self, test_database):
        """Test get_wbs_hierarchy with invalid WBS code."""
        with PARSStore(test_database) as store:
            with pytest.raises(PublicError, match="WBS element 99.99.99 not found"):
                store.get_wbs_subtree("proj_001", "99.99.99", depth=1)

    def test_get_wbs_hierarchy_leaf_node(self, test_database):
        """Test get_wbs_hierarchy for leaf node (no children)."""
        with PARSStore(test_database) as store:
            result = store.get_wbs_subtree("proj_001", "01.01.01", depth=1)
            assert result["element"]["wbs_code"] == "01.01.01"
            assert result["element"]["leaf_node"] is True
            assert result["children"] == []


class TestGetWBSLineageTool:
    """Test get_wbs_lineage tool."""

    def test_get_wbs_lineage_leaf_to_root(self, test_database):
        """Test get_wbs_lineage returns path from element to root."""
        with PARSStore(test_database) as store:
            lineage = store.get_wbs_lineage("proj_001", "01.01.01")
            assert len(lineage) == 3
            assert lineage[0].wbs_code == "01.01.01"
            assert lineage[1].wbs_code == "01.01"
            assert lineage[2].wbs_code == "01"

    def test_get_wbs_lineage_root_element(self, test_database):
        """Test get_wbs_lineage for root element."""
        with PARSStore(test_database) as store:
            lineage = store.get_wbs_lineage("proj_001", "01")
            assert len(lineage) == 1
            assert lineage[0].wbs_code == "01"

    def test_get_wbs_lineage_levels_decrease(self, test_database):
        """Test that lineage levels decrease from element to root."""
        with PARSStore(test_database) as store:
            lineage = store.get_wbs_lineage("proj_001", "01.01.02")
            for i in range(len(lineage) - 1):
                assert lineage[i].level > lineage[i + 1].level


class TestGetProjectInfoTool:
    """Test get_project_info tool."""

    def test_get_project_info_valid_project(self, test_database):
        """Test get_project_info with valid project ID."""
        with PARSStore(test_database) as store:
            projects = store.list_projects()
            project = projects[0]
            assert project.parsid == "proj_001"
            assert project.total_elements == 6
            assert project.hierarchy_depth == 3

    def test_get_project_info_metadata_fields(self, test_database):
        """Test that project metadata has all required fields."""
        with PARSStore(test_database) as store:
            projects = store.list_projects()
            for project in projects:
                assert isinstance(project.parsid, str)
                assert isinstance(project.project_name, str)
                assert isinstance(project.total_elements, int)
                assert isinstance(project.hierarchy_depth, int)
                assert project.total_elements > 0
                assert project.hierarchy_depth > 0


class TestGetLeafNodesTool:
    """Test get_leaf_nodes tool."""

    def test_get_leaf_nodes_all_are_terminals(self, test_database):
        """Test that get_leaf_nodes returns only leaf nodes."""
        with PARSStore(test_database) as store:
            filter_obj = WBSSearchFilter(parsid="proj_001", include_leaves_only=True)
            leaves = store.search_wbs(filter_obj)
            assert len(leaves) == 3
            for leaf in leaves:
                assert leaf.leaf_node is True
            codes = {leaf.wbs_code for leaf in leaves}
            assert codes == {"01.01.01", "01.01.02", "01.02.01"}

    def test_get_leaf_nodes_correct_count(self, test_database):
        """Test that leaf node count is correct for sample data."""
        with PARSStore(test_database) as store:
            filter_obj = WBSSearchFilter(parsid="proj_001", include_leaves_only=True)
            leaves = store.search_wbs(filter_obj)
            assert len(leaves) == 3


class TestGetWBSByLevelTool:
    """Test get_wbs_by_level tool."""

    def test_get_wbs_by_level_2(self, test_database):
        """Test getting all elements at level 2."""
        with PARSStore(test_database) as store:
            filter_obj = WBSSearchFilter(parsid="proj_001", min_level=2, max_level=2)
            elements = store.search_wbs(filter_obj)
            assert len(elements) == 2
            codes = {e.wbs_code for e in elements}
            assert codes == {"01.01", "01.02"}

    def test_get_wbs_by_level_3(self, test_database):
        """Test getting all elements at level 3."""
        with PARSStore(test_database) as store:
            filter_obj = WBSSearchFilter(parsid="proj_001", min_level=3, max_level=3)
            elements = store.search_wbs(filter_obj)
            assert len(elements) == 3
            codes = {e.wbs_code for e in elements}
            assert codes == {"01.01.01", "01.01.02", "01.02.01"}

    def test_get_wbs_by_level_nonexistent_level(self, test_database):
        """Test getting elements at level that doesn't exist."""
        with PARSStore(test_database) as store:
            filter_obj = WBSSearchFilter(parsid="proj_001", min_level=10, max_level=10)
            elements = store.search_wbs(filter_obj)
            assert len(elements) == 0


class TestCycleDetection:
    """Test cycle detection in WBS hierarchies."""

    def test_subtree_detects_self_parent(self):
        """Test that get_wbs_subtree detects self-parent cycles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "cycle.duckdb"
            conn = duckdb.connect(str(db_path), read_only=False)
            try:
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
                conn.execute(
                    "INSERT INTO projects (parsid, project_name) VALUES (?, ?)",
                    ("proj_cycle", "Cycle Test"),
                )
                conn.execute(
                    """
                    INSERT INTO wbs_elements
                    (parsid, wbs_code, title, level, parent_wbs, leaf_node)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    ("proj_cycle", "01", "Root", 1, "01", False),
                )
                conn.commit()
            finally:
                conn.close()

            with PARSStore(db_path) as store:
                with pytest.raises(ValueError, match="Cycle"):
                    store.get_wbs_subtree("proj_cycle", "01", depth=None)

    def test_lineage_detects_mutual_cycle(self):
        """Test that get_wbs_lineage detects mutual parent cycles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "mutual_cycle.duckdb"
            conn = duckdb.connect(str(db_path), read_only=False)
            try:
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
                conn.execute(
                    "INSERT INTO projects (parsid, project_name) VALUES (?, ?)",
                    ("proj_mutual", "Mutual Cycle Test"),
                )
                conn.execute(
                    """
                    INSERT INTO wbs_elements
                    (parsid, wbs_code, title, level, parent_wbs, leaf_node)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    ("proj_mutual", "01", "A", 1, "01.01", False),
                )
                conn.execute(
                    """
                    INSERT INTO wbs_elements
                    (parsid, wbs_code, title, level, parent_wbs, leaf_node)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    ("proj_mutual", "01.01", "B", 2, "01", False),
                )
                conn.commit()
            finally:
                conn.close()

            with PARSStore(db_path) as store:
                with pytest.raises(ValueError, match="Cycle"):
                    store.get_wbs_lineage("proj_mutual", "01.01")


BLANK_PROJECT_ID_ERROR = "project_id is required and must not be blank."

# Every tool that takes project_id, with the extra arguments it needs.
PROJECT_SEARCH_TOOLS = [
    ("search_wbs", {}),
    ("get_leaf_nodes", {}),
    ("get_wbs_by_level", {"level": 2}),
    ("get_wbs_hierarchy", {"wbs_code": "01"}),
    ("get_wbs_lineage", {"wbs_code": "01"}),
    ("get_project_info", {}),
]


class TestProjectIdRequired:
    """Every project-scoped tool refuses a blank project_id with the fixed error."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("project_id", ["", "   ", "\t"])
    @pytest.mark.parametrize(("tool", "arguments"), PROJECT_SEARCH_TOOLS)
    async def test_blank_project_id_returns_fixed_error(
        self, mcp_server, tool, arguments, project_id
    ):
        """A blank project_id gets the fixed error and no rows from any project."""
        async with Client(mcp_server) as client:
            result = await client.call_tool(
                tool, {"project_id": project_id, **arguments}
            )
        assert result.structured_content == {"error": BLANK_PROJECT_ID_ERROR}

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("tool", "arguments", "rows_key", "expected_count"),
        [
            ("search_wbs", {}, "elements", 6),
            ("get_leaf_nodes", {}, "leaf_nodes", 3),
            ("get_wbs_by_level", {"level": 2}, "elements", 2),
        ],
    )
    async def test_real_project_id_still_returns_rows(
        self, mcp_server, tool, arguments, rows_key, expected_count
    ):
        """A real project_id still returns that project's rows through each tool."""
        async with Client(mcp_server) as client:
            result = await client.call_tool(
                tool, {"project_id": "proj_001", **arguments}
            )
        payload = result.structured_content
        assert "error" not in payload
        assert len(payload[rows_key]) == expected_count


NOT_FOUND_TOOLS = [
    ("get_wbs_hierarchy", {"wbs_code": "99.99"}),
    ("get_wbs_lineage", {"wbs_code": "99.99"}),
]


class TestUnknownWBSCodeIsNamed:
    """An unknown WBS code gets a message that names it, not the masked error."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("tool", "arguments"), NOT_FOUND_TOOLS)
    async def test_unknown_wbs_code_returns_not_found_message(
        self, mcp_server, tool, arguments
    ):
        """The client sees the code and project it asked for, and no internals."""
        async with Client(mcp_server) as client:
            result = await client.call_tool(
                tool, {"project_id": "proj_001", **arguments}
            )
        assert result.structured_content == {
            "error": "WBS element 99.99 not found in project proj_001"
        }


class TestUnknownProjectIsNamed:
    """An unknown project gets a not-found error, not an empty result."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("tool", "arguments"),
        [
            ("search_wbs", {}),
            ("get_leaf_nodes", {}),
            ("get_wbs_by_level", {"level": 2}),
        ],
    )
    async def test_unknown_project_returns_not_found(self, mcp_server, tool, arguments):
        """Empty results would look like a valid project with no matches."""
        async with Client(mcp_server) as client:
            result = await client.call_tool(
                tool, {"project_id": "PROJ_999", **arguments}
            )
        assert result.structured_content == {"error": "Project PROJ_999 not found"}


class TestLevelRowsReportLeafNode:
    """get_wbs_by_level reports whether each element is a leaf."""

    @pytest.mark.asyncio
    async def test_level_rows_include_leaf_node(self, mcp_server):
        async with Client(mcp_server) as client:
            result = await client.call_tool(
                "get_wbs_by_level", {"project_id": "proj_001", "level": 3}
            )
        elements = result.structured_content["elements"]
        assert elements, "level 3 has elements in the test fixture"
        assert all("leaf_node" in element for element in elements)
        assert all(element["leaf_node"] is True for element in elements)


class TestProjectIdIsCaseInsensitive:
    """An ID that differs from a stored ID only by case returns that project."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("tool", "arguments"),
        [
            ("search_wbs", {}),
            ("get_leaf_nodes", {}),
            ("get_wbs_by_level", {"level": 2}),
            ("get_wbs_hierarchy", {"wbs_code": "01"}),
            ("get_wbs_lineage", {"wbs_code": "01.01.01"}),
            ("get_project_info", {}),
        ],
    )
    async def test_upper_case_id_returns_the_stored_project(
        self, mcp_server, tool, arguments
    ):
        """The result for PROJ_001 is the same as the result for proj_001."""
        async with Client(mcp_server) as client:
            exact = await client.call_tool(
                tool, {"project_id": "proj_001", **arguments}
            )
            upper = await client.call_tool(
                tool, {"project_id": "PROJ_001", **arguments}
            )
        assert "error" not in upper.structured_content
        assert upper.structured_content == exact.structured_content
