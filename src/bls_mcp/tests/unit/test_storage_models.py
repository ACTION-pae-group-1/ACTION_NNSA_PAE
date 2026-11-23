"""Typed DuckDB records never change the existing MCP model contracts."""

from datetime import datetime, timezone

import pytest

from bls_mcp.storage.models import (
    ObservationRecord,
    ObservationResult,
    SeriesRecord,
    SeriesSearchResult,
    SnapshotInfo,
    SnapshotState,
    SourceFileReceipt,
)

NOW = datetime(2026, 11, 5, 12, 0, tzinfo=timezone.utc)


def test_snapshot_identity_rejects_unsafe_ids_and_unaware_times():
    for identifier in ("", "../active", "with spaces", "/tmp/target"):
        with pytest.raises(ValueError, match="snapshot_id"):
            SnapshotInfo(identifier, NOW, ("pc",))
    with pytest.raises(ValueError, match="timezone"):
        SnapshotInfo("snapshot_1", NOW.replace(tzinfo=None), ("pc",))
    with pytest.raises(ValueError, match="nonempty tuple"):
        SnapshotInfo("snapshot_1", NOW, ())
    with pytest.raises(ValueError, match="duplicates"):
        SnapshotInfo("snapshot_1", NOW, ("pc", "pc"))
    with pytest.raises(ValueError, match="program_code"):
        SnapshotInfo("snapshot_1", NOW, ("PPI",))


def test_snapshot_identity_has_explicit_prepublication_state():
    info = SnapshotInfo("snapshot_1", NOW, ("pc", "cu", "ci"))
    assert info.lifecycle_state is SnapshotState.BUILDING
    assert info.schema_version == 5


def test_source_receipts_enforce_hash_sizes_and_timezones():
    valid = dict(
        source_file_id=1,
        program_code="pc",
        filename="pc.data.0.Current",
        sha256="f" * 64,
        size_bytes=0,
        selection_role="current",
    )
    assert SourceFileReceipt(**valid).size_bytes == 0
    with pytest.raises(ValueError, match="sha256"):
        SourceFileReceipt(**(valid | {"sha256": "bad"}))
    with pytest.raises(ValueError, match="negative"):
        SourceFileReceipt(**(valid | {"size_bytes": -1}))
    with pytest.raises(ValueError, match="timezone"):
        SourceFileReceipt(**(valid | {"retrieved_at": NOW.replace(tzinfo=None)}))


def test_double_records_allow_quarters_and_annual_averages_but_not_nan():
    for period in ("Q01", "Q04", "M01", "M13"):
        row = ObservationRecord("CIU1010000000000I", 2026, period, 123.45, 1)
        assert row.value == 123.45
    for value in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="finite"):
            ObservationRecord("CIU1010000000000I", 2026, "Q01", value, 1)


def test_typed_result_envelopes_include_snapshot_provenance():
    series = SeriesRecord("PCU123", "pc", "Test producer series")
    observation = ObservationRecord("PCU123", 2025, "M13", 112.5, 3)
    hits = SeriesSearchResult("snapshot_1", (series,))
    data = ObservationResult("snapshot_1", (observation,))
    assert hits.snapshot_id == data.snapshot_id
    assert data.observations[0].period == "M13"
