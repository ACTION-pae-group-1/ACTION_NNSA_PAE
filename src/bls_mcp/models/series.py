from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from bls_mcp.models.enums import Periodicity
from bls_mcp.models.periods import EconomicPeriod

# BLS database codes the search filter accepts. The store filters on whatever
# codes a snapshot holds, so a code for a program not yet ingested (oe, OEWS)
# returns no rows rather than an error, and needs no change here once its
# ingestion lands.
ProgramCode = Literal["pc", "pd", "wp", "ci", "cu", "oe"]


class SeriesMetadata(BaseModel):
    series_id: str
    program: str
    title: str
    description: str | None = None
    classification_system: str | None = None
    classification_code: str | None = None
    parent_code: str | None = None
    industry_code: str | None = None
    commodity_code: str | None = None
    occupation_code: str | None = None
    geography: str | None = None
    area_code: str | None = None
    periodicity: Periodicity | None = None
    seasonal_adjustment: bool | None = None
    units: str | None = None
    first_period: EconomicPeriod | None = None
    latest_period: EconomicPeriod | None = None
    active: bool | None = None
    source_url: str | None = None


class SeriesSearchRequest(BaseModel):
    """Search the local BLS series catalog."""

    query: str = Field(
        default="",
        description=(
            "Text to search for in the local BLS catalog. "
            "Examples: 'steel', "
            "'construction materials', or 'employment'."
        ),
    )

    programs: list[ProgramCode] | None = Field(
        default=None,
        description=(
            "Optional BLS program filter. "
            "PROGRAM SELECTION: "
            "wp: Commodity-based PPI. Prefer for materials. "
            "pc: Current industry-based PPI. "
            "pd: Discontinued historical industry PPI. "
            "ci: Employment Cost Index. Prefer for labor. "
            "cu: Consumer Price Index for All Urban Consumers (CPI-U), "
            "consumer prices by item and area. "
            "oe: Occupational Employment and Wage Statistics (OEWS), "
            "employment and wages by occupation and area; returns results "
            "once a snapshot includes OEWS data. "
            "Use lowercase codes only. "
            "Do not use 'PPI', 'CPI', 'OEWS', 'PC', or 'CI'. "
            "Omit this field to search all programs."
        ),
        examples=[
            ["pc"],
            ["ci"],
            ["cu"],
            ["pc", "ci"],
        ],
    )

    active_only: bool = Field(
        default=True,
        description=(
            "Return only active series when true. "
            "Set false to include inactive historical series."
        ),
    )

    limit: int = Field(
        default=25,
        ge=1,
        le=100,
        description=("Maximum number of matching series to return."),
    )


class SeriesSearchResult(BaseModel):
    series: SeriesMetadata
    match_score: float | None = None
    match_reason: str | None = None


class SeriesHierarchyEntry(BaseModel):
    """A code directly above or beneath a series' code."""

    dimension: str
    code: str
    name: str | None = None
    series_id: str | None = None
    has_observations: bool = False


class UnverifiedDimension(BaseModel):
    """A dimension whose relationships could not be identified, and why."""

    dimension: str
    reason: str


class SeriesHierarchy(BaseModel):
    """What a series' code sits inside, and what is nested beneath it."""

    series_id: str
    program: str
    title: str
    snapshot_id: str
    #: complete: every dimension was looked up. partial: some could not be
    #: identified (see unverified). unknown: none could be.
    status: Literal["complete", "partial", "unknown"]
    #: How the relationships were identified.
    basis: str
    parents: list[SeriesHierarchyEntry]
    sub_items: list[SeriesHierarchyEntry]
    unverified: list[UnverifiedDimension]
    note: str
