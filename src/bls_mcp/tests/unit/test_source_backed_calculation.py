"""TDD – Phase 2: SourceBackedCalculationService.

Verifies that calculate_index_from_bls resolves base and target observations
from the DuckDB snapshot and returns a populated CalculationLedger.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

pytest.importorskip("duckdb")

from bls_mcp.storage.connection import build_connection
from bls_mcp.storage.models import SnapshotInfo, SourceFileReceipt
from bls_mcp.storage.schema import initialize_schema
from bls_mcp.storage.snapshots import write_snapshot_info, write_source_file
from bls_mcp.storage.store import BLSStore

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SERIES_A = "PCU100000000000"
SERIES_B = "PCU200000000000"
QUARTERLY_C = "CIU300000000000"
QUARTERLY_D = "CIU400000000000"


# ---------------------------------------------------------------------------
# Minimal published DuckDB fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def published_path(tmp_path: Path) -> Path:
    path = tmp_path / "calc.duckdb"
    with build_connection(path, threads=1) as conn:
        initialize_schema(conn)
        write_snapshot_info(conn, SnapshotInfo("calc_test", datetime.now(UTC), ("pc",)))
        write_source_file(
            conn,
            SourceFileReceipt(1, "pc", "fixture.txt", "a" * 64, 1, "current"),
        )
        conn.execute("INSERT INTO pc_industry VALUES ('100---', 'Sector A')")
        conn.execute("INSERT INTO pc_product VALUES ('100---', '100---', 'Product A')")
        conn.execute("INSERT INTO pc_industry VALUES ('200---', 'Sector B')")
        conn.execute("INSERT INTO pc_product VALUES ('200---', '200---', 'Product B')")
        # Two series in the catalog
        conn.executemany(
            "INSERT INTO series_catalog VALUES (?, 'pc', ?, NULL, FALSE, "
            "2020, 'M01', 2026, 'M12', 'index', '202412', TRUE)",
            [(SERIES_A, "Series A"), (SERIES_B, "Series B")],
        )
        conn.executemany(
            "INSERT INTO pc_series VALUES (?, ?, ?, 'U', '202412')",
            [(SERIES_A, "100---", "100---"), (SERIES_B, "200---", "200---")],
        )
        # Observations: base 2024-M12, target 2025-M12
        conn.executemany(
            "INSERT INTO observations VALUES (?, ?, ?, ?, ?, ?)",
            [
                (SERIES_A, 2024, "M12", 100.0, None, 1),
                (SERIES_A, 2025, "M12", 110.0, None, 1),
                (SERIES_B, 2024, "M12", 200.0, None, 1),
                (SERIES_B, 2025, "M12", 220.0, None, 1),
            ],
        )
        conn.execute(
            "UPDATE snapshot_info "
            "SET lifecycle_state='PUBLISHED', validation_status='PASSED'"
        )
    return path


@pytest.fixture()
def published_path_quarterly(tmp_path: Path) -> Path:
    """Mixed fixture: annual and quarterly-only series (ECI-like)."""
    path = tmp_path / "calc_quarterly.duckdb"
    with build_connection(path, threads=1) as conn:
        initialize_schema(conn)
        write_snapshot_info(
            conn, SnapshotInfo("calc_quarterly", datetime.now(UTC), ("pc",))
        )
        write_source_file(
            conn,
            SourceFileReceipt(1, "pc", "fixture.txt", "a" * 64, 1, "current"),
        )
        conn.execute("INSERT INTO pc_industry VALUES ('100---', 'Sector A')")
        conn.execute("INSERT INTO pc_product VALUES ('100---', '100---', 'Product A')")
        conn.execute("INSERT INTO pc_industry VALUES ('300---', 'Sector C')")
        conn.execute("INSERT INTO pc_product VALUES ('300---', '300---', 'Product C')")
        conn.execute("INSERT INTO pc_industry VALUES ('400---', 'Sector D')")
        conn.execute("INSERT INTO pc_product VALUES ('400---', '400---', 'Product D')")
        conn.executemany(
            "INSERT INTO series_catalog VALUES (?, 'pc', ?, NULL, FALSE, "
            "2020, 'M01', 2026, 'M12', 'index', '202412', TRUE)",
            [
                (SERIES_A, "Series A"),
                (QUARTERLY_C, "Quarterly Series C"),
                (QUARTERLY_D, "Quarterly Series D"),
            ],
        )
        conn.executemany(
            "INSERT INTO pc_series VALUES (?, ?, ?, 'U', '202412')",
            [
                (SERIES_A, "100---", "100---"),
                (QUARTERLY_C, "300---", "300---"),
                (QUARTERLY_D, "400---", "400---"),
            ],
        )
        # Series A publishes an annual average; C and D publish quarters only,
        # and D has no Q04, so the annual anchor cannot resolve for it.
        conn.executemany(
            "INSERT INTO observations VALUES (?, ?, ?, ?, ?, ?)",
            [
                (SERIES_A, 2024, "M13", 101.0, None, 1),
                (SERIES_A, 2025, "M13", 111.0, None, 1),
                (QUARTERLY_C, 2024, "Q01", 150.0, None, 1),
                (QUARTERLY_C, 2024, "Q02", 152.0, None, 1),
                (QUARTERLY_C, 2024, "Q03", 154.0, None, 1),
                (QUARTERLY_C, 2024, "Q04", 156.0, None, 1),
                (QUARTERLY_C, 2025, "Q01", 164.0, None, 1),
                (QUARTERLY_C, 2025, "Q02", 165.0, None, 1),
                (QUARTERLY_C, 2025, "Q03", 166.0, None, 1),
                (QUARTERLY_C, 2025, "Q04", 168.0, None, 1),
                (QUARTERLY_D, 2024, "Q01", 180.0, None, 1),
                (QUARTERLY_D, 2024, "Q02", 181.0, None, 1),
                (QUARTERLY_D, 2024, "Q03", 182.0, None, 1),
                (QUARTERLY_D, 2025, "Q01", 190.0, None, 1),
                (QUARTERLY_D, 2025, "Q02", 191.0, None, 1),
                (QUARTERLY_D, 2025, "Q03", 192.0, None, 1),
            ],
        )
        conn.execute(
            "UPDATE snapshot_info "
            "SET lifecycle_state='PUBLISHED', validation_status='PASSED'"
        )
    return path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service(path: Path):
    from bls_mcp.services.calculations import EscalationCalculationService
    from bls_mcp.services.source_calculation import SourceBackedCalculationService
    from bls_mcp.services.validation import ValidationService

    store = BLSStore(path)
    calc = EscalationCalculationService()
    validation = ValidationService()
    return SourceBackedCalculationService(
        store=store, calculations=calc, validation=validation
    )


def _make_spec(*, base_period_kwargs, target_period_kwargs, components):
    from bls_mcp.models.periods import EconomicPeriod
    from bls_mcp.models.specifications import EscalationIndexSpec

    return EscalationIndexSpec(
        id="test-spec",
        name="Test Spec",
        base_period=EconomicPeriod(**base_period_kwargs),
        target_period=EconomicPeriod(**target_period_kwargs),
        components=components,
    )


def _component(*, id: str, series_id: str, weight: float):
    from bls_mcp.models.basket import EscalationComponent
    from bls_mcp.models.enums import ComponentType

    return EscalationComponent(
        id=id,
        name=id,
        component_type=ComponentType.MATERIAL,
        weight=weight,
        series_id=series_id,
    )


# ---------------------------------------------------------------------------
# Tests: happy path
# ---------------------------------------------------------------------------


def test_calculate_returns_result_and_ledger(published_path: Path) -> None:
    """calculate() returns an EscalationCalculationResult and a CalculationLedger."""
    from bls_mcp.models.calculations import EscalationCalculationResult
    from bls_mcp.models.enums import Periodicity
    from bls_mcp.models.provenance import CalculationLedger

    service = _make_service(published_path)
    spec = _make_spec(
        base_period_kwargs={
            "year": 2024,
            "month": 12,
            "periodicity": Periodicity.MONTHLY,
        },
        target_period_kwargs={
            "year": 2025,
            "month": 12,
            "periodicity": Periodicity.MONTHLY,
        },
        components=[_component(id="mat_a", series_id=SERIES_A, weight=1.0)],
    )
    result, ledger = service.calculate(spec)

    assert isinstance(result, EscalationCalculationResult)
    assert isinstance(ledger, CalculationLedger)


def test_composite_factor_is_correct_single_component(published_path: Path) -> None:
    """Single component: temporal factor = target / base = 110 / 100 = 1.1."""
    from bls_mcp.models.enums import Periodicity

    service = _make_service(published_path)
    spec = _make_spec(
        base_period_kwargs={
            "year": 2024,
            "month": 12,
            "periodicity": Periodicity.MONTHLY,
        },
        target_period_kwargs={
            "year": 2025,
            "month": 12,
            "periodicity": Periodicity.MONTHLY,
        },
        components=[_component(id="mat_a", series_id=SERIES_A, weight=1.0)],
    )
    result, _ = service.calculate(spec)

    assert result.temporal_composite_factor == pytest.approx(1.1)
    assert result.temporal_percent_change == pytest.approx(10.0)


def test_composite_factor_two_components(published_path: Path) -> None:
    """Two-component (50/50): factor = 0.5*(110/100) + 0.5*(220/200) = 1.1."""
    from bls_mcp.models.enums import Periodicity

    service = _make_service(published_path)
    spec = _make_spec(
        base_period_kwargs={
            "year": 2024,
            "month": 12,
            "periodicity": Periodicity.MONTHLY,
        },
        target_period_kwargs={
            "year": 2025,
            "month": 12,
            "periodicity": Periodicity.MONTHLY,
        },
        components=[
            _component(id="mat_a", series_id=SERIES_A, weight=0.5),
            _component(id="mat_b", series_id=SERIES_B, weight=0.5),
        ],
    )
    result, _ = service.calculate(spec)

    assert result.temporal_composite_factor == pytest.approx(1.1)


def test_ledger_captures_series_ids(published_path: Path) -> None:
    """Ledger provenance must list the series IDs that were used."""
    from bls_mcp.models.enums import Periodicity

    service = _make_service(published_path)
    spec = _make_spec(
        base_period_kwargs={
            "year": 2024,
            "month": 12,
            "periodicity": Periodicity.MONTHLY,
        },
        target_period_kwargs={
            "year": 2025,
            "month": 12,
            "periodicity": Periodicity.MONTHLY,
        },
        components=[_component(id="mat_a", series_id=SERIES_A, weight=1.0)],
    )
    _, ledger = service.calculate(spec)

    assert any(p.series_id == SERIES_A for p in ledger.provenance)
    assert ledger.specification == "test-spec"


def test_ledger_observations_used_contains_values(published_path: Path) -> None:
    """observations_used must record each raw value that entered the calculation."""
    from bls_mcp.models.enums import Periodicity

    service = _make_service(published_path)
    spec = _make_spec(
        base_period_kwargs={
            "year": 2024,
            "month": 12,
            "periodicity": Periodicity.MONTHLY,
        },
        target_period_kwargs={
            "year": 2025,
            "month": 12,
            "periodicity": Periodicity.MONTHLY,
        },
        components=[_component(id="mat_a", series_id=SERIES_A, weight=1.0)],
    )
    _, ledger = service.calculate(spec)

    # Both base and target must appear
    combined = " ".join(ledger.observations_used)
    assert "100.0" in combined
    assert "110.0" in combined


def test_component_calculations_have_periods_populated(published_path: Path) -> None:
    """ComponentCalculation.base_period and target_period must be set (not None)."""
    from bls_mcp.models.enums import Periodicity

    service = _make_service(published_path)
    spec = _make_spec(
        base_period_kwargs={
            "year": 2024,
            "month": 12,
            "periodicity": Periodicity.MONTHLY,
        },
        target_period_kwargs={
            "year": 2025,
            "month": 12,
            "periodicity": Periodicity.MONTHLY,
        },
        components=[_component(id="mat_a", series_id=SERIES_A, weight=1.0)],
    )
    result, _ = service.calculate(spec)

    comp = result.components[0]
    assert comp.base_period is not None
    assert comp.target_period is not None
    assert comp.base_period.year == 2024
    assert comp.target_period.year == 2025


# ---------------------------------------------------------------------------
# Tests: FIXED_UNINDEXED components bypass observation lookup
# ---------------------------------------------------------------------------


def test_fixed_component_does_not_require_series(published_path: Path) -> None:
    """FIXED_UNINDEXED components must calculate with factor=1 and no DB lookup."""
    from bls_mcp.models.basket import EscalationComponent
    from bls_mcp.models.enums import ComponentType, Periodicity

    service = _make_service(published_path)
    fixed = EscalationComponent(
        id="overhead",
        name="Overhead",
        component_type=ComponentType.FIXED_UNINDEXED,
        weight=1.0,
    )
    spec = _make_spec(
        base_period_kwargs={
            "year": 2024,
            "month": 12,
            "periodicity": Periodicity.MONTHLY,
        },
        target_period_kwargs={
            "year": 2025,
            "month": 12,
            "periodicity": Periodicity.MONTHLY,
        },
        components=[fixed],
    )
    result, _ = service.calculate(spec)

    assert result.temporal_composite_factor == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Tests: error conditions
# ---------------------------------------------------------------------------


def test_raises_on_missing_base_observation(published_path: Path) -> None:
    """ObservationNotFoundError when base period has no data."""
    from bls_mcp.exceptions import ObservationNotFoundError
    from bls_mcp.models.enums import Periodicity

    service = _make_service(published_path)
    # Base in 2022 — no data for that year in fixture
    spec = _make_spec(
        base_period_kwargs={
            "year": 2022,
            "month": 12,
            "periodicity": Periodicity.MONTHLY,
        },
        target_period_kwargs={
            "year": 2025,
            "month": 12,
            "periodicity": Periodicity.MONTHLY,
        },
        components=[_component(id="mat_a", series_id=SERIES_A, weight=1.0)],
    )
    with pytest.raises(ObservationNotFoundError, match="base"):
        service.calculate(spec)


def test_raises_on_missing_target_observation(published_path: Path) -> None:
    """ObservationNotFoundError when target period has no data."""
    from bls_mcp.exceptions import ObservationNotFoundError
    from bls_mcp.models.enums import Periodicity

    service = _make_service(published_path)
    # Target in 2030 — no data
    spec = _make_spec(
        base_period_kwargs={
            "year": 2024,
            "month": 12,
            "periodicity": Periodicity.MONTHLY,
        },
        target_period_kwargs={
            "year": 2030,
            "month": 12,
            "periodicity": Periodicity.MONTHLY,
        },
        components=[_component(id="mat_a", series_id=SERIES_A, weight=1.0)],
    )
    with pytest.raises(ObservationNotFoundError, match="target"):
        service.calculate(spec)


def test_raises_on_zero_base_value(tmp_path: Path) -> None:
    """CalculationError must be raised when the base observation is zero."""
    from bls_mcp.exceptions import CalculationError
    from bls_mcp.models.enums import Periodicity

    path = tmp_path / "zero.duckdb"
    with build_connection(path, threads=1) as conn:
        initialize_schema(conn)
        write_snapshot_info(conn, SnapshotInfo("zero_test", datetime.now(UTC), ("pc",)))
        write_source_file(
            conn, SourceFileReceipt(1, "pc", "fixture.txt", "c" * 64, 1, "current")
        )
        conn.execute("INSERT INTO pc_industry VALUES ('100---', 'Sector A')")
        conn.execute("INSERT INTO pc_product VALUES ('100---', '100---', 'Product A')")
        conn.execute(
            "INSERT INTO series_catalog VALUES (?, 'pc', 'Series A', NULL, FALSE, "
            "2020, 'M01', 2026, 'M12', 'index', '202412', TRUE)",
            [SERIES_A],
        )
        conn.execute(
            "INSERT INTO pc_series VALUES (?, '100---', '100---', 'U', '202412')",
            [SERIES_A],
        )
        conn.executemany(
            "INSERT INTO observations VALUES (?, ?, ?, ?, ?, ?)",
            [
                (SERIES_A, 2024, "M12", 0.0, None, 1),  # zero base!
                (SERIES_A, 2025, "M12", 110.0, None, 1),
            ],
        )
        conn.execute(
            "UPDATE snapshot_info "
            "SET lifecycle_state='PUBLISHED', validation_status='PASSED'"
        )

    service = _make_service(path)
    spec = _make_spec(
        base_period_kwargs={
            "year": 2024,
            "month": 12,
            "periodicity": Periodicity.MONTHLY,
        },
        target_period_kwargs={
            "year": 2025,
            "month": 12,
            "periodicity": Periodicity.MONTHLY,
        },
        components=[_component(id="mat_a", series_id=SERIES_A, weight=1.0)],
    )
    with pytest.raises(CalculationError, match="zero"):
        service.calculate(spec)


def test_raises_on_spec_validation_error(published_path: Path) -> None:
    """CalculationError when spec has ERROR-level findings (bad weights)."""
    from bls_mcp.exceptions import CalculationError
    from bls_mcp.models.enums import Periodicity

    service = _make_service(published_path)
    # Weights sum to 0.5, not 1.0 — validation ERROR
    spec = _make_spec(
        base_period_kwargs={
            "year": 2024,
            "month": 12,
            "periodicity": Periodicity.MONTHLY,
        },
        target_period_kwargs={
            "year": 2025,
            "month": 12,
            "periodicity": Periodicity.MONTHLY,
        },
        components=[_component(id="mat_a", series_id=SERIES_A, weight=0.5)],
    )
    with pytest.raises(CalculationError, match="validation"):
        service.calculate(spec)


# ---------------------------------------------------------------------------
# Tests: period-to-BLS code mapping
# ---------------------------------------------------------------------------


def test_period_to_bls_monthly() -> None:
    from bls_mcp.models.enums import Periodicity
    from bls_mcp.models.periods import EconomicPeriod
    from bls_mcp.services.source_calculation import _period_to_bls

    p = EconomicPeriod(year=2025, month=6, periodicity=Periodicity.MONTHLY)
    year, code = _period_to_bls(p)
    assert year == 2025
    assert code == "M06"


def test_period_to_bls_annual_average() -> None:
    from bls_mcp.models.enums import Periodicity
    from bls_mcp.models.periods import EconomicPeriod
    from bls_mcp.services.source_calculation import _period_to_bls

    p = EconomicPeriod(year=2024, periodicity=Periodicity.ANNUAL_AVERAGE)
    year, code = _period_to_bls(p)
    assert year == 2024
    assert code == "M13"


def test_period_to_bls_quarterly() -> None:
    from bls_mcp.models.enums import Periodicity
    from bls_mcp.models.periods import EconomicPeriod
    from bls_mcp.services.source_calculation import _period_to_bls

    p = EconomicPeriod(year=2024, quarter=3, periodicity=Periodicity.QUARTERLY)
    year, code = _period_to_bls(p)
    assert year == 2024
    assert code == "Q03"


# ---------------------------------------------------------------------------
# Tests: series resolution
# ---------------------------------------------------------------------------


def test_shared_series_is_queried_once_per_period(published_path: Path) -> None:
    """Two components on one series must not duplicate the snapshot lookup."""
    from bls_mcp.models.enums import Periodicity

    service = _make_service(published_path)
    requested: list[list[str]] = []
    get_observations = service.store.get_observations

    def recording(series_ids, **kwargs):  # type: ignore[no-untyped-def]
        requested.append(list(series_ids))
        return get_observations(series_ids, **kwargs)

    service.store.get_observations = recording  # type: ignore[method-assign]
    spec = _make_spec(
        base_period_kwargs={
            "year": 2024,
            "month": 12,
            "periodicity": Periodicity.MONTHLY,
        },
        target_period_kwargs={
            "year": 2025,
            "month": 12,
            "periodicity": Periodicity.MONTHLY,
        },
        components=[
            _component(id="mat_a1", series_id=SERIES_A, weight=0.5),
            _component(id="mat_a2", series_id=SERIES_A, weight=0.5),
        ],
    )
    result, _ = service.calculate(spec)

    assert requested == [[SERIES_A], [SERIES_A]]  # one base + one target lookup
    assert result.temporal_composite_factor == pytest.approx(1.1)


def test_raises_on_series_absent_from_snapshot(published_path: Path) -> None:
    """SeriesNotFoundError names a series the snapshot catalog does not hold."""
    from bls_mcp.exceptions import SeriesNotFoundError
    from bls_mcp.models.enums import Periodicity

    service = _make_service(published_path)
    spec = _make_spec(
        base_period_kwargs={
            "year": 2024,
            "month": 12,
            "periodicity": Periodicity.MONTHLY,
        },
        target_period_kwargs={
            "year": 2025,
            "month": 12,
            "periodicity": Periodicity.MONTHLY,
        },
        components=[_component(id="mat_x", series_id="PCU999999999999", weight=1.0)],
    )
    with pytest.raises(SeriesNotFoundError, match="PCU999999999999"):
        service.calculate(spec)


def test_period_to_bls_annual_uses_annual_average_row() -> None:
    from bls_mcp.models.enums import Periodicity
    from bls_mcp.models.periods import EconomicPeriod
    from bls_mcp.services.source_calculation import _period_to_bls

    p = EconomicPeriod(year=2024, periodicity=Periodicity.ANNUAL)
    assert _period_to_bls(p) == (2024, "M13")


# ---------------------------------------------------------------------------
# Tests: quarterly -> annual alignment (ECI-like series)
# ---------------------------------------------------------------------------


def _annual_spec(components: list) -> object:
    from bls_mcp.models.enums import Periodicity

    return _make_spec(
        base_period_kwargs={"year": 2024, "periodicity": Periodicity.ANNUAL},
        target_period_kwargs={"year": 2025, "periodicity": Periodicity.ANNUAL},
        components=components,
    )


def test_quarterly_series_is_resolved_from_q04_anchor(
    published_path_quarterly: Path,
) -> None:
    """A quarterly series under an annual spec resolves from its Q04 rows.

    Factor = 168.0 / 156.0.
    """
    from bls_mcp.models.enums import Periodicity
    from bls_mcp.models.periods import EconomicPeriod

    service = _make_service(published_path_quarterly)
    spec = _annual_spec([_component(id="labor", series_id=QUARTERLY_C, weight=1.0)])
    result, ledger = service.calculate(spec)

    assert result.temporal_composite_factor == pytest.approx(168.0 / 156.0)

    labor = result.components[0]
    assert labor.base_period == EconomicPeriod(
        year=2024, quarter=4, periodicity=Periodicity.QUARTERLY
    )
    assert labor.target_period == EconomicPeriod(
        year=2025, quarter=4, periodicity=Periodicity.QUARTERLY
    )


def test_quarterly_alignment_is_disclosed(
    published_path_quarterly: Path,
) -> None:
    """The alignment must be stated in the ledger, provenance and values."""
    service = _make_service(published_path_quarterly)
    spec = _annual_spec([_component(id="labor", series_id=QUARTERLY_C, weight=1.0)])
    _, ledger = service.calculate(spec)

    assert any(QUARTERLY_C in w and "Q04" in w for w in ledger.warnings)
    assert any(
        p.series_id == QUARTERLY_C and "Q04" in (p.notes or "")
        for p in ledger.provenance
    )
    assert f"{QUARTERLY_C}@2024-Q04 = 156.0" in ledger.observations_used
    assert f"{QUARTERLY_C}@2025-Q04 = 168.0" in ledger.observations_used


def test_mixed_annual_and_quarterly_composite(
    published_path_quarterly: Path,
) -> None:
    """Materials (annual) and labor (quarterly, Q04-aligned) in one spec.

    factor = 0.5 * (111/101) + 0.5 * (168/156).
    """
    service = _make_service(published_path_quarterly)
    spec = _annual_spec(
        [
            _component(id="mat", series_id=SERIES_A, weight=0.5),
            _component(id="labor", series_id=QUARTERLY_C, weight=0.5),
        ]
    )
    result, _ = service.calculate(spec)

    expected = 0.5 * (111.0 / 101.0) + 0.5 * (168.0 / 156.0)
    assert result.temporal_composite_factor == pytest.approx(expected)


def test_annual_series_is_not_realigned(published_path_quarterly: Path) -> None:
    """Series publishing M13 keeps using M13; no alignment warning."""
    from bls_mcp.models.enums import Periodicity

    service = _make_service(published_path_quarterly)
    spec = _annual_spec([_component(id="mat", series_id=SERIES_A, weight=1.0)])
    result, ledger = service.calculate(spec)

    assert result.temporal_composite_factor == pytest.approx(111.0 / 101.0)
    mat = result.components[0]
    assert mat.base_period is not None and mat.base_period.year == 2024
    # The spec period passes through unchanged; only the resolved BLS row is M13.
    assert mat.base_period.periodicity == Periodicity.ANNUAL
    assert not ledger.warnings or all(SERIES_A not in w for w in ledger.warnings)


def test_missing_anchor_quarter_raises(published_path_quarterly: Path) -> None:
    """A quarterly series without Q04 cannot be aligned; raise, don't guess."""
    from bls_mcp.exceptions import ObservationNotFoundError

    service = _make_service(published_path_quarterly)
    spec = _annual_spec([_component(id="labor", series_id=QUARTERLY_D, weight=1.0)])
    with pytest.raises(ObservationNotFoundError, match=QUARTERLY_D):
        service.calculate(spec)


