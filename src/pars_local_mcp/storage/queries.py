"""Database query interface for PARS storage.

Provides PARSStore context manager for querying WBS elements, projects, and hierarchies
from DuckDB backend.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from pars_local_mcp.mcp.errors import PublicError

from .models import ProjectMetadata, WBSElement, WBSSearchFilter

# Upper bound on hierarchy walks; guards against cyclic parent_wbs data.
MAX_HIERARCHY_DEPTH = 64


class PARSStore:
    """Read-only context manager for querying PARS DuckDB storage."""

    def __init__(self, db_path: str | Path) -> None:
        """Initialize store with database path.

        Args:
            db_path: Path to DuckDB database file

        Raises:
            FileNotFoundError: On ``__enter__`` if the database file is missing
        """
        self.db_path = str(db_path)
        self.conn: duckdb.DuckDBPyConnection | None = None

    def __enter__(self) -> PARSStore:
        """Enter context manager, opening database connection."""
        # Check explicitly: a read-write connect would silently create an empty
        # database, and read_only avoids taking an exclusive file lock.
        # Messages carry no path or driver text: they can reach tool clients.
        if not Path(self.db_path).is_file():
            raise FileNotFoundError("PARS database file is not present")
        try:
            self.conn = duckdb.connect(self.db_path, read_only=True)
        except Exception as e:
            raise RuntimeError("PARS database could not be opened") from e
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager, closing database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def search_wbs(
        self,
        filter_obj: WBSSearchFilter,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[WBSElement]:
        """Search WBS elements with optional filtering.

        Args:
            filter_obj: Search filter with constraints
            limit: Maximum number of results to return
            offset: Number of results to skip

        Returns:
            List of matching WBSElement instances
        """
        if not self.conn:
            raise RuntimeError("Database connection not open")

        query = (
            "SELECT parsid, wbs_code, title, level, parent_wbs, leaf_node "
            "FROM wbs_elements WHERE 1=1"
        )
        params: list[Any] = []

        # An explicit project_id is required: a blank one must not drop the filter.
        if filter_obj.parsid is not None:
            if not filter_obj.parsid.strip():
                raise ValueError("project_id is required and must not be blank")
            query += " AND parsid = ?"
            params.append(filter_obj.parsid)

        if filter_obj.wbs_pattern:
            query += " AND wbs_code LIKE ?"
            params.append(filter_obj.wbs_pattern)

        if filter_obj.min_level is not None:
            query += " AND level >= ?"
            params.append(filter_obj.min_level)

        if filter_obj.max_level is not None:
            query += " AND level <= ?"
            params.append(filter_obj.max_level)

        if filter_obj.include_leaves_only:
            query += " AND leaf_node = true"

        query += " ORDER BY parsid, wbs_code"

        if limit is not None:
            if limit < 0:
                raise ValueError("limit must be non-negative")
            query += " LIMIT ?"
            params.append(int(limit))

        if offset is not None:
            if offset < 0:
                raise ValueError("offset must be non-negative")
            query += " OFFSET ?"
            params.append(int(offset))

        try:
            result = self.conn.execute(query, params).fetchall()
            return [
                WBSElement(
                    parsid=row[0],
                    wbs_code=row[1],
                    title=row[2],
                    level=row[3],
                    parent_wbs=row[4],
                    leaf_node=bool(row[5]),
                )
                for row in result
            ]
        except Exception as e:
            raise RuntimeError(f"Search query failed: {e}") from e

    def list_projects(self) -> list[ProjectMetadata]:
        """List all projects with metadata.

        Returns:
            List of ProjectMetadata instances
        """
        if not self.conn:
            raise RuntimeError("Database connection not open")

        try:
            # Get all projects with element counts and max depth
            query = """
            SELECT
                p.parsid,
                p.project_name,
                COUNT(w.wbs_code) as total_elements,
                COALESCE(MAX(w.level), 0) as hierarchy_depth
            FROM projects p
            LEFT JOIN wbs_elements w ON p.parsid = w.parsid
            GROUP BY p.parsid, p.project_name
            ORDER BY p.parsid
            """
            result = self.conn.execute(query).fetchall()
            return [
                ProjectMetadata(
                    parsid=row[0],
                    project_name=row[1],
                    total_elements=row[2],
                    hierarchy_depth=row[3],
                )
                for row in result
            ]
        except Exception as e:
            raise RuntimeError(f"Failed to list projects: {e}") from e

    def get_project(self, parsid: str) -> ProjectMetadata | None:
        """Get metadata for a single project, or None if it does not exist."""
        if not self.conn:
            raise RuntimeError("Database connection not open")

        try:
            row = self.conn.execute(
                """
                SELECT
                    p.parsid,
                    p.project_name,
                    COUNT(w.wbs_code) AS total_elements,
                    COALESCE(MAX(w.level), 0) AS hierarchy_depth
                FROM projects p
                LEFT JOIN wbs_elements w ON p.parsid = w.parsid
                WHERE p.parsid = ?
                GROUP BY p.parsid, p.project_name
                """,
                [parsid],
            ).fetchone()
        except Exception as e:
            raise RuntimeError(f"Failed to get project: {e}") from e

        if row is None:
            return None
        return ProjectMetadata(
            parsid=row[0],
            project_name=row[1],
            total_elements=row[2],
            hierarchy_depth=row[3],
        )

    def get_wbs_subtree(
        self,
        parsid: str,
        wbs_code: str,
        depth: int | None = None,
        _visited: frozenset[str] = frozenset(),
    ) -> dict[str, Any]:
        """Get WBS element and its children as a tree structure.

        Args:
            parsid: Project ID
            wbs_code: WBS code of root element
            depth: Maximum depth to traverse (None = unlimited)

        Returns:
            Dict with 'element' (WBSElement or dict) and 'children' (list)

        Raises:
            Exception: If element not found
        """
        if not self.conn:
            raise RuntimeError("Database connection not open")

        if wbs_code in _visited or len(_visited) >= MAX_HIERARCHY_DEPTH:
            raise ValueError(f"Cycle or excessive depth in WBS hierarchy at {wbs_code}")
        visited = _visited | {wbs_code}

        try:
            # Get the root element
            select_cols = "SELECT parsid, wbs_code, title, level, parent_wbs, leaf_node"
            elem_result = self.conn.execute(
                f"{select_cols} FROM wbs_elements WHERE parsid = ? AND wbs_code = ?",
                [parsid, wbs_code],
            ).fetchone()

            if not elem_result:
                raise PublicError(
                    f"WBS element {wbs_code} not found in project {parsid}"
                )

            element = {
                "parsid": elem_result[0],
                "wbs_code": elem_result[1],
                "title": elem_result[2],
                "level": elem_result[3],
                "parent_wbs": elem_result[4],
                "leaf_node": bool(elem_result[5]),
            }

            # Get immediate children
            children_query = (
                f"{select_cols} FROM wbs_elements "
                "WHERE parsid = ? AND parent_wbs = ? ORDER BY wbs_code"
            )
            children_result = self.conn.execute(
                children_query,
                [parsid, wbs_code],
            ).fetchall()

            children = []
            for child_row in children_result:
                child_elem = {
                    "parsid": child_row[0],
                    "wbs_code": child_row[1],
                    "title": child_row[2],
                    "level": child_row[3],
                    "parent_wbs": child_row[4],
                    "leaf_node": bool(child_row[5]),
                }
                # Recursively get grandchildren if depth allows
                child_subtree = {"element": child_elem, "children": []}
                if depth is None or depth > 1:
                    grandchildren = self.get_wbs_subtree(
                        parsid,
                        child_row[1],
                        depth=depth - 1 if depth else None,
                        _visited=visited,
                    )
                    child_subtree["children"] = grandchildren["children"]
                children.append(child_subtree)

            return {"element": element, "children": children}
        except (ValueError, PublicError):
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to get WBS subtree: {e}") from e

    def get_wbs_lineage(self, parsid: str, wbs_code: str) -> list[WBSElement]:
        """Get full lineage from element to root (leaf-first order).

        Args:
            parsid: Project ID
            wbs_code: WBS code to get lineage for

        Returns:
            List of WBSElement from target to root (inclusive, leaf-first)
        """
        if not self.conn:
            raise RuntimeError("Database connection not open")

        try:
            # Get the target element
            select_cols = "SELECT parsid, wbs_code, title, level, parent_wbs, leaf_node"
            elem = self.conn.execute(
                f"{select_cols} FROM wbs_elements WHERE parsid = ? AND wbs_code = ?",
                [parsid, wbs_code],
            ).fetchone()

            if not elem:
                raise PublicError(
                    f"WBS element {wbs_code} not found in project {parsid}"
                )

            lineage: list[WBSElement] = []
            seen: set[str] = set()
            current_code = wbs_code

            # Walk up the parent chain, accumulating in leaf-to-root order
            elem_query = (
                f"{select_cols} FROM wbs_elements WHERE parsid = ? AND wbs_code = ?"
            )
            while current_code:
                if current_code in seen or len(seen) >= MAX_HIERARCHY_DEPTH:
                    raise ValueError(
                        f"Cycle or excessive depth in WBS lineage at {current_code}"
                    )
                seen.add(current_code)
                row = self.conn.execute(
                    elem_query,
                    [parsid, current_code],
                ).fetchone()

                if not row:
                    break

                lineage.append(
                    WBSElement(
                        parsid=row[0],
                        wbs_code=row[1],
                        title=row[2],
                        level=row[3],
                        parent_wbs=row[4],
                        leaf_node=bool(row[5]),
                    )
                )
                current_code = row[4]  # Move to parent

            return lineage  # Return leaf-to-root order
        except (ValueError, PublicError):
            raise
        except Exception as e:
            raise RuntimeError(f"Failed to get WBS lineage: {e}") from e

    def get_labeled_wbs(self, parsid: str | None = None) -> list:
        """Get labeled WBS records with CAEF hierarchy codes.

        Args:
            parsid: Project ID filter (None = all projects)

        Returns:
            List of LabeledWBSRecord instances
        """
        from .models import LabeledWBSRecord

        if not self.conn:
            raise RuntimeError("Database connection not open")

        try:
            query = (
                "SELECT parsid, wbs_code, title, caef_level_2, caef_level_3, "
                "caef_level_4, caef_level_5, caef_level_6, caef_level_7, caef_level_8 "
                "FROM labeled_wbs WHERE 1=1"
            )
            params: list[Any] = []

            if parsid:
                query += " AND parsid = ?"
                params.append(parsid)

            query += " ORDER BY parsid, wbs_code"

            # Check if table exists first
            tables = self.conn.execute("SHOW TABLES").fetchall()
            table_names = [t[0] for t in tables]

            if "labeled_wbs" not in table_names:
                return []

            result = self.conn.execute(query, params).fetchall()
            return [
                LabeledWBSRecord(
                    parsid=row[0],
                    wbs_code=row[1],
                    title=row[2],
                    caef_level_2=row[3] or "",
                    caef_level_3=row[4] or "",
                    caef_level_4=row[5] or "",
                    caef_level_5=row[6] or "",
                    caef_level_6=row[7] or "",
                    caef_level_7=row[8] or "",
                    caef_level_8=row[9] or "",
                )
                for row in result
            ]
        except Exception as e:
            raise RuntimeError(f"Failed to get labeled WBS: {e}") from e

    def get_project_split(self, train_ratio: float = 0.8) -> dict[str, Any]:
        """Split all labeled data into training and test sets by project.

        Uses different projects for train vs test sets to avoid data leakage.

        Args:
            train_ratio: Proportion of data for training (default 0.8)

        Returns:
            Dict with 'train' and 'test' keys, each containing lists of LabeledWBSRecord
        """
        from .models import LabeledWBSRecord

        if not self.conn:
            raise RuntimeError("Database connection not open")

        try:
            # Check if labeled_wbs table exists
            tables = self.conn.execute("SHOW TABLES").fetchall()
            table_names = [t[0] for t in tables]

            if "labeled_wbs" not in table_names:
                return {"train": [], "test": []}

            # Get all labeled data grouped by project
            select_labeled = (
                "SELECT parsid, wbs_code, title, caef_level_2, caef_level_3, "
                "caef_level_4, caef_level_5, caef_level_6, caef_level_7, caef_level_8 "
                "FROM labeled_wbs ORDER BY parsid, wbs_code"
            )
            all_records = self.conn.execute(select_labeled).fetchall()

            # Get unique projects
            projects = self.conn.execute(
                "SELECT DISTINCT parsid FROM labeled_wbs ORDER BY parsid"
            ).fetchall()
            project_ids = [p[0] for p in projects]

            if not project_ids:
                return {"train": [], "test": []}

            # Split projects into train/test (disjoint)
            n_projects = len(project_ids)
            train_n = max(1, int(n_projects * train_ratio))
            train_projects = set(project_ids[:train_n])

            # Categorize records by split
            train_records = []
            test_records = []

            for row in all_records:
                record = LabeledWBSRecord(
                    parsid=row[0],
                    wbs_code=row[1],
                    title=row[2],
                    caef_level_2=row[3] or "",
                    caef_level_3=row[4] or "",
                    caef_level_4=row[5] or "",
                    caef_level_5=row[6] or "",
                    caef_level_6=row[7] or "",
                    caef_level_7=row[8] or "",
                    caef_level_8=row[9] or "",
                )

                if record.parsid in train_projects:
                    train_records.append(record)
                else:
                    test_records.append(record)

            return {"train": train_records, "test": test_records}
        except Exception as e:
            raise RuntimeError(f"Failed to get project split: {e}") from e
