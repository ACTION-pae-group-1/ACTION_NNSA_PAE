"""Saved index specs persist in their own DuckDB file."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import duckdb
import pytest

from bls_mcp.models.basket import EscalationComponent
from bls_mcp.models.enums import ComponentType, Periodicity
from bls_mcp.models.periods import EconomicPeriod
from bls_mcp.models.specifications import EscalationIndexSpec
from bls_mcp.repositories.specifications import SpecificationRepository


def _spec(spec_id: str, name: str = "Basket") -> EscalationIndexSpec:
    return EscalationIndexSpec(
        id=spec_id,
        name=name,
        base_period=EconomicPeriod(year=2024, periodicity=Periodicity.ANNUAL),
        target_period=EconomicPeriod(year=2025, periodicity=Periodicity.ANNUAL),
        components=[
            EscalationComponent(
                id="material",
                name="Material",
                component_type=ComponentType.MATERIAL,
                weight=1.0,
                series_id="PCU100000000000",
            )
        ],
    )


@pytest.fixture()
def repo(tmp_path: Path) -> SpecificationRepository:
    return SpecificationRepository(str(tmp_path / "nested" / "specs.duckdb"))


def test_get_missing_returns_none(repo: SpecificationRepository) -> None:
    assert repo.get("absent") is None
    assert repo.list() == []


def test_save_then_get_round_trips(repo: SpecificationRepository) -> None:
    saved = repo.save(_spec("a"))
    fetched = repo.get("a")
    assert fetched is not None
    assert fetched.model_dump() == saved.model_dump()


def test_save_same_id_replaces(repo: SpecificationRepository) -> None:
    repo.save(_spec("a", name="First"))
    repo.save(_spec("a", name="Second"))
    assert [spec.name for spec in repo.list()] == ["Second"]


def test_concurrent_saves_get_distinct_revisions(
    repo: SpecificationRepository,
) -> None:
    """Two saves may not both observe the previous revision and write n+1."""
    with ThreadPoolExecutor(max_workers=8) as pool:
        saved = list(
            pool.map(lambda i: repo.save(_spec("a", name=f"Save {i}")), range(8))
        )
    assert sorted(spec.revision for spec in saved) == list(range(1, 9))
    fetched = repo.get("a")
    assert fetched is not None
    assert fetched.revision == 8


def test_list_orders_most_recently_updated_first(
    repo: SpecificationRepository,
) -> None:
    repo.save(_spec("a"))
    repo.save(_spec("b"))
    repo.save(_spec("a", name="Touched"))
    assert [spec.id for spec in repo.list()] == ["a", "b"]


def test_delete_removes_only_that_spec(repo: SpecificationRepository) -> None:
    repo.save(_spec("a"))
    repo.save(_spec("b"))
    repo.delete("a")
    assert repo.get("a") is None
    assert repo.get("b") is not None


def test_specs_persist_in_a_duckdb_file(repo: SpecificationRepository) -> None:
    repo.save(_spec("a"))
    reopened = SpecificationRepository(repo.database_path)
    assert reopened.get("a") is not None
    with duckdb.connect(repo.database_path, read_only=True) as conn:
        count = conn.execute("SELECT count(*) FROM saved_index_specs").fetchone()
    assert count == (1,)
