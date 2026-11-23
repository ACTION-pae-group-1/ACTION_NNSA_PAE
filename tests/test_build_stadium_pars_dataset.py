"""Tests for the pure helpers in tools/build_stadium_pars_dataset.py.

main() is never called: it writes the stadium database and manifest.
"""

from __future__ import annotations

import hashlib
import importlib.util
import random
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "tools" / "build_stadium_pars_dataset.py"


@pytest.fixture
def module(monkeypatch):
    monkeypatch.syspath_prepend(str(REPO / "tools"))
    monkeypatch.syspath_prepend(str(REPO / "src"))
    spec = importlib.util.spec_from_file_location("build_stadium_pars_dataset", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["build_stadium_pars_dataset"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_sha256_matches_hashlib(module, tmp_path: Path) -> None:
    path = tmp_path / "taxonomy.bin"
    path.write_bytes(b"caef")
    assert module.sha256(path) == hashlib.sha256(b"caef").hexdigest()


def test_caef_chain_fills_ancestors_and_blanks_below_target(module) -> None:
    nodes = {"1": "Site", "1.1": "Site Work", "1.1.2": "Grading"}
    labels = module.caef_chain("1.1.2", nodes)
    assert labels["caef_level_2"] == "site work"
    assert labels["caef_level_3"] == "grading"
    for depth in range(4, 9):
        assert labels[f"caef_level_{depth}"] == ""


def test_caef_chain_single_segment_has_no_levels(module) -> None:
    labels = module.caef_chain("1", {"1": "Site"})
    assert set(labels) == {f"caef_level_{d}" for d in range(2, 9)}
    assert all(value == "" for value in labels.values())


def test_build_project_is_hierarchical_and_labels_leaves(module) -> None:
    elements, labels = module.build_project("P1", "role", random.Random(7), {}, {})
    by_code = {
        code: (parent, level, work) for code, parent, level, _title, work in elements
    }
    phases = [code for code, (_p, level, _w) in by_code.items() if level == 1]
    assert phases, "expected at least one phase"
    for parent, level, _work in by_code.values():
        if level == 2:
            assert parent in phases
        elif level == 3:
            assert parent in by_code and by_code[parent][1] == 2
    leaves = [code for code, (_p, level, _w) in by_code.items() if level == 3]
    assert sorted(code for code, _title, _work in labels) == sorted(leaves)


def test_build_project_is_deterministic_for_a_seed(module) -> None:
    first = module.build_project("P1", "role", random.Random(42), {}, {})
    second = module.build_project("P1", "role", random.Random(42), {}, {})
    assert first == second
