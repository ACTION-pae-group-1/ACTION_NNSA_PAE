"""Build the synthetic PARS databases the tests read, when they are missing.

``mock_pars_full.duckdb`` and ``caef_synthetic_labeled.duckdb`` are
deterministic, synthetic and git-ignored (see docs/DATA_HANDLING.md), so a
fresh checkout has neither. They are built once per test session, with the
same generators the developer commands use, so the tests run instead of
failing on a missing file. An existing file is left as it is.
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session", autouse=True)
def _synthetic_pars_databases() -> None:
    from pars_local_mcp.data import generate_caef_training, generate_full_mock

    if not generate_full_mock.DEFAULT_OUTPUT.exists():
        generate_full_mock.build_mock_database()
    if not generate_caef_training.DEFAULT_OUTPUT.exists():
        generate_caef_training.build_database()
