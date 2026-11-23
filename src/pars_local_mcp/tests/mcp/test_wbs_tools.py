"""Tests for the wbs_* MCP tools (src/pars_local_mcp/mcp/wbs_tools.py).

Every tool is invoked through a FastMCP in-memory Client, so tool names, argument
schemas and the call path are exercised together. Disk reads (manifest bytes, bundle
bytes, export parquet) are extra checks only; they never drive the pipeline.

Runs use the labeled contract fixture (built from bundled data) with n_iter=2 and
n_jobs=1 to keep them fast. The bundled synthetic mock is used only to confirm that
it passes the input contract. A non-conforming copy of the fixture exercises the
refusal path. All writes go under tmp_path.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import duckdb
import joblib
import polars as pl
import pytest
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError

from pars_local_mcp.config import Settings
from pars_local_mcp.mcp.tools import register_tools
from pars_local_mcp.wbs import artifacts as wbs_artifacts
from pars_local_mcp.wbs_port import pipeline as wbs_pipeline
from pars_local_mcp.wbs_port.contract_fixture import (
    build_contract_fixture,
    build_nonconforming_copy,
)

# The fixture writes every CAEF row (all projects) to silver_spae_data.
FIXTURE_SPAE_ROWS = 16680
STAGES = ("clean", "tune_train", "predict", "write_back")
LEVEL_COLUMNS = [f"level_{i}" for i in range(2, 9)]
PREDICTION_KEY = ["parsid", "wbs", "parent_wbs"]
FAST = {"n_iter": 2, "cv_folds": 3, "n_jobs": 1}
MANIFEST = "run_manifest.json"
MISSING = object()  # marks a schema argument that has no default
INT, STR, NULL = "integer", "string", "null"
# Contract tables in the bundled mock (local names, no source suffix).
MOCK_CONTRACT_TABLES = ("gold_corrections", "silver_spae_data")

# name -> {argument: (JSON schema types, default or MISSING)}
EXPECTED_ARGUMENTS: dict[str, dict[str, tuple[set[str], Any]]] = {
    "validate_wbs_inputs": {},
    "clean_wbs_data": {"run_id": ({STR, NULL}, None)},
    "tune_and_train_wbs": {
        "run_id": ({STR}, MISSING),
        "n_iter": ({INT}, 10),
        "cv_folds": ({INT}, 3),
        "n_jobs": ({INT}, 4),
        "search_seed": ({INT, NULL}, None),
        "split_seed": ({INT, NULL}, None),
    },
    "predict_wbs": {
        "run_id": ({STR}, MISSING),
        "model_variant": ({STR}, "untuned"),
    },
    "write_back_wbs": {"run_id": ({STR}, MISSING)},
    "run_wbs_pipeline": {
        "run_id": ({STR, NULL}, None),
        "n_iter": ({INT}, 10),
        "cv_folds": ({INT}, 3),
        "n_jobs": ({INT}, 4),
        "search_seed": ({INT, NULL}, None),
        "split_seed": ({INT, NULL}, None),
        "model_variant": ({STR}, "untuned"),
    },
    "get_wbs_run_status": {"run_id": ({STR}, MISSING)},
    "get_wbs_project_descriptions": {"limit": ({INT}, 20)},
    "get_wbs_rows": {"limit": ({INT}, 20)},
}


# ----------------------------------------------------------------- helpers
def make_settings(tmp_path: Path, source_db: Path | None = None) -> Settings:
    """Settings with every write redirected under tmp_path.

    ``_env_file=None`` keeps pydantic-settings from reading any .env file.
    Leaving ``source_db`` as None keeps the default source (the bundled mock).
    """
    overrides: dict[str, Any] = {
        "database_path": tmp_path / "wbs.duckdb",
        "model_dir": tmp_path / "models",
        "model_signing_key_path": tmp_path / "keys" / "model_signing.key",
        "wbs_runs_dir": tmp_path / "runs",
    }
    if source_db is not None:
        overrides["wbs_source_db"] = source_db
    return Settings(_env_file=None, **overrides)


def make_server(settings: Settings) -> FastMCP:
    mcp = FastMCP("wbs-tools-test", instructions="WBS tool tests")
    register_tools(mcp, settings)
    return mcp


async def call(client: Client, name: str, **arguments: Any) -> dict[str, Any]:
    """Call a tool through the MCP transport and return its structured dict."""
    result = await client.call_tool(name, arguments)
    payload = result.structured_content
    assert isinstance(payload, dict), payload
    return payload


def assert_no_error(result: dict[str, Any]) -> dict[str, Any]:
    assert "error" not in result, result.get("error")
    return result


def assert_error(result: dict[str, Any], *fragments: str) -> str:
    assert result.get("error"), f"expected an error, got {result}"
    for fragment in fragments:
        assert fragment in result["error"], result["error"]
    return result["error"]


def run_dir(settings: Settings, run_id: str) -> Path:
    return Path(settings.wbs_runs_dir) / run_id


def files_under(root: Path) -> list[str]:
    """Every file and directory below root, as sorted relative paths."""
    return sorted(str(p.relative_to(root)) for p in root.rglob("*"))


def manifest_text(settings: Settings, run_id: str) -> str:
    return (run_dir(settings, run_id) / MANIFEST).read_text(encoding="utf-8")


def manifest_stages(settings: Settings, run_id: str) -> dict[str, Any]:
    return json.loads(manifest_text(settings, run_id))["stages"]


async def clean_run(client: Client) -> str:
    return assert_no_error(await call(client, "clean_wbs_data"))["run_id"]


async def tuned_run(client: Client) -> str:
    rid = await clean_run(client)
    assert_no_error(await call(client, "tune_and_train_wbs", run_id=rid, **FAST))
    return rid


def fixture_spae_rows(fixture_db: Path) -> int:
    with duckdb.connect(str(fixture_db), read_only=True) as conn:
        row = conn.execute("SELECT count(*) FROM silver_spae_data").fetchone()
        return row[0]


def mock_sample_values(source_db: Path) -> list[str]:
    """First rows of the contract tables in the mock (extra check, read-only)."""
    values: list[str] = []
    with duckdb.connect(str(source_db), read_only=True) as conn:
        for table in MOCK_CONTRACT_TABLES:
            for parsid, level in conn.execute(
                f'SELECT parsid, wbs_level FROM "{table}" LIMIT 3'
            ).fetchall():
                values.extend([str(parsid), str(level)])
    return sorted(set(values))


def schema_types(prop: dict[str, Any]) -> set[str]:
    if "anyOf" in prop:
        return {sub["type"] for sub in prop["anyOf"]}
    return {prop["type"]}


def prediction_diff(a: pl.DataFrame, b: pl.DataFrame) -> str:
    """Mismatch summary for two sorted prediction tables."""
    if a.height != b.height:
        return f"row counts differ: {a.height} vs {b.height}"
    joined = a.join(b, on=PREDICTION_KEY, how="full", suffix="_b", coalesce=True)
    per_level = [
        f"{col}={joined.filter(pl.col(col) != pl.col(f'{col}_b')).height}"
        for col in LEVEL_COLUMNS
    ]
    any_differs = pl.any_horizontal(
        [pl.col(col) != pl.col(f"{col}_b") for col in LEVEL_COLUMNS]
    )
    return (
        f"rows with any level differing: {joined.filter(any_differs).height} "
        f"of {a.height}; per level: {', '.join(per_level)}"
    )


class _LoadSpy:
    """Stands in for joblib inside artifacts.py; counts calls, optionally delegates."""

    def __init__(self, allow: bool):
        self.allow = allow
        self.calls = 0

    def load(self, *args, **kwargs):
        self.calls += 1
        if not self.allow:
            raise AssertionError("joblib.load must not run on a tampered bundle")
        return joblib.load(*args, **kwargs)


# ---------------------------------------------------------------- fixtures
@pytest.fixture(scope="session")
def contract_fixture(tmp_path_factory) -> Path:
    path = build_contract_fixture(
        tmp_path_factory.mktemp("wbs_source") / "contract_fixture.duckdb"
    )
    assert fixture_spae_rows(path) == FIXTURE_SPAE_ROWS
    return path


# ---------------------------------------------------------------- discovery
@pytest.mark.asyncio
async def test_all_wbs_tools_are_listed_with_expected_arguments(tmp_path):
    async with Client(make_server(make_settings(tmp_path))) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}

    assert set(EXPECTED_ARGUMENTS) <= set(tools), set(EXPECTED_ARGUMENTS) - set(tools)

    for name, expected in EXPECTED_ARGUMENTS.items():
        tool = tools[name]
        assert tool.description and tool.description.strip(), name
        schema = tool.inputSchema
        assert schema.get("type") == "object", name
        assert set(schema.get("properties", {})) == set(expected), name
        required = {arg for arg, (_, default) in expected.items() if default is MISSING}
        assert set(schema.get("required", [])) == required, name
        for arg, (types, default) in expected.items():
            prop = schema["properties"][arg]
            assert schema_types(prop) == types, (name, arg, prop)
            if default is MISSING:
                assert "default" not in prop, (name, arg)
            else:
                assert prop.get("default", MISSING) == default, (name, arg, prop)


# -------------------------------------------------------------- source reads
@pytest.mark.asyncio
async def test_read_tools_return_capped_rows_from_the_source(tmp_path):
    async with Client(make_server(make_settings(tmp_path))) as client:
        projects = assert_no_error(
            await call(client, "get_wbs_project_descriptions", limit=5)
        )
        wbs = assert_no_error(await call(client, "get_wbs_rows", limit=5))

    assert projects["table"] == "silver_project_descriptions"
    assert projects["returned"] == 5 and len(projects["rows"]) == 5
    assert projects["total_rows"] > 5
    assert set(projects["rows"][0]) == set(projects["columns"])

    assert wbs["table"] == "silver_spae_data"
    assert wbs["returned"] == 5 and len(wbs["rows"]) == 5
    assert set(wbs["rows"][0]) == set(wbs["columns"])
    assert {"wbs", "wbs_level", "wbs_title", "parsid"} <= set(wbs["columns"])


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_limit", [0, 501])
async def test_read_tools_reject_limits_outside_1_to_500(tmp_path, bad_limit):
    async with Client(make_server(make_settings(tmp_path))) as client:
        for name in ("get_wbs_project_descriptions", "get_wbs_rows"):
            result = await call(client, name, limit=bad_limit)
            assert_error(result, "between 1 and 500")


# --------------------------------------------------------- input validation
@pytest.mark.asyncio
async def test_malformed_run_id_is_rejected_by_every_run_tool(
    tmp_path, contract_fixture
):
    settings = make_settings(tmp_path, contract_fixture)

    bad_run_ids = [
        "../x",
        "abc",
        "R0123456789AB",
        "r0123456789",
        "r0123456789abc",
    ]

    async with Client(make_server(settings)) as client:
        for bad_run_id in bad_run_ids:
            calls = [
                ("clean_wbs_data", {"run_id": bad_run_id}),
                ("run_wbs_pipeline", {"run_id": bad_run_id, **FAST}),
                ("tune_and_train_wbs", {"run_id": bad_run_id, **FAST}),
                ("predict_wbs", {"run_id": bad_run_id}),
                ("write_back_wbs", {"run_id": bad_run_id}),
                ("get_wbs_run_status", {"run_id": bad_run_id}),
            ]

            for name, arguments in calls:
                result = await call(client, name, **arguments)
                assert_error(result, "run_id must look like")

    assert not (tmp_path / "x").exists(), "path traversal created a directory"
    assert not settings.wbs_runs_dir.exists(), "a bad run_id created a run directory"


@pytest.mark.asyncio
async def test_unknown_run_id_is_reported_as_not_found(tmp_path, contract_fixture):
    settings = make_settings(tmp_path, contract_fixture)
    rid = "r" + "0" * 11 + "1"
    async with Client(make_server(settings)) as client:
        for name, arguments in [
            ("get_wbs_run_status", {"run_id": rid}),
            ("write_back_wbs", {"run_id": rid}),
            ("predict_wbs", {"run_id": rid}),
        ]:
            assert_error(await call(client, name, **arguments), "Run not found")
    assert not run_dir(settings, rid).exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("variant", ["both", "TUNED", ""])
async def test_predict_rejects_unknown_model_variant(
    tmp_path, contract_fixture, variant
):
    settings = make_settings(tmp_path, contract_fixture)
    async with Client(make_server(settings)) as client:
        rid = await clean_run(client)
        before = manifest_text(settings, rid)
        result = await call(client, "predict_wbs", run_id=rid, model_variant=variant)
        assert_error(result, "model_variant must be one of")
        assert manifest_text(settings, rid) == before


@pytest.mark.asyncio
@pytest.mark.parametrize(("argument", "value"), [("n_iter", 0), ("cv_folds", 1)])
async def test_tune_rejects_out_of_range_arguments_and_server_keeps_working(
    tmp_path, contract_fixture, argument, value
):
    settings = make_settings(tmp_path, contract_fixture)
    async with Client(make_server(settings)) as client:
        rid = await clean_run(client)
        before = manifest_text(settings, rid)
        arguments = {"run_id": rid, **FAST, argument: value}
        result = await call(client, "tune_and_train_wbs", **arguments)
        assert_error(result, "n_iter must be >= 1 and cv_folds must be >= 2")
        assert manifest_text(settings, rid) == before
        assert "tune_train" not in manifest_stages(settings, rid)

        # The server must still answer after the failed call.
        health = await call(client, "validate_wbs_inputs")
        assert health["data_origin"] == "labeled_test_fixture"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("argument", "value", "message"),
    [
        ("n_iter", 101, "n_iter must be <= 100"),
        ("cv_folds", 11, "cv_folds must be <= 10"),
        ("n_jobs", 9, "n_jobs must be between -1 and 8"),
    ],
)
async def test_tune_and_pipeline_reject_arguments_above_the_caps(
    tmp_path, argument, value, message
):
    settings = make_settings(tmp_path)
    rid = "r" + "3" * 12
    async with Client(make_server(settings)) as client:
        for name in ("tune_and_train_wbs", "run_wbs_pipeline"):
            arguments = {"run_id": rid, **FAST, argument: value}
            assert_error(await call(client, name, **arguments), message)
    assert not run_dir(settings, rid).exists(), "a capped call started a run"


@pytest.mark.asyncio
async def test_run_pipeline_reports_tune_argument_error_before_creating_a_run(
    tmp_path, contract_fixture
):
    # Changed from "keeps clean stage": the bounds are now checked before clean runs.
    settings = make_settings(tmp_path, contract_fixture)
    rid = "r" + "2" * 12
    async with Client(make_server(settings)) as client:
        result = await call(
            client, "run_wbs_pipeline", run_id=rid, n_iter=0, cv_folds=3, n_jobs=1
        )
    assert_error(result, "n_iter must be >= 1 and cv_folds must be >= 2")
    assert not run_dir(settings, rid).exists()


@pytest.mark.asyncio
async def test_run_pipeline_failure_reports_the_run_id_it_would_have_used(
    tmp_path, contract_fixture
):
    """Without a run_id one is picked and named in the error; no run is created."""
    # Changed from "names the run it created": validation now fails before any run.
    settings = make_settings(tmp_path, contract_fixture)
    async with Client(make_server(settings)) as client:
        result = await call(client, "run_wbs_pipeline", n_iter=0, cv_folds=3, n_jobs=1)
    assert_error(result, "n_iter must be >= 1 and cv_folds must be >= 2")
    rid = result["run_id"]
    assert rid
    assert not run_dir(settings, rid).exists()


@pytest.mark.asyncio
async def test_wrong_argument_type_is_rejected_by_the_transport(
    tmp_path, contract_fixture
):
    settings = make_settings(tmp_path, contract_fixture)
    async with Client(make_server(settings)) as client:
        rid = await clean_run(client)
        with pytest.raises(ToolError):
            await client.call_tool(
                "tune_and_train_wbs", {"run_id": rid, "n_iter": "ten"}
            )


# ------------------------------------------------------------ validate_inputs
@pytest.mark.asyncio
async def test_validate_inputs_on_bundled_mock_passes_contract(tmp_path):
    settings = make_settings(tmp_path)  # default wbs_source_db: bundled mock
    async with Client(make_server(settings)) as client:
        report = await call(client, "validate_wbs_inputs")

    assert report["ok"] is True, report["problems"]
    assert report["problems"] == []
    assert report["data_origin"] == "synthetic_mock"

    # Summary shape: fixed top-level keys, and per-table entries carry a row count only.
    assert set(report) == {"source_db_name", "ok", "problems", "tables", "data_origin"}
    assert all(set(entry) == {"rows"} for entry in report["tables"].values())


@pytest.mark.asyncio
async def test_validate_inputs_response_contains_no_source_record_values(tmp_path):
    source = Path(make_settings(tmp_path).wbs_source_db)
    async with Client(make_server(make_settings(tmp_path))) as client:
        report = await call(client, "validate_wbs_inputs")

    text = json.dumps(report)
    leaked = [
        value
        for value in mock_sample_values(source)
        if re.search(rf"(?<!\w){re.escape(value)}(?!\w)", text)
    ]
    assert not leaked, f"response carries source record values: {leaked}"


@pytest.mark.asyncio
async def test_validate_inputs_on_contract_fixture_passes(tmp_path, contract_fixture):
    settings = make_settings(tmp_path, contract_fixture)
    async with Client(make_server(settings)) as client:
        report = await call(client, "validate_wbs_inputs")

    assert report["ok"] is True
    assert report["problems"] == []
    assert report["data_origin"] == "labeled_test_fixture"
    assert report["tables"]["silver_spae_data"]["rows"] == FIXTURE_SPAE_ROWS
    assert set(report) == {"source_db_name", "ok", "problems", "tables", "data_origin"}


# --------------------------------------------------------- dependency errors
@pytest.mark.asyncio
async def test_tune_before_clean_is_rejected_and_creates_no_run(
    tmp_path, contract_fixture
):
    settings = make_settings(tmp_path, contract_fixture)
    rid = "r" + "1" * 12  # valid format, never cleaned
    async with Client(make_server(settings)) as client:
        result = await call(client, "tune_and_train_wbs", run_id=rid, **FAST)
    assert_error(result, "Run not found", "clean_wbs_data")
    assert not run_dir(settings, rid).exists()


@pytest.mark.asyncio
async def test_tune_on_run_whose_clean_failed_is_rejected(tmp_path, contract_fixture):
    rid = "r" + "a" * 12
    broken = build_nonconforming_copy(
        contract_fixture, tmp_path / "source" / "broken.duckdb"
    )
    failing = make_settings(tmp_path, broken)  # breaks the input contract
    async with Client(make_server(failing)) as client:
        failed = await call(client, "clean_wbs_data", run_id=rid)
    assert_error(failed, "input contract")
    assert not (run_dir(failing, rid) / MANIFEST).exists()

    settings = make_settings(tmp_path, contract_fixture)  # same runs directory
    async with Client(make_server(settings)) as client:
        tune = await call(client, "tune_and_train_wbs", run_id=rid, **FAST)
        status = await call(client, "get_wbs_run_status", run_id=rid)
    assert_error(tune, "Run not found")
    assert_error(status, "Run not found")
    assert not (run_dir(settings, rid) / MANIFEST).exists()


@pytest.mark.asyncio
async def test_predict_before_tune_is_rejected_and_manifest_is_unchanged(
    tmp_path, contract_fixture
):
    settings = make_settings(tmp_path, contract_fixture)
    async with Client(make_server(settings)) as client:
        rid = await clean_run(client)
        before = manifest_text(settings, rid)
        result = await call(client, "predict_wbs", run_id=rid)
        assert_error(result, "Stage 'tune_train' has not completed")
        assert manifest_text(settings, rid) == before
        assert not (run_dir(settings, rid) / "predictions").exists()


@pytest.mark.asyncio
async def test_write_back_before_predict_is_rejected_and_manifest_is_unchanged(
    tmp_path, contract_fixture
):
    settings = make_settings(tmp_path, contract_fixture)
    async with Client(make_server(settings)) as client:
        rid = await tuned_run(client)
        before = manifest_text(settings, rid)
        result = await call(client, "write_back_wbs", run_id=rid)
        assert_error(result, "Stage 'predict' has not completed")
        assert manifest_text(settings, rid) == before
        assert not (run_dir(settings, rid) / "predictions").exists()


@pytest.mark.asyncio
async def test_run_status_on_unknown_run_is_rejected_and_creates_no_run(
    tmp_path, contract_fixture
):
    settings = make_settings(tmp_path, contract_fixture)
    rid = "r" + "f" * 12
    async with Client(make_server(settings)) as client:
        result = await call(client, "get_wbs_run_status", run_id=rid)
    assert_error(result, "Run not found")
    assert not run_dir(settings, rid).exists()


# ------------------------------------------------------------- full chain
@pytest.mark.slow
@pytest.mark.asyncio
async def test_individual_tools_run_the_full_chain_in_order(tmp_path, contract_fixture):
    settings = make_settings(tmp_path, contract_fixture)
    async with Client(make_server(settings)) as client:
        clean = assert_no_error(await call(client, "clean_wbs_data"))
        rid = clean["run_id"]
        assert clean["stage"] == "clean"
        assert clean["data_origin"] == "labeled_test_fixture"

        tune = assert_no_error(
            await call(client, "tune_and_train_wbs", run_id=rid, **FAST)
        )
        assert tune["n_iter"] == 2 and tune["cv_folds"] == 3 and tune["n_jobs"] == 1
        assert tune["train_rows"] > 0 and tune["test_rows"] > 0

        predict = assert_no_error(await call(client, "predict_wbs", run_id=rid))
        assert predict["model_variant"] == "untuned"
        assert predict["predicted_rows"] == FIXTURE_SPAE_ROWS

        write = assert_no_error(await call(client, "write_back_wbs", run_id=rid))
        status = assert_no_error(await call(client, "get_wbs_run_status", run_id=rid))

    statuses = {stage: status["stages"][stage]["status"] for stage in STAGES}
    assert statuses == {stage: "ok" for stage in STAGES}
    assert status["data_origin"] == "labeled_test_fixture"

    assert write["read_back_verified"] is True
    assert all(write["read_back_checks"].values()), write["read_back_checks"]
    assert write["mapped_rows"] == FIXTURE_SPAE_ROWS
    assert write["matched_rows"] == write["mapped_rows"]

    predictions = pl.read_parquet(run_dir(settings, rid) / predict["predictions_file"])
    assert predictions.height == FIXTURE_SPAE_ROWS

    export = run_dir(settings, rid) / write["export_file"]
    assert export.is_file()
    assert hashlib.sha256(export.read_bytes()).hexdigest() == write["export_sha256"]
    mapped = pl.read_parquet(export)
    assert mapped.height == write["mapped_rows"]
    null_counts = mapped.select(LEVEL_COLUMNS).null_count().to_dicts()[0]
    assert null_counts == {column: 0 for column in LEVEL_COLUMNS}, null_counts


# -------------------------------------------------------------- run_pipeline
@pytest.mark.slow
@pytest.mark.asyncio
async def test_run_pipeline_runs_every_stage_in_one_call(tmp_path, contract_fixture):
    settings = make_settings(tmp_path, contract_fixture)
    async with Client(make_server(settings)) as client:
        result = assert_no_error(await call(client, "run_wbs_pipeline", **FAST))
        rid = result["run_id"]
        status = assert_no_error(await call(client, "get_wbs_run_status", run_id=rid))

    assert set(result["stages"]) == set(STAGES)
    assert result["stages"]["predict"]["predicted_rows"] == FIXTURE_SPAE_ROWS
    assert result["stages"]["write_back"]["read_back_verified"] is True
    assert result["artifacts_dir"] == str(run_dir(settings, rid))
    statuses = {stage: status["stages"][stage]["status"] for stage in STAGES}
    assert statuses == {stage: "ok" for stage in STAGES}


# ------------------------------------------------------------- invalidation
@pytest.mark.slow
@pytest.mark.asyncio
async def test_rerunning_clean_marks_downstream_stages_stale(
    tmp_path, contract_fixture
):
    settings = make_settings(tmp_path, contract_fixture)
    async with Client(make_server(settings)) as client:
        rid = assert_no_error(await call(client, "run_wbs_pipeline", **FAST))["run_id"]
        clean_again = assert_no_error(await call(client, "clean_wbs_data", run_id=rid))
        assert clean_again["run_id"] == rid
        status = assert_no_error(await call(client, "get_wbs_run_status", run_id=rid))
        predict_now = await call(client, "predict_wbs", run_id=rid)

    assert status["stages"]["clean"]["status"] == "ok"
    for stage in ("tune_train", "predict", "write_back"):
        assert status["stages"][stage]["status"] == "stale", stage
        assert status["stages"][stage]["reason"] == "clean re-run", stage
    assert_error(predict_now, "Stage 'tune_train' has not completed")


# ------------------------------------------------------------ repeat runs
@pytest.mark.slow
@pytest.mark.asyncio
async def test_two_runs_with_same_seeds_produce_identical_predictions(
    tmp_path, contract_fixture
):
    settings = make_settings(tmp_path, contract_fixture)
    seeds = {"split_seed": 7, "search_seed": 7}
    tables: list[pl.DataFrame] = []
    summaries: list[dict[str, Any]] = []
    async with Client(make_server(settings)) as client:
        for _ in range(2):
            rid = await clean_run(client)
            tune = assert_no_error(
                await call(client, "tune_and_train_wbs", run_id=rid, **FAST, **seeds)
            )
            predict = assert_no_error(await call(client, "predict_wbs", run_id=rid))
            tables.append(
                pl.read_parquet(run_dir(settings, rid) / predict["predictions_file"])
            )
            summaries.append(
                {k: tune[k] for k in ("train_rows", "untuned_test_f1", "tuned_test_f1")}
            )

    first, second = (table.sort(PREDICTION_KEY) for table in tables)
    message = f"{prediction_diff(first, second)}; tune summaries: {summaries}"
    assert first.equals(second), message


# ------------------------------------------------- signing and integrity
@pytest.mark.slow
@pytest.mark.asyncio
async def test_tampered_untuned_model_is_rejected_before_deserialization(
    tmp_path, contract_fixture, monkeypatch
):
    settings = make_settings(tmp_path, contract_fixture)
    async with Client(make_server(settings)) as client:
        rid = await tuned_run(client)
        model_file = (
            run_dir(settings, rid) / "bundles" / "untuned" / wbs_artifacts.MODEL_FILE
        )
        original = model_file.read_bytes()
        tampered = bytearray(original)
        tampered[len(tampered) // 2] ^= 0xFF
        model_file.write_bytes(bytes(tampered))
        assert model_file.read_bytes() != original

        refuse = _LoadSpy(allow=False)
        with monkeypatch.context() as patch:
            patch.setattr(
                wbs_artifacts,
                "joblib",
                SimpleNamespace(load=refuse.load, dump=joblib.dump),
            )
            result = await call(
                client, "predict_wbs", run_id=rid, model_variant="untuned"
            )

        error = assert_error(result)
        assert re.search(r"checksum|signature", error, re.IGNORECASE), error
        assert wbs_artifacts.MODEL_FILE in error
        assert refuse.calls == 0, "tampered bundle was deserialized"
        assert "predict" not in manifest_stages(settings, rid)
        predicted = run_dir(settings, rid) / "predictions" / "predicted_levels.parquet"
        assert not predicted.exists()

        # Restore: a new run with a fresh tune. The load hook must still be on
        # the predict path (control).
        allow = _LoadSpy(allow=True)
        fresh = await tuned_run(client)
        with monkeypatch.context() as patch:
            patch.setattr(
                wbs_artifacts,
                "joblib",
                SimpleNamespace(load=allow.load, dump=joblib.dump),
            )
            restored = assert_no_error(await call(client, "predict_wbs", run_id=fresh))
    assert restored["predicted_rows"] == FIXTURE_SPAE_ROWS
    assert allow.calls > 0, "control: the load hook was not on the predict path"


@pytest.mark.slow
@pytest.mark.asyncio
async def test_edited_bundle_manifest_fails_signature_check_before_deserialization(
    tmp_path, contract_fixture, monkeypatch
):
    settings = make_settings(tmp_path, contract_fixture)
    async with Client(make_server(settings)) as client:
        rid = await tuned_run(client)
        manifest_path = (
            run_dir(settings, rid) / "bundles" / "untuned" / wbs_artifacts.MANIFEST_FILE
        )
        body = json.loads(manifest_path.read_text(encoding="utf-8"))
        body["run_id"] = "tampered"
        manifest_path.write_text(json.dumps(body, indent=2), encoding="utf-8")

        refuse = _LoadSpy(allow=False)
        with monkeypatch.context() as patch:
            patch.setattr(
                wbs_artifacts,
                "joblib",
                SimpleNamespace(load=refuse.load, dump=joblib.dump),
            )
            result = await call(
                client, "predict_wbs", run_id=rid, model_variant="untuned"
            )

    assert_error(result, "Model manifest signature is missing or invalid")
    assert refuse.calls == 0, "bundle with a bad signature was deserialized"


# ------------------------------------------------------ legacy table names (A)
@pytest.mark.asyncio
async def test_get_wbs_rows_resolves_the_legacy_suffixed_source_table(
    tmp_path, monkeypatch
):
    """With PARS_LEGACY_TABLE_SUFFIX set, the read tools must find the suffixed table.

    The module reads the variable once at import, so this test sets the two module
    values that the variable produces (the same ones validate_source uses). The source
    is a copy of the synthetic mock, the only origin the read tools return rows for.
    """
    suffix = "_legacy"
    monkeypatch.setattr(wbs_pipeline, "LEGACY_TABLE_SUFFIX", suffix)
    monkeypatch.setattr(
        wbs_pipeline,
        "SOURCE_TABLE_NAMES",
        {
            local: local + suffix
            for local in ("gold_corrections", "silver_spae_data", "silver_corrections")
        },
    )
    source = tmp_path / "source" / "suffixed.duckdb"
    source.parent.mkdir(parents=True)
    shutil.copyfile(Path(make_settings(tmp_path).wbs_source_db), source)
    with duckdb.connect(str(source)) as conn:
        total = conn.execute("SELECT count(*) FROM silver_spae_data").fetchone()[0]
        conn.execute("ALTER TABLE silver_spae_data RENAME TO silver_spae_data_legacy")

    settings = make_settings(tmp_path, source)
    async with Client(make_server(settings)) as client:
        wbs = assert_no_error(await call(client, "get_wbs_rows", limit=5))

    assert wbs["table"] == "silver_spae_data_legacy"
    assert wbs["returned"] == 5 and len(wbs["rows"]) == 5
    assert wbs["total_rows"] == total


# ------------------------------------------------------ synthetic-only rows (F)
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "origin", ["synthetic_mock", "labeled_test_fixture", "unknown"]
)
async def test_read_tools_return_rows_only_from_documented_synthetic_data(
    tmp_path, contract_fixture, origin
):
    if origin == "synthetic_mock":
        source = None  # default source: the bundled synthetic mock
    else:
        source = tmp_path / "source" / f"{origin}.duckdb"
        source.parent.mkdir(parents=True)
        shutil.copyfile(contract_fixture, source)
        if origin == "unknown":  # drop the marker so no origin is named
            with duckdb.connect(str(source)) as conn:
                conn.execute("DROP TABLE _fixture_marker")
    settings = make_settings(tmp_path, source)
    expected_table = "silver_spae_data"

    async with Client(make_server(settings)) as client:
        projects = await call(client, "get_wbs_project_descriptions", limit=5)
        wbs = await call(client, "get_wbs_rows", limit=5)

    if origin in ("synthetic_mock", "labeled_test_fixture"):
        assert_no_error(projects)
        assert assert_no_error(wbs)["table"] == expected_table
        return
    for result in (projects, wbs):
        assert_error(result, "documented synthetic data")
        assert set(result) == {"error"}, sorted(result)
        assert str(source) not in result["error"]


# --------------------------------------------------- run_id newline rejection (B)
@pytest.mark.asyncio
async def test_run_id_with_trailing_newline_is_rejected_and_creates_no_directory(
    tmp_path, contract_fixture
):
    settings = make_settings(tmp_path, contract_fixture)
    rid = "r" + "5" * 12 + "\n"
    async with Client(make_server(settings)) as client:
        for name, arguments in [
            ("get_wbs_run_status", {"run_id": rid}),
            ("clean_wbs_data", {"run_id": rid}),
            ("run_wbs_pipeline", {"run_id": rid, **FAST}),
        ]:
            assert_error(await call(client, name, **arguments), "run_id must look like")
    assert not settings.wbs_runs_dir.exists(), "a newline run_id created a directory"


# ------------------------------------------------ search bounds before writes (C)
@pytest.mark.asyncio
@pytest.mark.parametrize(("argument", "value"), [("n_iter", 0), ("cv_folds", 1)])
async def test_run_pipeline_rejects_low_bounds_before_creating_a_run(
    tmp_path, contract_fixture, argument, value
):
    settings = make_settings(tmp_path, contract_fixture)
    async with Client(make_server(settings)) as client:
        result = await call(client, "run_wbs_pipeline", **{**FAST, argument: value})
    assert_error(result, "n_iter must be >= 1 and cv_folds must be >= 2")
    assert not run_dir(settings, result["run_id"]).exists()
    runs = settings.wbs_runs_dir
    assert not runs.exists() or files_under(runs) == [], "a run directory was created"


# ------------------------------------------- jobs and seed rejection before writes (D)
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("argument", "value", "message"),
    [
        ("n_jobs", 0, "n_jobs must be -1 or between 1 and 8"),
        ("split_seed", -1, "split_seed must be between 0 and 4294967295"),
        ("search_seed", 2**32, "search_seed must be between 0 and 4294967295"),
    ],
)
async def test_tune_and_pipeline_reject_bad_jobs_and_seeds_before_any_write(
    tmp_path, contract_fixture, argument, value, message
):
    settings = make_settings(tmp_path, contract_fixture)
    fresh = "r" + "6" * 12
    async with Client(make_server(settings)) as client:
        rid = await clean_run(client)
        before = files_under(run_dir(settings, rid))
        tune = await call(
            client, "tune_and_train_wbs", run_id=rid, **{**FAST, argument: value}
        )
        pipeline = await call(
            client, "run_wbs_pipeline", run_id=fresh, **{**FAST, argument: value}
        )
    assert_error(tune, message)
    assert_error(pipeline, message)
    assert files_under(run_dir(settings, rid)) == before, "tune wrote to the run"
    assert not run_dir(settings, fresh).exists(), "pipeline created a run"
