"""Keep pytest from importing the live Ask Sage scripts in this folder.

``test_asksage_*.py`` here are scripts run by hand with Ask Sage credentials,
not pytest tests: they read ``LLM_BASE_URL`` at import time and their
``test_model`` functions take arguments that are not fixtures. When one of them
changes, the pre-commit fast suite passes it to pytest by path, which used to
fail with ``KeyError: 'LLM_BASE_URL'``. Each script is now reported as one
skipped item instead, and the offline checks live in ``tests/``.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

LIVE_SCRIPTS = frozenset(
    {
        "test_asksage_mcp.py",
        "test_asksage_tool_roundtrip.py",
        "test_asksage_tools.py",
    }
)


class _LiveScriptItem(pytest.Item):
    def runtest(self) -> None:
        pytest.skip(f"{self.path.name} is a live Ask Sage script; run it directly")

    def reportinfo(self) -> tuple[Path, int, str]:
        return self.path, 0, f"live script {self.path.name}"


class _LiveScript(pytest.File):
    def collect(self) -> Iterator[pytest.Item]:
        yield _LiveScriptItem.from_parent(self, name="live_script")


def pytest_pycollect_makemodule(
    module_path: Path, parent: pytest.Collector
) -> pytest.File | None:
    if module_path.name in LIVE_SCRIPTS:
        return _LiveScript.from_parent(parent, path=module_path)
    return None
