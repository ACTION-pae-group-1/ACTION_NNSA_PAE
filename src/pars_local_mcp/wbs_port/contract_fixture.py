"""LABELED TEST FIXTURE: a source-contract-conformant database built from bundled data.

This is NOT production data and NOT the bundled synthetic mock. It exists so the
verbatim WBS functions can be exercised end to end. The bundled mock
(mock_pars_full.duckdb) also passes ``validate_source``, but its gold_corrections
table is not the CAEF-labelled subset, so this fixture stays the labelled source
for gold_corrections.

Table identifiers are local names (no legacy source suffix). pipeline.validate_source
also accepts the legacy names listed in pipeline.SOURCE_TABLE_NAMES.

Mapping (documented in docs/wbs_model_mcp_parity.md, section "Test fixture"):

  parsid            the CAEF parsid, unchanged (integer text, 3-4 digits)
  wbs               wbs_code
  wbs_title         title; cleaned_title = title
  wbs_level         number of dot-separated components of wbs_code (CAEF depth)
  parent_wbs        wbs_code without its last component ('' at the top level)
  level_2..level_8  caef_level_k, '' where the element is shallower than k
  program, project_name, period_date (SPAE only): fixed fixture constants
  sample projects   the first SAMPLE_PROJECTS parsids in numeric order: labelled
                    sample (gold_corrections)
  all projects      SPAE (silver_spae_data); the sample projects are also in it

Supporting tables (abbreviations, stop words, stop phrases, project descriptions)
are copied unchanged from the bundled mock database.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import duckdb

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CAEF_DB = DATA_DIR / "caef_synthetic_labeled.duckdb"
MOCK_DB = DATA_DIR / "mock_pars_full.duckdb"
FIXTURE_MARKER = (
    "LABELED TEST FIXTURE derived from caef_synthetic_labeled.duckdb; "
    "not production data."
)
SAMPLE_PROJECTS = 4


def build_contract_fixture(
    out_path: Path, caef_db: Path = CAEF_DB, mock_db: Path = MOCK_DB
) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    con = duckdb.connect(str(out_path))
    try:
        con.execute(f"ATTACH '{Path(mock_db).as_posix()}' AS mock (READ_ONLY)")
        con.execute(f"ATTACH '{Path(caef_db).as_posix()}' AS caef (READ_ONLY)")
        for table in (
            "bronze_abbreviations",
            "silver_stop_words",
            "bronze_stop_phrases",
            "silver_project_descriptions",
        ):
            con.execute(f"CREATE TABLE {table} AS SELECT * FROM mock.main.{table}")
        con.execute(
            "CREATE TABLE _fixture_marker AS SELECT ? AS note", [FIXTURE_MARKER]
        )
        con.execute(
            "CREATE TABLE gold_corrections (parsid VARCHAR, wbs VARCHAR, "
            "wbs_title VARCHAR, cleaned_title VARCHAR, wbs_level VARCHAR, "
            "lowest_level VARCHAR, level_2 VARCHAR, level_3 VARCHAR, "
            "level_4 VARCHAR, level_5 VARCHAR, level_6 VARCHAR, "
            "level_7 VARCHAR, level_8 VARCHAR, parent_wbs VARCHAR)"
        )
        con.execute(
            "CREATE TABLE silver_spae_data (parsid VARCHAR, program VARCHAR, "
            "project_name VARCHAR, period_date VARCHAR, parent_wbs VARCHAR, "
            "wbs VARCHAR, wbs_title VARCHAR, wbs_level VARCHAR)"
        )
        rows = con.execute(
            "SELECT parsid, wbs_code, title, caef_level_2, caef_level_3, "
            "caef_level_4, caef_level_5, caef_level_6, caef_level_7, "
            "caef_level_8 FROM caef.main.labeled_wbs ORDER BY parsid, wbs_code"
        ).fetchall()
        sample_parsids = set(
            sorted({row[0] for row in rows}, key=int)[:SAMPLE_PROJECTS]
        )
        gold_rows = []
        spae_rows = []
        for parsid, code, title, *labels in rows:
            pid = parsid
            components = code.split(".")
            level = str(len(components))
            parent = ".".join(components[:-1])
            labels = ["" if label is None else label for label in labels]
            if pid in sample_parsids:
                gold_rows.append([pid, code, title, title, level, "", *labels, parent])
            spae_rows.append(
                [
                    pid,
                    "FIXTURE_PROGRAM",
                    f"FIXTURE_PROJECT_{pid}",
                    "2025-01",
                    parent,
                    code,
                    title,
                    level,
                ]
            )
        con.executemany(
            "INSERT INTO gold_corrections VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            gold_rows,
        )
        con.executemany(
            "INSERT INTO silver_spae_data VALUES (?,?,?,?,?,?,?,?)",
            spae_rows,
        )
        con.execute("CREATE TABLE silver_corrections AS SELECT * FROM gold_corrections")
    finally:
        con.close()
    return out_path


NONCONFORMING_WBS_LEVEL = "mock_wbs_level_7"


def build_nonconforming_copy(source: Path, out_path: Path) -> Path:
    """Copy a source and set every silver_spae_data wbs_level to non-integer text.

    The copy fails validate_source with exactly one problem. Tests use it to
    exercise the refusal path without depending on the bundled mock's contents.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()
    shutil.copyfile(source, out_path)
    with duckdb.connect(str(out_path)) as con:
        con.execute(
            "UPDATE silver_spae_data SET wbs_level = ?", [NONCONFORMING_WBS_LEVEL]
        )
    return out_path
