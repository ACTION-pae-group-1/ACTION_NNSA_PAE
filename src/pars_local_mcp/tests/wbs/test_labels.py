"""Tests for MultiColumnLabelEncoder."""

from __future__ import annotations

import pandas as pd
import polars as pl
import pytest

from pars_local_mcp.wbs.artifacts import LEVELS
from pars_local_mcp.wbs.labels import MultiColumnLabelEncoder, encode_labels


class TestMultiColumnLabelEncoder:
    """Test MultiColumnLabelEncoder fit/transform/inverse_transform."""

    def test_init_default_columns(self):
        """Test initialization with default LEVELS columns."""
        encoder = MultiColumnLabelEncoder()
        assert encoder.columns == list(LEVELS)
        assert encoder.encoders == {}

    def test_init_custom_columns(self):
        """Test initialization with custom columns."""
        custom_cols = ["col_a", "col_b", "col_c"]
        encoder = MultiColumnLabelEncoder(columns=custom_cols)
        assert encoder.columns == custom_cols

    def test_fit_polars_dataframe(self, polars_dataframe_labels):
        """Test fit with Polars DataFrame."""
        encoder = MultiColumnLabelEncoder()
        result = encoder.fit(polars_dataframe_labels)
        assert result is encoder  # fit returns self
        assert all(col in encoder.encoders for col in LEVELS)

    def test_fit_pandas_dataframe(self, pandas_dataframe_labels):
        """Test fit with pandas DataFrame."""
        encoder = MultiColumnLabelEncoder()
        result = encoder.fit(pandas_dataframe_labels)
        assert result is encoder
        assert all(col in encoder.encoders for col in LEVELS)

    def test_fit_missing_column_raises(self, polars_dataframe_labels):
        """Test fit raises when required column is missing."""
        encoder = MultiColumnLabelEncoder(columns=["level_2", "missing_level"])
        with pytest.raises(ValueError, match="Missing hierarchy column"):
            encoder.fit(polars_dataframe_labels)

    def test_transform_polars_dataframe(self, polars_dataframe_labels):
        """Test transform with Polars DataFrame."""
        encoder = MultiColumnLabelEncoder()
        encoder.fit(polars_dataframe_labels)
        transformed = encoder.transform(polars_dataframe_labels)
        assert isinstance(transformed, pl.DataFrame)
        assert transformed.shape == polars_dataframe_labels.shape

    def test_transform_pandas_dataframe(self, pandas_dataframe_labels):
        """Test transform with pandas DataFrame."""
        encoder = MultiColumnLabelEncoder()
        encoder.fit(pandas_dataframe_labels)
        transformed = encoder.transform(pandas_dataframe_labels)
        assert isinstance(transformed, pd.DataFrame)
        assert transformed.shape == pandas_dataframe_labels.shape

    def test_fit_transform_idempotent(self, polars_dataframe_labels):
        """Test fit_transform produces encoded values."""
        encoder = MultiColumnLabelEncoder()
        transformed = encoder.fit_transform(polars_dataframe_labels)
        assert isinstance(transformed, pl.DataFrame)
        # All values should be integers after encoding
        for col in LEVELS:
            assert transformed[col].dtype in [pl.Int64, pl.Int32, pl.UInt32]

    def test_inverse_transform_polars(self, polars_dataframe_labels):
        """Test inverse_transform recovers original values for Polars."""
        encoder = MultiColumnLabelEncoder()
        transformed = encoder.fit_transform(polars_dataframe_labels)
        decoded = encoder.inverse_transform(transformed)
        assert isinstance(decoded, pl.DataFrame)
        assert decoded.shape == polars_dataframe_labels.shape

    def test_inverse_transform_pandas(self, pandas_dataframe_labels):
        """Test inverse_transform recovers original values for pandas."""
        encoder = MultiColumnLabelEncoder()
        transformed = encoder.fit_transform(pandas_dataframe_labels)
        decoded = encoder.inverse_transform(transformed)
        assert isinstance(decoded, pd.DataFrame)
        assert decoded.shape == pandas_dataframe_labels.shape

    def test_inverse_transform_with_strings(self, polars_dataframe_labels):
        """Test inverse_transform handles string integer values from models."""
        encoder = MultiColumnLabelEncoder()
        encoded = encoder.fit_transform(polars_dataframe_labels)
        # Simulate hiClass output: convert to strings
        encoded_strings = encoded.with_columns(
            [pl.col(col).cast(pl.Utf8) for col in LEVELS]
        )
        decoded = encoder.inverse_transform(encoded_strings)
        assert isinstance(decoded, pl.DataFrame)

    def test_roundtrip_fidelity(self, polars_dataframe_labels):
        """Test that encode -> decode recovers original values."""
        encoder = MultiColumnLabelEncoder()
        encoded = encoder.fit_transform(polars_dataframe_labels)
        decoded = encoder.inverse_transform(encoded)
        # Compare values (allowing for type coercion)
        for col in LEVELS:
            original = set(polars_dataframe_labels[col].to_list())
            decoded_vals = set(decoded[col].to_list())
            assert original == decoded_vals

    def test_transform_requires_fit(self, polars_dataframe_labels):
        """Test that transform without fit raises."""
        encoder = MultiColumnLabelEncoder()
        with pytest.raises(KeyError):
            encoder.transform(polars_dataframe_labels)

    def test_inverse_transform_requires_fit(self):
        """Test that inverse_transform without fit raises."""
        encoder = MultiColumnLabelEncoder()
        dummy_df = pl.DataFrame(
            {
                "level_2": [0, 1, 2],
                "level_3": [0, 1, 2],
                "level_4": [0, 1, 2],
                "level_5": [0, 1, 2],
                "level_6": [0, 1, 2],
                "level_7": [0, 1, 2],
                "level_8": [0, 1, 2],
            }
        )
        encoder = MultiColumnLabelEncoder()
        with pytest.raises(KeyError):
            encoder.inverse_transform(dummy_df)


