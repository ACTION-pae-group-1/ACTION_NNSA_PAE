"""Tests for inference (batch prediction and decoding)."""

from __future__ import annotations

from unittest import mock

import numpy as np
import pandas as pd
import polars as pl
import pytest

from pars_local_mcp.wbs.inference import (
    _texts,
    decode_predictions,
    predict_batches,
    predict_dataframe,
)
from pars_local_mcp.wbs.labels import MultiColumnLabelEncoder

pytestmark = pytest.mark.slow


class TestTextConversion:
    """Test _texts utility function."""

    def test_texts_from_numpy_array(self):
        """Test _texts converts numpy array to string array."""
        texts = _texts(np.array(["hello", "world"]))
        assert texts.dtype == object
        assert len(texts) == 2

    def test_texts_from_list(self):
        """Test _texts converts list to numpy string array."""
        texts = _texts(["hello", "world"])
        assert isinstance(texts, np.ndarray)
        assert texts.dtype == object

    def test_texts_handles_none_values(self):
        """Test _texts converts None to empty string."""
        texts = _texts(["hello", None, "world"])
        assert texts[1] == ""

    def test_texts_handles_nan_values(self):
        """Test _texts converts NaN to empty string."""
        texts = _texts(["hello", np.nan, "world"])
        assert texts[1] == ""

    def test_texts_converts_numbers_to_strings(self):
        """Test _texts converts numeric values to strings."""
        texts = _texts([1, 2, 3])
        assert all(isinstance(t, str) for t in texts)

    def test_texts_rejects_multidimensional(self):
        """Test _texts rejects multi-dimensional input."""
        arr = np.array([["a", "b"], ["c", "d"]])
        with pytest.raises(ValueError, match="1-D"):
            _texts(arr)


class TestPredictBatches:
    """Test predict_batches function."""

    def test_predict_batches_empty_input(self, mock_trained_model):
        """Test predict_batches handles empty input."""
        predictions = predict_batches(np.array([], dtype=object), mock_trained_model)
        assert predictions.shape == (0, 7)

    def test_predict_batches_single_sample(self, mock_trained_model, test_titles_batch):
        """Test predict_batches with single sample."""
        predictions = predict_batches(test_titles_batch[:1], mock_trained_model)
        assert predictions.shape == (1, 7)

    def test_predict_batches_multiple_samples(
        self, mock_trained_model, test_titles_batch
    ):
        """Test predict_batches with multiple samples."""
        predictions = predict_batches(test_titles_batch, mock_trained_model)
        assert predictions.shape == (len(test_titles_batch), 7)

    def test_predict_batches_respects_batch_size(self, mock_trained_model):
        """Test predict_batches chunks correctly."""
        texts = np.array([f"text_{i}" for i in range(15)], dtype=object)
        batch_sizes_called = []

        def on_batch(current, total):
            batch_sizes_called.append(current)

        predictions = predict_batches(
            texts, mock_trained_model, batch_size=5, on_batch=on_batch
        )

        assert predictions.shape == (15, 7)
        assert batch_sizes_called == [5, 10, 15]

    def test_predict_batches_invalid_batch_size_raises(self, mock_trained_model):
        """Test predict_batches raises on invalid batch_size."""
        with pytest.raises(ValueError, match="batch_size must be positive"):
            predict_batches(
                np.array(["text"], dtype=object),
                mock_trained_model,
                batch_size=0,
            )

    def test_predict_batches_with_callback(self, mock_trained_model):
        """Test predict_batches calls callback for each batch."""
        texts = np.array([f"text_{i}" for i in range(10)], dtype=object)
        progress = []

        def on_batch(current, total):
            progress.append((current, total))

        predict_batches(texts, mock_trained_model, batch_size=3, on_batch=on_batch)

        assert len(progress) == 4  # 3 + 3 + 3 + 1
        assert progress[-1] == (10, 10)

    def test_predict_batches_model_error_propagates(self):
        """Test predict_batches propagates model errors."""

        class BadModel:
            def predict(self, texts):
                raise RuntimeError("Model failed")

        with pytest.raises(RuntimeError, match="Prediction failed"):
            predict_batches(
                np.array(["text"], dtype=object),
                BadModel(),
                batch_size=5,
            )

    def test_predict_batches_shape_mismatch_raises(self):
        """Test predict_batches raises on shape mismatch."""

        class BadModel:
            def predict(self, texts):
                return np.zeros((len(texts), 5))  # Wrong shape

        with pytest.raises(ValueError, match="shape mismatch"):
            predict_batches(
                np.array(["text"], dtype=object),
                BadModel(),
                batch_size=5,
            )

    @pytest.mark.parametrize("batch_size", [1, 5, 100])
    def test_predict_batches_various_sizes(self, mock_trained_model, batch_size):
        """Test predict_batches with various batch sizes."""
        texts = np.array([f"text_{i}" for i in range(10)], dtype=object)
        predictions = predict_batches(texts, mock_trained_model, batch_size=batch_size)
        assert predictions.shape == (10, 7)


