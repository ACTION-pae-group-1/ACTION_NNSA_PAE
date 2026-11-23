"""Thin transport launcher; server assembly remains in server.py."""

from __future__ import annotations

import os
import sys
from importlib import import_module
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from bls_mcp.server import create_server


class LaunchSettings(BaseSettings):
    """Transport configuration, separate from BLS service configuration."""

    mcp_transport: Literal["stdio", "streamable-http"] = "stdio"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = Field(default=8000, ge=1, le=65535)
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


def _preload_windows_stdio_numeric_libraries() -> None:
    """Initialize OpenBLAS-backed native modules before stdio reads stdin.

    On Windows, first-loading NumPy/SciPy while the MCP stdio transport has a
    pending pipe read may deadlock in the native DLL loader.  Import on the
    main thread, before starting the stdio transport; do not change the
    process-wide BLAS thread count or disable certificate verification.
    See modelcontextprotocol/python-sdk issue #2832.
    """
    if sys.platform == "win32":
        import_module("numpy.core.multiarray")
        import_module("scipy.sparse.linalg")


def main() -> None:
    """Use a platform port first, explicit HTTP second, otherwise stdio."""
    settings = LaunchSettings()
    platform_port = os.getenv("DATABRICKS_APP_PORT") or os.getenv("PORT")
    if platform_port:
        port = int(platform_port)
        if not 1 <= port <= 65535:
            raise ValueError("Platform port must be between 1 and 65535")
        create_server().run(transport="http", host="0.0.0.0", port=port)
    elif settings.mcp_transport == "streamable-http":
        create_server().run(
            transport="http", host=settings.mcp_host, port=settings.mcp_port
        )
    else:
        _preload_windows_stdio_numeric_libraries()
        create_server().run(transport="stdio")


if __name__ == "__main__":
    main()
