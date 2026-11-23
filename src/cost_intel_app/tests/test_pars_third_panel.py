"""Third panel (Project & evidence): project scoping, missing data, invalid IDs,
CAEF saved and unavailable states, the read-only guard, and the optional BLS review.

Every test uses a faked PARS session or temporary files. No PARS data is changed.
"""

import hashlib
import inspect
import json
from contextlib import contextmanager

import pytest

from cost_intel_app import basket_state, server
from cost_intel_app import caef_summary as caef
from cost_intel_app import pars_panels as pp

PROJECTS = {
    "proj_001": {"name": "Alpha Stadium", "total": 3, "depth": 2},
    "proj_002": {"name": "Beta Expansion", "total": 2, "depth": 2},
    "proj_003": {"name": "Empty Project", "total": 0, "depth": 0},
}
LEAVES = {
    "proj_001": [("01.01", "Alpha foundations"), ("01.02", "Alpha roof")],
    "proj_002": [("01.01", "Beta drainage")],
    "proj_003": [],
}
LEVELS = {
    "proj_001": [
        {"wbs_code": "01", "title": "Alpha program", "level": 1, "parent_wbs": ""},
        {
            "wbs_code": "01.01",
            "title": "Alpha foundations",
            "level": 2,
            "parent_wbs": "01",
        },
        {"wbs_code": "01.02", "title": "Alpha roof", "level": 2, "parent_wbs": "01"},
    ],
    "proj_002": [
        {"wbs_code": "01", "title": "Beta program", "level": 1, "parent_wbs": ""},
        {"wbs_code": "01.01", "title": "Beta drainage", "level": 2, "parent_wbs": "01"},
    ],
    "proj_003": [],
}
DESCRIPTIONS = [
    {"parsid": "proj_002", "project_description": "Beta narrative"},
    {"parsid": "proj_001", "project_description": "Alpha narrative"},
]
EVIDENCE_OK = {
    "data_origin": "synthetic_mock",
    "ok": True,
    "problems": [],
    "tables": {"gold_corrections": {"rows": 1}},
}


class ProjectsFake:
    """Stands in for a live PARS session: answers read tools per project.

    It also records each call.
    """

    def __init__(self, fail=(), descriptions=DESCRIPTIONS):
        self.fail = set(fail)
        self.descriptions = list(descriptions)
        self.calls = []

    def call(self, tool, arguments):
        self.calls.append((tool, dict(arguments)))
        if tool in self.fail:
            return {"error": "simulated failure"}
        pid = arguments.get("project_id")
        if tool == "get_project_info":
            info = PROJECTS.get(pid)
            if info is None:
                return {"error": f"Project {pid} not found"}
            return {
                "parsid": pid,
                "project_name": info["name"],
                "total_elements": info["total"],
                "hierarchy_depth": info["depth"],
            }
        if tool == "validate_wbs_inputs":
            return EVIDENCE_OK
        if tool == "get_leaf_nodes":
            return {
                "leaf_nodes": [
                    {"wbs_code": c, "title": t, "level": c.count(".") + 1}
                    for c, t in LEAVES.get(pid, [])
                ]
            }
        if tool == "get_wbs_by_level":
            rows = [r for r in LEVELS.get(pid, []) if r["level"] == arguments["level"]]
            return {"elements": [dict(r) for r in rows]}
        if tool == "get_wbs_hierarchy":
            title = dict(LEAVES.get(pid, [])).get(arguments["wbs_code"], "")
            return {
                "element": {
                    "wbs_code": arguments["wbs_code"],
                    "title": title,
                    "level": 2,
                    "leaf_node": True,
                },
                "children": [],
            }
        if tool == "get_wbs_project_descriptions":
            return {
                "columns": ["parsid", "project_description"],
                "rows": self.descriptions,
                "total_rows": len(self.descriptions),
            }
        raise AssertionError(f"unexpected PARS tool in test: {tool}")


def use_session(monkeypatch, fake, opened=None):
    @contextmanager
    def session():
        if opened is not None:
            opened.append(True)
        yield fake

    monkeypatch.setattr(server, "_pars_session", session)


def codes(state):
    return [c["wbs_code"] for c in state["wbs_choices"]]


# --- project scoping -------------------------------------------------------------


