"""Typed records for the analytical store, separate from legacy MCP models.

The old MCP Observation model serializes Decimal as text. These new records
intentionally use float for DuckDB DOUBLE, and retain original BLS period codes.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class SnapshotState(StrEnum):
    BUILDING = "BUILDING"
    VALIDATING = "VALIDATING"
    READY = "READY"
    PUBLISHED = "PUBLISHED"


class ValidationStatus(StrEnum):
    NOT_RUN = "NOT_RUN"
    PASSED = "PASSED"
    FAILED = "FAILED"


_SNAPSHOT_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
_SHA256 = re.compile(r"[0-9a-fA-F]{64}\Z")
_PROGRAM = re.compile(r"[a-z]{2}\Z")


def _check_timestamp(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must have a timezone")


def _check_program(value: str) -> None:
    if not _PROGRAM.fullmatch(value):
        raise ValueError("program_code must be a two-letter lowercase BLS code")


@dataclass(frozen=True, slots=True)
class SnapshotInfo:
    snapshot_id: str
    built_at: datetime
    programs: tuple[str, ...]
    schema_version: int = 5
    build_commit: str | None = None
    lifecycle_state: SnapshotState = SnapshotState.BUILDING
    validation_status: ValidationStatus = ValidationStatus.NOT_RUN

    def __post_init__(self) -> None:
        if not _SNAPSHOT_ID.fullmatch(self.snapshot_id):
            raise ValueError("snapshot_id must be a safe, nonempty identifier")
        _check_timestamp(self.built_at, "built_at")
        if not isinstance(self.programs, tuple) or not self.programs:
            raise ValueError("programs must be a nonempty tuple")
        for program in self.programs:
            _check_program(program)
        if len(self.programs) != len(set(self.programs)):
            raise ValueError("programs must not contain duplicates")
        if not isinstance(self.lifecycle_state, SnapshotState):
            raise ValueError("invalid snapshot lifecycle state")
        if not isinstance(self.validation_status, ValidationStatus):
            raise ValueError("invalid snapshot validation status")
        if self.schema_version < 1:
            raise ValueError("schema_version must be positive")


@dataclass(frozen=True, slots=True)
class SourceFileReceipt:
    source_file_id: int
    program_code: str
    filename: str
    sha256: str
    size_bytes: int
    selection_role: str
    source_url: str | None = None
    retrieved_at: datetime | None = None
    etag: str | None = None
    last_modified: str | None = None

    def __post_init__(self) -> None:
        if self.source_file_id < 1:
            raise ValueError("source_file_id must be positive")
        _check_program(self.program_code)
        if not self.filename or not self.selection_role:
            raise ValueError("filename and selection_role are required")
        if not _SHA256.fullmatch(self.sha256):
            raise ValueError("sha256 must contain 64 hexadecimal characters")
        if self.size_bytes < 0:
            raise ValueError("size_bytes cannot be negative")
        if self.retrieved_at is not None:
            _check_timestamp(self.retrieved_at, "retrieved_at")


@dataclass(frozen=True, slots=True)
class SeriesRecord:
    series_id: str
    program_code: str
    title: str
    description: str | None = None
    seasonal_adjustment: bool | None = None
    first_year: int | None = None
    first_period: str | None = None
    last_year: int | None = None
    last_period: str | None = None
    units: str | None = None
    original_reference_base: str | None = None
    active: bool | None = None

    def __post_init__(self) -> None:
        if not self.series_id or not self.title:
            raise ValueError("series_id and title are required")
        _check_program(self.program_code)


@dataclass(frozen=True, slots=True)
class ObservationRecord:
    series_id: str
    year: int
    period: str
    value: float
    source_file_id: int
    footnote_codes: str | None = None

    def __post_init__(self) -> None:
        if not self.series_id or not self.period:
            raise ValueError("series_id and period are required")
        if not 0 <= self.year <= 32767:
            raise ValueError("year must fit positive SMALLINT")
        if not math.isfinite(self.value):
            raise ValueError("value must be finite")
        if self.source_file_id < 1:
            raise ValueError("source_file_id must be positive")


@dataclass(frozen=True, slots=True)
class SeriesSearchResult:
    """Future query-service result. Every response names its source snapshot."""

    snapshot_id: str
    series: tuple[SeriesRecord, ...]


@dataclass(frozen=True, slots=True)
class ObservationResult:
    """Future query-service result; large exports may use Arrow instead."""

    snapshot_id: str
    observations: tuple[ObservationRecord, ...]
