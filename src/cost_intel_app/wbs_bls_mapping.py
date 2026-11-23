"""Read-only WBS-to-BLS series review; never changes cost calculations.

PARS supplies the verified project and WBS element. The basket supplies a
synthetic illustrative PPI series. This adapter records a proposed analytical
association, not cost allocation, escalation, or permission to write to PARS.
No network or file I/O occurs in this module.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from cost_intel_ui.data_access import SeriesSource

DISCLAIMER = (
    "Synthetic BLS series. Mapping candidate only; no PARS baseline costs "
    "were used, no escalation was applied, and no PARS records were modified."
)


def empty_mapping_review(message: str = "") -> dict[str, str]:
    """Stable, UI-bindable shape for idle, invalid, and reviewed mappings."""
    return {
        "state": "error" if message else "idle",
        "message": message,
        "project_id": "",
        "wbs_code": "",
        "element_title": "",
        "component_id": "",
        "series_name": "",
        "series_id": "",
        "rationale": "",
        "pars_origin": "",
        "bls_origin": "synthetic_demo",
        "disclaimer": DISCLAIMER,
    }


def review_mapping(
    *,
    project_id: str,
    wbs_code: str,
    component_id: str,
    rationale: str,
    sources: Sequence[SeriesSource],
    header: dict[str, Any],
    evidence: dict[str, Any],
    hierarchy: dict[str, Any] | None,
) -> dict[str, str]:
    """Build a candidate only when read-only PARS evidence verifies identity.

    This function never infers a mapping from WBS titles, invents a real BLS
    series ID, or modifies the basket allocation or calculation output.
    """
    pid, code, reason = project_id.strip(), wbs_code.strip(), rationale.strip()
    if not pid or len(pid) > 128 or not code or len(code) > 128:
        return empty_mapping_review("Choose a PARS project and WBS element.")
    if not 12 <= len(reason) <= 500:
        return empty_mapping_review("Enter a rationale of 12 to 500 characters.")
    source = next((s for s in sources if s.component_id == component_id), None)
    if source is None:
        return empty_mapping_review("Choose a listed BLS basket component.")
    if header.get("state") != "loaded" or header.get("project_id") != pid:
        return empty_mapping_review("PARS project verification failed.")
    if (
        evidence.get("state") == "error"
        or evidence.get("ok") is not True
        or evidence.get("read_only_views") is not True
        or evidence.get("origin") != "synthetic_mock"
    ):
        return empty_mapping_review("Validated synthetic PARS evidence is required.")
    if not hierarchy or hierarchy.get("state") not in ("loaded", "empty"):
        return empty_mapping_review("PARS could not verify the selected WBS element.")
    element = hierarchy.get("element")
    if not isinstance(element, dict) or element.get("wbs_code") != code:
        return empty_mapping_review("PARS WBS element does not match the selection.")
    title = element.get("title")
    if not isinstance(title, str) or not title.strip():
        return empty_mapping_review("PARS returned an invalid WBS title.")
    return {
        "state": "reviewed",
        "message": "",
        "project_id": pid,
        "wbs_code": code,
        "element_title": title,
        "component_id": source.component_id,
        "series_name": source.name,
        "series_id": source.series_id,
        "rationale": reason,
        "pars_origin": evidence["origin"],
        "bls_origin": "synthetic_demo",
        "disclaimer": DISCLAIMER,
    }
