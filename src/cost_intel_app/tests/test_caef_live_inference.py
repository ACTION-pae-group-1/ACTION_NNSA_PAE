"""Inference-only CAEF text adapter tests (real packaged model, read-only data)."""

from pathlib import Path

import polars as pl
import pytest

from cost_intel_app import caef_live_inference as A
from cost_intel_app.caef_summary import empty_caef_summary

PACK = Path(A.__file__).resolve().parent / "demo_assets" / "caef" / "r8fec4416f3d5"


@pytest.fixture(scope="module")
def project_100_source() -> pl.DataFrame:
    """Training source rows for project 100, stored order (codes may repeat)."""
    import duckdb

    con = duckdb.connect(str(PACK / "working.duckdb"), read_only=True)
    try:
        return con.execute(
            "SELECT parsid, wbs, wbs_title, wbs_level FROM gold_corrections "
            "WHERE CAST(parsid AS VARCHAR) = '100'"
        ).pl()
    finally:
        con.close()


@pytest.fixture(scope="module")
def project_100_training_text() -> pl.DataFrame:
    import duckdb

    con = duckdb.connect(str(PACK / "working.duckdb"), read_only=True)
    try:
        return con.execute(
            "SELECT CAST(parsid AS VARCHAR) AS parsid, wbs, original_title, wbs_title, "
            "level_2, level_3, level_4, level_5, level_6, level_7, level_8 "
            "FROM silver_cleaned_concat_sample WHERE CAST(parsid AS VARCHAR) = '100'"
        ).pl()
    finally:
        con.close()


def test_training_text_reproduced_exactly_for_project_100(
    project_100_source, project_100_training_text
):
    cleaned = A.prepare_text(project_100_source, validate=False)
    cleaned = cleaned.unique(subset=["wbs_title", "parsid"], maintain_order=True)
    adapter = set(
        map(tuple, cleaned.select(["wbs", "original_title", "wbs_title"]).rows())
    )
    training = set(
        map(
            tuple,
            project_100_training_text.select(
                ["wbs", "original_title", "wbs_title"]
            ).rows(),
        )
    )
    assert adapter == training
    assert len(training) == 834


def test_project_100_predictions_keyed_to_source_wbs_and_fit_training_labels(
    project_100_source, project_100_training_text
):
    cleaned = A.prepare_text(project_100_source, validate=False)
    cleaned = cleaned.unique(subset=["wbs_title", "parsid"], maintain_order=True)
    pred = A.predict_text(cleaned, "100")
    assert pred.height == 834
    assert set(pred["wbs"].to_list()) <= set(project_100_source["wbs"].to_list())
    joined = pred.join(
        project_100_training_text.select(["wbs", "original_title", *A.LEVELS]),
        on=["wbs", "original_title"],
        how="inner",
        suffix="_t",
    )
    assert joined.height == 834
    # Fit check against training rows' own labels (training-set fit only).
    level_2_agreement = (
        joined.filter(pl.col("level_2") == pl.col("level_2_t")).height / joined.height
    )
    assert level_2_agreement >= 0.95


def test_proj_001_identifiers_and_count():
    summary = A.predict_live_project("proj_001")
    assert summary["state"] == "loaded"
    rows = pl.DataFrame(summary["rows"])
    raw = A.load_live_project("proj_001")
    expected = set(raw.filter(pl.col("wbs_level") >= 2)["wbs"].to_list())
    assert rows.height == 33 == len(expected)
    assert set(rows["wbs"].to_list()) == expected
    assert set(rows["parsid"].to_list()) == {"proj_001"}


def test_proj_002_identifiers_and_count():
    summary = A.predict_live_project("proj_002")
    assert summary["state"] == "loaded"
    rows = pl.DataFrame(summary["rows"])
    raw = A.load_live_project("proj_002")
    expected = set(raw.filter(pl.col("wbs_level") >= 2)["wbs"].to_list())
    assert rows.height == 24 == len(expected)
    assert set(rows["wbs"].to_list()) == expected
    assert set(rows["parsid"].to_list()) == {"proj_002"}


