"""Tests for the audit/provenance JSON and the PARS write-back preview."""

import json

from cost_intel_ui.audit_view import (
    AUDIT_FILENAME,
    audit_payload,
    pars_preview,
)
from cost_intel_ui.data_access import ResultPacket
from cost_intel_ui.fake_data import InMemoryDataSource
from cost_intel_ui.session import approve, start_session

NOW = "2026-11-13T00:00:00+00:00"


def test_audit_payload_without_session_is_not_calculated():
    payload = audit_payload(None, InMemoryDataSource())
    assert payload["calculation_status"] == "not_calculated"
    assert payload["project"] is None
    assert payload["pars_write_back"] == {
        "status": "planned_preview_only",
        "executed": False,
    }


def test_audit_payload_for_approved_session_includes_result_and_trace():
    source = InMemoryDataSource()
    s = approve(
        start_session(source, "y12", session_id=1, now=NOW), source, NOW
    ).session
    payload = audit_payload(s, source)
    assert payload["calculation_status"] == "validated_sample"
    assert payload["approval"] == {
        "status": "approved",
        "scenario": "recommended",
        "approved_at": NOW,
    }
    result = payload["calculation_result"]
    assert result["base_year_adjustment"]["source_year"] == 2026
    assert payload["source_provenance"]["snapshot_id"] == "DEMO-ANNUAL-2021-2026-v1"
    assert [t["tool"] for t in payload["tool_trace"]][0] == "cpds_pars.read_project"
    assert payload["validation_errors"] == []
    json.dumps(payload)


def test_audit_filename_matches_html():
    assert AUDIT_FILENAME == "nnsa-ppi-index-audit-demo.json"


def test_pars_preview_is_preview_only_and_derives_base_year():
    source = InMemoryDataSource()
    s = approve(
        start_session(source, "y12", session_id=1, now=NOW), source, NOW
    ).session
    view = pars_preview(s, source)
    assert view.title == "PARS WBS write-back preview"
    assert view.available
    assert view.payload == {
        "operation": "PARS_CUSTOM_INDEX_WRITE",
        "mode": "PREVIEW_ONLY",
        "project_id": "DEMO-NNSA-Y12-001",
        "spec_id": "y12-recommended",
        "annual_base_year": 2023,
        "latest_composite_factor": "1.126250052151",
        "approval_required": True,
        "executed": False,
    }


def test_pars_preview_blocked_for_invalid_result():
    broken = ResultPacket(result={"schema_version": "0.9"}, presentation={})
    source = InMemoryDataSource(result_overrides={("y12", "recommended"): broken})
    s = approve(
        start_session(source, "y12", session_id=1, now=NOW), source, NOW
    ).session
    view = pars_preview(s, source)
    assert not view.available
    assert view.title == "PARS write-back unavailable"
    assert view.kicker == "VALIDATION BLOCKED"
