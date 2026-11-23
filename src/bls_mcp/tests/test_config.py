"""Settings read BLS_ environment variables and keep documented defaults."""

import pytest
from pydantic import ValidationError

from bls_mcp.config import Settings, get_settings

BLS_VARIABLES = (
    "BLS_SNAPSHOT_REGISTRY_DIR",
    "BLS_SPECS_DB_PATH",
    "BLS_HTTP_TIMEOUT_SECONDS",
    "BLS_HTTP_RETRY_COUNT",
    "BLS_LOG_LEVEL",
)


@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    """Run from an empty directory with no BLS_ variables, so no .env leaks in."""
    monkeypatch.chdir(tmp_path)
    for name in BLS_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    return tmp_path


def test_bls_variables_set_the_matching_fields(clean_env, monkeypatch):
    monkeypatch.setenv("BLS_SNAPSHOT_REGISTRY_DIR", str(clean_env / "registry"))
    monkeypatch.setenv("BLS_HTTP_TIMEOUT_SECONDS", "3.5")
    monkeypatch.setenv("BLS_LOG_LEVEL", "DEBUG")

    settings = get_settings()

    assert settings.snapshot_registry_dir == str(clean_env / "registry")
    assert settings.http_timeout_seconds == 3.5
    assert settings.log_level == "DEBUG"


def test_registry_directory_has_no_default(clean_env):
    with pytest.raises(ValidationError):
        Settings()


def test_unset_fields_take_their_documented_defaults(clean_env, monkeypatch):
    monkeypatch.setenv("BLS_SNAPSHOT_REGISTRY_DIR", str(clean_env))

    settings = Settings(_env_file=None)

    assert settings.http_timeout_seconds == 10.0
    assert settings.http_retry_count == 2
    assert settings.log_level == "INFO"
    assert settings.specs_db_path == "./bls_specs.duckdb"