def test_each_selected_project_shows_only_its_own_wbs(monkeypatch):
    fake = ProjectsFake()
    use_session(monkeypatch, fake)
    one = server.load_pars_context("proj_001")
    assert one["state"] == "loaded"
    assert one["project_id"] == "proj_001"
    assert codes(one) == ["01.01", "01.02"]
    assert [c["label"] for c in one["wbs_choices"]] == [
        "01.01 — Alpha foundations",
        "01.02 — Alpha roof",
    ]

    before = len(fake.calls)
    two = server.load_pars_context("proj_002")
    assert two["state"] == "loaded"
    assert two["project_id"] == "proj_002"
    assert [c["label"] for c in two["wbs_choices"]] == ["01.01 — Beta drainage"]
    assert "Alpha" not in json.dumps(two)
    assert [r["wbs_code"] for r in two["roots"] if r["visible"]] == ["01"]
    # Every PARS call made for proj_002 carries proj_002, never proj_001.
    sent = [a["project_id"] for _, a in fake.calls[before:] if "project_id" in a]
    assert sent and set(sent) == {"proj_002"}


def test_description_is_matched_by_parsid_not_by_row_order(monkeypatch):
    use_session(monkeypatch, ProjectsFake(descriptions=DESCRIPTIONS))
    assert server.load_pars_context("proj_001")["description"] == "Alpha narrative"
    reversed_rows = list(reversed(DESCRIPTIONS))
    use_session(monkeypatch, ProjectsFake(descriptions=reversed_rows))
    assert server.load_pars_context("proj_001")["description"] == "Alpha narrative"


def test_a_failed_second_load_leaves_no_first_project_data(monkeypatch):
    use_session(monkeypatch, ProjectsFake())
    assert codes(server.load_pars_context("proj_001")) == ["01.01", "01.02"]
    use_session(monkeypatch, ProjectsFake(fail={"get_leaf_nodes"}))
    failed = server.load_pars_context("proj_002")
    assert failed["state"] == "error"
    assert failed["message"] == "PARS WBS elements are unavailable."
    assert failed["project_id"] == ""
    assert failed["wbs_choices"] == []
    assert "Alpha" not in json.dumps(failed)


# --- missing WBS data --------------------------------------------------------------


def test_failed_roots_load_gives_a_clear_message_and_no_elements(monkeypatch):
    use_session(monkeypatch, ProjectsFake(fail={"get_wbs_by_level"}))
    state = server.load_pars_context("proj_001")
    assert state["state"] == "error"
    assert state["message"] == pp.FAILED_LEVEL
    assert state["wbs_choices"] == []


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Known gap: a project with zero WBS elements loads as 'loaded' with no "
        "message; the third panel shows an empty list. server.load_pars_context "
        "needs an explicit 'no WBS elements' message."
    ),
)
def test_project_with_no_wbs_elements_shows_a_message(monkeypatch):
    use_session(monkeypatch, ProjectsFake())
    state = server.load_pars_context("proj_003")
    assert state["message"] != ""
    assert state["state"] != "loaded"


# --- invalid project IDs -----------------------------------------------------------


@pytest.mark.parametrize("pid", ["", "   "])
def test_blank_project_id_is_refused_without_a_pars_session(monkeypatch, pid):
    opened = []
    use_session(monkeypatch, ProjectsFake(), opened)
    state = server.load_pars_context(pid)
    assert state["state"] == "error"
    assert state["message"] == "Choose a project."
    assert state["wbs_choices"] == []
    assert opened == []


def test_unknown_project_id_is_a_clear_error_with_no_wbs_data(monkeypatch):
    fake = ProjectsFake()
    use_session(monkeypatch, fake)
    state = server.load_pars_context("proj_999")
    assert state["state"] == "error"
    assert state["message"] == "PARS could not load this project."
    assert state["project_id"] == ""
    assert state["wbs_choices"] == []
    assert all(not r["visible"] for r in state["roots"])
    # Only proj_999 is ever sent; no other project's data is requested.
    sent = {a["project_id"] for _, a in fake.calls if "project_id" in a}
    assert sent == {"proj_999"}


def test_overlong_project_id_is_refused_without_a_pars_session(monkeypatch):
    opened = []
    use_session(monkeypatch, ProjectsFake(), opened)
    state = server.load_pars_context("x" * 129)
    assert state["message"] == "Enter a PARS project ID of 128 characters or fewer."
    assert opened == []


@pytest.mark.parametrize("pid", ["", "   ", "x" * 129])
def test_caef_summary_refuses_blank_or_overlong_ids(pid):
    state = server.load_caef_mapping_summary(pid)
    assert state["state"] == "unavailable"
    assert state["categories"] and not any(c["visible"] for c in state["categories"])


# --- CAEF saved and unavailable states (missing model artifacts) -------------------


