"""Tests for model artifact bundling and checksums."""

from __future__ import annotations

import hashlib
import json

import joblib
import polars as pl
import pytest

from pars_local_mcp.wbs.artifacts import (
    ENCODER_FILE,
    LEVELS,
    MANIFEST_FILE,
    MODEL_FILE,
    _sha256,
    _signature,
    load_bundle,
    save_bundle,
)
from pars_local_mcp.wbs.labels import MultiColumnLabelEncoder

pytestmark = pytest.mark.slow

KEY = b"test-signing-key-0123456789abcdef"


def _fitted_encoder():
    encoder = MultiColumnLabelEncoder()
    df = pl.DataFrame(
        {
            "level_2": ["01"],
            "level_3": ["01.01"],
            "level_4": ["01.01.01"],
            "level_5": ["01.01.01.01"],
            "level_6": [""],
            "level_7": [""],
            "level_8": [""],
        }
    )
    return encoder.fit(df)


class MockModel:
    """Mock model with predict method."""

    def predict(self, texts):
        import numpy as np

        return np.zeros((len(texts), 7), dtype=object)


class TestBundleSaving:
    """Test save_bundle function."""

    def test_save_bundle_creates_files(self, temp_dir):
        """Test save_bundle creates all required files."""
        model = MockModel()
        encoder = MultiColumnLabelEncoder()

        # Fit encoder with minimal data
        df = pl.DataFrame(
            {
                "level_2": ["01", "02"],
                "level_3": ["01.01", "02.01"],
                "level_4": ["01.01.01", "02.01.01"],
                "level_5": ["01.01.01.01", "02.01.01.01"],
                "level_6": ["", ""],
                "level_7": ["", ""],
                "level_8": ["", ""],
            }
        )
        encoder.fit(df)

        destination = save_bundle(model, encoder, temp_dir, signing_key=KEY)

        assert (destination / MODEL_FILE).exists()
        assert (destination / ENCODER_FILE).exists()
        assert (destination / MANIFEST_FILE).exists()

    def test_save_bundle_creates_valid_manifest(self, temp_dir):
        """Test save_bundle creates a valid manifest JSON."""
        model = MockModel()
        encoder = MultiColumnLabelEncoder()

        df = pl.DataFrame(
            {
                "level_2": ["01", "02"],
                "level_3": ["01.01", "02.01"],
                "level_4": ["01.01.01", "02.01.01"],
                "level_5": ["01.01.01.01", "02.01.01.01"],
                "level_6": ["", ""],
                "level_7": ["", ""],
                "level_8": ["", ""],
            }
        )
        encoder.fit(df)

        save_bundle(model, encoder, temp_dir, run_id="test_run_123", signing_key=KEY)

        manifest_path = temp_dir / MANIFEST_FILE
        with open(manifest_path) as f:
            manifest = json.load(f)

        assert manifest["schema_version"] == 1
        assert manifest["model_file"] == MODEL_FILE
        assert manifest["encoder_file"] == ENCODER_FILE
        assert manifest["levels"] == list(LEVELS)
        assert manifest["run_id"] == "test_run_123"
        assert "sha256" in manifest
        assert MODEL_FILE in manifest["sha256"]
        assert ENCODER_FILE in manifest["sha256"]

    def test_save_bundle_with_extra_metadata(self, temp_dir):
        """Test save_bundle includes extra metadata."""
        model = MockModel()
        encoder = MultiColumnLabelEncoder()

        df = pl.DataFrame(
            {
                "level_2": ["01"],
                "level_3": ["01.01"],
                "level_4": ["01.01.01"],
                "level_5": ["01.01.01.01"],
                "level_6": [""],
                "level_7": [""],
                "level_8": [""],
            }
        )
        encoder.fit(df)

        extra = {"cv_f1": 0.95, "test_f1": 0.92}
        save_bundle(model, encoder, temp_dir, extra=extra, signing_key=KEY)

        manifest_path = temp_dir / MANIFEST_FILE
        with open(manifest_path) as f:
            manifest = json.load(f)

        assert manifest["extra"] == extra

    def test_save_bundle_requires_predict_method(self, temp_dir):
        """Test save_bundle rejects model without predict method."""

        class BadModel:
            pass

        encoder = MultiColumnLabelEncoder()
        df = pl.DataFrame(
            {
                "level_2": ["01"],
                "level_3": ["01.01"],
                "level_4": ["01.01.01"],
                "level_5": ["01.01.01.01"],
                "level_6": [""],
                "level_7": [""],
                "level_8": [""],
            }
        )
        encoder.fit(df)

        with pytest.raises(TypeError, match="must implement predict"):
            save_bundle(BadModel(), encoder, temp_dir, signing_key=KEY)

    def test_save_bundle_requires_inverse_transform(self, temp_dir):
        """Test save_bundle rejects encoder without inverse_transform."""

        class BadEncoder:
            pass

        with pytest.raises(TypeError, match="must implement inverse_transform"):
            save_bundle(MockModel(), BadEncoder(), temp_dir, signing_key=KEY)

    def test_save_bundle_creates_parent_directories(self, temp_dir):
        """Test save_bundle creates parent directories if missing."""
        model = MockModel()
        encoder = MultiColumnLabelEncoder()

        df = pl.DataFrame(
            {
                "level_2": ["01"],
                "level_3": ["01.01"],
                "level_4": ["01.01.01"],
                "level_5": ["01.01.01.01"],
                "level_6": [""],
                "level_7": [""],
                "level_8": [""],
            }
        )
        encoder.fit(df)

        nested_path = temp_dir / "deep" / "nested" / "path"
        destination = save_bundle(model, encoder, nested_path, signing_key=KEY)

        assert destination.exists()
        assert (destination / MODEL_FILE).exists()