def test_switching_projects_has_no_carry_over():
    first = A.predict_live_project("proj_001")["rows"]
    other = A.predict_live_project("proj_002")["rows"]
    again = A.predict_live_project("proj_001")["rows"]
    assert first == again
    assert {r["parsid"] for r in other} == {"proj_002"}
    assert {r["wbs"] for r in other} == set(
        A.load_live_project("proj_002")
        .filter(pl.col("wbs_level") >= 2)["wbs"]
        .to_list()
    )


def test_ancestor_text_matches_wbs_code_prefixes():
    import contextlib
    import io

    from pars_local_mcp.wbs_port import functions as wbs

    raw = A.load_live_project("proj_001")
    title = dict(zip(raw["wbs"].to_list(), raw["wbs_title"].to_list()))
    df = raw.select(
        pl.lit(1, dtype=pl.Int64).alias("parsid"),
        "wbs",
        "wbs_title",
        pl.col("wbs_level").cast(pl.Int64),
    )
    with contextlib.redirect_stdout(io.StringIO()):
        cc = wbs.concatenate_data(
            df,
            text_field="wbs_title",
            starting_level=2,
            level_field="wbs_level",
            with_dates=False,
        )
    for row in cc.to_dicts():
        segs = row["wbs"].split(".")
        for k in range(2, row["wbs_level"] + 1):
            assert (
                str(row[f"wbs_level_{k}"]).strip()
                == str(title[".".join(segs[:k])]).strip()
            )


def test_missing_title_is_a_controlled_error():
    rows = pl.DataFrame({"wbs": ["01.01"], "wbs_title": [None], "wbs_level": [2]})
    with pytest.raises(A.CAEFAdapterError, match="no title"):
        A.prepare_text(rows)


def test_missing_required_field_is_a_controlled_error():
    rows = pl.DataFrame({"wbs": ["01.01"], "wbs_level": [2]})
    with pytest.raises(A.CAEFAdapterError, match="missing required WBS fields"):
        A.prepare_text(rows)


def test_level_gap_is_a_controlled_error():
    rows = pl.DataFrame(
        {"wbs": ["01.01", "01.01.01.01"], "wbs_title": ["a", "b"], "wbs_level": [2, 4]}
    )
    with pytest.raises(A.CAEFAdapterError, match="missing level"):
        A.prepare_text(rows)


def test_no_level_two_rows_is_a_controlled_error():
    rows = pl.DataFrame({"wbs": ["01"], "wbs_title": ["a"], "wbs_level": [1]})
    with pytest.raises(A.CAEFAdapterError, match="level 2 or below"):
        A.prepare_text(rows)


def test_invalid_project_id_returns_unavailable_summary():
    summary = A.predict_live_project("../etc")
    assert summary == empty_caef_summary("Choose a valid PARS project first.")


def test_unknown_project_returns_unavailable_summary():
    summary = A.predict_live_project("proj_999")
    assert summary["state"] == "unavailable"
    assert "not found" in summary["message"]


def test_missing_model_artifact_is_a_controlled_error(tmp_path):
    with pytest.raises(A.CAEFAdapterError, match="not available"):
        A._load_model(root=tmp_path)


def test_wrong_verification_key_is_a_controlled_error():
    with pytest.raises(A.CAEFAdapterError, match="could not be verified"):
        A._load_model(key=b"x" * 32)


def test_inference_error_is_contained(monkeypatch):
    def boom(*_args, **_kwargs):
        raise RuntimeError("internal detail that must not leak")

    monkeypatch.setattr(A, "predict_text", boom)
    summary = A.predict_live_project("proj_001")
    assert summary["state"] == "unavailable"
    assert "internal detail" not in summary["message"]


def test_model_receives_only_the_text_column(monkeypatch):
    seen = {}
    model, encoder = A._model()

    class Spy:
        def predict(self, values):
            seen["dtype"] = str(values.dtype)
            return model.predict(values)

    monkeypatch.setattr(A, "_model", lambda: (Spy(), encoder))
    A.predict_live_project("proj_002")
    assert seen["dtype"] == "String"


def test_reference_tables_are_global():
    refs = A._refs()
    for name, frame in refs.items():
        assert "parsid" not in frame.columns, name
    assert refs["abbreviations"].height == 500
    assert refs["stop_words"].height == 500
    assert refs["stop_phrases"].height == 500
