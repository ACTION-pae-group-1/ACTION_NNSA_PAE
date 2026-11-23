"""Configuration for PARS MCP server.

Provides settings for database paths, model directories, and runtime options.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings

# All default inputs and outputs live inside this repository.
REPO_DATA_DIR = Path(__file__).resolve().parent / "data"


def _refuse_shared_drive(value):
    text = str(value)
    is_unc = text.startswith("\\\\") or text.startswith("//")
    is_o_drive = text[:2].upper() == "O:"
    if is_unc or is_o_drive:
        raise ValueError(
            f"Shared-drive path not allowed: {text}. Use a path inside the repository."
        )
    return value


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    database_path: Path = Field(
        default=REPO_DATA_DIR / "wbs.duckdb",
        description="Path to DuckDB database file",
    )

    model_dir: Path = Field(
        default=REPO_DATA_DIR / "models",
        description="Directory for trained models",
    )

    model_signing_key_path: Path = Field(
        default=REPO_DATA_DIR / "keys" / "model_signing.key",
        description="Secret used to sign model manifests. Must be outside model_dir.",
    )

    @field_validator(
        "database_path",
        "model_dir",
        "model_signing_key_path",
        "wbs_runs_dir",
        "wbs_source_db",
        mode="before",
    )
    @classmethod
    def _no_shared_drive(cls, value):
        return _refuse_shared_drive(value)

    wbs_runs_dir: Path = Field(
        default=REPO_DATA_DIR / "wbs_runs",
        description=(
            "Run directory for WBS pipeline artifacts (working DB, bundles, "
            "predictions, logs)"
        ),
    )

    wbs_source_db: Path = Field(
        default=REPO_DATA_DIR / "mock_pars_full.duckdb",
        description=(
            "Source database for the WBS pipeline. The default is the bundled "
            "synthetic mock, which passes the input contract."
        ),
    )


def get_settings() -> Settings:
    """Get application settings instance.

    Returns:
        Settings instance with values from environment or defaults
    """
    return Settings()
