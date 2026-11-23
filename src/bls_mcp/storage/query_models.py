"""Typed, snapshot-scoped query requests and results for the DuckDB store.

These models are deliberately independent of MCP and of the MCP-facing
``Decimal`` observation response. DuckDB index levels are stored as DOUBLE.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import StrEnum

from bls_mcp.storage.models import ObservationRecord, SeriesRecord

MAX_SERIES_IDS = 1_000
MAX_RESULT_ROWS = 1_000_000
DEFAULT_RESULT_ROWS = 100_000
MAX_SEARCH_PAGE = 1_000

_PERIOD = re.compile(r"(?:M(?:0[1-9]|1[0-3])|Q0[1-4]|S0[1-3])\Z")
_PROGRAM = re.compile(r"[a-z]{2}\Z")


def validate_year(value: int | None, name: str) -> None:
    if value is not None and (
        not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 32767
    ):
        raise ValueError(f"{name} must be a year between 1 and 32767")


def validate_window(start_year: int | None, end_year: int | None) -> None:
    validate_year(start_year, "start_year")
    validate_year(end_year, "end_year")
    if start_year is not None and end_year is not None and start_year > end_year:
        raise ValueError("start_year cannot exceed end_year")


def validate_max_rows(value: int) -> None:
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or not 1 <= value <= MAX_RESULT_ROWS
    ):
        raise ValueError(f"max_rows must be between 1 and {MAX_RESULT_ROWS}")


def validate_series_ids(series_ids: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    if not isinstance(series_ids, (tuple, list)):
        raise TypeError("series_ids must be a list or tuple of series identifiers")
    result = tuple(series_ids)
    if not 1 <= len(result) <= MAX_SERIES_IDS:
        raise ValueError(f"Supply between 1 and {MAX_SERIES_IDS} series IDs")
    if any(
        not isinstance(value, str)
        or not value
        or len(value) > 128
        or value != value.strip()
        for value in result
    ):
        raise ValueError("series_ids must contain nonempty, bounded identifiers")
    if len(set(result)) != len(result):
        raise ValueError("series_ids must not contain duplicates")
    return result


@dataclass(frozen=True, slots=True)
class SeriesSearchFilters:
    """Literal substring search and exact source-program classification filters."""

    query: str = ""
    programs: tuple[str, ...] | None = None
    active_only: bool = False
    seasonal_adjustment: bool | None = None
    industry_code: str | None = None
    product_code: str | None = None
    area_code: str | None = None
    item_code: str | None = None
    periodicity_code: str | None = None
    limit: int = 50
    offset: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.query, str) or len(self.query) > 256:
            raise ValueError("query must be a string of at most 256 characters")
        if self.programs is not None:
            if not isinstance(self.programs, tuple) or not self.programs:
                raise ValueError("programs must be a nonempty tuple when specified")
            if any(
                not isinstance(p, str) or not _PROGRAM.fullmatch(p)
                for p in self.programs
            ) or len(set(self.programs)) != len(self.programs):
                raise ValueError("programs must contain distinct two-letter BLS codes")
        if not isinstance(self.active_only, bool):
            raise ValueError("active_only must be a boolean")
        if self.seasonal_adjustment is not None and not isinstance(
            self.seasonal_adjustment, bool
        ):
            raise ValueError("seasonal_adjustment must be a boolean or None")
        for field in (
            "industry_code",
            "product_code",
            "area_code",
            "item_code",
            "periodicity_code",
        ):
            value = getattr(self, field)
            if value is not None and (
                not isinstance(value, str) or not value or len(value) > 64
            ):
                raise ValueError(f"{field} must be a nonempty code of at most 64 chars")
        if (
            not isinstance(self.limit, int)
            or isinstance(self.limit, bool)
            or not 1 <= self.limit <= MAX_SEARCH_PAGE
        ):
            raise ValueError(f"limit must be between 1 and {MAX_SEARCH_PAGE}")
        if (
            not isinstance(self.offset, int)
            or isinstance(self.offset, bool)
            or not 0 <= self.offset <= 1_000_000
        ):
            raise ValueError("offset must be between 0 and 1,000,000")


@dataclass(frozen=True, slots=True)
class PCClassification:
    industry_code: str
    industry_name: str | None
    product_code: str | None
    product_name: str | None
    seasonal_code: str
    base_date: str | None


@dataclass(frozen=True, slots=True)
class CUClassification:
    area_code: str
    area_name: str | None
    item_code: str
    item_name: str | None
    seasonal_code: str
    periodicity_code: str
    base_code: str
    base_period: str


@dataclass(frozen=True, slots=True)
class CIClassification:
    """Employment Cost Index dimensions of one current-dollar index series."""

    owner_code: str
    owner_name: str | None
    industry_code: str
    industry_name: str | None
    occupation_code: str
    occupation_name: str | None
    subcell_code: str
    subcell_name: str | None
    area_code: str
    area_name: str | None
    estimate_code: str
    estimate_name: str | None
    seasonal_code: str
    periodicity_code: str


@dataclass(frozen=True, slots=True)
class SeriesSearchHit:
    series: SeriesRecord
    classification: PCClassification | CUClassification | CIClassification | None
    match_score: float | None = None
    match_reason: str | None = None


@dataclass(frozen=True, slots=True)
class HierarchyEntry:
    """One code directly above or beneath a series' code."""

    dimension: str  # "industry", "product", "item", or an ECI dimension name
    code: str
    name: str | None
    series_id: str | None  # the matching series in this snapshot, if any
    has_observations: bool


