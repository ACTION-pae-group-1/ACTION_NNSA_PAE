"""Final PARS MCP-to-CAEF inference evaluation for the unseen stadium projects.

Starts the application-side launcher on the packaged stadium database through
pars_live.live_session, wraps the session to record every MCP tool call, runs the
application's retrieval-and-inference path, and checks outputs against the database.
Read-only. No protected database is opened. Writes
eval/caef/results/release-2026-11-19/pars_mcp_inference.json.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import duckdb

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

DB = REPO / "src/cost_intel_app/demo_assets/caef_stadium/stadium_pars.duckdb"
PROTECTED = REPO / "src/pars_local_mcp/data/wbs.duckdb"
OUT = REPO / "eval/caef/results/release-2026-11-19/pars_mcp_inference.json"
PROJECTS = ["5401", "5402"]
os.environ["COST_INTEL_PARS_STADIUM_DB"] = str(DB)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


class Recording:
    def __init__(self, inner):
        self.inner = inner
        self.calls = []

    def call(self, tool, arguments):
        result = self.inner.call(tool, arguments)
        self.calls.append(
            {
                "tool": tool,
                "arguments": dict(arguments),
                "outcome": "error" if "error" in result else "ok",
                "elements": len(result.get("elements", []))
                if "elements" in result
                else None,
            }
        )
        return result

    def tool_names(self):
        return self.inner.tool_names()


def main() -> int:
    from cost_intel_app import caef_live_inference as A
    from cost_intel_app import pars_live

    protected_before = sha(PROTECTED)
    db_before = sha(DB)
    out = {
        "database": str(DB.relative_to(REPO)).replace("\\", "/"),
        "database_sha256_before": db_before,
        "projects": {},
        "tool_inventory": None,
    }
    con = duckdb.connect(str(DB), read_only=True)
    with pars_live.live_session(str(REPO)) as live:
        out["tool_inventory"] = len(live.tool_names())
        listing = live.call("list_projects", {})
        listing_text = json.dumps(listing)
        out["discovery"] = {
            "tool": "list_projects",
            "outcome": "error" if "error" in listing else "ok",
            "projects_listed": {pid: pid in listing_text for pid in PROJECTS},
        }
        session = Recording(live)
        for pid in PROJECTS:
            session.calls.clear()
            summary = A.predict_retrieved_project(pid, session)
            rows = summary.get("rows", [])
            db_codes = {
                r[0]
                for r in con.execute(
                    "SELECT wbs_code FROM wbs_elements WHERE parsid = ? AND level >= 2",
                    [pid],
                ).fetchall()
            }
            got = [r["wbs"] for r in rows]
            out["projects"][pid] = {
                "discovered_via_mcp": out["discovery"]["projects_listed"][pid],
                "mcp_calls": [
                    {
                        "tool": c["tool"],
                        "level": c["arguments"].get("level"),
                        "outcome": c["outcome"],
                        "elements": c["elements"],
                    }
                    for c in session.calls
                ],
                "state": summary.get("state"),
                "coverage": summary.get("coverage"),
                "classified_rows": len(rows),
                "db_elements_level_ge_2": len(db_codes),
                "all_codes_classified": set(got) == db_codes
                and len(got) == len(set(got)),
                "all_rows_carry_project_id": all(r["parsid"] == pid for r in rows),
                "structure_fields_present": all(
                    k in rows[0]
                    for k in (
                        "parsid",
                        "wbs",
                        "cleaned_title",
                        "parent_wbs",
                        "level_2",
                        "level_3",
                        "level_4",
                        "level_5",
                        "level_6",
                        "level_7",
                        "level_8",
                    )
                )
                if rows
                else False,
                "level_2_values": sorted({r["level_2"] for r in rows}),
            }
    con.close()
    out["database_sha256_after"] = sha(DB)
    out["database_unchanged"] = (
        out["database_sha256_before"] == out["database_sha256_after"]
    )
    out["protected_pars_database_unchanged"] = sha(PROTECTED) == protected_before
    out["protected_pars_database_sha256"] = protected_before
    out["inference_path_reads_crosswalk_or_labels"] = any(
        s in Path(A.__file__).read_text(encoding="utf-8")
        for s in ("crosswalk", "labeled_wbs")
    )
    out["evidence_category"] = (
        "newly executed; live PARS MCP stdio via launcher; model-driven predictions; "
        "not Phoenix-recorded; not browser-verified"
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                pid: {
                    k: v[k]
                    for k in (
                        "state",
                        "classified_rows",
                        "db_elements_level_ge_2",
                        "all_codes_classified",
                        "all_rows_carry_project_id",
                    )
                }
                for pid, v in out["projects"].items()
            },
            indent=2,
        )
    )
    print(
        "tools:",
        out["tool_inventory"],
        "db unchanged:",
        out["database_unchanged"],
        "protected unchanged:",
        out["protected_pars_database_unchanged"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
