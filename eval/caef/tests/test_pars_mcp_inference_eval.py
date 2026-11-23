"""Tests for the pure helpers in eval/caef/pars_mcp_inference_eval.py.

Importing the module sets COST_INTEL_PARS_STADIUM_DB; the fixture restores it.
main() is never called.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "eval" / "caef" / "pars_mcp_inference_eval.py"
ENV_KEY = "COST_INTEL_PARS_STADIUM_DB"


@pytest.fixture
def module(monkeypatch):
    # setenv records the original value; pytest restores it on teardown,
    # undoing the import-time assignment made by the script.
    monkeypatch.setenv(ENV_KEY, os.environ.get(ENV_KEY, ""))
    monkeypatch.syspath_prepend(str(REPO / "src"))
    spec = importlib.util.spec_from_file_location("pars_mcp_inference_eval", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeInner:
    def __init__(self, results: dict[str, dict]) -> None:
        self.results = results

    def call(self, tool: str, arguments: dict) -> dict:
        return self.results[tool]

    def tool_names(self) -> list[str]:
        return ["list_projects", "get_wbs_by_level"]


def test_sha_matches_hashlib(module, tmp_path: Path) -> None:
    path = tmp_path / "payload.bin"
    path.write_bytes(b"pars inference")
    assert module.sha(path) == hashlib.sha256(b"pars inference").hexdigest()


def test_recording_logs_successful_call(module) -> None:
    result = {"elements": [1, 2]}
    recorder = module.Recording(FakeInner({"get_wbs_by_level": result}))
    assert recorder.call("get_wbs_by_level", {"project": "5401"}) is result
    assert recorder.calls == [
        {
            "tool": "get_wbs_by_level",
            "arguments": {"project": "5401"},
            "outcome": "ok",
            "elements": 2,
        }
    ]


def test_recording_marks_error_results(module) -> None:
    recorder = module.Recording(FakeInner({"list_projects": {"error": "down"}}))
    recorder.call("list_projects", {})
    assert recorder.calls[0]["outcome"] == "error"
    assert recorder.calls[0]["elements"] is None


def test_recording_passes_tool_names_through(module) -> None:
    recorder = module.Recording(FakeInner({}))
    assert recorder.tool_names() == ["list_projects", "get_wbs_by_level"]


def test_stadium_db_is_not_the_protected_database(module) -> None:
    assert module.DB != module.PROTECTED
    assert module.PROTECTED.name == "wbs.duckdb"
    assert os.environ[ENV_KEY] == str(module.DB)