@dataclass(frozen=True, slots=True)
class SeriesHierarchy:
    snapshot_id: str
    series_id: str
    program_code: str
    title: str
    parents: tuple[HierarchyEntry, ...]
    sub_items: tuple[HierarchyEntry, ...]
    #: Dimensions whose relationships were looked up.
    dimensions: tuple[str, ...] = ()
    #: dimension -> why its relationships could not be identified.
    unverified: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class SeriesSearchPage:
    snapshot_id: str
    matches: tuple[SeriesSearchHit, ...]
    total_matches: int
    limit: int
    offset: int


class QueryStatus(StrEnum):
    SUCCESS = "success"
    UNKNOWN_SERIES = "unknown_series"
    MISSING_BASE = "missing_base"
    ZERO_BASE = "zero_base"
    NO_ROWS_IN_WINDOW = "no_rows_in_window"


@dataclass(frozen=True, slots=True)
class SeriesOutcome:
    series_id: str
    status: QueryStatus
    observation_count: int = 0
    base_value: float | None = None


@dataclass(frozen=True, slots=True)
class ObservationsPage:
    snapshot_id: str
    observations: tuple[ObservationRecord, ...]
    statuses: tuple[SeriesOutcome, ...]


@dataclass(frozen=True, slots=True)
class NormalizedObservation:
    series_id: str
    year: int
    period: str
    raw_value: float
    normalized_value: float
    base_value: float
    source_file_id: int
    footnote_codes: str | None = None

    def __post_init__(self) -> None:
        if not all(
            math.isfinite(value)
            for value in (self.raw_value, self.normalized_value, self.base_value)
        ):
            raise ValueError("normalized observations must contain finite values")
        if self.base_value == 0:
            raise ValueError("base_value must be nonzero")


@dataclass(frozen=True, slots=True)
class NormalizationResult:
    snapshot_id: str
    base_year: int
    base_period: str
    target_base: float
    observations: tuple[NormalizedObservation, ...]
    statuses: tuple[SeriesOutcome, ...]


def validate_normalization(
    base_year: int, base_period: str, target_base: float
) -> None:
    validate_year(base_year, "base_year")
    if not isinstance(base_period, str) or not _PERIOD.fullmatch(base_period):
        raise ValueError("base_period must be an M01-M13, Q01-Q04, or S01-S03 code")
    if (
        isinstance(target_base, bool)
        or not isinstance(target_base, (int, float))
        or not math.isfinite(target_base)
        or target_base <= 0
    ):
        raise ValueError("target_base must be finite and positive")
