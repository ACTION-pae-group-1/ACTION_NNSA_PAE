"""Offline WBS / BLS review contracts; no MCP process or network."""

from cost_intel_app.wbs_bls_mapping import empty_mapping_review, review_mapping
from cost_intel_ui.fake_data import InMemoryDataSource

SOURCE = InMemoryDataSource().list_sources()
HEADER = {"state": "loaded", "project_id": "100"}
EVIDENCE = {
    "state": "loaded",
    "ok": True,
    "read_only_views": True,
    "origin": "synthetic_mock",
}
HIERARCHY = {
    "state": "loaded",
    "element": {"wbs_code": "1", "title": "Materials"},
}


def _review(**changes):
    args = {
        "project_id": "100",
        "wbs_code": "1",
        "component_id": "steel",
        "rationale": "Material prices warrant steel series review.",
        "sources": SOURCE,
        "header": HEADER,
        "evidence": EVIDENCE,
        "hierarchy": HIERARCHY,
    }
    args.update(changes)
    return review_mapping(**args)


def test_review_preserves_both_source_identities_without_applying_costs():
    actual = _review()
    assert actual["state"] == "reviewed"
    assert actual["project_id"] == "100"
    assert actual["wbs_code"] == "1"
    assert actual["series_id"] == "DEMO-WPU1017"
    assert actual["pars_origin"] == "synthetic_mock"
    assert actual["bls_origin"] == "synthetic_demo"
    assert "no escalation was applied" in actual["disclaimer"]
    assert "cost" not in actual or isinstance(actual.get("cost"), str)


def test_unverified_pars_project_or_wbs_element_is_refused():
    assert _review(header={"state": "error"})["state"] == "error"
    assert _review(project_id="101")["state"] == "error"
    assert _review(hierarchy=None)["state"] == "error"
    assert _review(wbs_code="1.1")["state"] == "error"


def test_non_synthetic_and_unvalidated_pars_evidence_is_refused():
    assert _review(evidence={**EVIDENCE, "origin": "live"})["state"] == "error"
    assert _review(evidence={**EVIDENCE, "ok": False})["state"] == "error"
    assert _review(evidence={**EVIDENCE, "read_only_views": False})["state"] == "error"


def test_unknown_series_or_missing_rationale_is_refused():
    assert _review(component_id="unlisted")["state"] == "error"
    assert _review(rationale="guess")["state"] == "error"


def test_idle_review_state_contains_every_binding_and_no_implicit_link():
    idle = empty_mapping_review()
    assert idle["state"] == "idle"
    assert idle["project_id"] == ""
    assert idle["wbs_code"] == ""
    assert idle["series_id"] == ""
    assert idle["bls_origin"] == "synthetic_demo"