class TestDecodePredictions:
    """Test decode_predictions function."""

    def test_decode_predictions_shape(
        self, polars_dataframe_labels, mock_label_encoder
    ):
        """Test decode_predictions preserves shape."""
        # Create encoded predictions using the encoder
        encoder = MultiColumnLabelEncoder()
        encoded = encoder.fit_transform(polars_dataframe_labels)
        predictions = np.asarray(encoded.to_numpy(), dtype=object)

        decoded = decode_predictions(predictions, encoder)
        assert decoded.shape == (10, 7)

    def test_decode_predictions_returns_array(self, polars_dataframe_labels):
        """Test decode_predictions returns numpy array."""
        # Create predictions from properly encoded data
        encoder = MultiColumnLabelEncoder()
        encoded = encoder.fit_transform(polars_dataframe_labels)
        predictions = np.asarray(encoded[:5].to_numpy(), dtype=object)

        decoded = decode_predictions(predictions, encoder)
        assert isinstance(decoded, np.ndarray)

    def test_decode_predictions_invalid_shape_raises(self, mock_label_encoder):
        """Test decode_predictions rejects wrong shape."""
        predictions = np.zeros((10, 5))  # Wrong: 5 instead of 7
        with pytest.raises(ValueError, match="Expected"):
            decode_predictions(predictions, mock_label_encoder)

    def test_decode_predictions_multidimensional_check(self, mock_label_encoder):
        """Test decode_predictions rejects 1D input."""
        predictions = np.array([0, 1, 2, 3, 4, 5, 6])
        with pytest.raises(ValueError, match="Expected"):
            decode_predictions(predictions, mock_label_encoder)

    def test_decode_predictions_with_string_indices(self, mock_label_encoder):
        """Test decode_predictions handles string indices from hiClass."""
        # hiClass can return string integers
        predictions = np.array(
            [
                ["0", "1", "2", "3", "0", "0", "0"],
                ["1", "2", "3", "4", "0", "0", "0"],
            ]
        )
        decoded = decode_predictions(predictions, mock_label_encoder)
        assert decoded.shape == (2, 7)

    def test_decode_predictions_roundtrip(self, polars_dataframe_labels):
        """Test encode -> predict -> decode roundtrip."""
        encoder = MultiColumnLabelEncoder()
        encoded = encoder.fit_transform(polars_dataframe_labels)

        # Simulate model output
        predictions = np.asarray(encoded.to_numpy(), dtype=object)

        decoded = decode_predictions(predictions, encoder)
        assert decoded.shape == polars_dataframe_labels.shape


