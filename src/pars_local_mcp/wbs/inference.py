"""Shared batch prediction and decoding for Notebook 02 and Shiny."""

from __future__ import annotations

import numpy as np

from .artifacts import LEVELS


def _texts(values):
    if hasattr(values, "to_numpy"):
        values = values.to_numpy()
    arr = np.asarray(values, dtype=object)
    if arr.ndim != 1:
        raise ValueError(f"Expected 1-D text array, received {arr.shape}")
    return np.asarray(
        [
            "" if v is None or (isinstance(v, float) and np.isnan(v)) else str(v)
            for v in arr
        ],
        dtype=object,
    )


def predict_batches(texts, model, *, batch_size=5000, on_batch=None):
    """Fail fast: never append error strings into prediction arrays."""
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    values = _texts(texts)
    if len(values) == 0:
        return np.empty((0, len(LEVELS)), dtype=object)
    chunks = []
    for start in range(0, len(values), batch_size):
        stop = min(start + batch_size, len(values))
        try:
            chunk = np.asarray(model.predict(values[start:stop]))
        except Exception as exc:
            raise RuntimeError(f"Prediction failed for rows {start}:{stop}") from exc
        if chunk.shape != (stop - start, len(LEVELS)):
            raise ValueError(
                f"Prediction shape mismatch for rows {start}:{stop}: "
                f"expected {(stop - start, len(LEVELS))}, got {chunk.shape}"
            )
        chunks.append(chunk)
        if on_batch:
            on_batch(stop, len(values))
    return np.concatenate(chunks, axis=0)


def decode_predictions(predictions, label_encoder):
    """Decode with original fitted encoder; do not refit on new data."""
    raw = np.asarray(predictions)
    if raw.ndim != 2 or raw.shape[1] != len(LEVELS):
        raise ValueError(f"Expected (n, {len(LEVELS)}) predictions, got {raw.shape}")
    try:
        import polars as pl

        encoded = pl.DataFrame({name: raw[:, i] for i, name in enumerate(LEVELS)})
        decoded = label_encoder.inverse_transform(encoded)
    except ImportError:
        import pandas as pd

        encoded = pd.DataFrame(raw, columns=LEVELS)
        decoded = label_encoder.inverse_transform(encoded)
    if hasattr(decoded, "to_numpy"):
        decoded = decoded.to_numpy()
    decoded = np.asarray(decoded)
    if decoded.shape != raw.shape:
        raise ValueError(f"Decoded prediction shape mismatch: {decoded.shape}")
    return decoded


def predict_dataframe(
    frame,
    model,
    label_encoder,
    *,
    text_field="wbs_title",
    batch_size=5000,
    on_batch=None,
):
    """Return input columns plus decoded hierarchy columns in original row order."""
    if text_field not in frame.columns:
        raise ValueError(f"Missing text field {text_field!r}")
    collisions = set(LEVELS) & set(frame.columns)
    if collisions:
        raise ValueError(
            f"Input already contains prediction columns: {sorted(collisions)}"
        )
    predictions = predict_batches(
        frame[text_field], model, batch_size=batch_size, on_batch=on_batch
    )
    decoded = decode_predictions(predictions, label_encoder)
    if len(decoded) != len(frame):
        raise ValueError("Prediction row count differs from input")
    if frame.__class__.__module__.startswith("polars"):
        import polars as pl

        columns = pl.DataFrame(
            {name: decoded[:, i].astype(str) for i, name in enumerate(LEVELS)}
        )
        return frame.hstack(columns)
    if frame.__class__.__module__.startswith("pandas"):
        import pandas as pd

        columns = pd.DataFrame(decoded, columns=LEVELS, index=frame.index)
        return pd.concat([frame.copy(), columns], axis=1)
    raise TypeError("Expected a pandas or Polars DataFrame")


def rows_to_paths(decoded, titles):
    """Build {title, path, leaf} rows; path keeps non-empty labels in level order."""
    decoded = np.asarray(decoded)
    if len(decoded) != len(titles):
        raise ValueError("Decoded predictions and titles differ in length")
    results = []
    for title, row in zip(titles, decoded):
        path = [str(v) for v in row if v is not None and str(v).strip() != ""]
        results.append(
            {"title": str(title), "path": path, "leaf": path[-1] if path else None}
        )
    return results
