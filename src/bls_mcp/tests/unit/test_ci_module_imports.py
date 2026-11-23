"""The BLS CI ingestion module must stay importable.

Merge f6f3995 emptied src/bls_mcp/ingestion/ci.py. The BLS app, its CLI, and the
lifecycle module then failed at import time. These tests fail on that state.
"""

import importlib


def test_ci_module_defines_its_public_names():
    ci = importlib.import_module("bls_mcp.ingestion.ci")
    assert hasattr(ci, "CIIngestReport")
    assert hasattr(ci, "ingest_ci")


def test_lifecycle_and_cli_modules_import():
    importlib.import_module("bls_mcp.ingestion.lifecycle")
    importlib.import_module("bls_mcp.ingestion.cli")


def test_app_module_imports():
    importlib.import_module("bls_mcp.app")
