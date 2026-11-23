"""Full-server tests against a published DuckDB snapshot.

They cover:

  - Server starts from the active snapshot in the registry.
  - search_series / describe_series / get_cached_series_data return data
    sourced from the published DuckDB snapshot.
  - bls://series/{series_id} resource reads from the DuckDB catalog.
  - get_series_data (live BLS path) is unaffected.
  - Spec persistence (save/get) works.
  - Settings carries snapshot_registry_dir.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from fastmcp import Client
from fastmcp.exceptions import ToolError

from bls_mcp.tests.harness import CannedTransport
from bls_mcp.tests.harness_duckdb import (
    FIXTURE_PC_SERIES,
    FIXTURE_PC_TITLE,
    duckdb_server_env,
)

pytest.importorskip("duckdb")

# ---------------------------------------------------------------------------
# Shared fixture components (no BLSProgram enum values)
# ---------------------------------------------------------------------------

BASE = {"year": 2024, "periodicity": "ANNUAL"}
TARGET = {"year": 2025, "periodicity": "ANNUAL"}
COMPONENTS = [
    {
        "id": "machinery",
        "name": "Machinery",
        "component_type": "MATERIAL",
        "weight": 0.6,
        "series_id": FIXTURE_PC_SERIES,
    },
    {
        "id": "labor",
        "name": "Labor",
        "component_type": "LABOR",
        "weight": 0.4,
        "series_id": "PLACEHOLDER_ECI",
    },
]


def spec_args(spec_id: str = "phase1-basket") -> dict[str, Any]:
    return {
        "id": spec_id,
        "name": "Phase 1 basket",
        "base_period": BASE,
        "target_period": TARGET,
        "components": COMPONENTS,
    }


# ---------------------------------------------------------------------------
# Shared client fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def client(tmp_path: Path) -> Client:
    async with duckdb_server_env(tmp_path) as env:
        yield env.client


# ---------------------------------------------------------------------------
# 1. Server starts cleanly from the published snapshot
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_server_starts_from_published_snapshot(tmp_path: Path) -> None:
    """The server starts on the fixture snapshot and exposes its tools."""
    async with duckdb_server_env(tmp_path) as env:
        tools = await env.client.list_tools()
        assert len(tools) > 0


@pytest.mark.asyncio
async def test_settings_has_snapshot_registry_dir(tmp_path: Path) -> None:
    """Settings must expose snapshot_registry_dir after Phase 1a."""
    from bls_mcp.config import Settings

    s = Settings(BLS_SNAPSHOT_REGISTRY_DIR=str(tmp_path / "registry"))
    assert hasattr(s, "snapshot_registry_dir")
    assert s.snapshot_registry_dir == str(tmp_path / "registry")


# ---------------------------------------------------------------------------
# 2. search_series reads from DuckDB
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_series_returns_duckdb_data(client: Client) -> None:
    """search_series must return series from the published DuckDB snapshot."""
    result = await client.call_tool(
        "search_series",
        {"request": {"query": "Machinery"}},
    )
    hits = result.structured_content["result"]
    assert len(hits) >= 1
    ids = {h["series"]["series_id"] for h in hits}
    assert FIXTURE_PC_SERIES in ids


@pytest.mark.asyncio
async def test_search_series_accepts_two_letter_program_code(client: Client) -> None:
    """programs filter must accept lowercase two-letter codes like 'pc', not 'PPI'."""
    result = await client.call_tool(
        "search_series",
        {"request": {"query": "", "programs": ["pc"]}},
    )
    hits = result.structured_content["result"]
    assert len(hits) >= 1


@pytest.mark.asyncio
async def test_search_series_rejects_old_enum_program_values(
    client: Client,
) -> None:
    """'PPI' / 'ECI' / 'OEWS' must no longer be valid program filter values."""
    with pytest.raises(ToolError):
        await client.call_tool(
            "search_series",
            {"request": {"query": "", "programs": ["PPI"]}},
        )


@pytest.mark.asyncio
async def test_search_series_empty_query_returns_results(client: Client) -> None:
    result = await client.call_tool(
        "search_series",
        {"request": {}},
    )
    assert len(result.structured_content["result"]) >= 1


@pytest.mark.asyncio
async def test_search_series_rejects_unknown_program_and_names_valid_codes(
    client: Client,
) -> None:
    """An unknown program is a tool error that tells the agent the valid codes."""
    with pytest.raises(ToolError, match="'pc', 'pd', 'wp', 'ci', 'cu' or 'oe'"):
        await client.call_tool(
            "search_series",
            {"request": {"programs": ["xx"]}},
        )


# ---------------------------------------------------------------------------
# 3. describe_series reads from DuckDB catalog
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_describe_series_returns_duckdb_metadata(client: Client) -> None:
    result = await client.call_tool(
        "describe_series",
        {"series_id": FIXTURE_PC_SERIES},
    )
    series = result.structured_content["result"]
    assert series is not None
    assert series["series_id"] == FIXTURE_PC_SERIES
    assert series["title"] == FIXTURE_PC_TITLE


@pytest.mark.asyncio
async def test_describe_series_unknown_returns_null(client: Client) -> None:
    result = await client.call_tool(
        "describe_series",
        {"series_id": "DOES_NOT_EXIST"},
    )
    assert result.structured_content["result"] is None


# ---------------------------------------------------------------------------
# 4. get_cached_series_data reads from DuckDB observations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_cached_series_data_returns_duckdb_observations(
    client: Client,
) -> None:
    """get_cached_series_data must return observations from the DuckDB snapshot."""
    result = await client.call_tool(
        "get_cached_series_data",
        {"series_id": FIXTURE_PC_SERIES},
    )
    observations = result.structured_content["result"]
    assert len(observations) == 3  # three rows seeded in harness
    values = {float(o["value"]) for o in observations}
    assert 100.0 in values
    assert 110.0 in values


@pytest.mark.asyncio
async def test_get_cached_series_data_year_filter(client: Client) -> None:
    result = await client.call_tool(
        "get_cached_series_data",
        {"series_id": FIXTURE_PC_SERIES, "start_year": 2025, "end_year": 2025},
    )
    observations = result.structured_content["result"]
    assert all(o["period"]["year"] == 2025 for o in observations)
    assert len(observations) == 2


@pytest.mark.asyncio
async def test_get_cached_series_data_limit(client: Client) -> None:
    result = await client.call_tool(
        "get_cached_series_data",
        {"series_id": FIXTURE_PC_SERIES, "limit": 1},
    )
    assert len(result.structured_content["result"]) == 1


@pytest.mark.asyncio
async def test_get_cached_series_data_unknown_series_returns_empty(
    client: Client,
) -> None:
    result = await client.call_tool(
        "get_cached_series_data",
        {"series_id": "UNKNOWN_SERIES"},
    )
    assert result.structured_content["result"] == []


@pytest.mark.asyncio
async def test_get_cached_series_data_invalid_period_raises(
    client: Client,
) -> None:
    with pytest.raises(ToolError):
        await client.call_tool(
            "get_cached_series_data",
            {"series_id": FIXTURE_PC_SERIES, "start_year": 2026, "end_year": 2025},
        )


# ---------------------------------------------------------------------------
# 5. bls://series/{series_id} resource reads from DuckDB catalog
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_series_resource_returns_duckdb_catalog_entry(
    client: Client,
) -> None:
    resources = await client.read_resource(f"bls://series/{FIXTURE_PC_SERIES}")
    assert resources[0].mimeType == "application/json"
    data = json.loads(resources[0].text)
    assert data["series_id"] == FIXTURE_PC_SERIES
    assert data["title"] == FIXTURE_PC_TITLE


@pytest.mark.asyncio
async def test_series_resource_not_found_raises(client: Client) -> None:
    with pytest.raises(Exception, match="was not found"):
        await client.read_resource("bls://series/DOES_NOT_EXIST")


# ---------------------------------------------------------------------------
# 6. Live BLS path (get_series_data) is unaffected by DuckDB migration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_series_data_still_calls_bls_api(tmp_path: Path) -> None:
    """The live fetch path must still use BLSClient, not BLSStore."""
    transport = CannedTransport()
    async with duckdb_server_env(tmp_path, transport=transport) as env:
        result = await env.client.call_tool(
            "get_series_data",
            {
                "series_ids": [FIXTURE_PC_SERIES],
                "start_year": 2024,
                "end_year": 2025,
            },
        )
        assert len(transport.requests) == 1, (
            "get_series_data must dispatch exactly one HTTP request to the BLS API"
        )
        observations = result.structured_content["result"]
        assert len(observations) == 2


@pytest.mark.asyncio
async def test_get_series_data_requires_api_key(tmp_path: Path) -> None:
    async with duckdb_server_env(tmp_path, key=None) as env:
        with pytest.raises(ToolError):
            await env.client.call_tool(
                "get_series_data",
                {
                    "series_ids": [FIXTURE_PC_SERIES],
                    "start_year": 2024,
                    "end_year": 2025,
                },
            )


# ---------------------------------------------------------------------------
# 7. Spec persistence still works (backend-agnostic)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_spec_create_save_get_roundtrip(client: Client) -> None:
    """create → save → get must round-trip regardless of spec backend."""
    created = await client.call_tool("create_index_spec", spec_args("roundtrip-basket"))
    spec = created.structured_content

    absent = await client.call_tool("get_index_spec", {"spec_id": spec["id"]})
    assert absent.structured_content == {"result": None}

    await client.call_tool("save_index_spec", {"spec": spec})
    fetched = await client.call_tool("get_index_spec", {"spec_id": spec["id"]})
    assert fetched.structured_content["result"]["id"] == spec["id"]
    assert fetched.structured_content["result"]["name"] == spec["name"]


@pytest.mark.asyncio
async def test_spec_save_is_idempotent(client: Client) -> None:
    created = await client.call_tool(
        "create_index_spec", spec_args("idempotent-basket")
    )
    spec = created.structured_content
    await client.call_tool("save_index_spec", {"spec": spec})
    revised = dict(spec, name="Revised name")
    await client.call_tool("save_index_spec", {"spec": revised})
    fetched = await client.call_tool("get_index_spec", {"spec_id": spec["id"]})
    assert fetched.structured_content["result"]["name"] == "Revised name"


# ---------------------------------------------------------------------------
# 8. HTTP transport lifecycle is properly managed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_http_transport_is_closed_on_server_exit(tmp_path: Path) -> None:
    """Lifespan must close the HTTP transport even when the body raises."""
    transport = CannedTransport()
    with pytest.raises(RuntimeError, match="deliberate"):
        async with duckdb_server_env(tmp_path, transport=transport):
            raise RuntimeError("deliberate")
    assert transport.closed


# ---------------------------------------------------------------------------
# Series hierarchy: the lesson for choosing an index
# ---------------------------------------------------------------------------

LESSON = (
    "seeing the narrower sub-items nested beneath a parent code is the "
    "primary way to verify what an index includes"
)


@pytest.mark.asyncio
async def test_series_hierarchy_tool_and_lesson_reach_the_agent(
    client: Client,
) -> None:
    """The tool is callable and the lesson is in what every host reads."""
    tools = {tool.name: tool for tool in await client.list_tools()}
    assert LESSON in " ".join(tools["get_series_hierarchy"].description.split()).lower()
    for name in ("search_series", "describe_series"):
        assert "get_series_hierarchy" in tools[name].description
    assert LESSON in " ".join(client.initialize_result.instructions.split()).lower()

    found = await client.call_tool(
        "get_series_hierarchy", {"series_id": FIXTURE_PC_SERIES}
    )
    result = found.structured_content["result"]
    assert result["series_id"] == FIXTURE_PC_SERIES
    assert result["snapshot_id"] == "fixture_snap"
    assert result["note"]
    absent = await client.call_tool("get_series_hierarchy", {"series_id": "PCUNOPE"})
    assert absent.structured_content == {"result": None}


@pytest.mark.asyncio
async def test_escalation_workflow_guide_and_prompt_are_registered(
    client: Client,
) -> None:
    uris = {str(r.uri) for r in await client.list_resources()}
    assert "guide://escalation-workflow" in uris
    guide = (await client.read_resource("guide://escalation-workflow"))[0]
    assert guide.mimeType == "text/markdown"
    assert "get_series_hierarchy" in guide.text
    assert "`status` is not `complete`" in " ".join(guide.text.split())

    prompts = {p.name for p in await client.list_prompts()}
    assert "design_escalation_basket" in prompts
    got = await client.get_prompt(
        "design_escalation_basket",
        {"project_description": "Two-storey school", "base_period": "2023"},
    )
    text = got.messages[0].content.text
    assert "Two-storey school" in text
    assert "Base period: 2023" in text
    assert "get_series_hierarchy" in text
    assert "guide://escalation-workflow" in client.initialize_result.instructions
