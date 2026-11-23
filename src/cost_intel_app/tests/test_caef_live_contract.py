"""Regression coverage for the PARS-to-CAEF data contract.

Three kinds of test, kept apart on purpose:

* Contract tests document the current incompatibility. They pass, but they are
  NOT evidence that the integration works.
* Fail-closed tests check that no predictions are invented or substituted for a
  live PARS project.
* The end-to-end gate is a strict xfail. It stays BLOCKED until the real workflow
  (select project -> WBS -> validate inputs -> packaged model -> labels) succeeds.
  When it starts passing, pytest reports XPASS(strict) as a failure, which forces
  the gate to be updated rather than silently counted as done.

Known finding (HIGH severity, integration test coverage gap): the packaged CAEF
model needs period_date and program per WBS row, plus preprocessing reference
tables. The live PARS store used by proj_001 and proj_002 has neither, so the
optional third panel cannot produce predictions for them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cost_intel_app import caef_summary as cs

REPO = Path(__file__).resolve().parents[3]
LIVE_STORE = REPO / "src" / "pars_local_mcp" / "data" / "wbs.duckdb"
LIVE_PROJECTS = ("proj_001", "proj_002")

# Contract fields that the live store supplies, under their live names.
LIVE_SUPPLIED_CONTRACT_FIELDS = {
    "parsid",
    "wbs",
    "wbs_title",
    "wbs_level",
    "parent_wbs",
    "project_name",
}


def _live_tables_and_columns() -> dict[str, set[str]]:
    import duckdb

    con = duckdb.connect(str(LIVE_STORE), read_only=True)
    try:
        tables = [r[0] for r in con.execute("SHOW TABLES").fetchall()]
        return {
            t: {r[0] for r in con.execute(f'DESCRIBE "{t}"').fetchall()} for t in tables
        }
    finally:
        con.close()


@pytest.fixture(scope="module")
def live_schema():
    if not LIVE_STORE.is_file():
        pytest.skip("Live PARS store is not present in this checkout.")
    return _live_tables_and_columns()


@pytest.fixture(scope="module")
def pipeline_contract():
    from pars_local_mcp.wbs_port.pipeline import REQUIRED_COLUMNS, SOURCE_TABLES

    return REQUIRED_COLUMNS, SOURCE_TABLES


# --------------------------------------------------------------- contract tests
def test_live_store_is_missing_period_date_and_program(live_schema, pipeline_contract):
    required_columns, _ = pipeline_contract
    required = set(required_columns["silver_spae_data"])
    unmet = required - LIVE_SUPPLIED_CONTRACT_FIELDS
    # Exactly these two fields block inference for live projects.
    assert unmet == {"program", "period_date"}
    assert "period_date" not in {c for cols in live_schema.values() for c in cols}
    assert "program" not in live_schema["wbs_elements"]


def test_live_store_lacks_the_text_cleaning_reference_tables(
    live_schema, pipeline_contract
):
    _, source_tables = pipeline_contract
    reference = {
        "bronze_abbreviations",
        "bronze_stop_phrases",
        "silver_stop_words",
        "silver_corrections",
        "gold_corrections",
    }
    assert reference <= set(source_tables)
    assert reference.isdisjoint(live_schema.keys())


def test_live_projects_are_the_two_selectable_synthetic_projects(live_schema):
    import duckdb

    con = duckdb.connect(str(LIVE_STORE), read_only=True)
    try:
        ids = {r[0] for r in con.execute("SELECT parsid FROM projects").fetchall()}
    finally:
        con.close()
    assert ids == set(LIVE_PROJECTS)


# ------------------------------------------------------------- fail-closed tests
@pytest.mark.parametrize("project_id", LIVE_PROJECTS)
def test_live_projects_get_no_substituted_predictions(project_id):
    """The packaged predictions cover only synthetic parsids; never reuse them."""
    summary = cs.run_model_for_project(project_id)
    assert summary["state"] == "unavailable"
    assert not any(c["visible"] for c in summary["categories"])
    assert project_id in summary["coverage"] or summary["coverage"] == ""


def test_saved_predictions_do_not_leak_into_live_projects(tmp_path):
    saved = cs.saved_prediction_path()
    if not saved:
        pytest.skip("No packaged predictions in this checkout.")
    for project_id in LIVE_PROJECTS:
        summary = cs.read_caef_summary(saved, project_id)
        assert summary["state"] == "unavailable"
        assert not any(c["visible"] for c in summary["categories"])


# -------------------------------------------------------- positive control
def test_packaged_model_positive_control_project_100():
    """Proves the inference harness works; this is the only real CAEF evidence."""
    if cs._bundled_run() is None:
        pytest.skip("Packaged CAEF demo bundle is not present.")
    summary = cs.run_model_for_project("100")
    assert summary["state"] == "loaded"
    assert summary["coverage"].startswith("Newly generated predictions")


# ----------------------------------------------------- end-to-end gate (BLOCKED)
@pytest.mark.xfail(
    strict=True,
    reason=(
        "BLOCKED: live proj_001 and proj_002 lack period_date, program, and the "
        "text-cleaning reference tables that the CAEF input contract requires. "
        "Do not count this as integration evidence until it passes."
    ),
)
@pytest.mark.parametrize("project_id", LIVE_PROJECTS)
def test_end_to_end_caef_gate_for_selected_live_project(project_id):
    """Select project -> WBS -> validate inputs -> packaged model -> labels."""
    summary = cs.run_model_for_project(project_id)
    assert summary["state"] == "loaded"
    assert summary["coverage"].startswith("Newly generated predictions")
    assert any(c["visible"] for c in summary["categories"])
