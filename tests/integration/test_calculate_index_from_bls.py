"""Phase 2: calculate_index_from_bls through the full server.

A spec saved to the DuckDB specs store is calculated from observations in the
published DuckDB snapshot; the caller supplies no index values.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from fastmcp import Client
from fastmcp.exceptions import ToolError

from bls_mcp.tests.harness_duckdb import FIXTURE_PC_SERIES, duckdb_server_env

# Fixture snapshot: FIXTURE_PC_SERIES is 100.0 at 2024-M12 and 110.0 at 2025-M12.
BASE = {"year": 2024, "month": 12, "periodicity": "MONTHLY"}
TARGET = {"year": 2025, "month": 12, "periodicity": "MONTHLY"}


def spec_args(spec_id: str, series_id: str = FIXTURE_PC_SERIES) -> dict[str, Any]:
    return {
        "id": spec_id,
        "name": "Source-backed basket",
        "base_period": BASE,
        "target_period": TARGET,
        "components": [
            {
                "id": "machinery",
                "name": "Machinery",
                "component_type": "MATERIAL",
                "weight": 0.6,
                "series_id": series_id,
            },
            {
                "id": "overhead",
                "name": "Overhead",
                "component_type": "FIXED_UNINDEXED",
                "weight": 0.4,
            },
        ],
    }


@pytest_asyncio.fixture
async def client(tmp_path: Path) -> Client:
    async with duckdb_server_env(tmp_path) as env:
        yield env.client


async def _save(client: Client, args: dict[str, Any]) -> None:
    created = await client.call_tool("create_index_spec", args)
    await client.call_tool("save_index_spec", {"spec": created.structured_content})


@pytest.mark.asyncio
async def test_saved_spec_is_calculated_from_snapshot(client: Client) -> None:
    await _save(client, spec_args("source-backed"))

    response = await client.call_tool(
        "calculate_index_from_bls", {"spec_id": "source-backed"}
    )
    result = response.structured_content["result"]
    ledger = response.structured_content["ledger"]

    # 0.6 * (110 / 100) + 0.4 * 1 = 1.06
    assert result["temporal_composite_factor"] == pytest.approx(1.06)
    assert result["temporal_percent_change"] == pytest.approx(6.0)
    machinery, overhead = result["components"]
    assert (machinery["base_value"], machinery["target_value"]) == (100.0, 110.0)
    assert (overhead["base_value"], overhead["target_value"]) == (None, None)

    assert ledger["specification"] == "source-backed"
    assert [p["series_id"] for p in ledger["provenance"]] == [FIXTURE_PC_SERIES]
    assert "snapshot_id=fixture_snap" in ledger["provenance"][0]["notes"]
    assert len(ledger["observations_used"]) == 2


@pytest.mark.asyncio
async def test_unknown_spec_id_is_a_tool_error(client: Client) -> None:
    with pytest.raises(ToolError, match="not found"):
        await client.call_tool("calculate_index_from_bls", {"spec_id": "missing"})


@pytest.mark.asyncio
async def test_series_absent_from_snapshot_is_a_tool_error(client: Client) -> None:
    await _save(client, spec_args("unknown-series", series_id="PCU999999999999"))
    with pytest.raises(ToolError, match="PCU999999999999"):
        await client.call_tool(
            "calculate_index_from_bls", {"spec_id": "unknown-series"}
        )


@pytest.mark.asyncio
async def test_specs_are_isolated_per_server(tmp_path: Path) -> None:
    """Each harness server owns its specs file; nothing leaks via the CWD."""
    async with duckdb_server_env(tmp_path / "a") as first:
        await _save(first.client, spec_args("only-in-a"))
    async with duckdb_server_env(tmp_path / "b") as second:
        fetched = await second.client.call_tool(
            "get_index_spec", {"spec_id": "only-in-a"}
        )
        assert fetched.structured_content == {"result": None}
