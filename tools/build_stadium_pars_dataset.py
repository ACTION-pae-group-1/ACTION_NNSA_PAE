"""Build the synthetic stadium PARS database and its split manifest (versioned v1).

Synthetic proof-of-concept only. Every project is marked synthetic. The CAEF labels
are the accepted reference labels from crosswalk v4 (31 rules), treated as assumed
human-labeled synthetic reference labels. They are not independently validated.

Writes only under data/local/caef_stadium/. Reads the CAEF workbook, the crosswalk,
and two legacy PARS projects from the protected wbs.duckdb, read-only.

Usage:  python tools/build_stadium_pars_dataset.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

import duckdb
import openpyxl

REPO = Path(__file__).resolve().parents[1]
REF = REPO / "src/pars_local_mcp/data/CAEF 2.0 Standard WBS.xlsx"
PROTECTED = REPO / "src/pars_local_mcp/data/wbs.duckdb"
CROSSWALK = REPO / "data/local/caef_stadium/crosswalk_v4.csv"
OUT_DIR = REPO / "data/local/caef_stadium"
DB_PATH = OUT_DIR / "stadium_pars_v1.duckdb"
MANIFEST = OUT_DIR / "stadium_pars_v1.manifest.json"
SEED = 20261119
MARKER = "pars_synthetic_marker"

# Project populations. Disjoint by construction; each parsid appears in one role only.
ROLES = {
    "training": ["5101", "5102", "5103", "5104", "5105", "5106", "5107", "5108"],
    "validation": ["5201", "5202"],
    "heldout": ["5301", "5302"],
    "demo_unseen": ["5401", "5402"],
}
NAMES = {
    "5101": "Riverside Open-Air Stadium (Historical A)",
    "5102": "Harbor Covered Arena (Historical B)",
    "5103": "Lakeside Multi-Use Stadium (Historical C)",
    "5104": "Valley Football Stadium Renovation (Historical D)",
    "5105": "Summit Retractable-Roof Stadium (Historical E)",
    "5106": "Coastal Baseball Park (Historical F)",
    "5107": "Prairie Soccer Stadium (Historical G)",
    "5108": "Metro Stadium Concourse Expansion (Historical H)",
    "5201": "Foothill Stadium (Validation I)",
    "5202": "Bayfront Arena Modernization (Validation J)",
    "5301": "Cascade Stadium (Held-out K)",
    "5302": "Mesa Multipurpose Stadium (Held-out L)",
    "5401": "Northgate Stadium Program (Demo M)",
    "5402": "Eastfield Stadium and Plaza (Demo N)",
}
ALL_STADIUM = [p for role in ROLES.values() for p in role]

# Work types: each has a CAEF target from crosswalk v4 and several realistic phrasings.
# {z} is a zone, {s} a system or asset. Phrasings vary so text is not one template.
PHRASES = {
    "site_office_substructure": [
        "Site office trailer foundation pads, {z}",
        "Substructure for the contractor site office, {z}",
        "Site office footings and slab on grade, {z}",
    ],
    "utility_building_structure": [
        "Utility building steel frame and roof deck, {z}",
        "Structure for the utility building, {z}",
        "Utility building shell and framing, {z}",
    ],
    "site_office_fitout": [
        "Site office interior partitions and finishes, {z}",
        "Fit-out of the site office, {z}",
        "Furnishings and finishes for the site office, {z}",
    ],
    "primary_facility_substructure": [
        "Bowl foundation piles and pile caps, {z}",
        "Stadium bowl substructure and retaining walls, {z}",
        "Foundations for the {s}, {z}",
    ],
    "primary_facility_structure_and_roof": [
        "Seating bowl structural frame, {z}",
        "Roof structure and membrane over the {s}, {z}",
        "Superstructure framing for the {s}, {z}",
    ],
    "site_grading": [
        "Mass grading and earthwork, {z}",
        "Site grading and cut-and-fill, {z}",
        "Earthwork for the {s} pad, {z}",
    ],
    "temporary_trailers_and_laydown": [
        "Contractor trailers and laydown yard, {z}",
        "Mobilization, trailers, and laydown areas, {z}",
        "Temporary offices and staging, {z}",
    ],
    "parking_and_access_roads": [
        "Parking lot paving and access roads, {z}",
        "Vehicle drop-off and parking structure access, {z}",
        "Mobility and roadway improvements, {z}",
    ],
    "landscaping_and_plaza": [
        "Plaza hardscape and landscaping, {z}",
        "Landscape and aesthetic improvements, {z}",
        "Entry plaza finishes and planting, {z}",
    ],
    "site_utility_upgrades": [
        "Utility upgrades for water and power service, {z}",
        "Site utility expansion, {z}",
        "Upgrade of the site water and electrical service, {z}",
    ],
    "vertical_transportation": [
        "Elevators and escalators for the {s}, {z}",
        "Vertical conveying for the {s}, {z}",
        "Escalator and elevator installation, {z}",
    ],
    "fire_protection": [
        "Fire sprinkler and alarm systems, {z}",
        "Life safety and fire protection, {z}",
        "Fire suppression for the {s}, {z}",
    ],
    "hvac_and_mechanical": [
        "HVAC air handling for the {s}, {z}",
        "Mechanical ventilation and chillers, {z}",
        "Ductwork and air distribution, {z}",
    ],
    "plumbing": [
        "Domestic water and drainage piping, {z}",
        "Restroom plumbing fixtures, {z}",
        "Plumbing distribution for the {s}, {z}",
    ],
    "facility_design_title_ii_vertical": [
        "Final design for the {s} building, {z}",
        "Title II design of the vertical facilities, {z}",
        "Architectural and structural final design, {z}",
    ],
    "facility_design_title_ii_site": [
        "Final design of site work and utilities, {z}",
        "Title II site design, {z}",
        "Civil final design for the {s} pad, {z}",
    ],
    "project_management": [
        "Project management and controls, {z}",
        "Owner project team and reporting, {z}",
        "Construction project management support, {z}",
    ],
    "commissioning_and_turnover": [
        "Systems commissioning and turnover, {z}",
        "Testing, startup, and turnover to operations, {z}",
        "Commissioning of building systems, {z}",
    ],
    "utility_relocations": [
        "Relocation of existing utilities, {z}",
        "Utility relocation and protection, {z}",
        "Existing service relocation, {z}",
    ],
    "broadcast_and_telecom": [
        "Broadcast and telecom cabling, {z}",
        "Fiber and network backbone for broadcast, {z}",
        "Telecommunications distribution, {z}",
    ],
    "scoreboard_av": [
        "Scoreboard and audiovisual systems, {z}",
        "Video display and public address systems, {z}",
        "Audio and display equipment, {z}",
    ],
    "ticketing_and_access_systems": [
        "Ticketing and gate network hardware, {z}",
        "Ticket scanning and turnstile network, {z}",
        "Ticketing system infrastructure, {z}",
    ],
    "access_control_and_cctv": [
        "Access control and CCTV security, {z}",
        "Perimeter security and camera systems, {z}",
        "Physical security devices and readers, {z}",
    ],
    "stadium_lighting": [
        "Stadium field lighting and poles, {z}",
        "Electrical lighting for the {s}, {z}",
        "Concourse and field lighting fixtures, {z}",
    ],
    "seating_bowl": [
        "Seating bowl installation, {z}",
        "Spectator seats and bleachers, {z}",
        "Stadium seating rows and risers, {z}",
    ],
    "premium_suites_and_hospitality": [
        "Premium suites and club interiors, {z}",
        "Hospitality lounge fit-out, {z}",
        "Luxury suite finishes, {z}",
    ],
    "concessions_and_kitchens": [
        "Concession stands and food service fit-out, {z}",
        "Concession kitchen interiors, {z}",
        "Food and beverage stand finishes, {z}",
    ],
    "playing_field_and_turf": [
        "Playing field turf and drainage, {z}",
        "Field surface and subsurface drainage, {z}",
        "Natural turf and field preparation, {z}",
    ],
    "central_plant_cooling_heating": [
        "Central plant chillers and boilers, {z}",
        "Cooling and heating plant equipment, {z}",
        "Central energy plant, {z}",
    ],
    "structural_concrete_frame": [
        "Structural concrete frame and columns, {z}",
        "Cast-in-place concrete framing, {z}",
        "Concrete superstructure for the {s}, {z}",
    ],
    "long_span_roof_steel": [
        "Long-span roof steel trusses, {z}",
        "Roof steel and cable framing over the bowl, {z}",
        "Long-span steel roof structure, {z}",
    ],
}
SYSTEM_WORDS = [
    "concourse",
    "grandstand",
    "club level",
    "press box",
    "field house",
    "main bowl",
    "service core",
]
ZONES = [
    "North",
    "South",
    "East",
    "West",
    "Club Level",
    "Concourse Level",
    "Field Level",
    "Upper Bowl",
    "Lower Bowl",
    "Service Core",
]
# Work types each stadium uses; a seeded subset gives variety across projects.
ALWAYS = [
    "project_management",
    "facility_design_title_ii_site",
    "facility_design_title_ii_vertical",
    "site_grading",
    "commissioning_and_turnover",
    "primary_facility_substructure",
]
PHASES = {  # group index for the WBS tree, by work type family
    "Design and Management": [
        "project_management",
        "facility_design_title_ii_vertical",
        "facility_design_title_ii_site",
    ],
    "Site and Civil": [
        "site_grading",
        "utility_relocations",
        "parking_and_access_roads",
        "landscaping_and_plaza",
        "site_utility_upgrades",
        "temporary_trailers_and_laydown",
    ],
    "Structure": [
        "primary_facility_substructure",
        "primary_facility_structure_and_roof",
        "structural_concrete_frame",
        "long_span_roof_steel",
        "seating_bowl",
    ],
    "Building Systems": [
        "hvac_and_mechanical",
        "plumbing",
        "fire_protection",
        "central_plant_cooling_heating",
        "vertical_transportation",
        "stadium_lighting",
    ],
    "Specialty Systems": [
        "broadcast_and_telecom",
        "scoreboard_av",
        "ticketing_and_access_systems",
        "access_control_and_cctv",
        "playing_field_and_turf",
    ],
    "Interiors and Support": [
        "premium_suites_and_hospitality",
        "concessions_and_kitchens",
        "site_office_substructure",
        "utility_building_structure",
        "site_office_fitout",
    ],
    "Commissioning and Turnover": ["commissioning_and_turnover"],
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_taxonomy() -> dict[str, str]:
    wb = openpyxl.load_workbook(REF, read_only=True)
    return {
        str(r[0]): str(r[1]).strip()
        for r in wb["WBS"].iter_rows(min_row=2, values_only=True)
        if r[0] is not None
    }


def caef_chain(code: str, nodes: dict[str, str]) -> dict[str, str]:
    """caef_level_2..8 for a target code: the ancestor at each depth; blank beyond the
    target."""
    parts = code.split(".")
    labels = {f"caef_level_{d}": "" for d in range(2, 9)}
    for depth in range(2, len(parts) + 1):
        anc = ".".join(parts[:depth])
        labels[f"caef_level_{depth}"] = nodes[anc].lower()
    return labels


def build_project(
    parsid: str,
    role: str,
    rng: random.Random,
    crosswalk: dict[str, str],
    nodes: dict[str, str],
):
    """Return (elements, labels). Elements:
    (wbs_code, parent, level, title, work_type)."""
    families = list(PHASES.items())
    chosen = set(ALWAYS)
    pool = [w for _, ws in families for w in ws if w not in ALWAYS]
    rng.shuffle(pool)
    chosen.update(pool[: rng.randint(16, 24)])
    phase_idx = {name: i + 1 for i, (name, _) in enumerate(families)}
    elements, labels = [], []
    group_counter = {}
    for name, works in families:
        active = [w for w in works if w in chosen]
        if not active:
            continue
        p = str(phase_idx[name])
        elements.append((p, None, 1, name, "phase"))
        for w in active:
            group_counter[p] = group_counter.get(p, 0) + 1
            g = f"{p}.{group_counter[p]}"
            elements.append((g, p, 2, w.replace("_", " ").capitalize(), "group"))
            n_leaves = rng.randint(2, 4)
            for k in range(1, n_leaves + 1):
                zone = rng.choice(ZONES)
                system = rng.choice(SYSTEM_WORDS)
                title = rng.choice(PHRASES[w]).format(z=f"{zone} zone", s=system)
                code = f"{g}.{k}"
                elements.append((code, g, 3, title, w))
                labels.append((code, title, w))
    return elements, labels


def main() -> int:
    if DB_PATH.exists():
        print(f"Refusing to overwrite {DB_PATH}. Remove it deliberately to rebuild.")
        return 2
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    nodes = load_taxonomy()
    taxonomy_before = sha256(REF)
    crosswalk = {
        r["work_type"]: r for r in csv.DictReader(CROSSWALK.open(encoding="utf-8"))
    }
    assert all(
        r["status"] in ("supported", "educated_guess") for r in crosswalk.values()
    )

    proto = duckdb.connect(str(PROTECTED), read_only=True)
    legacy_projects = proto.execute(
        "SELECT parsid, project_name FROM projects ORDER BY parsid"
    ).fetchall()
    legacy_elements = proto.execute(
        "SELECT parsid, wbs_code, title, level, parent_wbs, leaf_node FROM "
        "wbs_elements ORDER BY parsid, wbs_code"
    ).fetchall()
    proto.close()
    assert (
        sha256(PROTECTED)
        == "9882560b8c22841b4bb5c72a3c5eae47fc648e397ccba38478c6894bdbacc67d"  # pragma: allowlist secret  # noqa: E501
    )

    con = duckdb.connect(str(DB_PATH))
    con.execute(f"CREATE TABLE {MARKER} AS SELECT 'synthetic' AS marker")
    con.execute(
        "CREATE TABLE projects (parsid VARCHAR PRIMARY KEY, project_name VARCHAR NOT "
        "NULL, role VARCHAR NOT NULL, origin VARCHAR NOT NULL)"
    )
    con.execute(
        "CREATE TABLE wbs_elements (parsid VARCHAR NOT NULL, wbs_code VARCHAR NOT "
        "NULL, title VARCHAR NOT NULL, level INTEGER NOT NULL, parent_wbs VARCHAR, "
        "leaf_node BOOLEAN DEFAULT FALSE, PRIMARY KEY (parsid, wbs_code))"
    )
    con.execute(
        "CREATE TABLE labeled_wbs (parsid VARCHAR NOT NULL, wbs_code VARCHAR NOT NULL, "
        "title VARCHAR NOT NULL, caef_level_2 VARCHAR, caef_level_3 VARCHAR, "
        "caef_level_4 VARCHAR, caef_level_5 VARCHAR, caef_level_6 VARCHAR, "
        "caef_level_7 VARCHAR, caef_level_8 VARCHAR, work_type VARCHAR NOT NULL, "
        "PRIMARY KEY (parsid, wbs_code))"
    )

    # Legacy compatibility projects: PARS records copied read-only from the protected
    # store.
    # Their labeled_wbs placeholders (codes such as E1) are not CAEF titles, so they
    # are not copied.
    for parsid, name in legacy_projects:
        con.execute(
            "INSERT INTO projects VALUES (?, ?, 'legacy_compatibility', "
            "'copied_read_only_from_protected_store')",
            [parsid, name],
        )
    for row in legacy_elements:
        con.execute("INSERT INTO wbs_elements VALUES (?, ?, ?, ?, ?, ?)", list(row))

    label_counts = Counter()
    wbs_counts = {}
    manifest_projects = {}
    for role, parsids in ROLES.items():
        for parsid in parsids:
            rng = random.Random(f"{SEED}-{parsid}")
            elements, labels = build_project(parsid, role, rng, crosswalk, nodes)
            con.execute(
                "INSERT INTO projects VALUES (?, ?, ?, 'synthetic_stadium_v1')",
                [parsid, NAMES[parsid], role],
            )
            parents = {code: parent for code, parent, *_ in elements}
            leaves = {code for code, parent, *_ in elements if parent} - {
                p for p in parents.values() if p
            }
            for code, parent, level, title, work in elements:
                con.execute(
                    "INSERT INTO wbs_elements VALUES (?, ?, ?, ?, ?, ?)",
                    [parsid, code, title, level, parent, code in leaves],
                )
            wbs_counts[parsid] = len(elements)
            if role in ("training", "validation", "heldout"):
                for code, title, work in labels:
                    target = crosswalk[work]["caef_code"]
                    lab = caef_chain(target, nodes)
                    con.execute(
                        "INSERT INTO labeled_wbs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
                        "?)",
                        [
                            parsid,
                            code,
                            title,
                            lab["caef_level_2"],
                            lab["caef_level_3"],
                            lab["caef_level_4"],
                            lab["caef_level_5"],
                            lab["caef_level_6"],
                            lab["caef_level_7"],
                            lab["caef_level_8"],
                            work,
                        ],
                    )
                    label_counts[(role, target)] += 1
            manifest_projects[parsid] = {
                "name": NAMES[parsid],
                "role": role,
                "wbs_elements": len(elements),
                "labeled_elements": len(labels)
                if role in ("training", "validation", "heldout")
                else 0,
            }
    con.close()

    manifest = {
        "artifact": DB_PATH.name,
        "version": "stadium_pars_v1",
        "synthetic": True,
        "label_status": "assumed human-labeled synthetic reference labels (crosswalk "
        "v4, 31 rules); not independently validated",
        "seed": SEED,
        "taxonomy": {
            "file": "src/pars_local_mcp/data/CAEF 2.0 Standard WBS.xlsx",
            "sha256_before": taxonomy_before,
            "sha256_after": sha256(REF),
            "unchanged": taxonomy_before == sha256(REF),
        },
        "crosswalk": {
            "file": "data/local/caef_stadium/crosswalk_v4.csv",
            "sha256": sha256(CROSSWALK),
        },
        "protected_source": {
            "file": "src/pars_local_mcp/data/wbs.duckdb",
            "sha256": (
                "9882560b8c22841b4bb5c72a3c5eae47fc648e397ccba38478c6894bdbacc67d"  # pragma: allowlist secret  # noqa: E501
            ),
            "read_only": True,
        },
        "splits": {role: parsids for role, parsids in ROLES.items()},
        "legacy_compatibility": [p for p, _ in legacy_projects],
        "legacy_note": "copied read-only from the protected store; labeled_wbs "
        "placeholders not copied; excluded from training",
        "projects": manifest_projects,
        "label_counts_by_role_and_caef_code": {
            f"{role}|{code}": n for (role, code), n in sorted(label_counts.items())
        },
        "database": {"file": DB_PATH.name, "sha256": sha256(DB_PATH)},
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "projects": len(manifest_projects) + len(legacy_projects),
                "labeled_rows": sum(label_counts.values()),
                "db_sha256": manifest["database"]["sha256"],
                "taxonomy_unchanged": manifest["taxonomy"]["unchanged"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
