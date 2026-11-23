"""DuckDB-backed server harness for Phase 1 completion tests.

Builds a minimal published DuckDB snapshot with known fixture series,
creates a registry pointing to it, and starts the server with
BLS_SNAPSHOT_REGISTRY_DIR.  Saved specs go to a separate DuckDB file under
tmp_path (BLS_SPECS_DB_PATH) so tests never share state or touch the CWD.

The CannedTransport helper is re-exported unchanged so callers do not need
to import from both harness modules.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from fastmcp import Client

from bls_mcp.config import Settings
from bls_mcp.ingestion.lifecycle import build_candidate, validate_candidate
from bls_mcp.ingestion.publish import activate_snapshot, publish_candidate
from bls_mcp.server import create_server
from bls_mcp.tests.harness import CannedTransport  # re-export

# ---------------------------------------------------------------------------
# Fixture series seeded into every test snapshot
# ---------------------------------------------------------------------------

#: PC series present in every test snapshot built by this harness.
FIXTURE_PC_SERIES = "PCU334000334000"
#: Title used in catalog assertions.
FIXTURE_PC_TITLE = "Fixture Machinery PPI"

_HEADER = "series_id\tyear\tperiod\tvalue\tfootnote_codes\n"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _write_manifest(
    root: Path,
    code: str,
    files: dict[str, tuple[str, str]],
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    entries = []
    for name, (role, body) in files.items():
        raw = body.encode("utf-8")
        (root / name).write_bytes(raw)
        entries.append(
            {
                "path": name,
                "role": role,
                "sha256": _sha(raw),
                "size_bytes": len(raw),
            }
        )
    manifest = root / "source.json"
    manifest.write_text(
        json.dumps({"schema_version": 1, "program": code, "files": entries})
    )
    return manifest


def make_fixture_manifest(
    root: Path,
    *,
    extra_observations: list[tuple[str, int, str, float, str]] | None = None,
) -> Path:
    """Write a minimal PC manifest with FIXTURE_PC_SERIES and optional extras.

    extra_observations rows: (series_id, year, period, value, footnote_codes)
    They are appended to pc.data.0.Current and must reference series_ids that
    are already in pc.series (this helper only seeds FIXTURE_PC_SERIES).
    """
    obs_rows = (
        f"{FIXTURE_PC_SERIES}\t2024\tM12\t100.0\t\n"
        f"{FIXTURE_PC_SERIES}\t2025\tM06\t108.0\t\n"
        f"{FIXTURE_PC_SERIES}\t2025\tM12\t110.0\t\n"
    )
    if extra_observations:
        for sid, year, period, value, fn in extra_observations:
            obs_rows += f"{sid}\t{year}\t{period}\t{value}\t{fn}\n"

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
                f"{FIXTURE_PC_SERIES}\t334---\t334---\tU\t200012\t"
                f"{FIXTURE_PC_TITLE}\t\t2000\tM01\t2026\tM12\n",
            ),
            "pc.data.0.Current": ("current", _HEADER + obs_rows),
        },
    )


def build_registry(tmp_path: Path, snapshot_id: str = "fixture_snap") -> Path:
    """Build → validate → publish → activate one minimal PC snapshot.

    Returns the registry directory.  Callers pass it as BLS_SNAPSHOT_REGISTRY_DIR.
    """
    manifest = make_fixture_manifest(tmp_path / "raw")
    candidate = tmp_path / f"{snapshot_id}.duckdb"
    build_candidate(candidate, snapshot_id, pc_manifest=manifest)
    report = validate_candidate(candidate, pc_manifest=manifest)
    assert report.passed, f"Fixture snapshot validation failed: {report.issues}"
    registry = tmp_path / "registry"
    publish_candidate(candidate, registry)
    activate_snapshot(registry, snapshot_id)
    return registry


# ---------------------------------------------------------------------------
# Server environment context manager
# ---------------------------------------------------------------------------


@dataclass
class DuckDBServerEnv:
    """A connected in-memory client, its HTTP transport, and the registry path."""

    client: Client
    transport: CannedTransport
    registry_dir: Path


@asynccontextmanager
async def duckdb_server_env(
    tmp_path: Path,
    *,
    key: str | None = "fixture-secret",
    transport: CannedTransport | None = None,
    snapshot_id: str = "fixture_snap",
) -> AsyncIterator[DuckDBServerEnv]:
    """Run the server backed by a published DuckDB snapshot.

    Passes BLS_SNAPSHOT_REGISTRY_DIR to Settings.  Asserts the registry
    exists before startup (it must be pre-built) and that the HTTP transport
    is closed on every exit path.
    """
    registry = build_registry(tmp_path, snapshot_id)
    transport = transport if transport is not None else CannedTransport()
    server = create_server(
        Settings(
            BLS_SNAPSHOT_REGISTRY_DIR=str(registry),
            BLS_SPECS_DB_PATH=str(tmp_path / "specs.duckdb"),
            BLS_API_KEY=key,
        ),
        http_transport=transport,
    )
    assert registry.is_dir(), "Registry directory must exist before server start"
    try:
        async with Client(server) as client:
            yield DuckDBServerEnv(client, transport, registry)
    finally:
        assert transport.closed, "Lifespan must close the injected HTTP transport"
