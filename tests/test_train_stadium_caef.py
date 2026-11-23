"""Tests for the pure helpers in tools/train_stadium_caef.py.

main() and training are never run. DuckDB queries use an in-memory connection.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

import duckdb
import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "tools" / "train_stadium_caef.py"


@pytest.fixture
def module(monkeypatch):
    monkeypatch.syspath_prepend(str(REPO / "tools"))
    monkeypatch.syspath_prepend(str(REPO / "src"))
    spec = importlib.util.spec_from_file_location("train_stadium_caef", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["train_stadium_caef"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def con():
    connection = duckdb.connect(":memory:")
    connection.execute(
        "CREATE TABLE wbs_elements (parsid VARCHAR, wbs_code VARCHAR, title VARCHAR, "
        "level INTEGER, parent_wbs VARCHAR)"
    )
    connection.execute(
        "INSERT INTO wbs_elements VALUES "
        "('P1', '1', 'Site', 1, NULL), "
        "('P1', '1.1', 'Clearing', 2, '1'), "
        "('P1', '1.1.1', 'Grub clearing', 3, '1.1')"
    )
    levels = ", ".join(f"caef_level_{d} VARCHAR" for d in range(2, 9))
    connection.execute(
        f"CREATE TABLE labeled_wbs (parsid VARCHAR, wbs_code VARCHAR, {levels})"
    )
    connection.execute(
        "INSERT INTO labeled_wbs (parsid, wbs_code, caef_level_2, caef_level_3) "
        "VALUES ('P1', '1.1', 'site work', 'clearing')"
    )
    yield connection
    connection.close()


def test_sha_matches_hashlib(module, tmp_path: Path) -> None:
    path = tmp_path / "model.bin"
    path.write_bytes(b"weights")
    assert module.sha(path) == hashlib.sha256(b"weights").hexdigest()


def test_project_texts_tags_rows_with_parsid(module, con) -> None:
    frame = module.project_texts(con, "P1")
    assert "parsid" in frame.columns
    assert set(frame["parsid"].to_list()) == {"P1"}
    assert frame.height > 0


def test_labels_for_returns_only_the_requested_project(module, con) -> None:
    con.execute(
        "INSERT INTO labeled_wbs (parsid, wbs_code, caef_level_2) "
        "VALUES ('P2', '9', 'x')"
    )
    frame = module.labels_for(con, "P1")
    assert frame.height == 1
    assert frame["wbs"].to_list() == ["1.1"]


def test_build_without_labels_returns_no_label_frame(module, con) -> None:
    text_df, label_df = module.build(con, ["P1"], with_labels=False)
    assert label_df is None
    assert text_df.height > 0


def test_build_with_labels_returns_tagged_label_rows(module, con) -> None:
    text_df, label_df = module.build(con, ["P1"], with_labels=True)
    assert label_df is not None
    assert label_df["parsid"].to_list() == ["P1"]
    assert text_df["parsid"].unique().to_list() == ["P1"]