class TestBundleLoading:
    """Test load_bundle function."""

    def test_load_bundle_returns_tuple(self, temp_dir):
        """Test load_bundle returns (model, encoder, manifest)."""
        model = MockModel()
        encoder = MultiColumnLabelEncoder()

        df = pl.DataFrame(
            {
                "level_2": ["01"],
                "level_3": ["01.01"],
                "level_4": ["01.01.01"],
                "level_5": ["01.01.01.01"],
                "level_6": [""],
                "level_7": [""],
                "level_8": [""],
            }
        )
        encoder.fit(df)

        save_bundle(model, encoder, temp_dir, signing_key=KEY)
        loaded_model, loaded_encoder, manifest = load_bundle(temp_dir, signing_key=KEY)

        assert callable(getattr(loaded_model, "predict", None))
        assert callable(getattr(loaded_encoder, "inverse_transform", None))
        assert isinstance(manifest, dict)
        assert "levels" in manifest

    def test_load_bundle_verifies_checksums(self, temp_dir):
        """Test load_bundle validates SHA256 checksums."""
        model = MockModel()
        encoder = MultiColumnLabelEncoder()

        df = pl.DataFrame(
            {
                "level_2": ["01"],
                "level_3": ["01.01"],
                "level_4": ["01.01.01"],
                "level_5": ["01.01.01.01"],
                "level_6": [""],
                "level_7": [""],
                "level_8": [""],
            }
        )
        encoder.fit(df)

        save_bundle(model, encoder, temp_dir, signing_key=KEY)

        # Corrupt the model file
        model_path = temp_dir / MODEL_FILE
        with open(model_path, "ab") as f:
            f.write(b"corruption")

        with pytest.raises(ValueError, match="checksum mismatch"):
            load_bundle(temp_dir, signing_key=KEY)

    def test_load_bundle_validates_hierarchy_levels(self, temp_dir):
        """Test load_bundle rejects bundle with wrong hierarchy levels."""
        model = MockModel()
        encoder = MultiColumnLabelEncoder()

        df = pl.DataFrame(
            {
                "level_2": ["01"],
                "level_3": ["01.01"],
                "level_4": ["01.01.01"],
                "level_5": ["01.01.01.01"],
                "level_6": [""],
                "level_7": [""],
                "level_8": [""],
            }
        )
        encoder.fit(df)

        save_bundle(model, encoder, temp_dir, signing_key=KEY)

        # Corrupt the manifest levels
        manifest_path = temp_dir / MANIFEST_FILE
        with open(manifest_path) as f:
            manifest = json.load(f)
        manifest["levels"] = ["level_2", "level_3", "level_4"]  # Wrong
        manifest["signature"] = _signature(
            manifest, KEY
        )  # re-sign: test the levels check
        with open(manifest_path, "w") as f:
            json.dump(manifest, f)

        with pytest.raises(ValueError, match="Unexpected hierarchy levels"):
            load_bundle(temp_dir, signing_key=KEY)

    def test_load_bundle_missing_model_file_raises(self, temp_dir):
        """Test load_bundle raises when model file is missing."""
        model = MockModel()
        encoder = MultiColumnLabelEncoder()

        df = pl.DataFrame(
            {
                "level_2": ["01"],
                "level_3": ["01.01"],
                "level_4": ["01.01.01"],
                "level_5": ["01.01.01.01"],
                "level_6": [""],
                "level_7": [""],
                "level_8": [""],
            }
        )
        encoder.fit(df)

        save_bundle(model, encoder, temp_dir, signing_key=KEY)

        # Remove model file
        (temp_dir / MODEL_FILE).unlink()

        # Should raise FileNotFoundError or ValueError during checksum check
        with pytest.raises((FileNotFoundError, ValueError)):
            load_bundle(temp_dir, signing_key=KEY)

    def test_load_bundle_missing_manifest_raises(self, temp_dir):
        """Test load_bundle raises when manifest is missing."""
        # Create minimal bundle without manifest
        model_path = temp_dir / MODEL_FILE
        encoder_path = temp_dir / ENCODER_FILE
        joblib.dump(MockModel(), model_path)
        joblib.dump(MultiColumnLabelEncoder(), encoder_path)

        with pytest.raises(FileNotFoundError):
            load_bundle(temp_dir, signing_key=KEY)

    def test_load_bundle_roundtrip_fidelity(self, temp_dir):
        """Test save -> load preserves model and encoder."""
        model = MockModel()
        encoder = MultiColumnLabelEncoder()

        df = pl.DataFrame(
            {
                "level_2": ["01", "02"],
                "level_3": ["01.01", "02.01"],
                "level_4": ["01.01.01", "02.01.01"],
                "level_5": ["01.01.01.01", "02.01.01.01"],
                "level_6": ["", ""],
                "level_7": ["", ""],
                "level_8": ["", ""],
            }
        )
        encoder.fit(df)

        save_bundle(model, encoder, temp_dir, signing_key=KEY)
        loaded_model, loaded_encoder, _ = load_bundle(temp_dir, signing_key=KEY)

        # Test predictions work
        import numpy as np

        test_input = np.array(["test"])
        result1 = model.predict(test_input)
        result2 = loaded_model.predict(test_input)
        assert result1.shape == result2.shape

    def test_load_bundle_validates_predict_method(self, temp_dir):
        """Test load_bundle raises if loaded model has no predict method."""
        # Create a bundle with something that isn't a valid model
        encoder = MultiColumnLabelEncoder()
        df = pl.DataFrame(
            {
                "level_2": ["01"],
                "level_3": ["01.01"],
                "level_4": ["01.01.01"],
                "level_5": ["01.01.01.01"],
                "level_6": [""],
                "level_7": [""],
                "level_8": [""],
            }
        )
        encoder.fit(df)

        model_path = temp_dir / MODEL_FILE
        encoder_path = temp_dir / ENCODER_FILE

        (model_path).write_text("not a model")
        joblib.dump(encoder, encoder_path)

        # Create manifest
        manifest = {
            "schema_version": 1,
            "model_file": MODEL_FILE,
            "encoder_file": ENCODER_FILE,
            "levels": list(LEVELS),
            "sha256": {
                MODEL_FILE: hashlib.sha256(
                    (temp_dir / MODEL_FILE).read_bytes()
                ).hexdigest(),
                ENCODER_FILE: hashlib.sha256(
                    (temp_dir / ENCODER_FILE).read_bytes()
                ).hexdigest(),
            },
        }
        manifest["signature"] = _signature(manifest, KEY)
        (temp_dir / MANIFEST_FILE).write_text(json.dumps(manifest))

        # This should fail during validation when trying to load the bad model
        # May raise various errors: EOFError, KeyError, TypeError, AttributeError
        with pytest.raises((TypeError, AttributeError, EOFError, KeyError)):
            load_bundle(temp_dir, signing_key=KEY)


