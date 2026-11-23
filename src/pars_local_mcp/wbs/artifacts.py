"""Keep fitted estimator and matching label encoder in a versioned bundle."""

from __future__ import annotations

import hashlib
import hmac
import io
import json
from pathlib import Path

import joblib

LEVELS = tuple(f"level_{i}" for i in range(2, 9))
MODEL_FILE = "fitted_pipeline_sgd.joblib"
ENCODER_FILE = "label_encoder.joblib"
MANIFEST_FILE = "model_manifest.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


MIN_KEY_BYTES = 32


def _check_key(signing_key: bytes) -> bytes:
    if (
        not isinstance(signing_key, (bytes, bytearray))
        or len(signing_key) < MIN_KEY_BYTES
    ):
        raise ValueError(f"signing_key must be at least {MIN_KEY_BYTES} bytes")
    return bytes(signing_key)


def _signature(manifest: dict, signing_key: bytes) -> str:
    """HMAC over the manifest body, excluding the signature field itself."""
    body = {k: v for k, v in manifest.items() if k != "signature"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(signing_key, canonical, hashlib.sha256).hexdigest()


def save_bundle(
    model,
    label_encoder,
    destination,
    *,
    signing_key: bytes,
    run_id=None,
    extra=None,
):
    """Save a model bundle whose manifest is signed with signing_key.

    The key must be stored outside the bundle directory. Without it, a writer to
    the model directory cannot produce a manifest that load_bundle will accept.
    """
    signing_key = _check_key(signing_key)
    if not callable(getattr(model, "predict", None)):
        raise TypeError("Model must implement predict")
    if not callable(getattr(label_encoder, "inverse_transform", None)):
        raise TypeError("Label encoder must implement inverse_transform")
    dest = Path(destination)
    dest.mkdir(parents=True, exist_ok=True)
    model_path, encoder_path = dest / MODEL_FILE, dest / ENCODER_FILE
    joblib.dump(model, model_path)
    joblib.dump(label_encoder, encoder_path)
    manifest = {
        "schema_version": 1,
        "model_file": MODEL_FILE,
        "encoder_file": ENCODER_FILE,
        "levels": list(LEVELS),
        "run_id": run_id,
        "sha256": {
            MODEL_FILE: _sha256(model_path),
            ENCODER_FILE: _sha256(encoder_path),
        },
        "extra": extra or {},
    }
    manifest["signature"] = _signature(manifest, signing_key)
    (dest / MANIFEST_FILE).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return dest


def load_bundle(directory, *, signing_key: bytes):
    """Load a bundle only after its manifest signature verifies.

    joblib/pickle executes code on load, so the signature check must pass before
    any model file is deserialized.
    """
    signing_key = _check_key(signing_key)
    folder = Path(directory)
    manifest = json.loads((folder / MANIFEST_FILE).read_text(encoding="utf-8"))
    claimed = manifest.get("signature")
    if not isinstance(claimed, str) or not hmac.compare_digest(
        claimed, _signature(manifest, signing_key)
    ):
        raise ValueError("Model manifest signature is missing or invalid")
    if manifest.get("levels") != list(LEVELS):
        raise ValueError("Unexpected hierarchy levels in model manifest")
    # Read each file once, verify those exact bytes, and deserialize from memory.
    # Re-opening the path after hashing would let a writer swap the file in between.
    blobs = {name: (folder / name).read_bytes() for name in (MODEL_FILE, ENCODER_FILE)}
    for filename, blob in blobs.items():
        if manifest.get("sha256", {}).get(filename) != hashlib.sha256(blob).hexdigest():
            raise ValueError(f"Artifact checksum mismatch: {filename}")
    model = joblib.load(io.BytesIO(blobs[MODEL_FILE]))
    encoder = joblib.load(io.BytesIO(blobs[ENCODER_FILE]))
    if not callable(getattr(model, "predict", None)):
        raise TypeError("Loaded model has no predict method")
    if not callable(getattr(encoder, "inverse_transform", None)):
        raise TypeError("Loaded encoder has no inverse_transform method")
    return model, encoder, manifest


def load_model_from_run(run_id: str, tracking_uri: str, *, signing_key: bytes):
    """Download a complete bundle logged under model_bundle/ in MLflow."""
    if not run_id or any(ch not in "0123456789abcdef" for ch in run_id.lower()):
        raise ValueError("Expected an MLflow hexadecimal run ID")
    import mlflow

    mlflow.set_tracking_uri(tracking_uri)
    folder = mlflow.artifacts.download_artifacts(
        artifact_uri=f"runs:/{run_id}/model_bundle"
    )
    return load_bundle(folder, signing_key=signing_key)
