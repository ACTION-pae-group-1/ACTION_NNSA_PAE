"""Test double for the PARS read tools, with PARS return shapes.

All data is synthetic. ``fail`` names tools that answer with the PARS error
shape, so a panel's error state can be exercised. ``search_wbs`` matches WBS
codes with SQL LIKE semantics, as PARS does, and never matches titles.

The app never imports this module; it never connects to PARS.

Source column names are pinned to src/pars_local_mcp/wbs_port/pipeline.py
(SOURCE_READS on feat/pars_mcp); test_pars_mock.py checks them.
"""

from __future__ import annotations

import copy
import re
from typing import Any

_DESCRIPTION_COLUMNS = [
    "parsid",
    "program",
    "project_name",
    "project_status",
    "project_type",
    "project_description",
]
_WBS_COLUMNS = ["parsid", "program", "project_name", "wbs", "wbs_level", "wbs_title"]

_RESPONSES: dict[str, dict[str, Any]] = {
    "list_projects": {
        "projects": [
            {
                "parsid": "100",
                "project_name": "Demo Synthetic Project",
                "total_elements": 42,
                "hierarchy_depth": 4,
            }
        ]
    },
    "get_project_info": {
        "parsid": "100",
        "project_name": "Demo Synthetic Project",
        "total_elements": 42,
        "hierarchy_depth": 4,
    },
    "get_wbs_hierarchy": {
        "element": {
            "wbs_code": "1",
            "title": "Root",
            "level": 1,
            "parent_wbs": None,
            "leaf_node": False,
        },
        "children": [
            {
                "element": {
                    "wbs_code": "1.1",
                    "title": "Materials",
                    "level": 2,
                    "leaf_node": False,
                },
                "children": [],
            }
        ],
    },
    "search_wbs": {
        "elements": [
            {
                "wbs_code": "1.2.1",
                "title": "Pump",
                "level": 3,
                "parent_wbs": "1.2",
                "leaf_node": True,
            }
        ]
    },
    "get_wbs_lineage": {
        "lineage": [
            {"wbs_code": "1.2.1", "title": "Pump", "level": 3},
            {"wbs_code": "1.2", "title": "Equipment", "level": 2},
            {"wbs_code": "1", "title": "Root", "level": 1},
        ]
    },
    "get_leaf_nodes": {
        "leaf_nodes": [{"wbs_code": "1.2.1", "title": "Pump", "level": 3}]
    },
    "get_wbs_by_level": {
        "elements": [{"wbs_code": "1.1", "title": "Materials", "parent_wbs": "1"}]
    },
    "validate_wbs_inputs": {
        "source_db_name": "mock_pars",
        "ok": True,
        "problems": [],
        "tables": ["silver_spae_data"],
        "data_origin": "synthetic_mock",
    },
    "get_wbs_run_status": {
        "run_id": "r1",
        "created_at": "2026-11-15T10:00:00",
        "data_origin": "synthetic_mock",
        "stages": {"clean": {"status": "ok"}},
    },
    "get_wbs_project_descriptions": {
        "table": "silver_project_descriptions",
        "columns": _DESCRIPTION_COLUMNS,
        "total_rows": 1,
        "returned": 1,
        "rows": [
            {
                "parsid": "100",
                "program": "Demo Program",
                "project_name": "Demo Synthetic Project",
                "project_status": "Active",
                "project_type": "Synthetic",
                "project_description": "Synthetic demo project.",
            }
        ],
    },
    "get_wbs_rows": {
        "table": "silver_spae_data",
        "columns": _WBS_COLUMNS,
        "total_rows": 2,
        "returned": 2,
        "rows": [
            {
                "parsid": "100",
                "program": "Demo Program",
                "project_name": "Demo Synthetic Project",
                "wbs": "1.1",
                "wbs_level": 2,
                "wbs_title": "Materials",
            },
            {
                "parsid": "100",
                "program": "Demo Program",
                "project_name": "Demo Synthetic Project",
                "wbs": "1.2.1",
                "wbs_level": 3,
                "wbs_title": "Pump",
            },
        ],
    },
}


def _like(value: str, pattern: str) -> bool:
    """SQL LIKE with % and _ wildcards, as PARS's ``wbs_code LIKE ?`` behaves."""
    regex = "".join(
        ".*" if c == "%" else "." if c == "_" else re.escape(c) for c in pattern
    )
    return re.fullmatch(regex, value, re.DOTALL) is not None


class FakeParsMock:
    """Answers each read tool with a fresh copy of its synthetic response."""

    def __init__(self, fail: frozenset[str] | set[str] = frozenset()) -> None:
        self._fail = frozenset(fail)

    def call(self, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool in self._fail:
            return {"error": "mock failure"}
        response = copy.deepcopy(_RESPONSES[tool])
        if tool == "get_wbs_hierarchy":
            # Keep the synthetic fixture consistent with its level-1 picker.
            code = arguments.get("wbs_code", "")
            if code == "1.1":
                response["element"] = {
                    "wbs_code": "1.1",
                    "title": "Materials",
                    "level": 1,
                    "leaf_node": True,
                }
                response["children"] = []
            elif code != "1":
                return {"error": "WBS element not found"}
        if tool == "search_wbs" and arguments.get("wbs_pattern"):
            pattern = str(arguments["wbs_pattern"])
            response["elements"] = [
                e for e in response["elements"] if _like(e["wbs_code"], pattern)
            ]
        return response
