"""Tests for create_dataset.py. The Phoenix client is always mocked; no network."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

EVAL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EVAL_DIR))

import create_dataset  # noqa: E402

CONFIG = {
    "csv_path": "unused.csv",
    "input_keys": ["query"],
    "output_keys": ["responses"],
    "description": "test set",
}


@pytest.fixture
def csv_file(tmp_path: Path) -> Path:
    path = tmp_path / "set.csv"
    pd.DataFrame(
        {"query": ["List the projects"], "responses": ["proj_001 and proj_002"]}
    ).to_csv(path, index=False)
    return path


def test_validate_dataset_rejects_missing_columns(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    pd.DataFrame({"query": ["q"]}).to_csv(path, index=False)
    assert create_dataset.validate_dataset(path, CONFIG) is False


def test_validate_dataset_accepts_required_columns(csv_file: Path) -> None:
    assert create_dataset.validate_dataset(csv_file, CONFIG) is True


def test_upload_passes_base_url_and_input_output_keys(
    csv_file: Path, monkeypatch
) -> None:
    monkeypatch.setenv("PHOENIX_ENDPOINT", "http://localhost:6006")
    client = MagicMock()
    factory = MagicMock(return_value=client)

    ok = create_dataset.upload_dataset(
        "pars-eval-1", csv_file, config=CONFIG, client_factory=factory
    )

    assert ok is True
    factory.assert_called_once_with(base_url="http://localhost:6006")
    kwargs = client.datasets.create_dataset.call_args.kwargs
    assert kwargs["name"] == "pars-eval-1"
    assert list(kwargs["input_keys"]) == ["query"]
    assert list(kwargs["output_keys"]) == ["responses"]
    assert kwargs["dataframe"].shape == (1, 2)


def test_upload_returns_false_when_phoenix_import_breaks(
    csv_file: Path, monkeypatch
) -> None:
    # arize-phoenix 20.x raises ValueError on import under this venv's Python.
    def broken_import():
        raise ValueError("mutable default for field boolean_names")

    monkeypatch.setattr(create_dataset, "_import_phoenix_client", broken_import)
    assert create_dataset.upload_dataset("x", csv_file, config=CONFIG) is False


def test_upload_refuses_non_loopback_phoenix(csv_file: Path, monkeypatch) -> None:
    monkeypatch.setenv("PHOENIX_ENDPOINT", "https://phoenix.example.com")
    factory = MagicMock()
    ok = create_dataset.upload_dataset(
        "x", csv_file, config=CONFIG, client_factory=factory
    )
    assert ok is False
    factory.assert_not_called()


def test_dry_run_never_builds_a_client(csv_file: Path) -> None:
    factory = MagicMock()
    ok = create_dataset.upload_dataset(
        "x", csv_file, config=CONFIG, dry_run=True, client_factory=factory
    )
    assert ok is True
    factory.assert_not_called()
