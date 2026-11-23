"""Offline checks for eval/asksage/eval_asksage_mcp.py.

The script itself needs Ask Sage credentials, so these tests stay offline: they
check that it still starts (``--help``) and that its case prompts, which are
split across lines for line length, still read as complete sentences.
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "eval_asksage_mcp.py"
REPO_ROOT = Path(__file__).resolve().parents[3]


def _cases() -> list[tuple[str, str]]:
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "CASES"
            for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError("CASES not found")


def test_script_starts_and_prints_help_offline() -> None:
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")}
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "--server-config" in result.stdout


def test_case_names_are_unique() -> None:
    names = [name for name, _ in _cases()]
    assert len(names) == len(set(names))


def test_case_prompts_read_as_complete_sentences() -> None:
    for name, prompt in _cases():
        assert "  " not in prompt, name
        assert re.search(r"[.;,][A-Za-z]", prompt) is None, name
        assert re.search(r"[a-z][A-Z]", prompt) is None, name
        assert prompt.endswith("."), name