@pytest.fixture
def no_caef_files(monkeypatch, tmp_path):
    monkeypatch.delenv("CAEF_PREDICTIONS_FILE", raising=False)
    monkeypatch.setattr(caef, "_DEMO_DIR", tmp_path)
    return tmp_path


def test_no_prediction_file_gives_the_build_wording(no_caef_files):
    state = server.load_caef_mapping_summary("proj_001")
    assert state["state"] == "unavailable"
    assert (
        state["message"] == "No saved CAEF 2.0 predictions are included in this build."
    )
    assert state["coverage"] == ""


def test_configured_but_missing_file_is_unavailable(monkeypatch, no_caef_files):
    monkeypatch.setenv("CAEF_PREDICTIONS_FILE", str(no_caef_files / "absent.parquet"))
    state = server.load_caef_mapping_summary("proj_001")
    assert state["state"] == "unavailable"
    assert state["message"] == "Configured CAEF prediction file is unavailable."


def test_run_model_without_a_bundle_writes_nothing_and_says_so(
    no_caef_files, monkeypatch, tmp_path
):
    from cost_intel_app import caef_live_inference as live

    # Other tests may have cached a loaded model; start from an empty cache.
    monkeypatch.setattr(live, "_CACHE", {})
    monkeypatch.setattr(live, "STADIUM_BUNDLE", tmp_path / "absent-bundle")
    state = server.run_caef_mapping_model("proj_001")
    assert state["state"] == "unavailable"
    assert state["message"] == (
        "The packaged CAEF model is not included. "
        "Saved results remain available if provided."
    )
    assert list(no_caef_files.iterdir()) == []


def test_corrupt_prediction_file_is_unavailable_without_its_text(
    monkeypatch, no_caef_files
):
    path = no_caef_files / "predicted_levels.parquet"
    path.write_bytes(b"not a parquet file")
    monkeypatch.setenv("CAEF_PREDICTIONS_FILE", str(path))
    state = server.load_caef_mapping_summary("proj_001")
    assert state["state"] == "unavailable"
    assert state["message"] == "Could not read the completed CAEF predictions."


def test_saved_predictions_are_scoped_to_the_selected_project(
    monkeypatch, no_caef_files
):
    import polars as pl

    path = no_caef_files / "predicted_levels.parquet"
    levels = {f"level_{n}": [""] * 3 for n in range(2, 9)}
    pl.DataFrame(
        {
            "parsid": ["proj_001", "proj_001", "proj_002"],
            "level_2": ["alpha_class", "alpha_class", "beta_class"],
            **{k: v for k, v in levels.items() if k != "level_2"},
        }
    ).write_parquet(path)
    monkeypatch.setenv("CAEF_PREDICTIONS_FILE", str(path))
    two = server.load_caef_mapping_summary("proj_002")
    assert two["state"] == "loaded"
    assert two["coverage"] == "Saved predictions: 1 of 1 WBS elements classified"
    labels = [c["label"] for c in two["categories"] if c["visible"]]
    assert labels == ["beta_class: 1 WBS elements"]
    assert "alpha_class" not in json.dumps(two)


def test_project_absent_from_the_saved_file_is_unavailable(monkeypatch, no_caef_files):
    import polars as pl

    path = no_caef_files / "predicted_levels.parquet"
    pl.DataFrame(
        {"parsid": ["proj_002"], **{f"level_{n}": ["x"] for n in range(2, 9)}}
    ).write_parquet(path)
    monkeypatch.setenv("CAEF_PREDICTIONS_FILE", str(path))
    state = server.load_caef_mapping_summary("proj_001")
    assert state["state"] == "unavailable"
    assert state["message"] == "No predictions found for this project."
    assert state["coverage"] == ""


# --- read-only guard -----------------------------------------------------------------

MUTATING = (
    "write_back_wbs",
    "tune_and_train_wbs",
    "run_wbs_pipeline",
    "predict_wbs",
    "clean_wbs_data",
)


@pytest.mark.parametrize("tool", MUTATING)
def test_guard_refuses_each_mutating_tool_before_pars_sees_it(tool):
    fake = ProjectsFake()
    with pytest.raises(pp.ToolNotAllowed):
        pp.GuardedClient(fake).call(tool, {"project_id": "proj_001"})
    assert fake.calls == []


def test_read_only_allowlist_contains_no_write_or_run_tool():
    assert not (pp.READ_ONLY_TOOLS & set(MUTATING))


def test_third_panel_code_never_references_write_back_wbs():
    assert "write_back_wbs" not in inspect.getsource(pp)
    assert "write_back_wbs" not in inspect.getsource(server)


def test_collapsing_or_reopening_the_panel_has_no_tool_call():
    assert "CallTool" not in inspect.getsource(server._evidence_collapsed)


