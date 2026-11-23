"""Tests for the pure constants in tools/build_stadium_pars_v2_wording.py.

main() is never called: it writes the v2 stadium database and manifest.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "tools" / "build_stadium_pars_v2_wording.py"


@pytest.fixture
def module(monkeypatch):
    monkeypatch.syspath_prepend(str(REPO / "tools"))
    monkeypatch.syspath_prepend(str(REPO / "src"))
    spec = importlib.util.spec_from_file_location(
        "build_stadium_pars_v2_wording", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["build_stadium_pars_v2_wording"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_sha_matches_hashlib(module, tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_bytes(b"{}")
    assert module._sha(path) == hashlib.sha256(b"{}").hexdigest()


def test_v2_outputs_do_not_overwrite_v1(module) -> None:
    assert module.V2_DB != module.V1_DB
    assert module.V2_MANIFEST != module.V1_MANIFEST


def test_v2_phrases_are_never_used_in_v1(module) -> None:
    v1_templates = {t for templates in module.v1.PHRASES.values() for t in templates}
    v2_templates = {t for templates in module.PHRASES_V2.values() for t in templates}
    assert v2_templates
    assert v1_templates.isdisjoint(v2_templates)


def test_v2_templates_use_only_zone_and_system_placeholders(module) -> None:
    for templates in module.PHRASES_V2.values():
        for template in templates:
            template.format(z="zone", s="system")
