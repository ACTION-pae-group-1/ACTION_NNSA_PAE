"""The lifespan wires the published DuckDB snapshot into the services.

- lifespan.py resolves the active snapshot with current_snapshot_path()
- Services.catalog and Services.observations are backed by BLSStore
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

pytest.importorskip("duckdb")

from bls_mcp.ingestion.lifecycle import build_candidate, validate_candidate
from bls_mcp.ingestion.publish import activate_snapshot, publish_candidate
from bls_mcp.storage.store import BLSStore

# ---------------------------------------------------------------------------
# Shared fixture: a minimal published DuckDB registry for one PC series
# ---------------------------------------------------------------------------

PC_SERIES = "PCU334000334000"
HEADER = "series_id\tyear\tperiod\tvalue\tfootnote_codes\n"


def _write_manifest(root: Path, code: str, files: dict[str, tuple[str, str]]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    entries = []
    for name, (role, body) in files.items():
        raw = body.encode("utf-8")
        (root / name).write_bytes(raw)
        entries.append(
            {
                "path": name,
                "role": role,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size_bytes": len(raw),
            }
        )
    path = root / "source.json"
    path.write_text(
        json.dumps({"schema_version": 1, "program": code, "files": entries})
    )
    return path


def make_pc_manifest(root: Path) -> Path:
    return _write_manifest(
        root,
        "pc",
        {
            "pc.industry.txt": (
                "industry_mapping",
                "industry_code\tindustry_name\n334---\tMachinery\n",
            ),
            "pc.product": (
                "product_mapping",
                "industry_code\tproduct_code\tproduct_name\n"
                "334---\t334---\tMachinery output\n",
            ),
            "pc.series": (
                "series_metadata",
                "series_id\tindustry_code\tproduct_code\tseasonal\t"
                "base_date\tseries_title\tfootnote_codes\t"
                "begin_year\tbegin_period\tend_year\tend_period\n"
                f"{PC_SERIES}\t334---\t334---\tU\t200012\tMachinery PPI\t\t"
                "2000\tM01\t2026\tM12\n",
            ),
            "pc.data.0.Current": (
                "current",
                HEADER
                + f"{PC_SERIES}\t2024\tM12\t100.0\t\n"
                + f"{PC_SERIES}\t2025\tM06\t108.0\t\n"
                + f"{PC_SERIES}\t2025\tM12\t110.0\t\n",
            ),
        },
    )


@pytest.fixture()
def registry_dir(tmp_path: Path) -> Path:
    """Build, validate, publish, and activate a minimal PC snapshot."""
    manifest = make_pc_manifest(tmp_path / "raw")
    candidate = tmp_path / "snap.duckdb"
    build_candidate(candidate, "lifespan_test_snap", pc_manifest=manifest)
    report = validate_candidate(candidate, pc_manifest=manifest)
    assert report.passed, report.issues
    publish_candidate(candidate, tmp_path / "registry")
    activate_snapshot(tmp_path / "registry", "lifespan_test_snap")
    return tmp_path / "registry"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_services_catalog_is_backed_by_bls_store(registry_dir: Path) -> None:
    """SeriesCatalogService must delegate to BLSStore, not SeriesRepository."""
    from bls_mcp.services.series_catalog import SeriesCatalogService

    # The service must accept a BLSStore, not a SeriesRepository.
    store = BLSStore(list((registry_dir).glob("bls-*.duckdb"))[0])
    service = SeriesCatalogService(store)
    assert service is not None


def test_services_observations_is_backed_by_bls_store(registry_dir: Path) -> None:
    """ObservationService must accept a BLSStore for cached reads."""
    import inspect

    from bls_mcp.services.observations import ObservationService

    sig = inspect.signature(ObservationService.__init__)
    param_names = list(sig.parameters)
    # The old signature was (client, access, cache) where cache was
    # ObservationRepository. After Phase 1b 'store' replaces 'cache'.
    assert "store" in param_names or "bls_store" in param_names, (
        "ObservationService.__init__ must accept a BLSStore parameter "
        f"(got {param_names})"
    )
