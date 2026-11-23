"""Pytest fixtures for PARS MCP test suite."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
import pytest


@pytest.fixture
def temp_dir():
    """Temporary directory for test artifacts."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def synthetic_titles():
    """Generate synthetic WBS titles for testing."""
    return np.array(
        [
            "Program Management",
            "Engineering Analysis",
            "System Integration",
            "Testing and Validation",
            "Quality Assurance",
            "Documentation",
            "Project Planning",
            "Risk Management",
            "Configuration Management",
            "Schedule Management",
        ],
        dtype=object,
    )


@pytest.fixture
def synthetic_hierarchy_labels():
    """Generate synthetic 7-level hierarchy labels."""
    labels = np.array(
        [
            ["01", "01.01", "01.01.01", "01.01.01.01", "", "", ""],
            ["01", "01.02", "01.02.01", "01.02.01.01", "", "", ""],
            ["02", "02.01", "02.01.01", "02.01.01.01", "02.01.01.01.01", "", ""],
            ["02", "02.02", "02.02.01", "02.02.01.01", "02.02.01.01.01", "", ""],
            ["03", "03.01", "03.01.01", "03.01.01.01", "", "", ""],
            ["03", "03.02", "03.02.01", "03.02.01.01", "", "", ""],
            [
                "04",
                "04.01",
                "04.01.01",
                "04.01.01.01",
                "04.01.01.01.01",
                "04.01.01.01.01.01",
                "",
            ],
            [
                "04",
                "04.02",
                "04.02.01",
                "04.02.01.01",
                "04.02.01.01.01",
                "04.02.01.01.01.01",
                "",
            ],
            ["05", "05.01", "05.01.01", "05.01.01.01", "", "", ""],
            ["05", "05.02", "05.02.01", "05.02.01.01", "", "", ""],
        ],
        dtype=object,
    )
    return labels


@pytest.fixture
def test_titles_batch():
    """Batch of test titles for inference."""
    return np.array(
        [
            "New Program Management Task",
            "Engineering Work Package",
            "Integration Testing Activity",
        ],
        dtype=object,
    )


@pytest.fixture
def polars_dataframe_labels(synthetic_hierarchy_labels):
    """Create a Polars DataFrame with hierarchy labels."""
    return pl.DataFrame(
        {
            "level_2": synthetic_hierarchy_labels[:, 0].astype(str),
            "level_3": synthetic_hierarchy_labels[:, 1].astype(str),
            "level_4": synthetic_hierarchy_labels[:, 2].astype(str),
            "level_5": synthetic_hierarchy_labels[:, 3].astype(str),
            "level_6": synthetic_hierarchy_labels[:, 4].astype(str),
            "level_7": synthetic_hierarchy_labels[:, 5].astype(str),
            "level_8": synthetic_hierarchy_labels[:, 6].astype(str),
        }
    )


@pytest.fixture
def pandas_dataframe_labels(synthetic_hierarchy_labels):
    """Create a pandas DataFrame with hierarchy labels."""
    return pd.DataFrame(
        {
            "level_2": synthetic_hierarchy_labels[:, 0].astype(str),
            "level_3": synthetic_hierarchy_labels[:, 1].astype(str),
            "level_4": synthetic_hierarchy_labels[:, 2].astype(str),
            "level_5": synthetic_hierarchy_labels[:, 3].astype(str),
            "level_6": synthetic_hierarchy_labels[:, 4].astype(str),
            "level_7": synthetic_hierarchy_labels[:, 5].astype(str),
            "level_8": synthetic_hierarchy_labels[:, 6].astype(str),
        }
    )


@pytest.fixture
def mock_trained_model():
    """Create a mock trained model with predict method."""

    class MockModel:
        def predict(self, texts):
            n_samples = len(texts)
            # Return integer indices that will be passed to inverse_transform
            # Valid indices are 0-7 for our encoder which has 8 classes
            return np.random.randint(0, 8, size=(n_samples, 7))

    return MockModel()


@pytest.fixture
def mock_label_encoder():
    """Create a mock label encoder with inverse_transform method."""
    from src.pars_local_mcp.wbs.labels import MultiColumnLabelEncoder

    # Initialize with broader sample data to handle more indices
    sample_df = pl.DataFrame(
        {
            "level_2": ["01", "02", "03", "04", "05", "06", "07", "08"],
            "level_3": [
                "01.01",
                "02.01",
                "03.01",
                "04.01",
                "05.01",
                "06.01",
                "07.01",
                "08.01",
            ],
            "level_4": [
                "01.01.01",
                "02.01.01",
                "03.01.01",
                "04.01.01",
                "05.01.01",
                "06.01.01",
                "07.01.01",
                "08.01.01",
            ],
            "level_5": [
                "01.01.01.01",
                "02.01.01.01",
                "03.01.01.01",
                "04.01.01.01",
                "05.01.01.01",
                "06.01.01.01",
                "07.01.01.01",
                "08.01.01.01",
            ],
            "level_6": ["", "", "", "", "", "", "", ""],
            "level_7": ["", "", "", "", "", "", "", ""],
            "level_8": ["", "", "", "", "", "", "", ""],
        }
    )

    encoder = MultiColumnLabelEncoder()
    encoder.fit(sample_df)
    return encoder
