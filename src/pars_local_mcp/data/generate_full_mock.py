"""Generate a fake copy of every table in the PARS WBS database.

Reads table and column structure from mock_schema_pars_full.json (names and
types only, no values) and fills each table with synthetic values using
DuckDB SQL. Output is written only inside this package's data directory.

WBS elements are the elements of the CAEF 2.0 reference (sheet "WBS"): the
code and level come from the reference, and each element gets one unique
Faker title (element_titles). The level_2..level_8 columns hold the CAEF labels
of the element's ancestors (caef_level_labels), so they are the training targets.
The CAEF training data reuses the same titles and labels.

Every value is derived from the row index i, so keys agree across tables:
- parsid: one 3- or 4-digit id per project (PROJECT_PARSIDS).
- project_name: one made-up name per parsid (PROJECT_NAMES).
- wbs / wbs_title / wbs_level / level_2..level_8: the element at index
  (i // N_PROJECTS) mod the element count. Within a parsid a WBS number maps to
  exactly one title.
- period_date: the pass through the elements, one month per pass.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import duckdb
import pandas as pd
import polars as pl
from faker import Faker

from pars_local_mcp.data.config import concatenate_data

DATA_DIR = Path(__file__).resolve().parent
SCHEMA_FILE = DATA_DIR / "mock_schema_pars_full.json"
REFERENCE_FILE = DATA_DIR / "CAEF 2.0 Standard WBS.xlsx"
DEFAULT_OUTPUT = DATA_DIR / "mock_pars_full.duckdb"
FACT_ROWS = 50_000
REFERENCE_ROWS = 500
REFERENCE_MARKERS = (
    "abbreviations",
    "ignore_list",
    "stop_phrases",
    "stop_words",
    "project_descriptions",
)
MARKER_TABLE = "_mock_marker"
MARKER_TEXT = "SYNTHETIC MOCK DATA - NOT REAL. Generated from table structure only."
TITLE_SEED = 42
PERIODS = 36  # period_date moves forward one month per pass through the elements
LABEL_LEVELS = tuple(range(2, 9))

PROJECT_NAMES = [
    "Crescent Bay Football Stadium Construction",
    "Northpoint Multiuse Stadium Expansion",
    "Lakeshore Championship Arena District",
    "Ironwood Retractable Roof Stadium",
    "Summit Park Stadium Modernization",
    "Westhaven Soccer Stadium Development",
    "Harborfront Ballpark and Transit Hub",
    "Redstone College Athletics Complex",
    "Canyon View Indoor Sports Arena",
    "Silvergate Stadium Campus Redevelopment",
    "Bluewater Olympic Aquatics Center",
    "Eastgate Major League Ballpark",
    "Pinecrest Stadium Seismic Retrofit",
    "Riverton Stadium Sustainability Upgrade",
    "Prairie City Football Stadium Campus",
    "Grand Valley Stadium and Entertainment District",
    "Northshore Motorsport Grandstand Complex",
    "Bridgeport World Cup Stadium Conversion",
    "Hillcrest Stadium Accessibility Expansion",
    "Sunset Coast Stadium Roof and Concourse Renewal",
]

N_PROJECTS = len(PROJECT_NAMES)
# Unique 3- or 4-digit parsids: 100 + (k * 487) for k < 20 stays below 9900.
PROJECT_PARSIDS = [100 + (k * 487) % 9900 for k in range(N_PROJECTS)]


def load_caef_elements(path: Path = REFERENCE_FILE) -> list[tuple[str, str, int]]:
    """(wbs_code, CAEF label, level) for each CAEF WBS element, in sheet order."""
    frame = pd.read_excel(
        path, sheet_name="WBS", usecols=["WBS", "Title", "Level"], dtype=str
    )
    return [
        (str(code).strip(), str(label).strip(), int(level))
        for code, label, level in zip(
            frame["WBS"], frame["Title"], frame["Level"], strict=True
        )
    ]


# Capital acquisition terminology; all combinations are generated locally by Faker.
ACQUISITION_ACTIONS = (
    "Develop",
    "Design",
    "Procure",
    "Construct",
    "Install",
    "Integrate",
    "Inspect",
    "Test",
    "Commission",
    "Qualify",
    "Upgrade",
    "Validate",
)
ACQUISITION_ASSETS = (
    "Lower Bowl Concrete Structure",
    "Upper Deck Steel Superstructure",
    "Retractable Roof Truss System",
    "Seating Bowl and Premium Suites",
    "Stadium Field Drainage and Irrigation",
    "LED Ribbon Boards and Video Displays",
    "Concourse and Concession Facilities",
    "Stadium Power Distribution Network",
    "Public Transit and Pedestrian Plaza",
    "Broadcast Compound and Fiber Backbone",
    "Locker Rooms and Player Facilities",
    "Accessible Entrances and Vertical Circulation",
    "Stadium HVAC and Smoke Control",
    "Security Screening and Crowd Management",
    "Parking Garages and Site Roads",
    "Stadium Floodlighting and Emergency Power",
    "Foundations and Deep Pile System",
    "Press Box and Media Center",
    "Stormwater Detention and Utility Relocation",
    "Fan Experience and Wayfinding Systems",
)
ACQUISITION_DELIVERABLES = (
    "feasibility study",
    "concept design",
    "structural analysis",
    "permit submission",
    "procurement bid package",
    "construction work package",
    "site logistics plan",
    "safety and accessibility review",
    "commissioning and testing",
    "construction cost estimate",
    "schedule baseline",
    "systems acceptance and turnover",
)


def element_titles(count: int, seed: int = TITLE_SEED) -> list[str]:
    """Generate unique, reproducible capital-project WBS titles using Faker."""
    fake = Faker()
    fake.seed_instance(seed)
    titles: list[str] = []
    seen: set[str] = set()
    while len(titles) < count:
        title = (
            f"{fake.random_element(ACQUISITION_ACTIONS)} "
            f"{fake.random_element(ACQUISITION_ASSETS)} - "
            f"{fake.random_element(ACQUISITION_DELIVERABLES)}"
        )
        if title not in seen:
            seen.add(title)
            titles.append(title)
    return titles


def caef_level_labels(elements) -> list[dict[int, str]]:
    """Per element, the CAEF label of its ancestor at each level 2..8 ('' if none).

    Ancestors are found with concatenate_data, which uses each element's level,
    not its code. Elements at levels 0 and 1 are not chained and get blanks.
    """
    frame = pl.DataFrame(
        {
            "wbs": [f"e{i}" for i in range(len(elements))],
            "wbs_title": [label for _, label, _ in elements],
            "wbs_level": [level for _, _, level in elements],
        }
    )
    chained = concatenate_data(
        frame,
        text_field="wbs_title",
        level_field="wbs_level",
        starting_level=2,
        with_dates=False,
    )
    labels: list[dict[int, str]] = [{k: "" for k in LABEL_LEVELS} for _ in elements]
    for record in chained.iter_rows(named=True):
        index = int(record["wbs"][1:])
        labels[index] = {
            k: (record.get(f"wbs_level_{k}") or "").strip() for k in LABEL_LEVELS
        }
    return labels


def _catalog(elements, titles) -> dict:
    """SQL literals for the element lists, plus the element count."""
    labels = caef_level_labels(elements)
    return {
        "count": len(elements),
        "codes": _sql_list(code for code, _, _ in elements),
        "titles": _sql_list(titles),
        "levels": _sql_list(level for _, _, level in elements),
        "labels": {k: _sql_list(row[k] for row in labels) for k in LABEL_LEVELS},
    }


def _sql_list(values) -> str:
    return "[" + ", ".join("'" + str(v).replace("'", "''") + "'" for v in values) + "]"


def _typed(expression: str, col_type: str) -> str:
    if col_type.upper() == "VARCHAR":
        return expression
    return f"CAST({expression} AS {col_type})"


PARSID_SQL = f"list_extract({_sql_list(PROJECT_PARSIDS)}, (i % {N_PROJECTS}) + 1)"
PROJECT_NAME_SQL = f"list_extract({_sql_list(PROJECT_NAMES)}, (i % {N_PROJECTS}) + 1)"
LABEL_COLUMNS = {f"level_{k}": k for k in LABEL_LEVELS}


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _row_count(table: str, fact_rows: int, reference_rows: int) -> int:
    if table == "silver_project_descriptions":
        return N_PROJECTS  # one description row per project
    if any(marker in table for marker in REFERENCE_MARKERS):
        return reference_rows
    return fact_rows


def _column_expression(name: str, col_type: str, catalog: dict) -> str:
    lowered = name.lower()
    element = f"((i // {N_PROJECTS}) % {catalog['count']})"
    if lowered == "parsid":
        return _typed(PARSID_SQL, col_type)
    if lowered == "project_name":
        return _typed(PROJECT_NAME_SQL, col_type)
    if lowered == "program":
        return _typed("'Major Sports Venue Capital Program'", col_type)
    if lowered == "project_description":
        return _typed(
            f"'Multi-year stadium capital project: ' || {PROJECT_NAME_SQL} || "
            "'. Includes site works, seating and structural systems, ' || "
            "'fan amenities, transport access, commissioning, ' || "
            "'and billion-dollar cost oversight.'",
            col_type,
        )
    if lowered == "project_status":
        return _typed(
            "list_extract("
            "['Planning', 'Design', 'Execution', 'Closeout'], "
            "(i % 4) + 1)",
            col_type,
        )
    if lowered == "project_type":
        return _typed("'Major Sports Venue Construction'", col_type)
    if lowered == "nuclear_non_nuclear":
        return _typed("'Non-Nuclear'", col_type)
    if lowered == "ev_method":
        return _typed(
            "list_extract(['0/100', '50/50', 'Milestone'], (i % 3) + 1)", col_type
        )
    # Stadium programs have large construction budgets; keep schema types unchanged.
    if lowered.endswith("_dollars"):
        amount = "(2500000 + (i % 200) * 150000 + (i % 17) * 8000)"
        return _typed(f"CAST({amount} AS VARCHAR)", col_type)
    if lowered.endswith("_hours"):
        return _typed("CAST(8000 + (i % 1000) * 25 AS VARCHAR)", col_type)
    if lowered in ("wbs", "wbs_code"):
        return _typed(f"list_extract({catalog['codes']}, {element} + 1)", col_type)
    if lowered == "wbs_title":
        return _typed(f"list_extract({catalog['titles']}, {element} + 1)", col_type)
    if lowered == "wbs_level":
        return _typed(f"list_extract({catalog['levels']}, {element} + 1)", col_type)
    if lowered in LABEL_COLUMNS:
        labels = catalog["labels"][LABEL_COLUMNS[lowered]]
        return _typed(f"list_extract({labels}, {element} + 1)", col_type)
    if lowered == "period_date":
        pass_index = f"(i // {N_PROJECTS * catalog['count']}) % {PERIODS}"
        return _typed(
            f"strftime(DATE '2022-01-31' + CAST({pass_index} AS INTEGER) "
            f"* INTERVAL 1 MONTH, '%Y-%m-%d')",
            col_type,
        )
    if col_type.upper() != "VARCHAR":
        return f"CAST(i AS {col_type})"
    return "'mock_" + lowered.replace("'", "") + "_' || CAST(i % 97 AS VARCHAR)"


def build_mock_database(
    output_path: Path = DEFAULT_OUTPUT,
    schema_path: Path = SCHEMA_FILE,
    fact_rows: int = FACT_ROWS,
    reference_rows: int = REFERENCE_ROWS,
) -> dict[str, int]:
    """Build the mock database and return {table: row_count}.

    Builds into a temporary file and swaps it in, so a failed run never leaves
    a partially written database in place.
    """
    output_path = Path(output_path).resolve()
    if DATA_DIR not in output_path.parents:
        raise ValueError(f"Output must be inside {DATA_DIR}")
    schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))["tables"]
    elements = load_caef_elements()
    catalog = _catalog(elements, element_titles(len(elements)))

    tmp_path = output_path.with_suffix(".building.duckdb")
    if tmp_path.exists():
        tmp_path.unlink()
    counts: dict[str, int] = {}
    try:
        counts = _populate(tmp_path, schema, fact_rows, reference_rows, catalog)
        os.replace(tmp_path, output_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise
    return counts


def _populate(tmp_path, schema, fact_rows, reference_rows, catalog):
    counts: dict[str, int] = {}
    con = duckdb.connect(str(tmp_path))
    try:
        con.execute(
            f"CREATE TABLE {_quote(MARKER_TABLE)} (note VARCHAR, created_at TIMESTAMP)"
        )
        con.execute(
            f"INSERT INTO {_quote(MARKER_TABLE)} VALUES (?, now())", [MARKER_TEXT]
        )
        for table, columns in schema.items():
            cols_sql = ", ".join(f"{_quote(c['name'])} {c['type']}" for c in columns)
            con.execute(f"CREATE TABLE {_quote(table)} ({cols_sql})")
            n = _row_count(table, fact_rows, reference_rows)
            select_sql = ", ".join(
                f"{_column_expression(c['name'], c['type'], catalog)} "
                f"AS {_quote(c['name'])}"
                for c in columns
            )
            con.execute(
                f"INSERT INTO {_quote(table)} SELECT {select_sql} "
                f"FROM range({int(n)}) AS r(i)"
            )
            counts[table] = n
    finally:
        con.close()
    return counts


if __name__ == "__main__":
    result = build_mock_database()
    print(f"Built {len(result)} tables; total rows {sum(result.values()):,}")
