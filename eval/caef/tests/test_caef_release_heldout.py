"""Tests for the pure helpers in eval/caef/caef_release_heldout.py.

main() is never called: it runs the held-out evaluation and writes results.
"""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "eval" / "caef" / "caef_release_heldout.py"


@pytest.fixture
def module(monkeypatch):
    monkeypatch.syspath_prepend(str(REPO / "tools"))
    monkeypatch.syspath_prepend(str(REPO / "src"))
    spec = importlib.util.spec_from_file_location("caef_release_heldout", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_sha_matches_hashlib(module, tmp_path: Path) -> None:
    path = tmp_path / "payload.bin"
    path.write_bytes(b"stadium release")
    assert module.sha(path) == hashlib.sha256(b"stadium release").hexdigest()


def test_sha_differs_for_different_content(module, tmp_path: Path) -> None:
    first = tmp_path / "first.bin"
    second = tmp_path / "second.bin"
    first.write_bytes(b"one")
    second.write_bytes(b"two")
    assert module.sha(first) != module.sha(second)


def test_output_is_under_release_results(module) -> None:
    expected = REPO / "eval" / "caef" / "results" / "release-2026-11-19"
    assert module.OUT.parent == expected
