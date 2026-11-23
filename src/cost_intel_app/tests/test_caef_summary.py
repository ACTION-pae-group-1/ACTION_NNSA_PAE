"""Read-only CAEF summary and visible UI integration tests."""

import asyncio
import json

from fastmcp import Client

from cost_intel_app.caef_summary import empty_caef_summary, summarize_predictions
from cost_intel_app.server import mcp


def test_classification_is_project_scoped_and_not_weighted():
    rows = [
        {"parsid": "12", "level_2": "construction", "level_3": "steel"},
        {"parsid": "12", "level_2": "construction", "level_3": "steel"},
        {"parsid": "12", "level_2": ""},
        {"parsid": "99", "level_2": "unrelated"},
    ]
    summary = summarize_predictions(rows, "12")
    assert summary["coverage"] == "Saved predictions: 2 of 3 WBS elements classified"
    assert summary["categories"][0]["label"] == "steel: 2 WBS elements"
    assert summary["state"] == "loaded"
    assert "weight" not in json.dumps(summary)


def test_missing_project_has_explicit_unavailable_state():
    assert summarize_predictions([], "12")["state"] == "unavailable"
    assert empty_caef_summary()["state"] == "unavailable"
    assert empty_caef_summary()["message"].startswith("No saved CAEF 2.0 predictions")


def test_result_source_label_distinguishes_new_run_from_saved(tmp_path):
    import polars as pl

    from cost_intel_app import caef_summary as caef

    path = tmp_path / "predicted_levels.parquet"
    pl.DataFrame(
        {
            "parsid": ["12", "12", "99"],
            "level_2": ["construction", "construction", "unrelated"],
            "level_3": ["steel", "", ""],
            "level_4": ["", "", ""],
            "level_5": ["", "", ""],
            "level_6": ["", "", ""],
            "level_7": ["", "", ""],
            "level_8": ["", "", ""],
        }
    ).write_parquet(path)
    saved = caef.read_caef_summary(str(path), "12")
    new = caef.read_caef_summary(str(path), "12", caef.SOURCE_NEW)
    assert saved["coverage"].startswith("Saved predictions: ")
    assert new["coverage"].startswith("Newly generated predictions: ")
    assert saved["coverage"].endswith("2 of 2 WBS elements classified")
    assert new["state"] == "loaded"


def test_ui_exposes_description_caef_and_optional_index_review():
    async def open_app():
        async with Client(mcp) as client:
            response = await client.call_tool("ppi_basket", {})
            return json.dumps(response.structured_content["view"])

    encoded = asyncio.run(open_app())
    assert "Project description" in encoded
    assert "Project CAEF 2.0 mapping" in encoded
    assert "Optional economic index review" in encoded
    assert "load_caef_mapping_summary" in encoded
    assert "No actual PARS project costs" in encoded


def test_selected_pars_project_description_uses_source_record(monkeypatch):
    from contextlib import contextmanager

    from cost_intel_app import server

    @contextmanager
    def session():
        yield object()

    monkeypatch.setattr(server, "_pars_session", session)
    monkeypatch.setattr(
        server.pars_panels,
        "project_header",
        lambda *_: {"state": "loaded", "name": "Project 12", "summary": "2 elements"},
    )
    monkeypatch.setattr(
        server.pars_panels,
        "evidence",
        lambda *_: {
            "state": "loaded",
            "ok": True,
            "read_only_views": True,
            "origin": "synthetic_mock",
            "label": "Synthetic fixture",
        },
    )
    monkeypatch.setattr(
        server.pars_panels,
        "project_roots",
        lambda *_: {"state": "loaded", "rows": []},
    )
    monkeypatch.setattr(
        server.pars_panels,
        "leaf_nodes",
        lambda *_: {"state": "loaded", "rows": []},
    )
    monkeypatch.setattr(
        server.pars_panels,
        "read_only_data",
        lambda *_args, **_kwargs: {
            "state": "loaded",
            "rows": [
                {"parsid": "99", "project_description": "Wrong project"},
                {"parsid": "12", "project_description": "Project narrative"},
            ],
        },
    )
    state = server.load_pars_context("12")
    assert state["description"] == "Project narrative"
    assert state["description_status"] == ""
    assert state["project_id"] == "12"


def test_browser_contrast_selectors_are_explicit():
    from cost_intel_app.server import _CARD_TEXT

    assert "[&_label]:!text-slate-100" in _CARD_TEXT
    assert "recharts-cartesian-axis-tick_text" in _CARD_TEXT


def test_saved_results_default_to_packaged_file(monkeypatch, tmp_path):
    from cost_intel_app import caef_summary as caef

    monkeypatch.delenv("CAEF_PREDICTIONS_FILE", raising=False)
    monkeypatch.setattr(caef, "_DEMO_DIR", tmp_path)
    assert caef.saved_prediction_path() == ""
    (tmp_path / "predicted_levels.parquet").write_bytes(b"test")
    assert caef.saved_prediction_path() == str(tmp_path / "predicted_levels.parquet")
    monkeypatch.setenv("CAEF_PREDICTIONS_FILE", str(tmp_path / "alternative.parquet"))
    assert caef.saved_prediction_path() == str(tmp_path / "alternative.parquet")


def test_model_refuses_missing_or_non_synthetic_bundle(monkeypatch, tmp_path):
    import json

    from cost_intel_app import caef_summary as caef

    monkeypatch.setattr(caef, "_DEMO_DIR", tmp_path)
    assert caef.run_model_for_project("proj_001")["state"] == "unavailable"
    (tmp_path / "r0123456789ab").mkdir()
    (tmp_path / "demo_verification.key").write_bytes(b"k" * 32)
    (tmp_path / "demo_run.json").write_text(
        json.dumps(
            {
                "run_id": "r0123456789ab",
                "data_origin": "live_pars",
                "stages": {"tune_train": {"status": "ok"}},
            }
        )
    )
    assert caef._bundled_run() is None


def test_ui_exposes_separate_saved_and_run_model_actions():
    import inspect

    from cost_intel_app import server

    source = inspect.getsource(server._context_rail)
    assert "View saved CAEF mapping" in source
    assert "Run model on bundled data" in source
    assert "run_caef_mapping_model" in source
