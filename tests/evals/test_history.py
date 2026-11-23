"""Longitudinal reporting reads existing records without changing them."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from eval.bls.graders import Check
from eval.bls.history import history_rows, render_csv, render_markdown
from eval.bls.recording import EpisodeResult, RunMetadata, load_runs, record_run
from eval.bls.transcript import Transcript


def test_history_rows_and_export(tmp_path: Path) -> None:
    good = EpisodeResult(
        "basket", "agent", [Check("factor", "accuracy", True)], Transcript()
    )
    bad = EpisodeResult(
        "basket", "agent", [Check("factor", "accuracy", False)], Transcript()
    )
    outage = EpisodeResult(
        "basket", "agent", [], Transcript(), infrastructure_error="503"
    )
    folder = record_run(
        RunMetadata(
            "model", "model", model={"provider": "asksage", "name": "sample-gov"}
        ),
        [good, bad, outage],
        runs_dir=tmp_path,
    )
    original = (folder / "run.json").read_bytes()
    rows = history_rows(load_runs(tmp_path))
    assert len(rows) == 2
    suite, case = rows
    assert suite["case_id"] == "__suite__"
    assert (suite["episodes"], suite["scored"], suite["infrastructure_errors"]) == (
        3,
        2,
        1,
    )
    assert suite["success_rate"] == 0.5
    assert suite["accuracy_rate"] == 0.5
    assert suite["process_rate"] is None
    assert suite["model"] == "sample-gov"
    assert (case["case_id"], case["scored"], case["success_rate"]) == ("basket", 2, 0.5)
    assert case["infrastructure_errors"] == ""
    csv_rows = list(csv.DictReader(io.StringIO(render_csv(rows))))
    assert len(csv_rows) == 2
    assert csv_rows[0]["success_rate"] == "0.5"
    assert "50.0%" in render_markdown(rows)
    assert (folder / "run.json").read_bytes() == original


def test_history_handles_unscored_and_empty_runs(tmp_path: Path) -> None:
    assert history_rows([]) == []
    outage = EpisodeResult(
        "basket", "agent", [], Transcript(), infrastructure_error="timeout"
    )
    folder = record_run(RunMetadata("model", "model"), [outage], runs_dir=tmp_path)
    rows = history_rows([json.loads((folder / "run.json").read_text())])
    assert len(rows) == 1  # no scored case rows
    assert rows[0]["success_rate"] is None
    assert rows[0]["infrastructure_errors"] == 1