class TestSha256Computation:
    """Test SHA256 checksum computation."""

    def test_sha256_consistent(self, temp_dir):
        """Test _sha256 produces consistent results."""
        filepath = temp_dir / "test.bin"
        filepath.write_bytes(b"test data")

        hash1 = _sha256(filepath)
        hash2 = _sha256(filepath)

        assert hash1 == hash2

    def test_sha256_different_content(self, temp_dir):
        """Test _sha256 differs for different content."""
        file1 = temp_dir / "file1.bin"
        file2 = temp_dir / "file2.bin"
        file1.write_bytes(b"content 1")
        file2.write_bytes(b"content 2")

        assert _sha256(file1) != _sha256(file2)

    def test_sha256_format(self, temp_dir):
        """Test _sha256 returns valid hex string."""
        filepath = temp_dir / "test.bin"
        filepath.write_bytes(b"test")

        hash_val = _sha256(filepath)
        assert isinstance(hash_val, str)
        assert len(hash_val) == 64  # SHA256 hex is 64 characters
        assert all(c in "0123456789abcdef" for c in hash_val)


class TestArtifactIntegration:
    """Integration tests for artifact bundling."""

    def test_complete_bundle_workflow(self, temp_dir):
        """Test complete save -> load workflow."""
        # Create and fit model and encoder
        model = MockModel()
        encoder = MultiColumnLabelEncoder()

        df = pl.DataFrame(
            {
                "level_2": ["01", "02", "03"],
                "level_3": ["01.01", "02.01", "03.01"],
                "level_4": ["01.01.01", "02.01.01", "03.01.01"],
                "level_5": ["01.01.01.01", "02.01.01.01", "03.01.01.01"],
                "level_6": ["", "", ""],
                "level_7": ["", "", ""],
                "level_8": ["", "", ""],
            }
        )
        encoder.fit(df)

        # Save
        extra = {"test_f1": 0.92}
        save_bundle(
            model, encoder, temp_dir, run_id="run_123", extra=extra, signing_key=KEY
        )

        # Load
        loaded_model, loaded_encoder, manifest = load_bundle(temp_dir, signing_key=KEY)

        # Verify
        assert manifest["run_id"] == "run_123"
        assert manifest["extra"]["test_f1"] == 0.92
        assert callable(getattr(loaded_model, "predict", None))
        assert callable(getattr(loaded_encoder, "inverse_transform", None))


