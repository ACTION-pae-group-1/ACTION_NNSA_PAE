"""The index visualization through the full server: MCP tool, HTTP API, UI.

A spec saved through the MCP tools is charted from a published fixture
snapshot. The HTTP response is also checked by the web UI's own
``validatePayload`` (run in Node when available), so the backend is held to
the exact contract the page enforces before drawing anything.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from fastmcp import Client
from fastmcp.exceptions import ToolError
from starlette.testclient import TestClient

from bls_mcp.config import Settings
from bls_mcp.ingestion.lifecycle import build_candidate, validate_candidate
from bls_mcp.ingestion.publish import activate_snapshot, publish_candidate
from bls_mcp.models.visualization import IndexVisualizationData
from bls_mcp.routes import UI_CONTENT_SECURITY_POLICY
from bls_mcp.server import create_server
from bls_mcp.tests.harness_duckdb import FIXTURE_PC_SERIES, make_fixture_manifest

WEB_PAGE = Path(__file__).parents[2] / "src" / "bls_mcp" / "web" / "index.html"
ANNUAL = [
    (FIXTURE_PC_SERIES, 2022, "M13", 92.0, ""),
    (FIXTURE_PC_SERIES, 2023, "M13", 96.0, ""),
    (FIXTURE_PC_SERIES, 2024, "M13", 100.0, ""),
    (FIXTURE_PC_SERIES, 2025, "M13", 104.0, ""),
]


def spec_args(spec_id: str = "machinery-index", **extra: Any) -> dict[str, Any]:
    return {
        "id": spec_id,
        "name": "Machinery escalation",
        "base_period": {"year": 2024, "periodicity": "ANNUAL"},
        "target_period": {"year": 2025, "periodicity": "ANNUAL"},
        "components": [
            {
                "id": "machinery",
                "name": "Machinery",
                "component_type": "EQUIPMENT",
                "weight": 1.0,
                "series_id": FIXTURE_PC_SERIES,
            }
        ],
        **extra,
    }


def make_server(tmp_path: Path):
    manifest = make_fixture_manifest(tmp_path / "raw", extra_observations=ANNUAL)
    candidate = tmp_path / "viz_snap.duckdb"
    build_candidate(candidate, "viz_snap", pc_manifest=manifest)
    assert validate_candidate(candidate, pc_manifest=manifest).passed
    registry = tmp_path / "registry"
    publish_candidate(candidate, registry)
    activate_snapshot(registry, "viz_snap")
    return create_server(
        Settings(
            BLS_SNAPSHOT_REGISTRY_DIR=str(registry),
            BLS_SPECS_DB_PATH=str(tmp_path / "specs.duckdb"),
            BLS_API_KEY=None,
        )
    )


async def save(client: Client, args: dict[str, Any]) -> dict[str, Any]:
    created = await client.call_tool("create_index_spec", args)
    saved = await client.call_tool(
        "save_index_spec", {"spec": created.structured_content}
    )
    return saved.structured_content


@pytest_asyncio.fixture
async def client(tmp_path: Path) -> Iterator[Client]:
    async with Client(make_server(tmp_path)) as connected:
        yield connected


@pytest.fixture
def http(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(make_server(tmp_path).http_app()) as test_client:
        yield test_client


@pytest.mark.asyncio
async def test_tool_returns_contract_payload(client: Client) -> None:
    await save(client, spec_args())
    response = await client.call_tool(
        "get_index_visualization",
        {"spec_id": "machinery-index", "start_year": 2022, "source_year": 2022},
    )
    data = IndexVisualizationData.model_validate(response.structured_content)

    assert data.index_identity.snapshot_id == "viz_snap"
    assert data.index_identity.spec_revision == 1
    assert [p.period for p in data.composite_points] == ["2022", "2023", "2024", "2025"]
    assert Decimal(data.composite_points[0].composite_factor) == Decimal("0.92")
    assert data.base_year_adjustment.source_year == 2022
    assert data.warnings == ()


@pytest.mark.asyncio
async def test_saving_again_increments_the_revision(client: Client) -> None:
    assert (await save(client, spec_args()))["revision"] == 1
    assert (await save(client, spec_args(name="Renamed")))["revision"] == 2
    response = await client.call_tool(
        "get_index_visualization", {"spec_id": "machinery-index"}
    )
    assert response.structured_content["index_identity"]["spec_revision"] == 2


@pytest.mark.asyncio
async def test_tool_errors_are_actionable(client: Client) -> None:
    with pytest.raises(ToolError, match="not found"):
        await client.call_tool("get_index_visualization", {"spec_id": "missing"})
    await save(client, spec_args())
    with pytest.raises(ToolError, match="must include the base year 2024"):
        await client.call_tool(
            "get_index_visualization",
            {"spec_id": "machinery-index", "start_year": 2025},
        )


def test_ui_is_served_with_a_locked_down_policy(http: TestClient) -> None:
    response = http.get("/ui")
    assert response.status_code == 200
    assert response.headers["content-security-policy"] == UI_CONTENT_SECURITY_POLICY
    assert response.headers["x-content-type-options"] == "nosniff"
    # Everything is inline; the page references no other origin.
    assert not re.search(r"""(?:src|href)=["']https?://""", response.text)
    assert "api/index-visualization" in response.text


