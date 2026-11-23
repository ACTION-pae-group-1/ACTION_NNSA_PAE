"""Tests for the pure helpers in tools/eval_stadium_v2_heldout.py.

main() is never called: it scores the held-out v2 bundle and writes JSON.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "tools" / "eval_stadium_v2_heldout.py"


@pytest.fixture
def module(monkeypatch):
    monkeypatch.syspath_prepend(str(REPO / "tools"))
    monkeypatch.syspath_prepend(str(REPO / "src"))
    spec = importlib.util.spec_from_file_location("eval_stadium_v2_heldout", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["eval_stadium_v2_heldout"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_tokens_lowercase_and_split_on_non_alphanumerics(module) -> None:
    tokens = module._tokens("Steel-Beam, 2 Ton!")
    assert tokens == frozenset({"steel", "beam", "2", "ton"})


def test_jaccard_identical_sets(module) -> None:
    tokens = frozenset({"a", "b"})
    assert module._jaccard(tokens, tokens) == 1.0


def test_jaccard_disjoint_sets(module) -> None:
    assert module._jaccard(frozenset({"a"}), frozenset({"b"})) == 0.0


def test_jaccard_partial_overlap(module) -> None:
    value = module._jaccard(frozenset({"a", "b"}), frozenset({"b", "c"}))
    assert value == pytest.approx(1 / 3)


def test_jaccard_two_empty_sets_is_zero(module) -> None:
    assert module._jaccard(frozenset(), frozenset()) == 0.0
