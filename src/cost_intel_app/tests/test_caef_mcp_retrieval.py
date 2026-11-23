"""CAEF inference on WBS records retrieved through PARS MCP (stadium release package).

Covers: records come from the PARS MCP tools; identifiers are preserved; the protected
database is not read; crosswalk and label tables are not used at inference; switching
projects does not mix results; the packaged database is unchanged by retrieval.
"""

import hashlib
from pathlib import Path

import duckdb
import pytest

from cost_intel_app import caef_live_inference as A
from cost_intel_app import pars_live

REPO = Path(__file__).resolve().parents[3]
STADIUM_DB = (
    REPO
    / "src"
    / "cost_intel_app"
    / "demo_assets"
    / "caef_stadium"
    / "stadium_pars.duckdb"
)
PROTECTED = REPO / "src" / "pars_local_mcp" / "data" / "wbs.duckdb"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class DbBackedSession:
    """Stands in for the PARS MCP session: answers get_wbs_by_level from the stadium DB.

    Test double only; the real session is the application-side launcher.
    """

    def __init__(self, path: Path):
        self.path = path
        self.calls = []

    def call(self, tool, arguments):
        self.calls.append((tool, dict(arguments)))
        if tool != "get_wbs_by_level":
            raise AssertionError("unexpected tool")
        con = duckdb.connect(str(self.path), read_only=True)
        try:
            rows = con.execute(
                "SELECT wbs_code, title, parent_wbs, leaf_node FROM wbs_elements "
                "WHERE parsid = ? AND level = ? ORDER BY wbs_code",
                [arguments["project_id"], arguments["level"]],
            ).fetchall()
        finally:
            con.close()
        return {
            "elements": [
                {"wbs_code": r[0], "title": r[1], "parent_wbs": r[2], "leaf_node": r[3]}
                for r in rows
            ]
        }


@pytest.fixture(scope="module")
def stadium_db():
    if not STADIUM_DB.is_file():
        pytest.skip("Packaged stadium database is not present.")
    return STADIUM_DB


def test_rows_are_the_records_pars_mcp_returned(stadium_db):
    session = DbBackedSession(stadium_db)
    rows = A.rows_from_mcp(session, "5401")
    con = duckdb.connect(str(stadium_db), read_only=True)
    try:
        expected = con.execute(
            "SELECT wbs_code, title, level FROM wbs_elements "
            "WHERE parsid = '5401' ORDER BY wbs_code"
        ).fetchall()
    finally:
        con.close()
    assert rows.height == len(expected)
    assert rows["wbs"].to_list() == [r[0] for r in expected]
    assert rows["wbs_title"].to_list() == [r[1] for r in expected]
    assert set(rows["parsid"].to_list()) == {"5401"}
    assert {tool for tool, _ in session.calls} == {"get_wbs_by_level"}
    assert sorted({args["level"] for _, args in session.calls}) == list(range(1, 9))


def test_predictions_keep_source_project_and_wbs_identifiers(stadium_db):
    summary = A.predict_retrieved_project("5401", DbBackedSession(stadium_db))
    assert summary["state"] == "loaded"
    rows = summary["rows"]
    assert rows and set(r["parsid"] for r in rows) == {"5401"}
    codes = {r["wbs"] for r in rows}
    con = duckdb.connect(str(stadium_db), read_only=True)
    try:
        known = {
            r[0]
            for r in con.execute(
                "SELECT wbs_code FROM wbs_elements WHERE parsid='5401'"
            ).fetchall()
        }
    finally:
        con.close()
    assert codes <= known


def test_switching_projects_never_mixes_predictions(stadium_db):
    session = DbBackedSession(stadium_db)
    first = A.predict_retrieved_project("5401", session)
    second = A.predict_retrieved_project("5402", session)
    assert {r["parsid"] for r in first["rows"]} == {"5401"}
    assert {r["parsid"] for r in second["rows"]} == {"5402"}
    assert {r["wbs"] for r in first["rows"]} != {r["wbs"] for r in second["rows"]}


def test_unavailable_pars_fails_closed(stadium_db):
    class Down:
        def call(self, tool, arguments):
            raise ConnectionError("down")

    summary = A.predict_retrieved_project("5401", Down())
    assert summary["state"] != "loaded"
    assert summary.get("rows", []) == []


def test_pars_error_reply_is_refused_not_predicted(stadium_db):
    class Refusing:
        def call(self, tool, arguments):
            return {"error": "tool failed"}

    summary = A.predict_retrieved_project("5401", Refusing())
    assert not summary.get("rows")


def test_retrieval_does_not_read_the_protected_database(stadium_db, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("protected PARS store was read")

    monkeypatch.setattr(A, "load_live_project", forbidden)
    summary = A.predict_retrieved_project("5402", DbBackedSession(stadium_db))
    assert summary["state"] == "loaded"


def test_inference_path_does_not_use_crosswalk_or_labels():
    source = Path(A.__file__).read_text(encoding="utf-8")
    for forbidden in ("crosswalk", "labeled_wbs", "caef_level_", "stadium_pars_v"):
        assert forbidden not in source, forbidden


def test_database_unchanged_by_retrieval_and_inference(stadium_db):
    before = _sha(stadium_db)
    A.predict_retrieved_project("5401", DbBackedSession(stadium_db))
    A.predict_retrieved_project("5402", DbBackedSession(stadium_db))
    assert _sha(stadium_db) == before


def test_every_wbs_code_keeps_a_prediction_at_inference(stadium_db):
    """Inference keeps all rows, including repeated titles, so costs can be summed."""
    for pid in ("5401", "5402"):
        summary = A.predict_retrieved_project(pid, DbBackedSession(stadium_db))
        con = duckdb.connect(str(stadium_db), read_only=True)
        try:
            expected = {
                r[0]
                for r in con.execute(
                    "SELECT wbs_code FROM wbs_elements WHERE parsid = ? AND level >= 2",
                    [pid],
                ).fetchall()
            }
        finally:
            con.close()
        got = [r["wbs"] for r in summary["rows"]]
        assert len(got) == len(set(got)) == len(expected)
        assert set(got) == expected
        assert "not classified" not in summary["coverage"]


@pytest.mark.skipif(
    not STADIUM_DB.is_file(), reason="Packaged stadium database not present"
)
def test_end_to_end_through_the_real_launcher(monkeypatch):
    monkeypatch.setenv("COST_INTEL_PARS_STADIUM_DB", str(STADIUM_DB))
    before = _sha(STADIUM_DB)
    with pars_live.live_session(str(REPO)) as session:
        summary = A.predict_retrieved_project("5401", session)
    assert summary["state"] == "loaded"
    assert {r["parsid"] for r in summary["rows"]} == {"5401"}
    assert _sha(STADIUM_DB) == before
    assert PROTECTED.is_file()
