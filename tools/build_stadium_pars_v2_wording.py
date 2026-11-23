"""Versioned v2 wording for the held-out and demonstration stadium projects.

v1 gives every work type three phrasings, and the held-out texts repeat them. v2 is a
new database file. It replaces the WBS titles of the held-out and demonstration
projects only, with unfamiliar, technically plausible phrasings that never appear in
the training or validation text. Work types, WBS codes, hierarchy, labels, and
project splits are unchanged. Training and validation records are copied as they are.

v1 is not modified. Writes data/local/caef_stadium/stadium_pars_v2.duckdb and a
manifest.

Usage:  python tools/build_stadium_pars_v2_wording.py
"""

from __future__ import annotations

import hashlib
import json
import random
import shutil
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_stadium_pars_dataset as v1  # noqa: E402

REPO = v1.REPO
V1_DB = v1.DB_PATH
V2_DB = v1.OUT_DIR / "stadium_pars_v2.duckdb"
V2_MANIFEST = v1.OUT_DIR / "stadium_pars_v2.manifest.json"
V1_MANIFEST = v1.MANIFEST

# New wording, never used in v1. {z} is a zone, {s} a system or asset.
PHRASES_V2 = {
    "site_office_substructure": [
        "Bearing pads and grade beams beneath the temporary field office, {z}",
        "Ground-bearing slab prep for the jobsite office cabin, {z}",
    ],
    "utility_building_structure": [
        "Pre-engineered metal building erection for the utility shed, {z}",
        "Cold-formed purlins and wall girts at the utility house, {z}",
    ],
    "site_office_fitout": [
        "Drywall, ceiling grid, and flooring in the jobsite trailer suite, {z}",
        "Casework and power distribution inside the field office, {z}",
    ],
    "primary_facility_substructure": [
        "Drilled shaft caissons for the arena bowl, {z}",
        "Mat slab and ground improvement under the {s}, {z}",
    ],
    "primary_facility_structure_and_roof": [
        "Tension ring and compression struts for the canopy, {z}",
        "Erection of the bowl's steel tier framing, {z}",
    ],
    "site_grading": [
        "Cut and haul of unsuitable soils to the spoil area, {z}",
        "Compaction and subgrade proof rolling, {z}",
    ],
    "temporary_trailers_and_laydown": [
        "Construction office complex and fenced staging compound, {z}",
        "Crane pad and material staging area setup, {z}",
    ],
    "parking_and_access_roads": [
        "Asphalt surface course and striping for the lot, {z}",
        "Curbing and signalized entrance at the access drive, {z}",
    ],
    "landscaping_and_plaza": [
        "Irrigation, sod, and tree planting around the plaza, {z}",
        "Pavers, seat walls, and wayfinding signage at the forecourt, {z}",
    ],
    "site_utility_upgrades": [
        "Transformer pad and duct bank for the new service, {z}",
        "Sanitary main replacement and fire loop tie-in, {z}",
    ],
    "vertical_transportation": [
        "Traction elevator car and hoistway doors, {z}",
        "Moving walk and escalator truss erection, {z}",
    ],
    "fire_protection": [
        "Wet-pipe sprinkler mains and dry-pipe zones, {z}",
        "Smoke detection and voice evacuation panels, {z}",
    ],
    "hvac_and_mechanical": [
        "Rooftop air handler units and exhaust fans, {z}",
        "Chilled water coils and VAV boxes, {z}",
    ],
    "plumbing": [
        "Waste stacks, vent risers, and cleanouts, {z}",
        "Booster pump station and domestic hot water heaters, {z}",
    ],
    "facility_design_title_ii_vertical": [
        "Construction documents for the bowl structure and enclosure, {z}",
        "Final drawings and specs for the {s}, {z}",
    ],
    "facility_design_title_ii_site": [
        "Civil construction drawings for grading and drainage, {z}",
        "Final site plan and utility design packages, {z}",
    ],
    "project_management": [
        "Owner's representative staffing and document controls, {z}",
        "Schedule management and monthly cost reporting, {z}",
    ],
    "commissioning_and_turnover": [
        "Functional performance tests on air systems, {z}",
        "Acceptance walkthroughs and handover binders, {z}",
    ],
    "utility_relocations": [
        "Relocated gas main and abandoned line capping, {z}",
        "Electric pole line shift around the work limit, {z}",
    ],
    "broadcast_and_telecom": [
        "Single-mode fiber trunk and patch panels, {z}",
        "Broadcast truck connection panels and conduit runs, {z}",
    ],
    "scoreboard_av": [
        "LED video board structure and power feeds, {z}",
        "Speaker clusters and amplifier racks, {z}",
    ],
    "ticketing_and_access_systems": [
        "Ticket validation readers and gate controllers, {z}",
        "Turnstile network switches and cabling, {z}",
    ],
    "access_control_and_cctv": [
        "Card readers and door controllers at the perimeter, {z}",
        "Pan-tilt-zoom cameras and video recorders, {z}",
    ],
    "stadium_lighting": [
        "Light poles and luminaire mounting for the field, {z}",
        "Emergency and egress lighting circuits, {z}",
    ],
    "seating_bowl": [
        "Precast bleacher units and aisle stairs, {z}",
        "Seat deck and row installation, {z}",
    ],
    "premium_suites_and_hospitality": [
        "Glazing, millwork, and lounge finishes for the suites, {z}",
        "Club bar and hospitality kitchen interiors, {z}",
    ],
    "concessions_and_kitchens": [
        "Hood systems and walk-in coolers for the stands, {z}",
        "Counter tops, fixtures, and stand plumbing, {z}",
    ],
    "playing_field_and_turf": [
        "Sand-based root zone and sub-surface drains, {z}",
        "Synthetic turf carpet and infill, {z}",
    ],
    "central_plant_cooling_heating": [
        "Water-cooled chillers and cooling tower cells, {z}",
        "Hot water boilers and pumping skid, {z}",
    ],
    "structural_concrete_frame": [
        "Post-tensioned slab and transfer beams, {z}",
        "Shear walls and cast-in-place columns, {z}",
    ],
    "long_span_roof_steel": [
        "Roof girders and tie rods over the seating bowl, {z}",
        "Cable-stayed roof spine and anchor blocks, {z}",
    ],
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    if V2_DB.exists():
        print(f"Refusing to overwrite {V2_DB}")
        return 2
    v1_hash_before = _sha(V1_DB)
    shutil.copyfile(V1_DB, V2_DB)  # v1 is only read; the copy is the new version

    nodes = v1.load_taxonomy()
    crosswalk = {
        r["work_type"]: r
        for r in __import__("csv").DictReader(v1.CROSSWALK.open(encoding="utf-8"))
    }
    manifest_v1 = json.loads(V1_MANIFEST.read_text(encoding="utf-8"))
    roles = {p: role for role, ps in manifest_v1["splits"].items() for p in ps}
    rewritten = {}
    con = duckdb.connect(str(V2_DB))
    for parsid in [p for p, r in roles.items() if r in ("heldout", "demo_unseen")]:
        rng = random.Random(f"{v1.SEED}-{parsid}")
        elements, _labels = v1.build_project(
            parsid, roles[parsid], rng, crosswalk, nodes
        )
        work_by_code = {
            code: work
            for code, _p, _lvl, _t, work in elements
            if work != "phase" and work != "group"
        }
        rng2 = random.Random(f"v2-{parsid}")
        count = 0
        for code, work in sorted(work_by_code.items()):
            title = rng2.choice(PHRASES_V2[work]).format(
                z=f"{rng2.choice(v1.ZONES)} zone", s=rng2.choice(v1.SYSTEM_WORDS)
            )
            con.execute(
                "UPDATE wbs_elements SET title = ? WHERE parsid = ? AND wbs_code = ?",
                [title, parsid, code],
            )
            con.execute(
                "UPDATE labeled_wbs SET title = ? WHERE parsid = ? AND wbs_code = ?",
                [title, parsid, code],
            )
            count += 1
        rewritten[parsid] = count
    con.close()

    v1_hash_after = _sha(V1_DB)
    manifest = {
        "artifact": V2_DB.name,
        "version": "stadium_pars_v2_wording",
        "base": {"file": V1_DB.name, "sha256": v1_hash_before},
        "change": "WBS titles of held-out and demonstration projects replaced with "
        "unfamiliar phrasings; "
        "work types, codes, hierarchy, labels, and splits unchanged; training and "
        "validation unchanged",
        "rewritten_titles_by_project": rewritten,
        "v1_unchanged": v1_hash_before == v1_hash_after,
        "label_status": manifest_v1["label_status"],
        "database": {"file": V2_DB.name, "sha256": _sha(V2_DB)},
    }
    V2_MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "rewritten": rewritten,
                "v1_unchanged": manifest["v1_unchanged"],
                "v2_sha256": manifest["database"]["sha256"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
