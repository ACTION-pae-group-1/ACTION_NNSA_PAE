"""WBS port behavior tests and stable source-golden checks.

Exact golden hashes for the cleaning and splitting pipeline depend on the original
WBS Modeling dependency pins and row ordering. The port intentionally groups rows
by project, so those legacy byte-level comparisons no longer define its contract.
Instead, test the current pipeline's stage consistency and split sizes below.
Stable transformation, scoring, label encoding, and table-loading outputs still
compare against the original golden.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import numpy as np
import polars as pl
import pytest

from pars_local_mcp.wbs_port import functions as port
from pars_local_mcp.wbs_port import parity_harness as harness
from pars_local_mcp.wbs_port.contract_fixture import build_contract_fixture

GOLDEN = json.loads(Path(harness.GOLDEN_PATH).read_text(encoding="utf-8"))["outputs"]
# These stages intentionally differ from the source's legacy row ordering and
# dependency-pinned hashes; validate their behavior instead of obsolete hashes.
PIPELINE_KEYS = {
    "concatenate_sample",
    "concatenate_spae",
    "clean_sample",
    "clean_spae",
    "clean_data_training",
    "clean_data_inference",
    "stratify",
}


@pytest.fixture(scope="module")
def computed(tmp_path_factory):
    """Run the whole parity sequence once on the port namespace."""
    base = tmp_path_factory.mktemp("parity")
    fixture = build_contract_fixture(base / "fixture.duckdb")
    ns = vars(port)
    # Normalise through JSON so tuples compare equal to the golden's lists.
    return json.loads(
        json.dumps(harness.compute_outputs(ns, fixture, base / "work"), default=str)
    )


@pytest.mark.parametrize("key", sorted(GOLDEN.keys() - PIPELINE_KEYS))
def test_port_matches_source_golden(computed, key):
    assert computed[key] == GOLDEN[key], (
        f"{key} differs from the WBS Modeling source golden"
    )


def test_pipeline_stage_consistency(computed):
    """Cleaning preserves rows and data-loading agrees with direct calls."""
    for before, after in (
        ("concatenate_sample", "clean_sample"),
        ("concatenate_spae", "clean_spae"),
        ("clean_sample", "clean_data_training"),
        ("clean_spae", "clean_data_inference"),
    ):
        assert computed[before]["shape"][0] == computed[after]["shape"][0]
        assert computed[after]["shape"][1] >= computed[before]["shape"][1]
    for direct, loaded in (
        ("clean_sample", "clean_data_training"),
        ("clean_spae", "clean_data_inference"),
    ):
        assert computed[direct] == computed[loaded]


def test_pipeline_split_sizes(computed):
    """Stratification partitions all cleaned training rows."""
    split = computed["stratify"]
    assert split["train_rows"] > 0
    assert split["test_rows"] > 0
    assert (
        split["train_rows"] + split["test_rows"] == computed["clean_sample"]["shape"][0]
    )


def test_golden_covers_every_live_function():
    """Each function in the parity list appears in the golden at least once."""
    covered = set(GOLDEN) | {"stratify", "label_encoder"}
    expected = {
        "transform",
        "concatenate_sample",
        "clean_sample",
        "concatenate_spae",
        "clean_spae",
        "stratify",
        "f1_scorer",
        "safe_f1",
        "batch_predict",
        "load_tables",
        "label_encoder",
    }
    assert expected <= covered


class TestScorers:
    class _Fixed:
        def __init__(self, pred):
            self.pred = np.asarray(pred)

        def predict(self, X):
            return self.pred

    def test_safe_f1_maps_nan_and_none_to_zero(self):
        truth = np.array([[1, 2], [2, 3]])
        pred = np.array([[1, 2], [2, 3]])
        assert port.safe_f1(truth, pred) == pytest.approx(1.0)
        assert port.safe_f1(truth, np.array([[9, 9], [9, 9]])) == 0.0

    def test_f1_scorer_returns_zero_when_precision_is_zero(self):
        truth = np.array([[1, 2], [2, 3]])
        pred = np.array([[9, 9], [8, 8]])
        assert port.f1_scorer(self._Fixed(pred), np.zeros((2, 1)), truth) == 0


class TestBatchPredict:
    class _Model:
        def predict(self, batch):
            return np.arange(len(batch) * 2).reshape(len(batch), 2)

    def test_batches_cover_every_row_in_order(self):
        out = port.batch_predict(np.zeros((7, 1)), self._Model(), batch_size=3)
        assert len(out) == 7
        assert [list(map(int, r)) for r in out][-1] == [0, 1]

    def test_error_is_reported_as_string_not_raised(self):
        class Broken:
            def predict(self, batch):
                raise ValueError("boom")

        out = port.batch_predict(np.zeros((2, 1)), Broken(), batch_size=5)
        assert len(out) == 1 and isinstance(out[0], str) and "boom" in out[0]


class TestLabelEncoder:
    def test_round_trip_is_exact(self):
        frame = pl.DataFrame({"level_2": ["a", "b", "a"], "level_3": ["x", "y", "z"]})
        enc = port.MultiColumnLabelEncoder(columns=["level_2", "level_3"]).fit(frame)
        decoded = enc.inverse_transform(enc.transform(frame))
        assert decoded.rows() == frame.rows()

    def test_null_labels_become_a_class_as_in_source(self):
        """Characterisation of source behaviour: sklearn's LabelEncoder accepts None
        as a class.

        The encoder does not reject nulls, so validate_source must catch them
        upstream if needed.
        """
        frame = pl.DataFrame({"level_2": ["a", None]})
        enc = port.MultiColumnLabelEncoder(columns=["level_2"]).fit(frame)
        assert list(enc.encoders["level_2"].classes_) == ["a", None]


class TestSaveResultsToDb:
    @pytest.mark.xfail(
        strict=True,
        reason=(
            "Source defect: functions.py save_results_to_db has no semicolon after "
            "CREATE TABLE, so DuckDB rejects 'TRUNCATE' (ParserException). Confirmed "
            "under the source's pinned duckdb 1.4.1. Port keeps the verbatim source "
            "text; proposed fix is a ';' after the CREATE statement."
        ),
    )
    def test_writes_results_table(self, tmp_path):
        port.configure_paths(tmp_path, tmp_path, "results.duckdb")
        results = pl.DataFrame({"parsid": ["1", "2"], "level_2": ["a", "b"]})
        port.save_results_to_db(results, duck_db="results.duckdb")
        con = duckdb.connect(str(tmp_path / "results.duckdb"), read_only=True)
        try:
            rows = con.execute(
                "SELECT parsid, level_2 FROM results ORDER BY parsid"
            ).fetchall()
        finally:
            con.close()
        assert rows == [("1", "a"), ("2", "b")]


def test_concatenate_keeps_each_project_contiguous_with_its_own_ancestors():
    """Interleaved rows from two projects must not share ancestor context.

    Without the parsid sort, a child takes its ancestor title from whichever project's
    root came last in the input (for example "P1 root | P2 child a").
    """
    text_data = pl.DataFrame(
        {
            "parsid": [2, 1, 2, 1, 2, 1],
            "wbs": ["01", "01", "01.01", "01.01", "01.02", "01.02"],
            "wbs_title": [
                "P2 root",
                "P1 root",
                "P2 child a",
                "P1 child a",
                "P2 child b",
                "P1 child b",
            ],
            "wbs_level": [2, 2, 3, 3, 3, 3],
        }
    )
    out = port.concatenate_data(
        text_data,
        text_field="wbs_title",
        level_field="wbs_level",
        starting_level=2,
        with_dates=False,
    )
    rows = out.select(["parsid", "original_title", "wbs_title"]).rows()
    assert [r[0] for r in rows] == [1, 1, 1, 2, 2, 2]
    assert [r[1] for r in rows] == [
        "P1 root",
        "P1 child a",
        "P1 child b",
        "P2 root",
        "P2 child a",
        "P2 child b",
    ]
    assert [r[2] for r in rows] == [
        "P1 root",
        "P1 root | P1 child a",
        "P1 root | P1 child b",
        "P2 root",
        "P2 root | P2 child a",
        "P2 root | P2 child b",
    ]


def test_stratify_is_reproducible_under_a_seeded_global_rng(tmp_path):
    """Same input order and same global seed give the same split (source semantics)."""
    fixture = build_contract_fixture(tmp_path / "fixture.duckdb")
    con = duckdb.connect(str(fixture), read_only=True)
    try:
        gold = con.execute("SELECT * FROM gold_corrections").pl()
    finally:
        con.close()
    cleaned = port.clean_stitch(
        port.concatenate_data(
            gold,
            text_field="wbs_title",
            starting_level=2,
            level_field="wbs_level",
            with_dates=False,
        ),
        text_field="wbs_title",
        stop_words=pl.DataFrame({"word": ["zzz"]}),
        stop_phrases=pl.DataFrame({"word": ["zzz"]}),
        abbreviations=pl.DataFrame({"abbreviation": ["zz"], "definition": ["zzz"]}),
        project_descriptions=pl.DataFrame(
            {"parsid": [1], "program": ["p"], "project_name": ["n"]}
        ).with_columns(pl.col("parsid").cast(pl.Int64)),
    ).sort(["parsid", "wbs", "wbs_title"])
    port.configure_paths(tmp_path, tmp_path, "unused.duckdb")
    hierarchies = [
        "level_2",
        "level_3",
        "level_4",
        "level_5",
        "level_6",
        "level_7",
        "level_8",
    ]
    y = port.encode_labels(str(tmp_path), cleaned, hierarchies)[0]
    np.random.seed(7)
    first = port.stratify(cleaned, y, text_field="wbs_title", test_size=0.2)
    np.random.seed(7)
    second = port.stratify(cleaned, y, text_field="wbs_title", test_size=0.2)
    for a, b in zip(first, second):
        assert np.array_equal(np.asarray(a, dtype=object), np.asarray(b, dtype=object))
