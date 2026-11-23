from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings for the BLS Cost Escalation MCP server.

    This configuration incorporates both the core BLS requirements and
    the transport settings required for MCP deployment.
    """

    # --- BLS Service Configuration ---
    bls_api_key: str | None = Field(default=None, alias="BLS_API_KEY")
    snapshot_registry_dir: str = Field(
        alias="BLS_SNAPSHOT_REGISTRY_DIR",
    )
    specs_db_path: str = Field(
        default="./bls_specs.duckdb",
        alias="BLS_SPECS_DB_PATH",
    )
    http_timeout_seconds: float = Field(
        default=10.0,
        alias="BLS_HTTP_TIMEOUT_SECONDS",
    )
    http_retry_count: int = Field(default=2, alias="BLS_HTTP_RETRY_COUNT")
    bls_user_agent: str | None = Field(
        default=None,
        alias="BLS_USER_AGENT",
    )
    weight_tolerance: float = Field(
        default=1e-4,
        alias="BLS_WEIGHT_TOLERANCE",
    )
    log_level: str = Field(default="INFO", alias="BLS_LOG_LEVEL")

    # --- MCP Transport Configuration ---
    mcp_transport: str = "stdio"
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="BLS_",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )


def get_settings() -> Settings:
    """Return a settings instance configured from environment variables."""
    return Settings()  # type: ignore[call-arg]