# --- optional WBS-to-BLS suggestion ---------------------------------------


def test_wbs_bls_review_leaves_the_basket_unchanged(monkeypatch):
    use_session(monkeypatch, ProjectsFake())
    component_id = server._source.list_sources()[0].component_id
    before = json.dumps(
        basket_state.initial_basket(server._source, "y12"), sort_keys=True
    )
    review = server.review_wbs_bls_mapping(
        "proj_001", "01.01", component_id, "Analyst rationale for the check"
    )
    after = json.dumps(
        basket_state.initial_basket(server._source, "y12"), sort_keys=True
    )
    assert review["state"] == "reviewed"
    assert review["project_id"] == "proj_001"
    assert review["wbs_code"] == "01.01"
    assert before == after


# --- CAEF 2.0 input schema (read-only, fake source databases) -----------


def _source_db(path, *, drop_gold_column=None, spae_parsid="1"):
    import duckdb

    from pars_local_mcp.wbs_port import pipeline

    gold_cols = [
        "parsid VARCHAR",
        "wbs VARCHAR",
        "wbs_title VARCHAR",
        "wbs_level VARCHAR",
    ]
    gold_cols += [f"{c} VARCHAR" for c in pipeline.HIERARCHIES]
    if drop_gold_column:
        gold_cols = [c for c in gold_cols if c.split()[0] != drop_gold_column]
    con = duckdb.connect(str(path))
    try:
        con.execute(
            "CREATE TABLE bronze_abbreviations "
            "(abbreviation VARCHAR, definition VARCHAR)"
        )
        con.execute("CREATE TABLE bronze_stop_phrases (word VARCHAR)")
        con.execute("CREATE TABLE silver_stop_words (word VARCHAR)")
        con.execute(
            "CREATE TABLE silver_project_descriptions "
            "(parsid BIGINT, program VARCHAR, project_name VARCHAR)"
        )
        con.execute("CREATE TABLE silver_corrections (x VARCHAR)")
        con.execute(f"CREATE TABLE gold_corrections ({', '.join(gold_cols)})")
        con.execute(
            "CREATE TABLE silver_spae_data (parsid VARCHAR, "
            "program VARCHAR, project_name VARCHAR, "
            "period_date VARCHAR, parent_wbs VARCHAR, wbs VARCHAR, "
            "wbs_title VARCHAR, wbs_level VARCHAR)"
        )
        con.execute("INSERT INTO silver_project_descriptions VALUES (1, 'p', 'n')")
        con.execute("INSERT INTO bronze_abbreviations VALUES ('a', 'b')")
        con.execute("INSERT INTO bronze_stop_phrases VALUES ('w')")
        con.execute("INSERT INTO silver_stop_words VALUES ('w')")
        con.execute(
            "INSERT INTO silver_spae_data VALUES "
            "(?, 'p', 'n', '2026-01-01', '', '01', 't', '1')",
            [spae_parsid],
        )
        values = {
            "parsid": "1",
            "wbs": "01",
            "wbs_title": "t",
            "wbs_level": "1",
            **{c: "" for c in pipeline.HIERARCHIES},
        }
        names = [c.split()[0] for c in gold_cols]
        con.execute(
            f"INSERT INTO gold_corrections ({', '.join(names)}) "
            f"VALUES ({', '.join(['?'] * len(names))})",
            [values[n] for n in names],
        )
    finally:
        con.close()


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_complete_numeric_source_passes_the_contract_read_only(tmp_path):
    from pars_local_mcp.wbs_port import pipeline

    db = tmp_path / "source.duckdb"
    _source_db(db)
    before = _digest(db)
    report = pipeline.validate_source(db)
    assert report["ok"] is True
    assert report["problems"] == []
    assert _digest(db) == before


def test_missing_required_caef_column_is_reported_by_name(tmp_path):
    from pars_local_mcp.wbs_port import pipeline

    db = tmp_path / "source.duckdb"
    _source_db(db, drop_gold_column="level_5")
    report = pipeline.validate_source(db)
    assert report["ok"] is False
    assert any("gold_corrections" in p and "level_5" in p for p in report["problems"])


def test_non_integer_parsid_in_source_fails_the_contract(tmp_path):
    """Rule check: the source contract needs integer parsid, so string IDs fail here."""
    from pars_local_mcp.wbs_port import pipeline

    db = tmp_path / "source.duckdb"
    _source_db(db, spae_parsid="proj_001")
    report = pipeline.validate_source(db)
    assert report["ok"] is False
    assert any("parsid" in p for p in report["problems"])
