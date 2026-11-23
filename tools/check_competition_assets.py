"""Offline preflight for the competition's bundled CAEF demonstration.

Reads only local packaged files; performs no network requests or model loads.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "src" / "cost_intel_app" / "demo_assets" / "caef"
PROJECTS = {"proj_001", "proj_002"}


def main() -> int:
    errors = []
    saved = ASSETS / "predicted_levels.parquet"
    meta = ASSETS / "demo_run.json"
    key = ASSETS / "demo_verification.key"
    for path in (saved, meta, key):
        if not path.is_file():
            errors.append("Missing packaged asset: " + path.name)
    if meta.is_file():
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
            run_id = data["run_id"]
            if data.get("data_origin") not in {
                "synthetic_mock",
                "labeled_test_fixture",
            }:
                errors.append("Bundled run is not marked as synthetic/test fixture")
            for name in (
                "run_manifest.json",
                "working.duckdb",
                "bundles/untuned/model_manifest.json",
                "bundles/untuned/fitted_pipeline_sgd.joblib",
                "bundles/untuned/label_encoder.joblib",
            ):
                if not (ASSETS / run_id / name).is_file():
                    errors.append("Missing run artifact: " + name)
        except (ValueError, KeyError, OSError):
            errors.append("Invalid bundled run metadata")
    if saved.is_file():
        try:
            import polars as pl

            ids = set(
                pl.read_parquet(saved, columns=["parsid"])
                .get_column("parsid")
                .cast(pl.String)
                .to_list()
            )
            if not PROJECTS.issubset(ids):
                errors.append(
                    "Saved mapping does not include both bundled "
                    "demo projects (proj_001 and proj_002)"
                )
        except (ImportError, OSError, ValueError, KeyError) as exc:
            errors.append(
                "Could not verify Parquet project coverage: " + type(exc).__name__
            )
    if errors:
        print("CAEF competition release: NOT READY")
        for error in errors:
            print(" - " + error)
        return 1
    print(
        "CAEF files and demo project IDs: READY (model inference/browser "
        "still require testing)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