# ---------------------------------------------------------------------------
# Tests: monthly spec periods against a quarterly-only series
# ---------------------------------------------------------------------------


def _monthly_spec(
    components: list, base: tuple[int, int], target: tuple[int, int]
) -> object:
    from bls_mcp.models.enums import Periodicity

    return _make_spec(
        base_period_kwargs={
            "year": base[0],
            "month": base[1],
            "periodicity": Periodicity.MONTHLY,
        },
        target_period_kwargs={
            "year": target[0],
            "month": target[1],
            "periodicity": Periodicity.MONTHLY,
        },
        components=components,
    )


def test_monthly_period_matches_the_containing_quarter(
    published_path_quarterly: Path,
) -> None:
    """A monthly spec period against a quarterly-only series repeats that
    quarter's value: 2024-M05 -> Q02 (152.0), 2025-M08 -> Q03 (166.0)."""
    from bls_mcp.models.enums import Periodicity
    from bls_mcp.models.periods import EconomicPeriod

    service = _make_service(published_path_quarterly)
    spec = _monthly_spec(
        [_component(id="labor", series_id=QUARTERLY_C, weight=1.0)],
        base=(2024, 5),
        target=(2025, 8),
    )
    result, _ = service.calculate(spec)

    assert result.temporal_composite_factor == pytest.approx(166.0 / 152.0)
    labor = result.components[0]
    assert labor.base_period == EconomicPeriod(
        year=2024, quarter=2, periodicity=Periodicity.QUARTERLY
    )
    assert labor.target_period == EconomicPeriod(
        year=2025, quarter=3, periodicity=Periodicity.QUARTERLY
    )


