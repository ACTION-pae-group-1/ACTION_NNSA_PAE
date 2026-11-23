"""K10: a late response for project A must not be returned as project B's result.

Server-side only. This test drives ``server.load_pars_context`` directly with a
gated PARS stub: the request for proj_001 (Alpha) blocks at its first PARS call
while the request for proj_002 (Beta) completes, then A is released. It shows
whether each call's return value is attributed to the project it requested.

It cannot prove browser behaviour: the Prefab UI binding
(``on_success=[SetState("pars_context", RESULT), ...]``) is not executed here.
Everything is synthetic and local; no PARS process or database is touched.
"""

import threading
from contextlib import contextmanager

from cost_intel_app import server

GATE_TIMEOUT_SECONDS = 5

PROJECTS = {
    "proj_001": {"name": "Alpha Stadium", "total": 2},
    "proj_002": {"name": "Beta Expansion", "total": 1},
}
LEAVES = {
    "proj_001": [("01.01", "Alpha foundations"), ("01.02", "Alpha roof")],
    "proj_002": [("01.01", "Beta drainage")],
}
EVIDENCE_OK = {
    "data_origin": "synthetic_mock",
    "ok": True,
    "problems": [],
    "tables": {"gold_corrections": {"rows": 1}},
}


class GatedProjectsStub:
    """Answers read tools per project; calls for ``gated_pid`` block until released."""

    def __init__(self, gated_pid: str) -> None:
        self.gated_pid = gated_pid
        self.entered = threading.Event()
        self.release = threading.Event()
        self.calls: list[tuple[str, dict]] = []

    def call(self, tool: str, arguments: dict) -> dict:
        self.calls.append((tool, dict(arguments)))
        pid = arguments.get("project_id")
        if pid == self.gated_pid:
            self.entered.set()
            if not self.release.wait(GATE_TIMEOUT_SECONDS):
                raise AssertionError("gate was never released")
        if tool == "get_project_info":
            info = PROJECTS[pid]
            return {
                "parsid": pid,
                "project_name": info["name"],
                "total_elements": info["total"],
                "hierarchy_depth": 2,
            }
        if tool == "validate_wbs_inputs":
            return EVIDENCE_OK
        if tool == "get_leaf_nodes":
            return {
                "leaf_nodes": [
                    {"wbs_code": c, "title": t, "level": 2} for c, t in LEAVES[pid]
                ]
            }
        if tool == "get_wbs_by_level":
            return {
                "elements": [
                    {
                        "wbs_code": "01",
                        "title": f"{PROJECTS[pid]['name']} program",
                        "level": 1,
                        "parent_wbs": "",
                    }
                ]
            }
        if tool == "get_wbs_project_descriptions":
            return {
                "columns": ["parsid", "project_description"],
                "rows": [
                    {"parsid": "proj_001", "project_description": "Alpha narrative"},
                    {"parsid": "proj_002", "project_description": "Beta narrative"},
                ],
                "total_rows": 2,
            }
        raise AssertionError(f"unexpected PARS tool in test: {tool}")


def _use_stub(monkeypatch, stub: GatedProjectsStub) -> None:
    @contextmanager
    def session():
        yield stub

    monkeypatch.setattr(server, "_pars_session", session)


def test_late_response_for_a_is_attributed_to_a_not_b(monkeypatch):
    stub = GatedProjectsStub(gated_pid="proj_001")
    _use_stub(monkeypatch, stub)
    results: dict[str, dict] = {}

    def load_a() -> None:
        results["A"] = server.load_pars_context("proj_001")

    thread_a = threading.Thread(target=load_a)
    thread_a.start()
    try:
        assert stub.entered.wait(GATE_TIMEOUT_SECONDS), "A never reached PARS"

        # The user has now selected B; B's request completes while A is in flight.
        result_b = server.load_pars_context("proj_002")
    finally:
        stub.release.set()
        thread_a.join(GATE_TIMEOUT_SECONDS)

    result_a = results["A"]

    # Each return value carries the project it was requested for.
    assert result_b["state"] == "loaded"
    assert result_b["project_id"] == "proj_002"
    assert result_b["name"] == "Beta Expansion"
    assert result_b["description"] == "Beta narrative"
    assert [c["wbs_code"] for c in result_b["wbs_choices"]] == ["01.01"]

    assert result_a["state"] == "loaded"
    assert result_a["project_id"] == "proj_001"
    assert result_a["name"] == "Alpha Stadium"
    assert result_a["description"] == "Alpha narrative"
    assert [c["wbs_code"] for c in result_a["wbs_choices"]] == ["01.01", "01.02"]

    # No A data leaks into B's result, and no B data into A's.
    assert "Alpha" not in str(result_b)
    assert "Beta" not in str(result_a)
    assert result_a["project_id"] != result_b["project_id"]
