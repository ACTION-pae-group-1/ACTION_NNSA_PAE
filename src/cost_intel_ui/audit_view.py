"""Audit/provenance JSON and the PARS write-back preview (both read-only)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from cost_intel_ui.contract import validate_packet
from cost_intel_ui.data_access import CostIntelDataSource, ResultPacket
from cost_intel_ui.session import Session

AUDIT_FILENAME = "nnsa-ppi-index-audit-demo.json"


def _approved_packet(
    session: Session | None, source: CostIntelDataSource
) -> ResultPacket | None:
    if session is None or session.phase != "approved":
        return None
    return source.get_result(session.data_project_key, session.scenario)


def audit_payload(
    session: Session | None, source: CostIntelDataSource
) -> dict[str, Any]:
    packet = _approved_packet(session, source)
    issues = validate_packet(packet) if packet is not None else []
    if packet is None:
        status, calculation = "not_calculated", None
    else:
        status = "rejected_invalid_contract" if issues else "validated_sample"
        result = packet.result
        adjustments = packet.presentation.get("adjustments_by_year") or {}
        calculation = {
            "schema_version": result.get("schema_version"),
            "index_identity": result.get("index_identity"),
            "normalization": result.get("normalization"),
            "components": result.get("components"),
            "component_points": result.get("component_points"),
            "composite_points": result.get("composite_points"),
            "base_year_adjustment": adjustments.get(session.selected_year)
            if session
            else None,
            "warnings": result.get("warnings"),
        }
    identity = (packet.result.get("index_identity") or {}) if packet else {}
    return {
        "application": "NNSA AI MCP Cost Intelligence",
        "demo_mode": True,
        "disclaimer": (
            "Synthetic annual PPI observations and fictional project context. No live "
            "government connection."
        ),
        "project": {
            "project_id": session.project_id,
            "project_name": session.name,
            "scope": session.scope,
            "wbs": session.wbs,
            "mission_relevance": session.mission,
        }
        if session
        else None,
        "approval": {
            "status": session.phase,
            "scenario": session.scenario,
            "approved_at": session.approved_at,
        }
        if session
        else None,
        "calculation_status": status,
        "calculation_result": calculation,
        "source_provenance": {
            "cpds_pars": "Fictional project context",
            "bls_ppi": "Synthetic PPI annual observations; DEMO series IDs",
            "snapshot_id": identity.get("snapshot_id"),
            "calculation_engine": (
                "Precomputed Decimal fixtures, generated before packaging this HTML"
            ),
        },
        "validation_errors": issues,
        "tool_trace": [asdict(e) for e in session.audit] if session else [],
        "pars_write_back": {"status": "planned_preview_only", "executed": False},
    }


@dataclass(frozen=True)
class ParsPreview:
    available: bool
    kicker: str
    title: str
    body: str
    payload: dict[str, Any] | None


def pars_preview(session: Session | None, source: CostIntelDataSource) -> ParsPreview:
    packet = _approved_packet(session, source)
    issues = validate_packet(packet) if packet is not None else []
    if issues:
        return ParsPreview(
            available=False,
            kicker="VALIDATION BLOCKED",
            title="PARS write-back unavailable",
            body=f"Invalid result cannot be used for a write-back. {issues[0]}",
            payload=None,
        )
    result = packet.result if packet else {}
    latest = result["composite_points"][-1] if packet else None
    return ParsPreview(
        available=True,
        kicker="PLANNED WRITE OPERATION",
        title="PARS WBS write-back preview",
        body=(
            "An authorized production WRITE tool could save an approved index "
            "specification and resulting cost adjustment against a WBS record. This "
            "prototype only displays a draft; it does not make any update."
        ),
        payload={
            "operation": "PARS_CUSTOM_INDEX_WRITE",
            "mode": "PREVIEW_ONLY",
            "project_id": session.project_id if session else None,
            "spec_id": result["index_identity"]["spec_id"] if packet else None,
            "annual_base_year": result["normalization"]["base_year"]
            if packet
            else None,
            "latest_composite_factor": latest["composite_factor"] if latest else None,
            "approval_required": True,
            "executed": False,
        },
    )
