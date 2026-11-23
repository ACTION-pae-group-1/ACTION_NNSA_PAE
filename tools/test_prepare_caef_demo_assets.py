"""Tests for the CAEF demo-asset packaging tool's safety and validation gates."""

from __future__ import annotations

import hashlib
import hmac
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import prepare_caef_demo_assets as pcda  # noqa: E402


def _run(monkeypatch, argv):
    monkeypatch.setattr(sys, "argv", ["prepare_caef_demo_assets.py", *argv])


def test_refuses_without_confirm_synthetic_only_flag(tmp_path, monkeypatch, capsys):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    key_path = tmp_path / "demo.key"
    key_path.write_bytes(b"k" * 32)
    _run(monkeypatch, ["--run", str(run_dir), "--demo-key", str(key_path)])
    with pytest.raises(SystemExit) as exc:
        pcda.main()
    assert exc.value.code == 2
    assert "confirm" in capsys.readouterr().err.lower()


def test_refuses_symlinked_run_directory(tmp_path, monkeypatch, capsys):
    real_dir = tmp_path / "real_run"
    real_dir.mkdir()
    link_dir = tmp_path / "r0123456789ab"
    try:
        link_dir.symlink_to(real_dir, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation not permitted in this environment")
    key_path = tmp_path / "demo.key"
    key_path.write_bytes(b"k" * 32)
    _run(
        monkeypatch,
        [
            "--run",
            str(link_dir),
            "--demo-key",
            str(key_path),
            "--confirm-synthetic-only",
        ],
    )
    with pytest.raises(SystemExit) as exc:
        pcda.main()
    assert exc.value.code == 2
    assert "symlink" in capsys.readouterr().err.lower()


def test_refuses_run_directory_name_not_matching_run_id(tmp_path, monkeypatch, capsys):
    run_dir = tmp_path / "not_a_valid_run_name"
    run_dir.mkdir()
    (run_dir / "run_manifest.json").write_text(
        json.dumps({"run_id": "r0123456789ab", "data_origin": "synthetic_mock"}),
        encoding="utf-8",
    )
    key_path = tmp_path / "demo.key"
    key_path.write_bytes(b"k" * 32)
    _run(
        monkeypatch,
        [
            "--run",
            str(run_dir),
            "--demo-key",
            str(key_path),
            "--confirm-synthetic-only",
        ],
    )
    with pytest.raises(SystemExit) as exc:
        pcda.main()
    assert exc.value.code == 2
    assert "hexadecimal" in capsys.readouterr().err.lower()


def test_refuses_non_synthetic_data_origin(tmp_path, monkeypatch, capsys):
    run_id = "r0123456789ab"
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    (run_dir / "run_manifest.json").write_text(
        json.dumps({"run_id": run_id, "data_origin": "production"}),
        encoding="utf-8",
    )
    key_path = tmp_path / "demo.key"
    key_path.write_bytes(b"k" * 32)
    _run(
        monkeypatch,
        [
            "--run",
            str(run_dir),
            "--demo-key",
            str(key_path),
            "--confirm-synthetic-only",
        ],
    )
    with pytest.raises(SystemExit) as exc:
        pcda.main()
    assert exc.value.code == 2
    assert "synthetic-origin" in capsys.readouterr().err.lower()


def test_refuses_undersized_demo_key(tmp_path, monkeypatch, capsys):
    run_id = "r0123456789ab"
    run_dir = tmp_path / run_id
    (run_dir / "bundles" / "untuned").mkdir(parents=True)
    (run_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "data_origin": "synthetic_mock",
                "stages": {"tune_train": {"status": "ok"}},
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "bundles" / "untuned" / "model_manifest.json").write_text(
        "{}", encoding="utf-8"
    )
    key_path = tmp_path / "demo.key"
    key_path.write_bytes(b"short")
    _run(
        monkeypatch,
        [
            "--run",
            str(run_dir),
            "--demo-key",
            str(key_path),
            "--confirm-synthetic-only",
        ],
    )
    with pytest.raises(SystemExit) as exc:
        pcda.main()
    assert exc.value.code == 2
    assert "32 to 4096 bytes" in capsys.readouterr().err


def test_packages_a_valid_signed_synthetic_run(tmp_path, monkeypatch, capsys):
    run_id = "r0123456789ab"
    run_dir = tmp_path / run_id
    bundle_dir = run_dir / "bundles" / "untuned"
    bundle_dir.mkdir(parents=True)
    (run_dir / "working.duckdb").write_bytes(b"db")

    key = b"k" * 32
    pipeline_bytes = b"pipeline-bytes"
    encoder_bytes = b"encoder-bytes"
    body = {
        "note": "fitted model manifest",
        "sha256": {
            "fitted_pipeline_sgd.joblib": hashlib.sha256(pipeline_bytes).hexdigest(),
            "label_encoder.joblib": hashlib.sha256(encoder_bytes).hexdigest(),
        },
    }
    payload = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = hmac.new(key, payload, hashlib.sha256).hexdigest()
    manifest = {**body, "signature": signature}
    (bundle_dir / "model_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    (bundle_dir / "fitted_pipeline_sgd.joblib").write_bytes(pipeline_bytes)
    (bundle_dir / "label_encoder.joblib").write_bytes(encoder_bytes)

    (run_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "data_origin": "synthetic_mock",
                "stages": {"tune_train": {"status": "ok"}},
            }
        ),
        encoding="utf-8",
    )

    key_path = tmp_path / "demo.key"
    key_path.write_bytes(key)

    dest = tmp_path / "dest"
    monkeypatch.setattr(pcda, "DEST", dest)
    _run(
        monkeypatch,
        [
            "--run",
            str(run_dir),
            "--demo-key",
            str(key_path),
            "--confirm-synthetic-only",
        ],
    )

    exit_code = pcda.main()

    # No predictions/ directory was supplied, so the tool packages the signed
    # model but reports it still needs a completed prediction run (exit 2).
    assert exit_code == 2
    assert (dest / run_id / "run_manifest.json").is_file()
    assert (dest / "demo_run.json").is_file()
    assert (dest / "demo_verification.key").read_bytes() == key
