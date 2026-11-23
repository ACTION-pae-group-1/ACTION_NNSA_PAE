"""Bundled CAEF results, with optional local prediction from a bundled demo run.

No training, remote requests, or PARS writes are performed.
"""

from __future__ import annotations

import os
import re
from collections import Counter
from pathlib import Path
from threading import Lock
from typing import Any

_PREDICTION_LOCK = Lock()

CAEF_CATEGORY_SLOTS = 8
_LEVELS = tuple(f"level_{n}" for n in range(2, 9))
# Shown with every result so an analyst can tell loaded output from a new run.
SOURCE_SAVED = "Saved predictions"
SOURCE_NEW = "Newly generated predictions"


def empty_caef_summary(message: str = "") -> dict[str, Any]:
    return {
        "state": "unavailable",
        "message": message
        or "No saved CAEF 2.0 predictions are included in this build.",
        "coverage": "",
        "categories": [
            {"visible": False, "label": ""} for _ in range(CAEF_CATEGORY_SLOTS)
        ],
    }


def summarize_predictions(
    rows: list[dict[str, Any]], project_id: str, source: str = SOURCE_SAVED
) -> dict[str, Any]:
    """Aggregate predicted labels, not dollar weights or model confidence."""
    project_rows = [
        row for row in rows if str(row.get("parsid", "")).strip() == project_id
    ]
    if not project_rows:
        return empty_caef_summary("No predictions found for this project.")
    counts: Counter[str] = Counter()
    assigned = 0
    for row in project_rows:
        labels = [str(row.get(level) or "").strip() for level in _LEVELS]
        labels = [
            label
            for label in labels
            if label and label.lower() not in {"null", "none", "0"}
        ]
        if labels:
            assigned += 1
            counts[labels[-1]] += 1
    top = [
        {"visible": True, "label": f"{label}: {count} WBS elements"}
        for label, count in counts.most_common(CAEF_CATEGORY_SLOTS)
    ]
    top.extend(
        {"visible": False, "label": ""} for _ in range(CAEF_CATEGORY_SLOTS - len(top))
    )
    return {
        "state": "loaded",
        "message": "",
        "coverage": (
            f"{source}: {assigned} of {len(project_rows)} WBS elements classified"
        ),
        "categories": top,
    }


def read_caef_summary(
    filename: str, project_id: str, source: str = SOURCE_SAVED
) -> dict[str, Any]:
    """Read one explicitly configured local Parquet; never discover remote files."""
    if not filename.strip():
        return empty_caef_summary()
    path = Path(filename).expanduser()
    if not path.is_file():
        return empty_caef_summary("Configured CAEF prediction file is unavailable.")
    if path.stat().st_size > 50_000_000:
        return empty_caef_summary("CAEF file exceeds the 50 MB review limit.")
    try:
        import polars as pl

        frame = pl.read_parquet(path, columns=["parsid", *_LEVELS])
        return summarize_predictions(frame.to_dicts(), project_id, source)
    except Exception:  # Corrupt or incompatible local artifact: no path/data in UI.
        return empty_caef_summary("Could not read the completed CAEF predictions.")


# All demo paths are relative to the installed application. Developers can still
# override the prediction file for controlled local testing, but judges cannot
# be required to configure environment variables.
_DEMO_DIR = Path(__file__).resolve().parent / "demo_assets" / "caef"


def saved_prediction_path() -> str:
    """Find included saved results without manual configuration."""
    override = os.environ.get("CAEF_PREDICTIONS_FILE", "").strip()
    if override:
        return override
    file = _DEMO_DIR / "predicted_levels.parquet"
    return str(file) if file.is_file() else ""


def _bundled_run() -> tuple[Path, str, Path] | None:
    """Return a pre-approved synthetic demo run and its demo-only key."""
    manifest_file = _DEMO_DIR / "demo_run.json"
    key_file = _DEMO_DIR / "demo_verification.key"
    if not manifest_file.is_file() or not key_file.is_file():
        return None
    try:
        import json

        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        run_id = manifest.get("run_id", "")
        # Explicitly forbid real or unlabelled PARS data in distributable assets.
        if manifest.get("data_origin") not in {
            "synthetic_mock",
            "labeled_test_fixture",
        }:
            return None
        if not re.fullmatch(r"r[0-9a-f]{12}", run_id):
            return None
        if manifest.get("stages", {}).get("tune_train", {}).get("status") != "ok":
            return None
        if not (_DEMO_DIR / run_id / "run_manifest.json").is_file():
            return None
        return _DEMO_DIR, run_id, key_file
    except (ValueError, OSError):
        return None


def run_model_for_project(project_id: str) -> dict[str, Any]:
    """Explicit prediction via an existing signed training run; no retraining.

    This operation overwrites only that run's local prediction artifact.
    The pipeline's signing-key validation must succeed before model deserialization.
    """
    if (
        not isinstance(project_id, str)
        or not project_id.strip()
        or len(project_id) > 128
    ):
        return empty_caef_summary("Choose a PARS project first.")
    bundled = _bundled_run()
    if bundled is None:
        return empty_caef_summary(
            "The packaged CAEF model is not included. "
            "Saved results remain available if provided."
        )
    runs_root, run_id, key_path = bundled
    if key_path.stat().st_size < 32 or key_path.stat().st_size > 4096:
        return empty_caef_summary("The demo model verification file is invalid.")
    try:
        signing_key = key_path.read_bytes()
        # Reuse the model's signed-bundle verification and prediction stage.
        from pars_local_mcp.wbs_port.pipeline import stage_predict

        if not _PREDICTION_LOCK.acquire(blocking=False):
            return empty_caef_summary("A CAEF prediction is already running.")
        try:
            stage_predict(Path(runs_root), run_id, signing_key=signing_key)
        finally:
            _PREDICTION_LOCK.release()
        prediction_file = (
            Path(runs_root) / run_id / "predictions" / "predicted_levels.parquet"
        )
        return read_caef_summary(str(prediction_file), project_id, SOURCE_NEW)
    except Exception:
        # No sensitive local paths or model internals in the UI.
        return empty_caef_summary(
            "Prediction did not complete. Check the packaged demonstration model "
            "and its local logs."
        )
