"""PARS workspace state: every PARS panel for one project, from one client.

Each panel is a state dict from pars_panels. The read-only data views are gated
by the evidence panel, so they never call PARS for a source that is not
synthetic. The client is a LoggedClient, so the call log covers the whole
render.
"""

from __future__ import annotations

from typing import Any

from cost_intel_app import pars_panels as pp


def explore_panels() -> dict[str, Any]:
    """Idle explore panels. Each one loads only when the user asks for it."""
    idle = {"state": "idle", "message": "", "rows": []}
    return {
        "search": dict(idle),
        "lineage": dict(idle),
        "leaves": dict(idle),
        "level": dict(idle),
        "run": {
            "state": "idle",
            "message": "",
            "run_id": "",
            "created_at": "",
            "label": "",
            "stages": [],
        },
    }


def workspace_state(client: pp.LoggedClient, project_id: str) -> dict[str, Any]:
    """Every panel for one project. A blank project opens the first listed project."""
    chosen = project_id.strip()
    listing = None
    if not chosen:
        listing = pp.project_list(client)
        if listing["state"] == "loaded":
            chosen = listing["rows"][0]["parsid"]
    header = pp.project_header(client, chosen)
    if listing is not None and listing["state"] == "error":
        header = {**header, "state": "error", "message": listing["message"]}
    evidence = pp.evidence(client)
    gated = evidence["read_only_views"] is True
    return {
        "project_id": chosen,
        "header": {**header, "label": evidence["label"]},
        "evidence": evidence,
        "roots": pp.project_roots(client, chosen),
        "descriptions": pp.read_only_data(client, "descriptions", gated),
        "rows": pp.read_only_data(client, "rows", gated),
        "panels": explore_panels(),
        "draft": pp.write_back_preview([]),
        "inputs": {
            "search": "",
            "lineage": "",
            "level": "1",
            "run": "",
            "draft_code": "",
            "draft_title": "",
        },
        "log": pp.chat_log(client.entries),
    }
