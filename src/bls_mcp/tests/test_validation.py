from bls_mcp.models.basket import EscalationComponent
from bls_mcp.models.enums import ComponentType, Periodicity
from bls_mcp.models.periods import EconomicPeriod
from bls_mcp.models.specifications import EscalationIndexSpec
from bls_mcp.services.validation import ValidationService

service = ValidationService()


def _spec() -> EscalationIndexSpec:
    return EscalationIndexSpec(
        id="spec-1",
        name="Valid basket",
        base_period=EconomicPeriod(
            year=2024,
            month=1,
            periodicity=Periodicity.MONTHLY,
        ),
        target_period=EconomicPeriod(
            year=2025,
            month=1,
            periodicity=Periodicity.MONTHLY,
        ),
        components=[
            EscalationComponent(
                id="labour",
                name="Labor",
                component_type=ComponentType.LABOR,
                weight=0.6,
                series_id="TEST_ECI_001",
            ),
            EscalationComponent(
                id="materials",
                name="Materials",
                component_type=ComponentType.MATERIAL,
                weight=0.4,
                series_id="TEST_PPI_001",
            ),
        ],
    )


def test_valid_basket() -> None:
    result = service.validate_spec(_spec())
    assert result.valid is True


def test_weights_not_equal_to_one() -> None:
    spec = _spec()
    spec.components[0].weight = 0.5
    spec.components[1].weight = 0.3
    result = service.validate_spec(spec)
    assert any(f.code == "WEIGHTS_SUM_MISMATCH" for f in result.findings)


def test_negative_weight() -> None:
    spec = _spec()
    spec.components[1].weight = -0.1
    result = service.validate_spec(spec)
    assert any(f.code == "NEGATIVE_WEIGHT" for f in result.findings)


def test_missing_series_on_indexed_component() -> None:
    spec = _spec()
    spec.components[0].series_id = None
    result = service.validate_spec(spec)
    assert any(f.code == "MISSING_SERIES_ID" for f in result.findings)


def test_series_on_fixed_component() -> None:
    spec = _spec()
    component = EscalationComponent(
        id="fixed",
        name="Fixed",
        component_type=ComponentType.FIXED_UNINDEXED,
        weight=0.2,
        series_id="TEST_PPI_999",
    )
    spec.components.append(component)
    result = service.validate_spec(spec)
    assert any(f.code == "FIXED_COMPONENT_HAS_SERIES" for f in result.findings)


def test_material_component_locality_warning() -> None:
    spec = _spec()
    spec.components[1].locality_adjustment_enabled = True
    result = service.validate_spec(spec)
    assert any(f.code == "LOCALITY_ON_MATERIAL_OR_EQUIPMENT" for f in result.findings)


def test_snapshot_availability_flags_missing_base_without_substitution():
    from types import SimpleNamespace

    from bls_mcp.models.basket import EscalationComponent
    from bls_mcp.models.enums import ComponentType, Periodicity
    from bls_mcp.models.periods import EconomicPeriod
    from bls_mcp.models.specifications import EscalationIndexSpec

    class Store:
        def get_observations(self, series_ids, *, start_year, end_year, max_rows):
            assert series_ids == ["PCU327420327420P"]
            periods = ["M13"] if start_year == 2026 else []
            return SimpleNamespace(
                observations=[SimpleNamespace(period=code) for code in periods]
            )

    spec = EscalationIndexSpec(
        id="availability-test",
        name="Gypsum availability",
        base_period=EconomicPeriod(year=2014, periodicity=Periodicity.ANNUAL_AVERAGE),
        target_period=EconomicPeriod(year=2026, periodicity=Periodicity.ANNUAL_AVERAGE),
        components=[
            EscalationComponent(
                id="gypsum",
                name="Gypsum",
                component_type=ComponentType.MATERIAL,
                weight=1.0,
                series_id="PCU327420327420P",
            )
        ],
    )
    result = ValidationService(store=Store()).validate_spec(spec)
    assert not result.valid
    missing = [f for f in result.findings if f.code == "SERIES_PERIOD_UNAVAILABLE"]
    assert len(missing) == 1
    assert missing[0].series_id == "PCU327420327420P"
    assert "2014/M13" in missing[0].message
