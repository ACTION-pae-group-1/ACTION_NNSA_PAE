"""Tests for config.py."""


def test_get_settings_returns_instance():
    """Test that get_settings() returns a Settings instance."""
    from pars_local_mcp.config import Settings, get_settings

    settings = get_settings()
    assert isinstance(settings, Settings)


def test_settings_has_database_path():
    """Test that Settings has database_path attribute."""
    from pars_local_mcp.config import get_settings

    settings = get_settings()
    assert hasattr(settings, "database_path")
    assert settings.database_path is not None
