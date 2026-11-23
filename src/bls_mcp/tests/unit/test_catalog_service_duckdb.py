"""TDD – Phase 1b: SeriesCatalogService backed by BLSStore.

Fails until SeriesCatalogService.search() and .get() delegate to
BLSStore instead of SeriesRepository, and SeriesSearchRequest.programs
accepts plain two-letter strings instead of BLSProgram enum values.
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
# Minimal published DuckDB fixture (no manifest pipeline needed here)
# ---------------------------------------------------------------------------

PC_A = "PCU334000334000"
PC_B = "PCU500000500000"


@pytest.fixture()
def published_path(tmp_path: Path) -> Path:
    path = tmp_path / "catalog.duckdb"
    with build_connection(path, threads=1) as conn:
        initialize_schema(conn)
        write_snapshot_info(
            conn,
            SnapshotInfo(
                "catalog_svc_test",
                datetime.now(UTC),
                ("pc",),
            ),
        )
        write_source_file(
            conn,
            SourceFileReceipt(1, "pc", "fixture.txt", "a" * 64, 1, "current"),
        )
        conn.execute("INSERT INTO pc_industry VALUES ('334---', 'Machinery')")
        conn.execute(
            "INSERT INTO pc_product VALUES ('334---', '334---', 'Machinery output')"
        )
        conn.executemany(
            "INSERT INTO series_catalog VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                # series_id, program_code, title, description, seasonal_adjustment,
                # first_year, first_period, last_year, last_period,
                # units, original_reference_base, active
                (
                    PC_A,
                    "pc",
                    "Machinery PPI",
                    None,
                    False,
                    2020,
                    "M01",
                    2026,
                    "M12",
                    "index",
                    "200012",
                    True,
                ),
                (
                    PC_B,
                    "pc",
                    "Steel PPI",
                    "Flat-rolled steel",
                    True,
                    2015,
                    "M01",
                    2026,
                    "M12",
                    "index",
                    "200012",
                    True,
                ),
            ],
        )
        conn.executemany(
            "INSERT INTO pc_series VALUES (?, '334---', '334---', ?, '200012')",
            [(PC_A, "U"), (PC_B, "S")],
        )
        conn.executemany(
            "INSERT INTO observations VALUES (?, ?, ?, ?, ?, ?)",
            [
                (PC_A, 2024, "M12", 100.0, None, 1),
                (PC_A, 2025, "M06", 108.0, None, 1),
                (PC_B, 2024, "M12", 200.0, None, 1),
                (PC_B, 2025, "M06", 215.0, None, 1),
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


# ---------------------------------------------------------------------------
# Tests: SeriesCatalogService
# ---------------------------------------------------------------------------


def test_catalog_service_accepts_bls_store(published_path: Path) -> None:
    """SeriesCatalogService constructor must accept BLSStore, not SeriesRepository."""
    from bls_mcp.services.series_catalog import SeriesCatalogService

    store = BLSStore(published_path)
    service = SeriesCatalogService(store)
    assert service is not None


def test_catalog_search_returns_results_from_duckdb(published_path: Path) -> None:
    """search() must return results from BLSStore."""
    from bls_mcp.models.series import SeriesSearchRequest
    from bls_mcp.services.series_catalog import SeriesCatalogService

    service = SeriesCatalogService(BLSStore(published_path))
    results = service.search(SeriesSearchRequest(query="Machinery"))
    assert len(results) >= 1
    ids = {r.series.series_id for r in results}
    assert PC_A in ids


def test_catalog_search_empty_query_returns_all(published_path: Path) -> None:
    from bls_mcp.models.series import SeriesSearchRequest
    from bls_mcp.services.series_catalog import SeriesCatalogService

    service = SeriesCatalogService(BLSStore(published_path))
    results = service.search(SeriesSearchRequest())
    assert len(results) == 2


def test_catalog_search_by_program_string(published_path: Path) -> None:
    """programs filter must accept plain two-letter strings, not BLSProgram enum."""
    from bls_mcp.models.series import SeriesSearchRequest
    from bls_mcp.services.series_catalog import SeriesCatalogService

    service = SeriesCatalogService(BLSStore(published_path))
    # "pc" must be accepted without raising — BLSProgram enum only had PPI/ECI/OEWS.
    results = service.search(SeriesSearchRequest(query="", programs=["pc"]))
    assert len(results) == 2


def test_catalog_search_rejects_unknown_program_and_names_valid_codes() -> None:
    """Unknown program codes fail validation, and the error lists the valid ones.

    Program codes became a Literal of the supported programs, so an unknown code
    is a validation error rather than an empty result. Naming the valid codes
    gives an agent what it needs to retry (EVALUATION_JOURNEY lesson 3).
    """
    import pydantic

    from bls_mcp.models.series import SeriesSearchRequest

    with pytest.raises(
        pydantic.ValidationError, match="'pc', 'pd', 'wp', 'ci', 'cu' or 'oe'"
    ):
        SeriesSearchRequest(programs=["xx"])


def test_catalog_get_known_series(published_path: Path) -> None:
    """get() must return metadata for a known series_id."""
    from bls_mcp.services.series_catalog import SeriesCatalogService

    service = SeriesCatalogService(BLSStore(published_path))
    result = service.get(PC_B)
    assert result is not None
    assert result.series_id == PC_B
    assert result.title == "Steel PPI"


def test_catalog_get_unknown_series_returns_none(published_path: Path) -> None:
    from bls_mcp.services.series_catalog import SeriesCatalogService

    service = SeriesCatalogService(BLSStore(published_path))
    assert service.get("DOES_NOT_EXIST") is None


def test_catalog_search_no_longer_accepts_series_repository(
    published_path: Path,
) -> None:
    """After Phase 1b, passing SeriesRepository to SeriesCatalogService must fail."""
    import inspect

    from bls_mcp.services.series_catalog import SeriesCatalogService

    sig = inspect.signature(SeriesCatalogService.__init__)
    param = sig.parameters.get("store") or sig.parameters.get("repository")
    assert param is not None
    if param.annotation is not inspect.Parameter.empty:
        annotation = str(param.annotation)
        assert "SeriesRepository" not in annotation, (
            "SeriesCatalogService constructor must not accept SeriesRepository; "
            f"found annotation: {annotation}"
        )


# ---------------------------------------------------------------------------
# Tests: SeriesSearchRequest model (BLSProgram replaced by str)
# ---------------------------------------------------------------------------


def test_series_search_request_accepts_supported_program_codes() -> None:
    """programs accepts each supported lowercase code, not BLSProgram members."""
    from bls_mcp.models.series import SeriesSearchRequest

    codes = ["pc", "ci", "wp", "pd", "cu", "oe"]
    req = SeriesSearchRequest(programs=codes)
    assert req.programs == codes


def test_series_search_request_rejects_old_enum_values() -> None:
    """PPI/ECI/OEWS must no longer be accepted as program codes.

    These were the old BLSProgram enum values that did not match any stored data.
    After Phase 1b the field uses plain two-letter strings validated against a
    two-letter pattern.
    """
    import pydantic

    from bls_mcp.models.series import SeriesSearchRequest

    for bad in ("PPI", "ECI", "OEWS"):
        with pytest.raises((pydantic.ValidationError, ValueError)):
            SeriesSearchRequest(programs=[bad])


def test_series_search_request_rejects_invalid_strings() -> None:
    import pydantic

    from bls_mcp.models.series import SeriesSearchRequest

    for bad in ("", "toolong", "P1", "123"):
        with pytest.raises((pydantic.ValidationError, ValueError)):
            SeriesSearchRequest(programs=[bad])


def test_search_ranking_and_reasons(published_path: Path) -> None:
    """Exact IDs and titles outrank weaker matches with useful explanations."""
    from bls_mcp.models.series import SeriesSearchRequest
    from bls_mcp.services.series_catalog import SeriesCatalogService

    service = SeriesCatalogService(BLSStore(published_path))
    exact_id = service.search(SeriesSearchRequest(query=PC_B))
    assert exact_id[0].series.series_id == PC_B
    assert exact_id[0].match_score == 1.0
    assert exact_id[0].match_reason == "exact series ID"

    exact_title = service.search(SeriesSearchRequest(query="Steel PPI"))
    assert exact_title[0].match_score == 0.95
    assert exact_title[0].match_reason == "exact normalized title"

    metadata = service.search(SeriesSearchRequest(query="flat rolled steel"))
    assert metadata[0].series.series_id == PC_B
    assert metadata[0].match_score == 0.5
    assert metadata[0].match_reason == "all catalog metadata tokens"


def test_search_punctuation_and_token_order(published_path: Path) -> None:
    from bls_mcp.models.series import SeriesSearchRequest
    from bls_mcp.services.series_catalog import SeriesCatalogService

    service = SeriesCatalogService(BLSStore(published_path))
    for query in ("flat-rolled steel", "steel flat rolled", "FLAT ROLLED STEEL"):
        results = service.search(SeriesSearchRequest(query=query))
        assert results[0].series.series_id == PC_B

    assert len(service.search(SeriesSearchRequest())) == 2


def test_search_includes_eligible_broader_parent(
    published_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Strong product hits can expose their actual catalog parent."""
    from types import SimpleNamespace

    from bls_mcp.models.series import SeriesSearchRequest
    from bls_mcp.services.series_catalog import SeriesCatalogService

    store = BLSStore(published_path)
    original = store.series_hierarchy

    def hierarchy(series_id: str):
        if series_id == PC_B:
            return SimpleNamespace(parents=(SimpleNamespace(series_id=PC_A),))
        return original(series_id)

    monkeypatch.setattr(store, "series_hierarchy", hierarchy)
    service = SeriesCatalogService(store)
    matches = service.search(SeriesSearchRequest(query="Steel PPI", limit=2))
    assert [m.series.series_id for m in matches] == [PC_B, PC_A]
    assert matches[1].match_score == 0.45
    assert "broader parent" in (matches[1].match_reason or "")

    # An exact identifier must not be expanded into a family search.
    exact = service.search(SeriesSearchRequest(query=PC_B, limit=2))
    assert [m.series.series_id for m in exact] == [PC_B]

    # Existing program filters must still apply to expanded candidates.
    other = service.search(SeriesSearchRequest(query="Steel PPI", programs=["ci"]))
    assert other == []
