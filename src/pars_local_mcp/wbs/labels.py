"""Importable hierarchy encoder; no dependence on globals in functions.py."""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.preprocessing import LabelEncoder

from .artifacts import LEVELS


def _non_null_values(frame, col):
    """Return column values, refusing nulls.

    A null hierarchy value would be learned as a class, and decoding would then
    write it back as text such as "None" or "nan" into level columns.
    """
    import pandas as pd

    values = np.asarray(frame[col], dtype=object)
    if pd.isna(values).any():
        raise ValueError(f"Null values not allowed in hierarchy column: {col}")
    return values


class MultiColumnLabelEncoder:
    """Stable module-qualified class for joblib persistence.

    Accepts Polars or pandas DataFrames with seven named hierarchy columns.
    """

    def __init__(self, columns=None):
        self.columns = list(columns) if columns is not None else list(LEVELS)
        self.encoders = {}

    def fit(self, frame, y=None):
        for col in self.columns:
            if col not in frame.columns:
                raise ValueError(f"Missing hierarchy column: {col}")
            self.encoders[col] = LabelEncoder().fit(_non_null_values(frame, col))
        return self

    def fit_label_space(self, *frames):
        """Fit each column's label vocabulary on several frames at once.

        Used so that labels present only in a held-out split can be encoded
        (and scored as misses) instead of raising during evaluation. The model
        itself must still be trained on training rows only.
        """
        for col in self.columns:
            for frame in frames:
                if col not in frame.columns:
                    raise ValueError(f"Missing hierarchy column: {col}")
            values = np.concatenate([_non_null_values(f, col) for f in frames])
            self.encoders[col] = LabelEncoder().fit(values)
        return self

    def transform(self, frame):
        values = {
            col: self.encoders[col].transform(np.asarray(frame[col]))
            for col in self.columns
        }
        if frame.__class__.__module__.startswith("polars"):
            import polars as pl

            return pl.DataFrame(values)
        import pandas as pd

        return pd.DataFrame(values, index=frame.index)

    def fit_transform(self, frame, y=None):
        return self.fit(frame, y).transform(frame)

    def inverse_transform(self, frame):
        values = {}
        for col in self.columns:
            arr = np.asarray(frame[col])
            # A fitted hiClass model can return integer-like values as strings.
            if arr.dtype.kind in "OUS":
                try:
                    arr = arr.astype(np.int64)
                except (ValueError, TypeError):
                    pass
            values[col] = self.encoders[col].inverse_transform(arr)
        if frame.__class__.__module__.startswith("polars"):
            import polars as pl

            return pl.DataFrame(values)
        import pandas as pd

        return pd.DataFrame(values, index=frame.index)


def encode_labels(input_dir, training_data, hierarchies=LEVELS, *, output_dir):
    """Equivalent external interface to original encode_labels, explicit paths."""
    output = Path(output_dir)
    inputs = Path(input_dir)
    output.mkdir(parents=True, exist_ok=True)
    inputs.mkdir(parents=True, exist_ok=True)
    subset = (
        training_data.select(list(hierarchies))
        if hasattr(training_data, "select")
        else training_data[list(hierarchies)]
    )
    encoder = MultiColumnLabelEncoder(columns=hierarchies)
    encoded = encoder.fit_transform(subset)
    decoded = encoder.inverse_transform(encoded)
    joblib.dump(encoder, output / "label_encoder.joblib")
    if hasattr(encoded, "write_csv"):
        encoded.write_csv(inputs / "hiclass_labels_caef2.csv")
        decoded.write_csv(inputs / "hiclass_target_names_caef2.csv")
    else:
        encoded.to_csv(inputs / "hiclass_labels_caef2.csv", index=False)
        decoded.to_csv(inputs / "hiclass_target_names_caef2.csv", index=False)
    return encoded, decoded


def records_to_frame(records):
    """LabeledWBSRecord list -> polars frame with title and level_2..level_8."""
    import polars as pl

    data = {"title": [r.title for r in records]}
    for level in LEVELS:
        data[level] = [getattr(r, "caef_" + level) for r in records]
    return pl.DataFrame(data)
