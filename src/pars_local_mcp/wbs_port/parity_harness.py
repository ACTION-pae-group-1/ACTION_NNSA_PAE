"""Function-level parity harness for the verbatim WBS functions.

The same ``compute_outputs`` runs against two namespaces:

* the ORIGINAL source functions, loaded from WBS Modeling ``functions.py`` by AST
  extraction (only the named top-level definitions are executed), under the source's
  pinned library versions (polars 1.13.1, hiclass 4.11.0, duckdb 1.4.1, joblib 1.4.2,
  scikit-learn 1.4.2, scikit-multilearn 0.2.0, numpy 1.26.4, pandas 2.3.3). The source
  functions hard-code legacy table names, so the source side uses those names;
* the PORT, ``pars_local_mcp.wbs_port.functions``, under the project venv, which uses
  local table names.

``generate_golden`` (run by a developer with the source checkout) stores the source
outputs in ``parity_golden.json``. The unit tests recompute the port outputs and compare
them with that file. No test needs the source repository. Outputs are keyed by local
table names on both sides.

Determinism notes (source behaviour, not changed here):
* ``stratify`` uses IterativeStratification, which draws from the global NumPy RNG when
  no random_state is given. The harness seeds the global RNG before it and sorts its
  input, because the source's ``unique()`` calls do not preserve row order.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import shutil
import sys
import types
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import polars as pl

FUNCTION_NAMES = (
    "load_tables",
    "transform",
    "concatenate_data",
    "clean_stitch",
    "clean_data",
    "MultiColumnLabelEncoder",
    "encode_labels",
    "stratify",
    "f1_scorer",
    "safe_f1",
    "batch_predict",
    "save_results_to_db",
)
HIERARCHIES = [
    "level_2",
    "level_3",
    "level_4",
    "level_5",
    "level_6",
    "level_7",
    "level_8",
]
STRATIFY_SEED = 0
GOLDEN_PATH = Path(__file__).with_name("parity_golden.json")

# Local table name -> legacy name that the source functions hard-code (source side
# only). The suffix comes from PARS_LEGACY_TABLE_SUFFIX, so the repository holds no
# source names. Regenerating the golden needs that variable set.
LEGACY_TABLE_SUFFIX = os.environ.get("PARS_LEGACY_TABLE_SUFFIX", "")
LEGACY_TABLE_NAMES = {
    local: local + LEGACY_TABLE_SUFFIX
    for local in (
        "silver_corrections",
        "silver_cleaned_concat_sample",
        "silver_cleaned_concat_spae",
    )
}
LOCAL_OF_LEGACY = {legacy: local for local, legacy in LEGACY_TABLE_NAMES.items()}


def load_source_namespace(source_file: Path) -> dict[str, Any]:
    """Execute the named top-level definitions of the source file in a fresh module."""
    text = Path(source_file).read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    tree = ast.parse(text)
    found: dict[str, ast.AST] = {}
    for node in tree.body:
        if (
            isinstance(node, (ast.FunctionDef, ast.ClassDef))
            and node.name in FUNCTION_NAMES
        ):
            found[node.name] = node  # the last definition wins, as in Python
    module = types.ModuleType("wbs_source_functions")
    sys.modules["wbs_source_functions"] = module
    ns = module.__dict__
    import hiclass
    from hiclass.metrics import f1, precision, recall
    from sklearn.preprocessing import LabelEncoder
    from skmultilearn.model_selection import IterativeStratification

    ns.update(
        {
            "os": __import__("os"),
            "re": __import__("re"),
            "np": np,
            "pl": pl,
            "joblib": __import__("joblib"),
            "duckdb": duckdb,
            "hiclass": hiclass,
            "f1": f1,
            "precision": precision,
            "recall": recall,
            "IterativeStratification": IterativeStratification,
            "LabelEncoder": LabelEncoder,
            "input_dir": None,
            "output_dir": None,
            "duck_db": "mock_pars_full.duckdb",
        }
    )
    for name in FUNCTION_NAMES:
        if name not in found:
            raise KeyError(f"source function not found: {name}")
        node = found[name]
        exec(
            compile(
                "".join(lines[node.lineno - 1 : node.end_lineno]),
                str(source_file),
                "exec",
            ),
            ns,
        )
    return ns


def load_port_namespace(port_module) -> dict[str, Any]:
    return vars(port_module)


def _sha_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _frame_sha(frame: pl.DataFrame, sort_by: list[str]) -> str:
    ordered = frame.sort(sort_by)
    return _sha_json({"columns": ordered.columns, "rows": ordered.rows()})


def _write_frame(
    con: duckdb.DuckDBPyConnection, name: str, frame: pl.DataFrame
) -> None:
    """Source write pattern: all-varchar CREATE OR REPLACE, then INSERT SELECT.

    The frame is registered under a temporary name and selected into the table.
    """
    col_defs = ",\n    ".join(f'"{c}" varchar' for c in frame.columns)
    con.execute(f'CREATE OR REPLACE TABLE "{name}" (\n    {col_defs}\n);')
    con.register("_frame_to_write", frame.cast({c: pl.Utf8 for c in frame.columns}))
    con.execute(f'INSERT INTO "{name}" SELECT * FROM _frame_to_write;')
    con.unregister("_frame_to_write")


class _FixedModel:
    """Deterministic stand-in for a fitted estimator.

    Returns precomputed predictions.
    """

    def __init__(self, table: np.ndarray):
        self.table = table

    def predict(self, X):
        return self.table[: len(X)]


def compute_outputs(
    ns: dict[str, Any], fixture_db: Path, workdir: Path, side: str = "port"
) -> dict[str, Any]:
    """Run the parity sequence on one namespace and return JSON-safe summaries.

    side "port" uses local table names; side "source" uses the legacy names the source
    functions hard-code. Output keys are local names on both sides.
    """
    if side not in ("port", "source"):
        raise ValueError("side must be 'port' or 'source'")
    names = LEGACY_TABLE_NAMES if side == "source" else {}

    def name_for(local: str) -> str:
        return names.get(local, local)

    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    db_copy = workdir / "parity.duckdb"
    shutil.copyfile(fixture_db, db_copy)
    ns["input_dir"] = str(workdir)
    ns["output_dir"] = str(workdir / "out")
    (workdir / "out").mkdir(exist_ok=True)
    ns["duck_db"] = db_copy.name
    out: dict[str, Any] = {}

    # transform: fixed literal input with case, cost, numeric WBS and blank-level cases.
    literal = pl.DataFrame(
        {
            "wbs": ["1", "1.1", "2.10", "1.1.1"],
            "parent_wbs": ["", "1", "2", "1.1"],
            "level_2": ["Level Two  COSTS", "Level Two  COSTS", "0", " Alpha "],
            "level_3": ["3.1 Title", "", "Commisioning", "3.2 Title"],
            "wbs_title": ["Construction Management", "x  y", "0", "z"],
        }
    )
    out["transform"] = {
        "rows": ns["transform"](literal).sort(["wbs", "parent_wbs", "wbs_title"]).rows()
    }

    con = duckdb.connect(str(db_copy))
    try:

        def read(table: str) -> pl.DataFrame:
            return con.execute(f'SELECT * FROM "{table}"').pl()

        abbreviations = read("bronze_abbreviations")
        stop_words = read("silver_stop_words")
        stop_phrases = read("bronze_stop_phrases")
        projects = read("silver_project_descriptions")
        gold = read("gold_corrections")
        spae = read("silver_spae_data")
        if side == "source":  # source load_tables() reads the legacy corrections name
            con.execute(
                f'ALTER TABLE "silver_corrections" '
                f'RENAME TO "{name_for("silver_corrections")}"'
            )
    finally:
        con.close()

    concat_sample = ns["concatenate_data"](
        gold,
        text_field="wbs_title",
        starting_level=2,
        level_field="wbs_level",
        with_dates=False,
    )
    out["concatenate_sample"] = {
        "shape": list(concat_sample.shape),
        "sha256": _frame_sha(concat_sample, ["parsid", "wbs"]),
    }
    cleaned = ns["clean_stitch"](
        concat_sample,
        text_field="wbs_title",
        stop_words=stop_words,
        stop_phrases=stop_phrases,
        abbreviations=abbreviations,
        project_descriptions=projects,
    ).unique(subset=["wbs_title", "parsid"])
    out["clean_sample"] = {
        "shape": list(cleaned.shape),
        "sha256": _frame_sha(cleaned, ["parsid", "wbs", "wbs_title"]),
    }

    concat_full = ns["concatenate_data"](
        spae,
        text_field="wbs_title",
        starting_level=1,
        level_field="wbs_level",
        with_dates=True,
    )
    out["concatenate_spae"] = {
        "shape": list(concat_full.shape),
        "sha256": _frame_sha(concat_full, ["parsid", "wbs", "period_date"]),
    }
    full = ns["clean_stitch"](
        concat_full,
        text_field="wbs_title",
        stop_words=stop_words,
        stop_phrases=stop_phrases,
        abbreviations=abbreviations,
        project_descriptions=projects,
    )
    full = full.drop("program_right", "project_name_right").unique()
    out["clean_spae"] = {
        "shape": list(full.shape),
        "sha256": _frame_sha(full, ["parsid", "wbs", "original_title"]),
    }

    # Stable ordering before the order-sensitive steps (see module docstring).
    ordered = cleaned.sort(["parsid", "wbs", "wbs_title"])
    encoder = ns["MultiColumnLabelEncoder"](columns=HIERARCHIES).fit(
        ordered.select(HIERARCHIES)
    )
    out["label_encoder"] = {c: list(encoder.encoders[c].classes_) for c in HIERARCHIES}
    encoded = encoder.transform(ordered.select(HIERARCHIES))
    out["label_codes_sha256"] = _sha_json(encoded.rows())
    decoded = encoder.inverse_transform(encoded)
    out["label_roundtrip_equal"] = decoded.rows() == ordered.select(HIERARCHIES).rows()

    # Persist derived tables the way the notebook chain does, so load_tables() can
    # read them.
    con = duckdb.connect(str(db_copy))
    try:
        _write_frame(con, name_for("silver_cleaned_concat_sample"), cleaned)
        _write_frame(con, name_for("silver_cleaned_concat_spae"), full)
    finally:
        con.close()

    np.random.seed(STRATIFY_SEED)
    y_encoded = ns["encode_labels"](str(workdir), ordered, HIERARCHIES)[0]
    X_tr, X_te, y_tr, y_te = ns["stratify"](
        ordered, y_encoded, text_field="wbs_title", test_size=0.2
    )
    out["stratify"] = {
        "train_rows": int(len(X_tr)),
        "test_rows": int(len(X_te)),
        "X_train_sha256": _sha_json([str(x) for x in X_tr]),
        "X_test_sha256": _sha_json([str(x) for x in X_te]),
        "y_train_sha256": _sha_json(np.asarray(y_tr).tolist()),
        "y_test_sha256": _sha_json(np.asarray(y_te).tolist()),
    }

    # Scorers on fixed predictions (no estimator fitting).
    truth = np.array([[1, 2], [1, 3], [2, 2], [2, 3]])
    fixed = np.array([[1, 2], [1, 3], [2, 2], [1, 3]])
    model = _FixedModel(fixed)
    out["f1_scorer"] = float(ns["f1_scorer"](model, np.zeros((4, 1)), truth))
    out["safe_f1"] = float(ns["safe_f1"](truth, fixed))
    batch = ns["batch_predict"](
        np.zeros((7, 1)), _FixedModel(np.arange(14).reshape(7, 2)), batch_size=3
    )
    out["batch_predict"] = [list(map(int, row)) for row in batch]

    tables = ns["load_tables"](input_dir=str(workdir), duck_db=db_copy.name)
    out["load_tables"] = {
        LOCAL_OF_LEGACY.get(name, name): [frame.height, frame.width]
        for name, frame in sorted(tables.items())
    }
    cd_train = ns["clean_data"](
        tables,
        text_field="wbs_title",
        file_type="training",
        level_field="wbs_level",
        starting_level=2,
        with_dates=False,
    )
    out["clean_data_training"] = {
        "shape": list(cd_train.shape),
        "sha256": _frame_sha(cd_train, ["parsid", "wbs", "wbs_title"]),
    }
    cd_infer = ns["clean_data"](
        tables,
        text_field="wbs_title",
        file_type="inference",
        level_field="wbs_level",
        starting_level=2,
        with_dates=True,
    )
    out["clean_data_inference"] = {
        "shape": list(cd_infer.shape),
        "sha256": _frame_sha(cd_infer, ["parsid", "wbs", "original_title"]),
    }
    return out


def generate_golden(
    source_file: Path, fixture_db: Path, workdir: Path, out_path: Path = GOLDEN_PATH
) -> dict[str, Any]:
    """Developer step: source outputs under the source-pinned environment.

    The outputs are written to out_path as the golden JSON file.
    """
    ns = load_source_namespace(Path(source_file))
    outputs = compute_outputs(ns, Path(fixture_db), Path(workdir), side="source")
    payload = {
        "provenance": {
            "source": "WBS Modeling functions.py",
            "source_revision": "e41fba1",
            "pinned_versions": {
                "polars": "1.13.1",
                "hiclass": "4.11.0",
                "duckdb": "1.4.1",
                "joblib": "1.4.2",
                "scikit-learn": "1.4.2",
                "scikit-multilearn": "0.2.0",
                "numpy": "1.26.4",
                "pandas": "2.3.3",
            },
            "fixture": (
                "labeled test fixture from "
                "wbs_port.contract_fixture.build_contract_fixture"
            ),
            "stratify_seed": STRATIFY_SEED,
        },
        "outputs": outputs,
    }
    Path(out_path).write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8"
    )
    return payload
