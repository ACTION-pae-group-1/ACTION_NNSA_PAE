"""Generate the CAEF-labelled training subset of the full mock.

Each row is one element of the full mock for one project: the same parsid,
project, WBS code and Faker title. caef_level_2..8 are the CAEF 2.0 reference
labels of the element's ancestors (the targets), computed by the same function
the full mock uses for its level_2..level_8 columns. Elements at levels 0 and 1
have no labelled row.

Elements, titles, labels and projects come from pars_local_mcp.data.generate_full_mock,
so this table is always a subset of the full mock.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

from pars_local_mcp.data.generate_full_mock import (
    LABEL_LEVELS,
    N_PROJECTS,
    PROJECT_NAMES,
    PROJECT_PARSIDS,
    REFERENCE_FILE,
    TITLE_SEED,
    caef_level_labels,
    element_titles,
    load_caef_elements,
)

LABEL_COLUMNS = [f"caef_level_{level}" for level in LABEL_LEVELS]
DATA_DIR = Path(__file__).parent
DEFAULT_REFERENCE = REFERENCE_FILE
DEFAULT_OUTPUT = DATA_DIR / "caef_synthetic_labeled.duckdb"


def build_labeled_rows(
    elements: list[tuple[str, str, int]],
    parsids: list[str],
    seed: int = TITLE_SEED,
) -> list[dict[str, str]]:
    """Build one labelled row per element per project.

    ``elements`` holds (wbs_code, CAEF label, level) in reference order. Each
    element's ``title`` is its Faker title (element_titles), shared by every
    project. caef_level_N is the CAEF label of the element's ancestor at level N
    (blank if there is none). Elements below level 2 are not labelled.
    """
    codes = [code for code, _, _ in elements]
    titles = element_titles(len(elements), seed)
    labels = caef_level_labels(elements)

    base = [
        {
            "wbs_code": codes[i],
            "title": titles[i],
            **{f"caef_level_{k}": labels[i][k] for k in LABEL_LEVELS},
        }
        for i, (_, _, level) in enumerate(elements)
        if level >= 2
    ]
    return [{"parsid": parsid, **row} for parsid in parsids for row in base]


def write_database(
    rows: list[dict[str, str]], projects: list[tuple[str, str]], output: Path
) -> None:
    output.unlink(missing_ok=True)
    with duckdb.connect(str(output)) as conn:
        conn.execute(
            "CREATE TABLE projects (parsid VARCHAR PRIMARY KEY, project_name VARCHAR)"
        )
        conn.executemany("INSERT INTO projects VALUES (?, ?)", projects)
        conn.execute(
            "CREATE TABLE labeled_wbs (parsid VARCHAR, wbs_code VARCHAR, "
            "title VARCHAR, " + ", ".join(f"{c} VARCHAR" for c in LABEL_COLUMNS) + ")"
        )
        columns = ["parsid", "wbs_code", "title", *LABEL_COLUMNS]
        placeholders = ", ".join("?" * len(columns))
        conn.executemany(
            f"INSERT INTO labeled_wbs ({', '.join(columns)}) VALUES ({placeholders})",
            [tuple(r[c] for c in columns) for r in rows],
        )


def build_database(
    output: Path = DEFAULT_OUTPUT,
    reference: Path = DEFAULT_REFERENCE,
    n_projects: int = N_PROJECTS,
) -> tuple[int, int]:
    """Write the labeled database; return (rows, projects) written."""
    projects = [
        (str(parsid), name) for parsid, name in zip(PROJECT_PARSIDS, PROJECT_NAMES)
    ][:n_projects]
    elements = load_caef_elements(reference)
    rows = build_labeled_rows(elements, [parsid for parsid, _ in projects])
    write_database(rows, projects, output)
    return len(rows), len(projects)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--projects", type=int, default=N_PROJECTS)
    args = parser.parse_args()

    n_rows, n_projects = build_database(args.output, args.reference, args.projects)
    print(
        f"[OK] Wrote {n_rows} labeled rows across {n_projects} projects "
        f"to {args.output}"
    )


if __name__ == "__main__":
    main()