class TestManifestSignature:
    """A1: a writer to the model directory must not be able to load a bundle."""

    def _bundle(self, temp_dir):
        encoder = MultiColumnLabelEncoder()
        df = pl.DataFrame(
            {
                "level_2": ["01"],
                "level_3": ["01.01"],
                "level_4": ["01.01.01"],
                "level_5": ["01.01.01.01"],
                "level_6": [""],
                "level_7": [""],
                "level_8": [""],
            }
        )
        encoder.fit(df)
        save_bundle(MockModel(), encoder, temp_dir, signing_key=KEY)

    def test_wrong_key_is_rejected(self, temp_dir):
        self._bundle(temp_dir)
        with pytest.raises(ValueError, match="signature"):
            load_bundle(temp_dir, signing_key=b"another-key-of-sufficient-length!!")

    def test_forged_manifest_without_key_is_rejected(self, temp_dir):
        self._bundle(temp_dir)
        manifest_path = temp_dir / MANIFEST_FILE
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["extra"] = {"forged": True}
        manifest["signature"] = "0" * 64
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        with pytest.raises(ValueError, match="signature"):
            load_bundle(temp_dir, signing_key=KEY)

    def test_model_file_is_not_deserialized_when_signature_fails(
        self, temp_dir, monkeypatch
    ):
        self._bundle(temp_dir)
        manifest_path = temp_dir / MANIFEST_FILE
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["signature"] = "0" * 64
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        def _fail(*args, **kwargs):
            raise AssertionError("joblib.load must not run before signature passes")

        monkeypatch.setattr("pars_local_mcp.wbs.artifacts.joblib.load", _fail)
        with pytest.raises(ValueError, match="signature"):
            load_bundle(temp_dir, signing_key=KEY)

    def test_short_key_is_rejected(self, temp_dir):
        with pytest.raises(ValueError, match="at least 32 bytes"):
            save_bundle(
                MockModel(), MultiColumnLabelEncoder(), temp_dir, signing_key=b"short"
            )


class TestDeserializesVerifiedBytes:
    """A1 blocker: the bytes that were verified must be the bytes deserialized."""

    def test_load_is_given_in_memory_bytes_not_a_path(self, temp_dir, monkeypatch):
        import io

        import joblib

        save_bundle(MockModel(), _fitted_encoder(), temp_dir, signing_key=KEY)
        seen = []
        real_load = joblib.load

        def spy(source, *args, **kwargs):
            seen.append(type(source))
            return real_load(source, *args, **kwargs)

        monkeypatch.setattr(joblib, "load", spy)
        load_bundle(temp_dir, signing_key=KEY)
        assert seen == [io.BytesIO, io.BytesIO]
