"""Import the repository's data/manual_monthly helpers for tests.

``data`` is also a regular package at ``src/pars_local_mcp/data``. Pytest puts
``src/pars_local_mcp`` on ``sys.path`` (its conftest folder has no
``__init__.py``), and a regular package anywhere on the path beats the
repository's top-level ``data/`` namespace package. So a plain
``from data.manual_monthly import ...`` fails in a full test run but passes when
these tests run alone. Loading the folder under a private package name avoids
the clash without changing either package.
"""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

_PACKAGE = "_manual_monthly_under_test"
_FOLDER = Path(__file__).resolve().parents[4] / "data" / "manual_monthly"


def load(module: str) -> types.ModuleType:
    """Return ``data/manual_monthly/<module>.py``, imported once per session."""
    if _PACKAGE not in sys.modules:
        package = types.ModuleType(_PACKAGE)
        package.__path__ = [str(_FOLDER)]
        package.__package__ = _PACKAGE
        sys.modules[_PACKAGE] = package
    return importlib.import_module(f"{_PACKAGE}.{module}")
