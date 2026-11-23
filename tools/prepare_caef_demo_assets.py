"""Package an EXISTING synthetic CAEF model run for the offline competition app.

Local only: reads a run directory and demo key, validates manifests/checksums,
then copies limited run assets into src/cost_intel_app/demo_assets/caef.
No network, no dependency installation, no model execution or PARS writes.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import shutil
import sys
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
DEST = APP_ROOT / "src" / "cost_intel_app" / "demo_assets" / "caef"
ALLOWED_ORIGINS = {"synthetic_mock", "labeled_test_fixture"}
MAX_FILE = 150 * 1024 * 1024
MAX_TOTAL = 350 * 1024 * 1024


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run",
        type=Path,
        required=True,
        help="Existing synthetic trained WBS run folder",
    )
    parser.add_argument(
        "--demo-key",
        type=Path,
        required=True,
        help="DEDICATED synthetic-demo HMAC signing key (never production)",
    )
    parser.add_argument(
        "--confirm-synthetic-only",
        action="store_true",
        help="Confirm no restricted data / production key",
    )
    args = parser.parse_args()
    if not args.confirm_synthetic_only:
        parser.error(
            "You must explicitly confirm all assets and the signing "
            "key are demonstration-only."
        )
    run = args.run.resolve(strict=True)
    key_path = args.demo_key.resolve(strict=True)
    if run.is_symlink() or key_path.is_symlink():
        parser.error("Symlinks are not accepted.")
    manifest = json.loads((run / "run_manifest.json").read_text(encoding="utf-8"))
    rid = manifest.get("run_id", "")
    if (
        rid != run.name
        or len(rid) != 13
        or not rid.startswith("r")
        or any(c not in "0123456789abcdef" for c in rid[1:])
    ):
        parser.error(
            "Expected a run directory named r "
            "followed by 12 lowercase hexadecimal digits"
        )
    if manifest.get("data_origin") not in ALLOWED_ORIGINS:
        parser.error("Only labelled synthetic-origin runs are distributable")
    if manifest.get("stages", {}).get("tune_train", {}).get("status") != "ok":
        parser.error("Run has no completed trained model")
    source_bundle = run / "bundles" / "untuned"
    signed_manifest_path = source_bundle / "model_manifest.json"
    bundle_manifest = json.loads(signed_manifest_path.read_text(encoding="utf-8"))
    key = key_path.read_bytes()
    if not 32 <= len(key) <= 4096:
        parser.error("Demonstration signing key must be 32 to 4096 bytes")
    body = {k: v for k, v in bundle_manifest.items() if k != "signature"}
    payload = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    expected = hmac.new(key, payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, bundle_manifest.get("signature", "")):
        parser.error("The demonstration key cannot verify the model manifest")
    model_files = ("fitted_pipeline_sgd.joblib", "label_encoder.joblib")
    for name in model_files:
        source = source_bundle / name
        if hashlib.sha256(source.read_bytes()).hexdigest() != bundle_manifest.get(
            "sha256", {}
        ).get(name):
            parser.error("Model checksum does not match for " + name)
    required = [
        run / "run_manifest.json",
        run / "working.duckdb",
        signed_manifest_path,
        *(source_bundle / name for name in model_files),
    ]
    pred = run / "predictions" / "predicted_levels.parquet"
    if pred.is_file():
        required.append(pred)
    for p in required:
        if not p.is_file() or p.is_symlink() or p.stat().st_size > MAX_FILE:
            parser.error("Missing/unsafe/oversized required artifact: " + p.name)
    if sum(p.stat().st_size for p in required) > MAX_TOTAL:
        parser.error("Packaged CAEF assets exceed the configured size ceiling")
    target = DEST / rid
    if target.exists() or (DEST / "demo_run.json").exists():
        parser.error(
            "Assets already packaged; review and remove the old demo package manually"
        )
    for file in required:
        out = target / file.relative_to(run)
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(file, out)
    shutil.copyfile(key_path, DEST / "demo_verification.key")
    (DEST / "demo_run.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    if pred.is_file():
        shutil.copyfile(pred, DEST / "predicted_levels.parquet")
    print("Packaged signed synthetic CAEF demo run", rid)
    if not pred.is_file():
        print(
            "No prior prediction Parquet. Run model once, "
            "then bundle its completed result."
        )
        return 2
    print(
        "WARNING: The included DEMO signing key is distributable, "
        "not production secure."
    )
    print("Review working.duckdb and all files for restricted content before sharing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
