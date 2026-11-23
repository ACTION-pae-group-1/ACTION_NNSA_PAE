"""Tests for the isolated PARS gap-eval stdio launcher's startup safety guard."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pars_gap_stdio_server as launcher  # noqa: E402

ALL_KEYS = list(launcher.REQUIRED)


def test_refuses_to_start_when_no_path_variables_are_set(monkeypatch):
    for key in ALL_KEYS:
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(SystemExit, match="unset"):
        launcher._check_env()


def test_refuses_to_start_when_one_path_variable_is_missing(monkeypatch, tmp_path):
    isolated = launcher.ISOLATION_ROOT / "run-x"
    for key in ALL_KEYS:
        monkeypatch.setenv(key, str(isolated / key))
    monkeypatch.delenv("WBS_SOURCE_DB", raising=False)
    with pytest.raises(SystemExit, match="unset"):
        launcher._check_env()


def test_refuses_a_path_outside_the_isolation_root(monkeypatch, tmp_path):
    isolated = launcher.ISOLATION_ROOT / "run-x"
    for key in ALL_KEYS:
        monkeypatch.setenv(key, str(isolated / key))
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "outside.duckdb"))
    with pytest.raises(SystemExit, match="outside the isolation root"):
        launcher._check_env()


def test_accepts_all_paths_under_the_isolation_root(monkeypatch):
    isolated = launcher.ISOLATION_ROOT / "run-x"
    for key in ALL_KEYS:
        monkeypatch.setenv(key, str(isolated / key))
    paths = launcher._check_env()
    assert set(paths) == set(ALL_KEYS)
    for key, path in paths.items():
        assert launcher.ISOLATION_ROOT in path.parents