class TestPredictDataframe:
    """Test predict_dataframe function."""

    def test_predict_dataframe_polars_input(self, polars_dataframe_labels):
        """Test predict_dataframe with Polars DataFrame."""
        # Create a model that returns properly encoded values
        encoder = MultiColumnLabelEncoder()
        encoded = encoder.fit_transform(polars_dataframe_labels)

        class ProperMockModel:
            def predict(self, texts):
                n_samples = len(texts)
                # Return encoded predictions from our test data
                return np.asarray(encoded[:n_samples].to_numpy())

        df = pl.DataFrame(
            {
                "wbs_title": ["title_1", "title_2", "title_3"],
                "project_id": ["proj_001", "proj_001", "proj_002"],
            }
        )

        result = predict_dataframe(
            df, ProperMockModel(), encoder, text_field="wbs_title"
        )

        assert isinstance(result, pl.DataFrame)
        assert len(result) == 3
        # Should have original columns plus prediction columns
        assert "wbs_title" in result.columns
        assert "project_id" in result.columns
        assert "level_2" in result.columns

    def test_predict_dataframe_pandas_input(self, polars_dataframe_labels):
        """Test predict_dataframe with pandas DataFrame."""
        # Create a model that returns properly encoded values
        encoder = MultiColumnLabelEncoder()
        encoded = encoder.fit_transform(polars_dataframe_labels)

        class ProperMockModel:
            def predict(self, texts):
                n_samples = len(texts)
                return np.asarray(encoded[:n_samples].to_numpy())

        df = pd.DataFrame(
            {
                "wbs_title": ["title_1", "title_2", "title_3"],
                "project_id": ["proj_001", "proj_001", "proj_002"],
            }
        )

        result = predict_dataframe(
            df, ProperMockModel(), encoder, text_field="wbs_title"
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
        assert "wbs_title" in result.columns
        assert "level_2" in result.columns

    def test_predict_dataframe_missing_text_field_raises(
        self, mock_trained_model, mock_label_encoder
    ):
        """Test predict_dataframe raises when text field missing."""
        df = pl.DataFrame(
            {
                "title": ["title_1"],
                "project_id": ["proj_001"],
            }
        )

        with pytest.raises(ValueError, match="Missing text field"):
            predict_dataframe(
                df, mock_trained_model, mock_label_encoder, text_field="wbs_title"
            )

    def test_predict_dataframe_collision_raises(
        self, mock_trained_model, mock_label_encoder
    ):
        """Test predict_dataframe raises when prediction columns already exist."""
        df = pl.DataFrame(
            {
                "wbs_title": ["title_1"],
                "level_2": ["existing"],  # Collision
            }
        )

        with pytest.raises(ValueError, match="already contains prediction columns"):
            predict_dataframe(
                df, mock_trained_model, mock_label_encoder, text_field="wbs_title"
            )

    def test_predict_dataframe_returns_all_columns(self, polars_dataframe_labels):
        """Test predict_dataframe preserves original columns."""
        encoder = MultiColumnLabelEncoder()
        encoded = encoder.fit_transform(polars_dataframe_labels)

        class ProperMockModel:
            def predict(self, texts):
                n_samples = len(texts)
                return np.asarray(encoded[:n_samples].to_numpy())

        df = pl.DataFrame(
            {
                "wbs_title": ["title_1", "title_2"],
                "project_id": ["proj_001", "proj_002"],
                "other_field": ["a", "b"],
            }
        )

        result = predict_dataframe(df, ProperMockModel(), encoder)

        assert "wbs_title" in result.columns
        assert "project_id" in result.columns
        assert "other_field" in result.columns

    def test_predict_dataframe_custom_batch_size(self, polars_dataframe_labels):
        """Test predict_dataframe respects batch_size."""
        encoder = MultiColumnLabelEncoder()
        encoded = encoder.fit_transform(polars_dataframe_labels)

        class ProperMockModel:
            def predict(self, texts):
                n_samples = min(len(texts), 10)
                return np.asarray(encoded[:n_samples].to_numpy())

        df = pl.DataFrame(
            {
                "wbs_title": [f"title_{i}" for i in range(10)],
            }
        )

        result = predict_dataframe(df, ProperMockModel(), encoder, batch_size=3)

        assert len(result) == 10
        # All predictions should be present
        assert result["level_2"].len() == 10

    def test_predict_dataframe_type_preservation(self, polars_dataframe_labels):
        """Test predict_dataframe preserves input type (Polars or pandas)."""
        encoder = MultiColumnLabelEncoder()
        encoded = encoder.fit_transform(polars_dataframe_labels)

        class ProperMockModel:
            def predict(self, texts):
                n_samples = len(texts)
                return np.asarray(encoded[:n_samples].to_numpy())

        polars_df = pl.DataFrame({"wbs_title": ["title_1", "title_2"]})
        pandas_df = pd.DataFrame({"wbs_title": ["title_1", "title_2"]})

        result_polars = predict_dataframe(polars_df, ProperMockModel(), encoder)
        result_pandas = predict_dataframe(pandas_df, ProperMockModel(), encoder)

        assert isinstance(result_polars, pl.DataFrame)
        assert isinstance(result_pandas, pd.DataFrame)

    def test_predict_dataframe_unsupported_type_raises(self, polars_dataframe_labels):
        """Test predict_dataframe raises on unsupported DataFrame type."""
        encoder = MultiColumnLabelEncoder()
        encoder.fit(polars_dataframe_labels)

        class CustomDF:
            columns = ["wbs_title"]

        # May raise TypeError or other error when trying to use unsupported type
        with pytest.raises((TypeError, AttributeError)):
            predict_dataframe(CustomDF(), mock.Mock(), encoder)


class TestInferenceIntegration:
    """Integration tests for inference pipeline."""

    def test_full_prediction_pipeline(self, synthetic_titles, polars_dataframe_labels):
        """Test complete prediction pipeline."""
        encoder = MultiColumnLabelEncoder()
        encoded = encoder.fit_transform(polars_dataframe_labels)

        # Create a proper mock model
        class TestModel:
            def predict(self, texts):
                n_samples = len(texts)
                # Return valid encoded predictions
                return np.asarray(encoded[:n_samples].to_numpy())

        predictions = predict_batches(synthetic_titles, TestModel(), batch_size=5)
        assert predictions.shape == (len(synthetic_titles), 7)

    def test_predict_dataframe_integration(self, polars_dataframe_labels):
        """Test predict_dataframe integration with proper model."""
        encoder = MultiColumnLabelEncoder()
        encoded = encoder.fit_transform(polars_dataframe_labels)

        class TestModel:
            def predict(self, texts):
                n_samples = len(texts)
                return np.asarray(encoded[:n_samples].to_numpy())

        df = pl.DataFrame(
            {
                "id": [1, 2, 3],
                "wbs_title": ["Engineering", "Management", "Testing"],
                "priority": ["high", "medium", "low"],
            }
        )

        result = predict_dataframe(df, TestModel(), encoder)

        # Verify structure
        assert len(result) == 3
        assert all(f"level_{i}" in result.columns for i in range(2, 9))
        assert "id" in result.columns
        assert "priority" in result.columns
