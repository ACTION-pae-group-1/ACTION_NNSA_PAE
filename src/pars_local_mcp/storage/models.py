"""Data models for PARS MCP storage layer.

Defines data classes for:
- WBSElement: Individual work breakdown structure element
- ProjectMetadata: Project summary information
- LabeledWBSRecord: Training data with CAEF hierarchy labels
- WBSSearchFilter: Query filter specification
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WBSElement:
    """A single element in the Work Breakdown Structure (WBS)."""

    parsid: str
    wbs_code: str
    title: str
    level: int
    parent_wbs: str | None
    leaf_node: bool


@dataclass
class ProjectMetadata:
    """Project summary information."""

    parsid: str
    project_name: str
    total_elements: int
    hierarchy_depth: int


@dataclass
class LabeledWBSRecord:
    """Labeled WBS record with CAEF hierarchy codes for training."""

    parsid: str
    wbs_code: str
    title: str
    caef_level_2: str
    caef_level_3: str
    caef_level_4: str
    caef_level_5: str
    caef_level_6: str
    caef_level_7: str
    caef_level_8: str


@dataclass
class WBSSearchFilter:
    """Filter specification for WBS element searches."""

    parsid: str | None = None
    wbs_pattern: str | None = None
    min_level: int | None = None
    max_level: int | None = None
    include_leaves_only: bool = False
