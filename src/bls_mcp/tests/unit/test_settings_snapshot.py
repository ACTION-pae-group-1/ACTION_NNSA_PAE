"""Settings for the snapshot registry and the saved-specifications file.

These tests do not start the server.
"""

from __future__ import annotations

import pytest

from bls_mcp.config import Settings


def test_snapshot_registry_dir_field_exists() -> None:
    """Settings must expose bls_snapshot_registry_dir."""
    s = Settings(BLS_SNAPSHOT_REGISTRY_DIR="/tmp/registry")
    assert s.snapshot_registry_dir == "/tmp/registry"


def test_snapshot_registry_dir_read_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BLS_SNAPSHOT_REGISTRY_DIR", "/env/registry")
    s = Settings()
    assert s.snapshot_registry_dir == "/env/registry"


def test_snapshot_registry_dir_has_no_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The registry directory must be required, with no environment fallback."""
    import pydantic

    monkeypatch.delenv("BLS_SNAPSHOT_REGISTRY_DIR", raising=False)

    with pytest.raises(pydantic.ValidationError):
        Settings(_env_file=None)


def test_specs_db_path_field_exists() -> None:
    """Settings must expose specs_db_path via BLS_SPECS_DB_PATH."""
    s = Settings(
        BLS_SNAPSHOT_REGISTRY_DIR="/tmp/registry",
        BLS_SPECS_DB_PATH="/tmp/specs.db",
    )
    assert s.specs_db_path == "/tmp/specs.db"


def test_specs_db_path_has_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """specs_db_path must have its documented default."""
    monkeypatch.delenv("BLS_SPECS_DB_PATH", raising=False)

    s = Settings(
        BLS_SNAPSHOT_REGISTRY_DIR="/tmp/registry",
        _env_file=None,
    )

    assert s.specs_db_path == "./bls_specs.duckdb"
