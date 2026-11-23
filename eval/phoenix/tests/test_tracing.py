"""Tests for Phoenix tracing with a local JSONL fallback.

Everything is mocked. The default network probe is replaced by a guard that fails
the test if it is ever reached, so no test can touch the network.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

EVAL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL_DIR))

import tracing  # noqa: E402


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def guard(url: str, timeout: float) -> bool:
        raise AssertionError(f"network probe reached in a test: {url}")

    monkeypatch.setattr(tracing, "default_probe", guard)
    for name in ("PHOENIX_COLLECTOR_ENDPOINT", "PHOENIX_ENDPOINT"):
        monkeypatch.delenv(name, raising=False)


def _records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


# --- backend selection ------------------------------------------------------


def test_phoenix_used_when_reachable_and_importable(tmp_path: Path) -> None:
    provider = MagicMock()
    register = MagicMock(return_value=provider)
    probe = MagicMock(return_value=True)

    t = tracing.setup_tracing(
        "pars-eval",
        tmp_path / "t.jsonl",
        endpoint="http://localhost:6006",
        register_fn=register,
        probe_fn=probe,
    )

    assert t.backend == "phoenix"
    assert t.fallback_reason == ""
    probe.assert_called_once()
    kwargs = register.call_args.kwargs
    assert kwargs["endpoint"] == "http://localhost:6006/v1/traces"
    assert kwargs["project_name"] == "pars-eval"
    assert kwargs["set_global_tracer_provider"] is False
    assert not (tmp_path / "t.jsonl").exists()


def test_falls_back_when_phoenix_unreachable(tmp_path: Path) -> None:
    register = MagicMock()
    t = tracing.setup_tracing(
        "p",
        tmp_path / "t.jsonl",
        endpoint="http://127.0.0.1:6006",
        register_fn=register,
        probe_fn=MagicMock(return_value=False),
    )
    assert t.backend == "jsonl"
    assert "unreachable" in t.fallback_reason
    register.assert_not_called()


def test_falls_back_when_probe_raises(tmp_path: Path) -> None:
    t = tracing.setup_tracing(
        "p",
        tmp_path / "t.jsonl",
        endpoint="http://localhost:6006",
        register_fn=MagicMock(),
        probe_fn=MagicMock(side_effect=OSError("refused")),
    )
    assert t.backend == "jsonl"
    assert "refused" in t.fallback_reason


def test_falls_back_when_phoenix_import_fails(tmp_path: Path, monkeypatch) -> None:
    def broken_import():
        raise ValueError("mutable default for field boolean_names")

    monkeypatch.setattr(tracing, "_import_register", broken_import)
    t = tracing.setup_tracing(
        "p",
        tmp_path / "t.jsonl",
        endpoint="http://localhost:6006",
        probe_fn=MagicMock(return_value=True),
    )
    assert t.backend == "jsonl"
    assert "ValueError" in t.fallback_reason


def test_falls_back_when_register_raises(tmp_path: Path) -> None:
    t = tracing.setup_tracing(
        "p",
        tmp_path / "t.jsonl",
        endpoint="http://localhost:6006",
        register_fn=MagicMock(side_effect=RuntimeError("bad exporter")),
        probe_fn=MagicMock(return_value=True),
    )
    assert t.backend == "jsonl"
    assert "bad exporter" in t.fallback_reason


def test_non_loopback_endpoint_is_never_probed(tmp_path: Path) -> None:
    probe = MagicMock(return_value=True)
    register = MagicMock()
    t = tracing.setup_tracing(
        "p",
        tmp_path / "t.jsonl",
        endpoint="https://phoenix.example.com",
        register_fn=register,
        probe_fn=probe,
    )
    assert t.backend == "jsonl"
    assert "loopback" in t.fallback_reason
    probe.assert_not_called()
    register.assert_not_called()


def test_disabled_goes_straight_to_jsonl(tmp_path: Path) -> None:
    probe = MagicMock()
    t = tracing.setup_tracing("p", tmp_path / "t.jsonl", enabled=False, probe_fn=probe)
    assert t.backend == "jsonl"
    assert "disabled" in t.fallback_reason
    probe.assert_not_called()


def test_endpoint_defaults_to_env_then_localhost(monkeypatch) -> None:
    assert tracing.phoenix_base_url() == "http://localhost:6006"
    monkeypatch.setenv("PHOENIX_ENDPOINT", "http://127.0.0.1:7000/")
    assert tracing.phoenix_base_url() == "http://127.0.0.1:7000"
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "http://localhost:9000")
    assert tracing.phoenix_base_url() == "http://localhost:9000"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("http://localhost:6006", True),
        ("http://127.0.0.1:6006", True),
        ("http://[::1]:6006", True),
        ("https://phoenix.example.com", False),
        ("http://10.0.0.5:6006", False),
        ("not a url", False),
    ],
)
def test_is_loopback(url: str, expected: bool) -> None:
    assert tracing.is_loopback(url) is expected


# --- JSONL backend ----------------------------------------------------------


def test_jsonl_span_writes_one_record(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "t.jsonl"
    t = tracing.setup_tracing("pars-eval", path, enabled=False)

    with t.span("pars_eval.example", {"example": 1, "query": "List"}) as span:
        span.set_attributes({"tool_names": ["a", "b"], "correctness": "correct"})
    t.shutdown()

    (rec,) = _records(path)
    assert rec["name"] == "pars_eval.example"
    assert rec["project"] == "pars-eval"
    assert rec["status"] == "ok"
    assert rec["error"] == ""
    assert rec["attributes"] == {
        "example": 1,
        "query": "List",
        "tool_names": ["a", "b"],
        "correctness": "correct",
    }
    assert len(rec["trace_id"]) == 32 and len(rec["span_id"]) == 16
    assert rec["duration_s"] >= 0
    assert rec["start_time"] <= rec["end_time"]


def test_jsonl_appends_across_spans_and_sessions(tmp_path: Path) -> None:
    path = tmp_path / "t.jsonl"
    for i in range(2):
        t = tracing.setup_tracing("p", path, enabled=False)
        with t.span("s", {"i": i}):
            pass
        t.shutdown()
    assert [r["attributes"]["i"] for r in _records(path)] == [0, 1]


def test_jsonl_records_exception_and_reraises(tmp_path: Path) -> None:
    path = tmp_path / "t.jsonl"
    t = tracing.setup_tracing("p", path, enabled=False)
    with pytest.raises(KeyError):
        with t.span("boom"):
            raise KeyError("missing")
    (rec,) = _records(path)
    assert rec["status"] == "error"
    assert "KeyError" in rec["error"]


def test_jsonl_serialises_unusual_values(tmp_path: Path) -> None:
    path = tmp_path / "t.jsonl"
    t = tracing.setup_tracing("p", path, enabled=False)
    with t.span("s", {"path": Path("a/b"), "nan": float("nan"), "none": None}):
        pass
    (rec,) = _records(path)
    assert rec["attributes"]["path"] in ("a/b", "a\\b")
    assert rec["attributes"]["none"] is None
    assert rec["attributes"]["nan"] is None


# --- Phoenix backend --------------------------------------------------------


def _phoenix(tmp_path: Path):
    provider = MagicMock()
    tracer = provider.get_tracer.return_value
    otel_span = tracer.start_as_current_span.return_value.__enter__.return_value
    t = tracing.setup_tracing(
        "p",
        tmp_path / "t.jsonl",
        endpoint="http://localhost:6006",
        register_fn=MagicMock(return_value=provider),
        probe_fn=MagicMock(return_value=True),
    )
    return t, provider, tracer, otel_span


def test_phoenix_span_sets_coerced_attributes(tmp_path: Path) -> None:
    t, _, tracer, otel_span = _phoenix(tmp_path)
    with t.span("pars_eval.example", {"example": 2}) as span:
        span.set_attributes(
            {"tool_names": ["a", "b"], "meta": {"k": 1}, "none": None, "ok": True}
        )

    tracer.start_as_current_span.assert_called_once_with("pars_eval.example")
    calls = dict(c.args for c in otel_span.set_attribute.call_args_list)
    assert calls == {
        "example": 2,
        "tool_names": ["a", "b"],
        "meta": '{"k": 1}',
        "none": "",
        "ok": True,
    }
    assert not (tmp_path / "t.jsonl").exists()


def test_phoenix_span_records_exception(tmp_path: Path) -> None:
    t, _, _, otel_span = _phoenix(tmp_path)
    with pytest.raises(RuntimeError):
        with t.span("s"):
            raise RuntimeError("x")
    otel_span.record_exception.assert_called_once()
    otel_span.set_attribute.assert_any_call("error", "RuntimeError: x")


def test_phoenix_shutdown_flushes_and_never_raises(tmp_path: Path) -> None:
    t, provider, _, _ = _phoenix(tmp_path)
    provider.shutdown.side_effect = RuntimeError("exporter gone")
    t.shutdown()
    provider.shutdown.assert_called_once()
