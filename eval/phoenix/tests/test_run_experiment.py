"""Tests for the eval tool scope and the per-row reporting of model and endpoint."""

from __future__ import annotations

import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL_DIR))

from llm_endpoint import EndpointInfo  # noqa: E402

AGENT_EP = EndpointInfo(
    provider="asksage", host="api.nnsa.asksage.ai", model="gpt-5.4-gov"
)
JUDGE_EP = EndpointInfo(
    provider="asksage", host="api.nnsa.asksage.ai", model="gpt-5.4-gov"
)


def _row(**overrides):
    from agent import AgentRun
    from run_experiment import build_row

    run = AgentRun(
        response="answer", tool_calls=2, tool_names=["a", "b"], latency_s=1.5
    )
    fields = dict(
        run_id="r1",
        timestamp_utc="2026-11-13T00:00:00Z",
        git_sha="abc123",
        dataset="pars-eval-0",
        prompt_version="v2",
        mode="tools",
        example=1,
        trial=1,
        query="List the projects",
        run=run,
        agent=AGENT_EP,
        judge=JUDGE_EP,
        scope="within_scope",
        correctness="correct",
        error="",
    )
    fields.update(overrides)
    return build_row(**fields)


def test_pars_tool_scope_is_the_seven_read_only_tools() -> None:
    from agent import READ_ONLY_TOOLS, pars_server_config

    assert set(READ_ONLY_TOOLS) == {
        "list_projects",
        "search_wbs",
        "get_wbs_hierarchy",
        "get_wbs_lineage",
        "get_project_info",
        "get_leaf_nodes",
        "get_wbs_by_level",
    }
    cfg = pars_server_config()
    assert cfg.allowed_tools == READ_ONLY_TOOLS
    assert "train_classifier" not in cfg.allowed_tools
    assert "classify_wbs" not in cfg.allowed_tools


def test_pars_server_launches_with_this_interpreter() -> None:
    import sys as _sys

    from agent import pars_server_config

    assert pars_server_config().command == _sys.executable


def test_pars_server_arguments_run_the_server_module() -> None:
    """The config's `uv run ...` arguments must not survive the interpreter swap."""
    from agent import pars_server_config

    assert pars_server_config().args == ("-m", "src.pars_local_mcp.server")


def test_every_row_reports_model_and_endpoint() -> None:
    row = _row()
    assert row["agent_provider"] == "asksage"
    assert row["agent_endpoint_host"] == "api.nnsa.asksage.ai"
    assert row["agent_model"] == "gpt-5.4-gov"
    assert row["judge_provider"] == "asksage"
    assert row["judge_endpoint_host"] == "api.nnsa.asksage.ai"
    assert row["judge_model"] == "gpt-5.4-gov"


def test_rows_carry_the_run_metadata_columns() -> None:
    from run_experiment import COLUMNS

    row = _row()
    assert set(row) == set(COLUMNS)
    assert row["tool_names"] == "a;b"
    assert row["mode"] == "tools"
    assert row["git_sha"] == "abc123"


def test_summary_reports_consistency_across_trials() -> None:
    from run_experiment import summarize

    rows = [
        _row(example=1, trial=1, correctness="correct"),
        _row(example=1, trial=2, correctness="correct"),
        _row(example=2, trial=1, correctness="correct"),
        _row(example=2, trial=2, correctness="incorrect"),
        _row(example=3, trial=1, error="agent: timeout", scope="", correctness=""),
    ]
    summary = summarize(rows)
    assert summary["errors"] == 1
    assert summary["scored"] == 4
    assert summary["correctness_rate"] == 0.75
    assert summary["consistent_examples"] == 1
    assert summary["examples"] == 2


# --- tracing integration (agent, judges, and Phoenix probe all mocked) ---------


