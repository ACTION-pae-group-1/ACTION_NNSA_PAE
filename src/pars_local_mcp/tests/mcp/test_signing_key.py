from __future__ import annotations

import pytest

from pars_local_mcp.config import Settings


def test_signing_key_inside_model_dir_is_refused(tmp_path):
    from pars_local_mcp.mcp.tools import _model_signing_key

    settings = Settings(
        database_path=tmp_path / "x.duckdb",
        model_dir=tmp_path / "models",
        model_signing_key_path=tmp_path / "models" / "model_signing.key",
    )
    with pytest.raises(ValueError, match="outside model_dir"):
        _model_signing_key(settings)


def test_signing_key_created_once_and_reused(tmp_path):
    from pars_local_mcp.mcp.tools import _model_signing_key

    settings = Settings(
        database_path=tmp_path / "x.duckdb",
        model_dir=tmp_path / "models",
        model_signing_key_path=tmp_path / "keys" / "model_signing.key",
    )
    first = _model_signing_key(settings)
    second = _model_signing_key(settings)
    assert len(first) == 32
    assert first == second


def test_signing_key_via_junction_into_model_dir_is_refused(tmp_path):
    import subprocess

    from pars_local_mcp.mcp.tools import _model_signing_key

    models = tmp_path / "models"
    models.mkdir()
    link = tmp_path / "jlink"
    try:
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(models)],
            capture_output=True,
        )
    except FileNotFoundError:
        pytest.skip("junction creation requires Windows cmd")
    if result.returncode != 0:
        pytest.skip("junction creation not available")

    settings = Settings(
        database_path=tmp_path / "x.duckdb",
        model_dir=models,
        model_signing_key_path=link / "model_signing.key",
    )
    with pytest.raises(ValueError, match="outside model_dir"):
        _model_signing_key(settings)