def _seed(http: TestClient, tmp_spec: dict[str, Any]) -> None:
    async def run() -> None:
        async with Client(http.app.state.fastmcp_server) as client:  # type: ignore[attr-defined]
            await save(client, tmp_spec)

    http.portal.call(run)  # type: ignore[union-attr]


def test_api_lists_specs_and_returns_a_packet(http: TestClient) -> None:
    _seed(http, spec_args())
    listed = http.get("/api/specs").json()["specs"]
    assert [(s["id"], s["revision"], s["base_year"]) for s in listed] == [
        ("machinery-index", 1, 2024)
    ]
    assert listed[0]["components"][0]["series_id"] == FIXTURE_PC_SERIES

    packet = http.get(
        "/api/index-visualization", params={"spec_id": "machinery-index"}
    ).json()
    assert packet["result"]["schema_version"] == "1.0"
    assert sorted(packet["presentation"]["adjustments_by_year"]) == ["2024", "2025"]
    assert packet["presentation"]["latest_change_percent"] == "4.000000000000"


def test_api_errors(http: TestClient) -> None:
    _seed(http, spec_args())
    missing = http.get("/api/index-visualization", params={"spec_id": "nope"})
    assert (missing.status_code, missing.json()["error"]["code"]) == (
        404,
        "spec_not_found",
    )
    bad = http.post("/api/index-visualization", json={"spec_id": 1, "extra": True})
    assert bad.status_code == 400
    weights = http.post(
        "/api/index-visualization",
        json={"spec_id": "machinery-index", "weights": {"machinery": "0.5"}},
    )
    assert weights.status_code == 422
    assert "Total component weights" in weights.json()["error"]["message"]


def test_api_rejects_an_oversized_body_while_reading_it(http: TestClient) -> None:
    # A body larger than MAX_BODY_BYTES fails at 413 as soon as the stream
    # crosses the limit, before the whole upload is buffered and parsed.
    oversized = b'["' + b"x" * (65 * 1024) + b'"]'
    response = http.post(
        "/api/index-visualization",
        content=oversized,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_too_large"


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js not installed")
def test_web_ui_validator_accepts_the_server_packet(
    http: TestClient, tmp_path: Path
) -> None:
    _seed(http, spec_args())
    packet = http.post(
        "/api/index-visualization",
        json={"spec_id": "machinery-index", "start_year": 2022},
    ).json()
    page = WEB_PAGE.read_text(encoding="utf-8")
    start = page.index("function validatePayload(f){")
    end = page.index("function eligibleAdjustmentYears(f){")
    script = tmp_path / "validate.js"
    script.write_text(
        page[start:end]
        + "const p=JSON.parse(require('fs').readFileSync(0,'utf8'));"
        + "const f={...p.result,demo_extensions:p.presentation};"
        + "process.stdout.write(JSON.stringify(validatePayload(f)));",
        encoding="utf-8",
    )
    completed = subprocess.run(
        ["node", str(script)],
        input=json.dumps(packet),
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    assert json.loads(completed.stdout) == []
