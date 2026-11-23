"""Tests for the offline CAEF competition-release preflight check."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_competition_assets as cca  # noqa: E402


def test_not_ready_when_all_packaged_files_are_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(cca, "ASSETS", tmp_path)
    assert cca.main() == 1


def test_not_ready_reports_each_missing_asset(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cca, "ASSETS", tmp_path)
    cca.main()
    out = capsys.readouterr().out
    assert "NOT READY" in out
    assert "predicted_levels.parquet" in out
    assert "demo_run.json" in out
    assert "demo_verification.key" in out


def test_not_ready_when_run_is_not_marked_synthetic(tmp_path, monkeypatch):
    monkeypatch.setattr(cca, "ASSETS", tmp_path)
    (tmp_path / "demo_verification.key").write_bytes(b"k" * 32)
    (tmp_path / "demo_run.json").write_text(
        json.dumps({"run_id": "r0123456789ab", "data_origin": "production"}),
        encoding="utf-8",
    )
    assert cca.main() == 1


def test_not_ready_when_run_artifacts_are_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(cca, "ASSETS", tmp_path)
    (tmp_path / "demo_verification.key").write_bytes(b"k" * 32)
    (tmp_path / "demo_run.json").write_text(
        json.dumps({"run_id": "r0123456789ab", "data_origin": "synthetic_mock"}),
        encoding="utf-8",
    )
    # Intentionally do not create the r0123456789ab/ run directory.
    exit_code = cca.main()
    assert exit_code == 1


def test_ready_when_all_assets_and_run_artifacts_are_present(tmp_path, monkeypatch):
    monkeypatch.setattr(cca, "ASSETS", tmp_path)
    run_id = "r0123456789ab"
    run_dir = tmp_path / run_id
    (run_dir / "bundles" / "untuned").mkdir(parents=True)
    (run_dir / "run_manifest.json").write_text("{}", encoding="utf-8")
    (run_dir / "working.duckdb").write_bytes(b"")
    (run_dir / "bundles" / "untuned" / "model_manifest.json").write_text(
        "{}", encoding="utf-8"
    )
    (run_dir / "bundles" / "untuned" / "fitted_pipeline_sgd.joblib").write_bytes(b"")
    (run_dir / "bundles" / "untuned" / "label_encoder.joblib").write_bytes(b"")
    (tmp_path / "demo_verification.key").write_bytes(b"k" * 32)
    (tmp_path / "demo_run.json").write_text(
        json.dumps({"run_id": run_id, "data_origin": "synthetic_mock"}),
        encoding="utf-8",
    )

    import polars as pl

    pl.DataFrame({"parsid": ["proj_001", "proj_002"]}).write_parquet(
        tmp_path / "predicted_levels.parquet"
    )

    assert cca.main() == 0