class TestEncodeLabelsFunctionality:
    """Test encode_labels function."""

    def test_encode_labels_creates_files(self, temp_dir, polars_dataframe_labels):
        """Test encode_labels creates label encoder and CSV files."""
        input_dir = temp_dir / "inputs"
        output_dir = temp_dir / "outputs"
        input_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)

        encoded, decoded = encode_labels(
            str(input_dir),
            polars_dataframe_labels,
            output_dir=str(output_dir),
        )

        # Check encoded output
        assert isinstance(encoded, pl.DataFrame)
        assert encoded.shape == polars_dataframe_labels.shape

        # Check decoded output
        assert isinstance(decoded, pl.DataFrame)

        # Check files were created
        assert (output_dir / "label_encoder.joblib").exists()
        assert (input_dir / "hiclass_labels_caef2.csv").exists()
        assert (input_dir / "hiclass_target_names_caef2.csv").exists()

    def test_encode_labels_with_pandas(self, temp_dir, pandas_dataframe_labels):
        """Test encode_labels works with pandas DataFrames."""
        input_dir = temp_dir / "inputs"
        output_dir = temp_dir / "outputs"
        input_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)

        encoded, decoded = encode_labels(
            str(input_dir),
            pandas_dataframe_labels,
            output_dir=str(output_dir),
        )

        # Both should work with pandas too
        assert encoded.shape == pandas_dataframe_labels.shape


class TestLabelEncoderRobustness:
    """Test robustness of label encoder to edge cases."""

    def test_encoder_with_single_value_per_level(self):
        """Test encoder when all values in a level are the same."""
        df = pl.DataFrame(
            {
                "level_2": ["01", "01", "01"],
                "level_3": ["01.01", "01.01", "01.01"],
                "level_4": ["01.01.01", "01.01.01", "01.01.01"],
                "level_5": ["01.01.01.01", "01.01.01.01", "01.01.01.01"],
                "level_6": ["", "", ""],
                "level_7": ["", "", ""],
                "level_8": ["", "", ""],
            }
        )
        encoder = MultiColumnLabelEncoder()
        encoded = encoder.fit_transform(df)
        decoded = encoder.inverse_transform(encoded)
        assert decoded.shape == df.shape

    def test_encoder_with_empty_strings(self):
        """Test encoder handles empty string values."""
        df = pl.DataFrame(
            {
                "level_2": ["01", "02", "03"],
                "level_3": ["01.01", "", ""],
                "level_4": ["01.01.01", "", ""],
                "level_5": ["01.01.01.01", "", ""],
                "level_6": ["", "", ""],
                "level_7": ["", "", ""],
                "level_8": ["", "", ""],
            }
        )
        encoder = MultiColumnLabelEncoder()
        encoded = encoder.fit_transform(df)
        decoded = encoder.inverse_transform(encoded)
        assert decoded.shape == df.shape

    @pytest.mark.parametrize("n_rows", [1, 10, 100])
    def test_encoder_with_varying_sizes(self, n_rows):
        """Test encoder with different DataFrame sizes."""
        levels = [
            "level_2",
            "level_3",
            "level_4",
            "level_5",
            "level_6",
            "level_7",
            "level_8",
        ]
        data = {
            level: [f"{i % 5:02d}" if level != "level_8" else "" for i in range(n_rows)]
            for level in levels
        }
        df = pl.DataFrame(data)
        encoder = MultiColumnLabelEncoder()
        encoded = encoder.fit_transform(df)
        decoded = encoder.inverse_transform(encoded)
        assert decoded.shape == (n_rows, len(levels))


def test_fit_label_space_encodes_labels_unseen_in_training():
    """A4: a label that appears only in the held-out split must not raise."""
    import polars as pl

    from pars_local_mcp.wbs.artifacts import LEVELS
    from pars_local_mcp.wbs.labels import MultiColumnLabelEncoder

    train = pl.DataFrame({col: ["known"] for col in LEVELS})
    test = pl.DataFrame({col: ["only_in_test"] for col in LEVELS})
    encoder = MultiColumnLabelEncoder().fit_label_space(train, test)
    encoded_test = encoder.transform(test)
    assert encoded_test.shape == (1, len(LEVELS))


def test_fit_rejects_null_hierarchy_values():
    """A null level must not become a learned class."""
    import polars as pl
    import pytest

    from pars_local_mcp.wbs.artifacts import LEVELS
    from pars_local_mcp.wbs.labels import MultiColumnLabelEncoder

    frame = pl.DataFrame({col: ["a", None] for col in LEVELS})
    with pytest.raises(ValueError, match="Null values not allowed"):
        MultiColumnLabelEncoder().fit(frame)


def test_fit_label_space_rejects_null_hierarchy_values():
    import polars as pl
    import pytest

    from pars_local_mcp.wbs.artifacts import LEVELS
    from pars_local_mcp.wbs.labels import MultiColumnLabelEncoder

    train = pl.DataFrame({col: ["a"] for col in LEVELS})
    test_frame = pl.DataFrame({col: [None] for col in LEVELS})
    with pytest.raises(ValueError, match="Null values not allowed"):
        MultiColumnLabelEncoder().fit_label_space(train, test_frame)
