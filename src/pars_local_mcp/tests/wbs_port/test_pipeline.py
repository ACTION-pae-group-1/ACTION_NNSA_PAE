"""Orchestration tests for wbs_port.pipeline.

No MCP transport here; see mcp/test_wbs_tools.py for that. Covers input validation
against the source contract, run identifiers, stage dependencies, and a full offline
run during which every socket connection attempt is blocked.
"""

from __future__ import annotations

import socket

import joblib
import numpy as np
import polars as pl
import pytest

from pars_local_mcp.wbs_port import pipeline as P
from pars_local_mcp.wbs_port.contract_fixture import (
    MOCK_DB,
    build_contract_fixture,
    build_nonconforming_copy,
)

pytestmark = pytest.mark.slow

KEY = b"k" * 32


@pytest.fixture(scope="module")
def fixture_db(tmp_path_factory):
    return build_contract_fixture(
        tmp_path_factory.mktemp("fx") / "contract_fixture.duckdb"
    )


@pytest.fixture(scope="module")
def nonconforming_db(fixture_db, tmp_path_factory):
    return build_nonconforming_copy(
        fixture_db, tmp_path_factory.mktemp("bad") / "nonconforming.duckdb"
    )


def test_bundled_mock_passes_the_contract():
    report = P.validate_source(MOCK_DB)
    assert report["ok"] is True, report["problems"]
    assert report["data_origin"] == "synthetic_mock"


def test_fixture_passes_the_contract(fixture_db):
    report = P.validate_source(fixture_db)
    assert report["ok"] is True, report["problems"]
    assert report["data_origin"] == "labeled_test_fixture"


def test_nonconforming_source_reports_one_precise_problem(nonconforming_db):
    report = P.validate_source(nonconforming_db)
    assert report["ok"] is False
    assert report["data_origin"] == "labeled_test_fixture"
    assert len(report["problems"]) == 1, report["problems"]
    assert report["problems"][0].startswith("silver_spae_data.wbs_level: ")


def test_missing_database_is_reported_not_created(tmp_path):
    report = P.validate_source(tmp_path / "absent.duckdb")
    assert report["ok"] is False
    assert not (tmp_path / "absent.duckdb").exists()


def test_clean_refuses_a_contract_violating_source(tmp_path, nonconforming_db):
    with pytest.raises(P.WBSPipelineError, match="fails the WBS input contract"):
        P.stage_clean(tmp_path / "runs", None, nonconforming_db)


@pytest.mark.parametrize(
    "bad", ["", "../escape", "R123", "r12345678901", "rZZZZZZZZZZZZ"]
)
def test_run_id_must_match_expected_format(tmp_path, bad):
    with pytest.raises(P.WBSPipelineError):
        P.run_dir_for(tmp_path, bad)


def test_new_run_ids_are_valid_and_unique():
    ids = {P.new_run_id() for _ in range(50)}
    assert len(ids) == 50
    for run_id in ids:
        P.run_dir_for("unused", run_id)


def test_downstream_stages_require_upstream_completion(tmp_path, fixture_db):
    stage = P.stage_clean(tmp_path / "runs", None, fixture_db)
    run_id = stage["run_id"]
    with pytest.raises(P.WBSPipelineError, match="'clean'|tune_train"):
        P.stage_predict(
            tmp_path / "runs", run_id, signing_key=KEY
        )  # tune_train has not run
    with pytest.raises(P.WBSPipelineError, match="predict"):
        P.stage_write_back(tmp_path / "runs", run_id)


def test_unknown_model_variant_is_rejected(tmp_path):
    with pytest.raises(P.WBSPipelineError, match="model_variant"):
        P.stage_predict(
            tmp_path / "runs", "r0123456789ab", signing_key=KEY, model_variant="bogus"
        )


def test_full_chain_runs_offline(tmp_path, fixture_db, monkeypatch):
    """Every network entry point is blocked for the duration of the run."""

    def _blocked(*args, **kwargs):
        raise AssertionError("network access attempted during the offline WBS run")

    monkeypatch.setattr(socket.socket, "connect", _blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    monkeypatch.setattr(socket, "getaddrinfo", _blocked)

    result = P.run_pipeline(
        tmp_path / "runs", fixture_db, signing_key=KEY, n_iter=2, cv_folds=3, n_jobs=1
    )
    stages = result["stages"]
    assert stages["write_back"]["read_back_verified"] is True
    assert stages["predict"]["predicted_rows"] == stages["write_back"]["mapped_rows"]
    assert (
        P.run_status(tmp_path / "runs", result["run_id"])["stages"]["write_back"][
            "status"
        ]
        == "ok"
    )


def _toy_rows(n_titles=60, copies=4, n_levels=3, seed=0):
    """Each title appears once per project (copies) with the same labels."""
    rng = np.random.default_rng(seed)
    labels = rng.integers(0, 4, size=(n_titles, n_levels)).astype(np.int32)
    titles = np.repeat(np.array([f"title {i}" for i in range(n_titles)]), copies)
    return titles, np.repeat(labels, copies, axis=0)


def test_title_grouped_split_keeps_each_title_on_one_side():
    titles, y = _toy_rows()
    train, test = P._title_grouped_split(titles, y, test_size=0.2)
    assert not set(titles[train]) & set(titles[test])
    assert int(train.sum() + test.sum()) == len(titles)
    assert 0.1 < test.mean() < 0.3


def test_title_grouped_folds_hold_out_whole_titles_and_cover_every_row_once():
    titles, y = _toy_rows()
    folds = P._title_grouped_folds(titles, y, n_splits=3)
    assert len(folds) == 3
    held_out = []
    for train, val in folds:
        assert not set(titles[train]) & set(titles[val])
        held_out.extend(val.tolist())
    assert sorted(held_out) == list(range(len(titles)))


def test_cv_scorer_casts_string_predictions_to_label_dtype():
    y_true = np.array([[1, 2], [3, 4]], dtype=np.int32)
    y_pred = np.array([["1", "2"], ["3", "4"]])
    assert P._cast_f1(y_true, y_pred) == pytest.approx(1.0)


def test_tune_split_and_cv_never_share_a_title(tmp_path, fixture_db):
    runs = tmp_path / "runs"
    rid = P.stage_clean(runs, None, fixture_db)["run_id"]
    tune = P.stage_tune_train(
        runs, rid, signing_key=KEY, n_iter=2, cv_folds=3, n_jobs=1
    )
    run_dir = P.run_dir_for(runs, rid)
    X_train = joblib.load(run_dir / "X_train.pkl")
    X_test = joblib.load(run_dir / "X_test.pkl")
    assert not set(X_train) & set(X_test)
    # Dummy data: only check the scorer is not returning the 0.0 fold default.
    assert tune["tuned_cv_best_score"] > 0.0


def test_level_offsets_keep_codes_from_different_levels_apart():
    frame = pl.DataFrame({"level_2": ["a", "b"], "level_3": ["a", "c"]})
    encoder = P.wbs.MultiColumnLabelEncoder(columns=["level_2", "level_3"]).fit(frame)
    raw = encoder.transform(frame).to_numpy()
    offsets = P._level_offsets(encoder)
    assert offsets.tolist() == [0, 2]
    shifted = raw + offsets
    assert not set(shifted[:, 0]) & set(shifted[:, 1])
    assert (shifted - offsets == raw).all()