def _offline_eval(monkeypatch, tmp_path, *, probe_result=False):
    """Patch run_experiment so run_eval runs fully offline.

    Returns (module, probe_calls).
    """
    import run_experiment
    import tracing
    from agent import AgentRun

    probe_calls = []

    def probe(url, timeout):
        probe_calls.append(url)
        return probe_result

    monkeypatch.setattr(tracing, "default_probe", probe)
    for name in ("PHOENIX_COLLECTOR_ENDPOINT", "PHOENIX_ENDPOINT"):
        monkeypatch.delenv(name, raising=False)

    class FakeAgent:
        def __init__(self, **kwargs):
            self.endpoint = AGENT_EP

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return None

        async def run(self, query):
            if "fail" in query:
                return AgentRun(response="", tool_calls=0, error="agent: timeout")
            return AgentRun(
                response=f"answer to {query}",
                tool_calls=1,
                tool_names=["pars_mcp__list_projects"],
                latency_s=0.01,
            )

    csv = tmp_path / "set.csv"
    csv.write_text(
        'query,responses\n"List projects","two"\n"please fail","n/a"\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(run_experiment, "PARSAgent", FakeAgent)
    monkeypatch.setattr(run_experiment, "judge_endpoint", lambda: JUDGE_EP)
    monkeypatch.setattr(
        run_experiment,
        "judge_row",
        lambda q, r, e: ("within_scope", "correct", ""),
    )
    monkeypatch.setattr(
        run_experiment,
        "load_dataset_config",
        lambda: {
            "t": {
                "csv_path": str(csv),
                "input_keys": ["query"],
                "output_keys": ["responses"],
            }
        },
    )
    monkeypatch.setattr(run_experiment, "RESULTS_DIR", tmp_path / "results")
    monkeypatch.setattr(run_experiment, "git_sha", lambda: "abc123")
    return run_experiment, probe_calls


def _run(run_experiment, **overrides):
    import asyncio

    kwargs = dict(
        prompt_version="v2",
        trials=1,
        max_examples=None,
        use_tools=True,
        validate=True,
    )
    kwargs.update(overrides)
    asyncio.run(run_experiment.run_eval("t", **kwargs))


def test_run_eval_writes_one_jsonl_span_per_row_when_phoenix_is_down(
    monkeypatch, tmp_path
) -> None:
    import json

    run_experiment, probe_calls = _offline_eval(monkeypatch, tmp_path)
    _run(run_experiment)

    assert probe_calls == ["http://localhost:6006"]
    (trace_file,) = (tmp_path / "results").glob("*.traces.jsonl")
    records = [json.loads(x) for x in trace_file.read_text("utf-8").splitlines()]
    assert len(records) == 2
    assert {r["name"] for r in records} == {"pars_eval.example"}
    first, second = (r["attributes"] for r in records)
    assert first["example"] == 1 and first["trial"] == 1
    assert first["query"] == "List projects"
    assert first["agent_model"] == "gpt-5.4-gov"
    assert first["judge_model"] == "gpt-5.4-gov"
    assert first["correctness"] == "correct"
    assert first["tool_names"] == "pars_mcp__list_projects"
    assert first["run_id"].startswith("t_v2_tools_")
    assert second["error"] == "agent: timeout"

    (meta_file,) = (tmp_path / "results").glob("*.json")
    meta = json.loads(meta_file.read_text("utf-8"))
    assert meta["tracing"]["backend"] == "jsonl"
    assert "unreachable" in meta["tracing"]["fallback_reason"]
    assert meta["tracing"]["jsonl_path"] == str(trace_file)


def test_run_eval_with_tracing_disabled_never_probes(monkeypatch, tmp_path) -> None:
    import json

    run_experiment, probe_calls = _offline_eval(monkeypatch, tmp_path)
    _run(run_experiment, tracing_enabled=False)

    assert probe_calls == []
    (meta_file,) = (tmp_path / "results").glob("*.json")
    assert (
        "disabled"
        in json.loads(meta_file.read_text("utf-8"))["tracing"]["fallback_reason"]
    )
    assert len(list((tmp_path / "results").glob("*.traces.jsonl"))) == 1


def test_run_eval_honours_an_explicit_trace_path(monkeypatch, tmp_path) -> None:
    run_experiment, _ = _offline_eval(monkeypatch, tmp_path)
    target = tmp_path / "custom" / "spans.jsonl"
    _run(run_experiment, trace_path=target)
    assert len(target.read_text("utf-8").splitlines()) == 2
