"""TDD – Phase 1b: ObservationService backed by BLSStore.

Fails until ObservationService.fetch_cached() reads from BLSStore
instead of ObservationRepository, and returns the same Observation
Pydantic model the tool layer already expects.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip("duckdb")

from bls_mcp.storage.connection import build_connection
from bls_mcp.storage.models import SnapshotInfo, SourceFileReceipt
from bls_mcp.storage.schema import initialize_schema
from bls_mcp.storage.snapshots import write_snapshot_info, write_source_file
from bls_mcp.storage.store import BLSStore

# ---------------------------------------------------------------------------
# Minimal published DuckDB fixture with observations
# ---------------------------------------------------------------------------

PC_SERIES = "PCU334000334000"


@pytest.fixture()
def published_path(tmp_path: Path) -> Path:
    path = tmp_path / "obs.duckdb"
    with build_connection(path, threads=1) as conn:
        initialize_schema(conn)
        write_snapshot_info(
            conn, SnapshotInfo("obs_svc_test", datetime.now(UTC), ("pc",))
        )
        write_source_file(
            conn,
            SourceFileReceipt(1, "pc", "fixture.txt", "b" * 64, 1, "current"),
        )
        conn.execute("INSERT INTO pc_industry VALUES ('334---', 'Machinery')")
        conn.execute(
            "INSERT INTO pc_product VALUES ('334---', '334---', 'Machinery output')"
        )
        conn.execute(
            "INSERT INTO series_catalog VALUES (?, 'pc', 'Machinery PPI', NULL, "
            "FALSE, 2020, 'M01', 2026, 'M12', 'index', '200012', TRUE)",
            [PC_SERIES],
        )
        conn.execute(
            "INSERT INTO pc_series VALUES (?, '334---', '334---', 'U', '200012')",
            [PC_SERIES],
        )
        conn.executemany(
            "INSERT INTO observations VALUES (?, ?, ?, ?, ?, ?)",
            [
                (PC_SERIES, 2024, "M10", 97.5, None, 1),
                (PC_SERIES, 2024, "M11", 98.0, None, 1),
                (PC_SERIES, 2024, "M12", 100.0, None, 1),
                (PC_SERIES, 2025, "M01", 103.0, "P", 1),
                (PC_SERIES, 2025, "M06", 108.0, None, 1),
                (PC_SERIES, 2025, "M12", 110.0, None, 1),
            ],
        )
        conn.execute(
            "CREATE INDEX observations_series_id_art ON observations(series_id)"
        )
        conn.execute(
            "UPDATE snapshot_info "
            "SET lifecycle_state='PUBLISHED', validation_status='PASSED'"
        )
    return path


def _make_service(path: Path):
    from bls_mcp.clients.bls import BLSClient
    from bls_mcp.services.access import BLSAccessService
    from bls_mcp.services.observations import ObservationService

    store = BLSStore(path)
    return ObservationService(BLSClient(), BLSAccessService(None), store)


# ---------------------------------------------------------------------------
# Tests: constructor signature
# ---------------------------------------------------------------------------


def test_observation_service_accepts_bls_store(published_path: Path) -> None:
    """ObservationService must accept BLSStore as the third positional argument."""
    service = _make_service(published_path)
    assert service is not None


def test_observation_service_no_longer_accepts_observation_repository(
    published_path: Path,
) -> None:
    """After Phase 1b, ObservationRepository must not be the cache parameter type."""
    import inspect

    from bls_mcp.services.observations import ObservationService

    sig = inspect.signature(ObservationService.__init__)
    for name, param in sig.parameters.items():
        if param.annotation is not inspect.Parameter.empty:
            annotation = str(param.annotation)
            assert "ObservationRepository" not in annotation, (
                f"Parameter '{name}' still annotated as ObservationRepository; "
                "switch to BLSStore"
            )


# ---------------------------------------------------------------------------
# Tests: fetch_cached behaviour via BLSStore
# ---------------------------------------------------------------------------


def test_fetch_cached_returns_observations_as_pydantic_models(
    published_path: Path,
) -> None:
    """fetch_cached must return a list of Observation Pydantic models."""
    from bls_mcp.models.observations import Observation

    service = _make_service(published_path)
    results = service.fetch_cached(PC_SERIES)
    assert len(results) > 0
    assert all(isinstance(r, Observation) for r in results)


def test_fetch_cached_returns_all_observations_by_default(
    published_path: Path,
) -> None:
    """With no filters, all stored observations for the series are returned."""
    service = _make_service(published_path)
    results = service.fetch_cached(PC_SERIES)
    assert len(results) == 6


def test_fetch_cached_limit_takes_latest_n(published_path: Path) -> None:
    """limit=N must return the N most recent observations (by period order)."""
    service = _make_service(published_path)
    results = service.fetch_cached(PC_SERIES, limit=2)
    assert len(results) == 2
    # Latest two are 2025-M06 and 2025-M12.
    years = [r.period.year for r in results]
    assert all(y == 2025 for y in years)


def test_fetch_cached_year_range_filters_correctly(published_path: Path) -> None:
    service = _make_service(published_path)
    results = service.fetch_cached(PC_SERIES, start_year=2025, end_year=2025)
    assert all(r.period.year == 2025 for r in results)
    assert len(results) == 3


def test_fetch_cached_unknown_series_returns_empty(published_path: Path) -> None:
    service = _make_service(published_path)
    assert service.fetch_cached("UNKNOWN_SERIES_ID") == []


def test_fetch_cached_observation_fields_are_populated(published_path: Path) -> None:
    """Mapped Observation fields must carry correct values from DuckDB."""
    from bls_mcp.models.observations import Observation

    service = _make_service(published_path)
    results = service.fetch_cached(PC_SERIES, start_year=2025, end_year=2025)
    by_month = {r.period.month: r for r in results if r.period.month is not None}
    jan = by_month[1]
    assert isinstance(jan, Observation)
    assert jan.series_id == PC_SERIES
    assert jan.period.year == 2025
    # DuckDB stores as DOUBLE; must be convertible to Decimal for the model.
    assert float(jan.value) == pytest.approx(103.0)


def test_fetch_cached_invalid_period_raises(published_path: Path) -> None:
    """Invalid year windows must raise InvalidPeriodError, same as before."""
    from bls_mcp.exceptions import InvalidPeriodError

    service = _make_service(published_path)
    with pytest.raises(InvalidPeriodError):
        service.fetch_cached(PC_SERIES, start_year=2026, end_year=2025)


def test_fetch_cached_invalid_limit_raises(published_path: Path) -> None:
    from bls_mcp.exceptions import InvalidPeriodError

    service = _make_service(published_path)
    with pytest.raises(InvalidPeriodError):
        service.fetch_cached(PC_SERIES, limit=0)
    with pytest.raises(InvalidPeriodError):
        service.fetch_cached(PC_SERIES, limit=101)


# ---------------------------------------------------------------------------
# Tests: live fetch() path is unchanged (still uses BLSClient)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_live_still_uses_bls_client(published_path: Path) -> None:
    """fetch() must still call BLSClient.get_series_observations, not BLSStore."""
    from bls_mcp.clients.bls import BLSClient
    from bls_mcp.models.observations import Observation
    from bls_mcp.services.access import BLSAccessService
    from bls_mcp.services.observations import ObservationService

    mock_client = MagicMock(spec=BLSClient)
    fake_obs = [
        Observation(
            series_id=PC_SERIES,
            period=__import__(
                "bls_mcp.models.periods", fromlist=["EconomicPeriod"]
            ).EconomicPeriod(year=2025, month=1, periodicity="MONTHLY"),
            value=Decimal("103.0"),
            retrieved_at=datetime.now(UTC),
            source="bls_api",
        )
    ]
    mock_client.get_series_observations = AsyncMock(return_value=fake_obs)

    service = ObservationService(
        mock_client, BLSAccessService("fixture-key"), BLSStore(published_path)
    )
    result = await service.fetch([PC_SERIES], 2025, 2025)
    mock_client.get_series_observations.assert_awaited_once_with(
        [PC_SERIES], 2025, 2025
    )
    assert result == fake_obs


@pytest.mark.asyncio
async def test_fetch_live_requires_api_key(published_path: Path) -> None:
    """fetch() must still raise BLSAPIError when no key is configured."""
    from bls_mcp.clients.bls import BLSClient
    from bls_mcp.exceptions import BLSAPIError
    from bls_mcp.services.access import BLSAccessService
    from bls_mcp.services.observations import ObservationService

    service = ObservationService(
        BLSClient(), BLSAccessService(None), BLSStore(published_path)
    )
    with pytest.raises(BLSAPIError):
        await service.fetch([PC_SERIES], 2025, 2025)
