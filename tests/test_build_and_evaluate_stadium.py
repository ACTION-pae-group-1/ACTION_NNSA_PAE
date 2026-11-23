"""Tests for the pure helpers in tools/build_and_evaluate_stadium.py.

main() and build_release() are never called: they build and write the release.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "tools" / "build_and_evaluate_stadium.py"


@pytest.fixture
def module(monkeypatch):
    monkeypatch.syspath_prepend(str(REPO / "tools"))
    monkeypatch.syspath_prepend(str(REPO / "src"))
    spec = importlib.util.spec_from_file_location("build_and_evaluate_stadium", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["build_and_evaluate_stadium"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_sha_matches_hashlib(module, tmp_path: Path) -> None:
    path = tmp_path / "bundle.bin"
    path.write_bytes(b"release")
    assert module._sha(path) == hashlib.sha256(b"release").hexdigest()


def test_tokens_match_lowercase_alphanumeric_runs(module) -> None:
    assert module._tokens("Concrete Slab-2") == frozenset({"concrete", "slab", "2"})


def test_dup_checks_counts_exact_and_near_duplicates(module) -> None:
    result = module.dup_checks(
        ["steel beam", "concrete slab"],
        ["steel beam", "steel beams deck"],
    )
    assert result["exact_text_duplicates_with_training"] == 1
    near = result["near_duplicate_jaccard_max_over_training"]
    # Near values are [1.0, 0.25]: an exact match, and a 1/4 overlap with
    # "steel beam" for the second test text.
    assert near["median"] == pytest.approx(0.625)
    assert near["share_ge_0_8"] == pytest.approx(0.5)
    assert near["share_ge_0_6"] == pytest.approx(0.5)