def test_monthly_alignment_is_disclosed(published_path_quarterly: Path) -> None:
    """The monthly fallback is stated in the ledger and provenance labels."""
    service = _make_service(published_path_quarterly)
    spec = _monthly_spec(
        [_component(id="labor", series_id=QUARTERLY_C, weight=1.0)],
        base=(2024, 5),
        target=(2025, 8),
    )
    _, ledger = service.calculate(spec)

    assert any(
        QUARTERLY_C in w and "Q02" in w and "monthly-to-quarterly" in w
        for w in ledger.warnings
    )
    assert any(
        p.series_id == QUARTERLY_C
        and "monthly_to_quarterly_alignment=2024:Q02,2025:Q03" in (p.notes or "")
        for p in ledger.provenance
    )
    assert f"{QUARTERLY_C}@2024-Q02 = 152.0" in ledger.observations_used
    assert f"{QUARTERLY_C}@2025-Q03 = 166.0" in ledger.observations_used


def test_monthly_period_does_not_fall_back_across_programs(
    published_path_quarterly: Path,
) -> None:
    """A series with no monthly and no quarterly rows in the year still fails."""
    from bls_mcp.exceptions import ObservationNotFoundError

    service = _make_service(published_path_quarterly)
    spec = _monthly_spec(
        [_component(id="mat", series_id=SERIES_A, weight=1.0)],
        base=(2024, 5),
        target=(2025, 8),
    )
    with pytest.raises(ObservationNotFoundError, match=SERIES_A):
        service.calculate(spec)


# ---------------------------------------------------------------------------
# Tests: one-sided alignment (only one endpoint falls back)
# ---------------------------------------------------------------------------


def test_partially_aligned_spec_does_not_crash(
    published_path_quarterly: Path,
) -> None:
    """Annual base (aligned to Q04) plus an exact quarterly target."""
    from bls_mcp.models.enums import Periodicity

    service = _make_service(published_path_quarterly)
    spec = _make_spec(
        base_period_kwargs={"year": 2024, "periodicity": Periodicity.ANNUAL},
        target_period_kwargs={
            "year": 2025,
            "quarter": 3,
            "periodicity": Periodicity.QUARTERLY,
        },
        components=[_component(id="labor", series_id=QUARTERLY_C, weight=1.0)],
    )
    result, ledger = service.calculate(spec)

    # Base aligned to 2024-Q04 (156.0); target matched 2025-Q03 (166.0) exactly.
    assert result.temporal_composite_factor == pytest.approx(166.0 / 156.0)
    note = next(p for p in ledger.provenance if p.series_id == QUARTERLY_C).notes or ""
    # Provenance records only the period that actually used alignment.
    assert "quarterly_to_annual_alignment=2024:Q04" in note
    assert "2025:Q04" not in note
