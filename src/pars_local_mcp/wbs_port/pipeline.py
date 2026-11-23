"""Local orchestration of the WBS Modeling notebook chain (ML path).

Order and glue are copied from the source notebooks (WBS Modeling, revision e41fba1):

  stage "clean"        00-setup_clean_jupyter_vscode_python.ipynb
                       cells 24, 27, 29, 31, 32
  stage "tune_train"   01-tune_train_save_ml.ipynb cells 0-9, 11
  stage "predict"     02-load_predict.ipynb cells 0-2
  stage "write_back"   02-load_predict.ipynb cells 3-6

Every algorithm call goes to the verbatim functions in ``wbs_port.functions``.
Environment adaptations (documented in docs/wbs_model_mcp_parity.md):

* The source database file is replaced by a per-run working copy of the
  configured source database. The source-database file itself is never written.
* Source paths (INPUTS_DIR / OUTPUT_DIR / LOG_DIR) map to the run directory.
* Fitted estimators are persisted only inside HMAC-signed bundles (see
  ``pars_local_mcp.wbs.artifacts``) and are loaded back only after the signature
  verifies. The source writes plain joblib files instead.
* Stratification and tuning use the global NumPy RNG exactly as the source does.
  ``split_seed`` / ``search_seed`` seed that RNG and RandomizedSearchCV. Repeat runs
  with the same seeds give the same predictions (see
  ``test_two_runs_with_same_seeds_produce_identical_predictions``) because the clean
  stage's ``unique()`` calls keep row order (``maintain_order=True``). The default
  ``None`` keeps the source behaviour.
"""

from __future__ import annotations

import contextlib
import datetime as _dt
import hashlib
import json
import math
import os
import re
import shutil
import threading
import uuid
from pathlib import Path
from typing import Any

import duckdb
import joblib
import numpy as np
import polars as pl
from hiclass import LocalClassifierPerParentNode
from hiclass.metrics import f1 as hiclass_f1
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import make_scorer
from sklearn.model_selection import RandomizedSearchCV
from sklearn.pipeline import Pipeline
from skmultilearn.model_selection import IterativeStratification

from pars_local_mcp.mcp.errors import PublicError
from pars_local_mcp.wbs import artifacts
from pars_local_mcp.wbs_port import functions as wbs

HIERARCHIES = [
    "level_2",
    "level_3",
    "level_4",
    "level_5",
    "level_6",
    "level_7",
    "level_8",
]  # 01 cell 0
TEXT_FIELD = "wbs_title"  # 01 cell 0
PREDICTED_COLUMNS = [f"level_{i + 2}" for i in range(7)]  # 02 cell 2
WORKING_DB = "working.duckdb"
MANIFEST = "run_manifest.json"
MODEL_VARIANTS = ("untuned", "tuned")
STAGES = ("clean", "tune_train", "predict", "write_back")
DOWNSTREAM = {
    "clean": ["tune_train", "predict", "write_back"],
    "tune_train": ["predict", "write_back"],
    "predict": ["write_back"],
    "write_back": [],
}
# Legacy table names of the source database (WBS Modeling). The source functions were
# written against these; the port uses local names. Only the inputs that the source
# database provides under legacy names are listed; they are renamed inside the per-run
# working copy and the source file is never modified. The suffix is not stored in the
# repository: set PARS_LEGACY_TABLE_SUFFIX where the real source database is read.
# Unset, legacy names equal local names and nothing is renamed.
LEGACY_TABLE_SUFFIX = os.environ.get("PARS_LEGACY_TABLE_SUFFIX", "")
SOURCE_TABLE_NAMES = {
    local: local + LEGACY_TABLE_SUFFIX
    for local in ("gold_corrections", "silver_spae_data", "silver_corrections")
}
# Input tables the source database must provide. silver_cleaned_concat_* are outputs
# of the clean stage and are not required here. silver_corrections is not read
# by the live path but load_tables() (functions.py L67-70) opens it, so it is required.
SOURCE_TABLES = (
    "bronze_abbreviations",
    "bronze_stop_phrases",
    "silver_stop_words",
    "silver_project_descriptions",
    "silver_corrections",
    "gold_corrections",
    "silver_spae_data",
)
# Tables that must exist in the source database and the columns the live path reads.
REQUIRED_COLUMNS = {
    "gold_corrections": [
        "parsid",
        "wbs",
        "wbs_title",
        "wbs_level",
        *HIERARCHIES,
    ],
    "silver_spae_data": [
        "parsid",
        "program",
        "project_name",
        "period_date",
        "parent_wbs",
        "wbs",
        "wbs_title",
        "wbs_level",
    ],
    "silver_project_descriptions": ["parsid", "program", "project_name"],
    "bronze_abbreviations": ["abbreviation", "definition"],
    "bronze_stop_phrases": ["word"],
    "silver_stop_words": ["word"],
    "silver_corrections": [],
}

# 01_ml cell 8, copied verbatim.
PARAM_GRID = {
    "vectorizer__ngram_range": [(1, 1), (1, 2)],
    "vectorizer__min_df": [1, 2, 5],
    "vectorizer__max_df": [0.85, 0.95, 1.0],
    "vectorizer__sublinear_tf": [False, True],
    "model__local_classifier__max_iter": [5000],  # hold constant
    "model__local_classifier__loss": ["log_loss", "hinge", "modified_huber"],
    "model__local_classifier__penalty": ["elasticnet"],
    "model__local_classifier__alpha": [1e-6, 1e-5, 1e-4, 1e-3],
    "model__local_classifier__l1_ratio": [0.0, 0.15, 0.5, 0.85],
    "model__local_classifier__learning_rate": ["optimal", "adaptive", "constant"],
    "model__local_classifier__eta0": [0.001, 0.01],
    "model__local_classifier__early_stopping": [False],
    "model__local_classifier__n_iter_no_change": [5, 10],
    "model__local_classifier__tol": [1e-4, 1e-3, None],
}

_LOCK = (
    threading.RLock()
)  # the source functions read module globals; serialise stage calls
_RUN_ID_RE = re.compile(r"r[0-9a-f]{12}")  # used with fullmatch: "$" accepts "\n"


class WBSPipelineError(PublicError):
    """Actionable pipeline failure (missing inputs, failed contract, missing stage).

    Subclasses PublicError, so the message reaches the MCP client as written. Never
    put paths, SQL, or record values in it.
    """


# --------------------------------------------------------------------------- runs
def new_run_id() -> str:
    return "r" + uuid.uuid4().hex[:12]


def run_dir_for(runs_root: Path, run_id: str) -> Path:
    if not _RUN_ID_RE.fullmatch(run_id or ""):
        raise WBSPipelineError(
            "run_id must look like 'r' followed by 12 lowercase hex characters"
        )
    return Path(runs_root) / run_id


def check_search_args(n_iter: int, cv_folds: int) -> None:
    """Reject search sizes the source functions cannot use.

    Callers run this before any run directory, source copy, or log exists.
    """
    if n_iter < 1 or cv_folds < 2:
        raise WBSPipelineError("n_iter must be >= 1 and cv_folds must be >= 2")


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _read_manifest(run_dir: Path) -> dict[str, Any]:
    path = run_dir / MANIFEST
    if not path.is_file():
        raise WBSPipelineError(
            f"Run not found: {run_dir.name}. "
            "Start with clean_wbs_data or run_wbs_pipeline."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _write_manifest(run_dir: Path, manifest: dict[str, Any]) -> None:
    (run_dir / MANIFEST).write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )


def _require_stage(manifest: dict[str, Any], stage: str) -> None:
    info = manifest["stages"].get(stage)
    if not info or info.get("status") != "ok":
        raise WBSPipelineError(
            f"Stage '{stage}' has not completed for run {manifest['run_id']}; "
            "run it first (order: clean -> tune_train -> predict -> write_back)."
        )


def run_status(runs_root: Path, run_id: str) -> dict[str, Any]:
    return _read_manifest(run_dir_for(runs_root, run_id))


# ------------------------------------------------------------ source reads
SOURCE_READS: dict[str, tuple[str, list[str]]] = {
    "project_descriptions": (
        "silver_project_descriptions",
        [
            "parsid",
            "program",
            "project_name",
            "project_status",
            "project_type",
            "project_description",
        ],
    ),
    "wbs_rows": (
        "silver_spae_data",
        ["parsid", "program", "project_name", "wbs", "wbs_level", "wbs_title"],
    ),
}


# Origins whose rows the read tools may return. The bundled synthetic mock and the
# labeled test fixture are both built from caef_synthetic_labeled.duckdb, which
# docs/DATA_HANDLING.md documents as synthetic. Unknown origins are not listed.
SYNTHETIC_ORIGINS = frozenset({"synthetic_mock", "labeled_test_fixture"})

# Search workers when the caller does not set n_jobs. The source uses -1 (every core),
# which starts one process per core. A fixed count keeps the search bounded.
# Results do not depend on the worker count when the search seed is fixed.
DEFAULT_N_JOBS = 4


def data_origin(existing: set[str]) -> str:
    """Origin named by the marker tables of a source database (one check for all)."""
    origin = "unknown"
    if "_mock_marker" in existing:
        origin = "synthetic_mock"
    if "_fixture_marker" in existing:
        origin = "labeled_test_fixture"
    return origin


def read_source_rows(source_db: Path, which: str, limit: int) -> dict[str, Any]:
    """Return up to ``limit`` rows of one source table, opened read-only.

    The table name resolves the same way validate_source resolves it: the legacy
    name is used when the database has it. Rows are returned only when the origin is
    in SYNTHETIC_ORIGINS; the error is fixed text and names no data or paths.
    """
    local_table, columns = SOURCE_READS[which]
    select = ", ".join(f'"{c}"' for c in columns)
    con = duckdb.connect(str(source_db), read_only=True)
    try:
        existing = {
            r[0]
            for r in con.execute(
                "SELECT table_name FROM information_schema.tables"
            ).fetchall()
        }
        if data_origin(existing) not in SYNTHETIC_ORIGINS:
            raise WBSPipelineError(
                "Source rows are returned only for documented synthetic data"
            )
        table = _resolve_name(existing, local_table)
        total = con.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
        fetched = con.execute(
            f'SELECT {select} FROM "{table}" LIMIT ?', [limit]
        ).fetchall()
    finally:
        con.close()
    return {
        "table": table,
        "columns": columns,
        "total_rows": total,
        "returned": len(fetched),
        "rows": [dict(zip(columns, row)) for row in fetched],
    }


# ---------------------------------------------------------------- source checks
def _is_int_castable(frame: pl.DataFrame, column: str) -> int:
    """Count values that do not cast to Int64. Values are never returned."""
    series = frame.get_column(column)
    cast = series.cast(pl.Int64, strict=False)
    bad = series.is_not_null() & cast.is_null()
    return int(bad.sum())


def _resolve_name(existing: set[str], local: str) -> str:
    """Source database name for a local identifier (legacy name when present)."""
    legacy = SOURCE_TABLE_NAMES.get(local)
    if legacy is not None and legacy in existing:
        return legacy
    return local


def validate_source(source_db: Path) -> dict[str, Any]:
    """Check the source database against the contract the source functions rely on.

    Accepts local identifiers or the legacy names in SOURCE_TABLE_NAMES. Returns a
    report; ``ok`` is False when any contract violation is found. Nothing is written.
    The report names tables, columns and problem types with counts only; it never
    returns source record values.
    """
    source_db = Path(source_db)
    report: dict[str, Any] = {
        "source_db_name": source_db.name,
        "ok": True,
        "problems": [],
        "tables": {},
        "data_origin": "unknown",
    }
    if not source_db.is_file():
        report["ok"] = False
        report["problems"].append(f"source database not found: {source_db.name}")
        return report
    con = duckdb.connect(str(source_db), read_only=True)
    try:
        existing = {
            r[0]
            for r in con.execute(
                "SELECT table_name FROM information_schema.tables"
            ).fetchall()
        }
        report["data_origin"] = data_origin(existing)
        for table in SOURCE_TABLES:
            name = _resolve_name(existing, table)
            if name not in existing:
                report["ok"] = False
                report["problems"].append(f"missing table: {table}")
                continue
            columns = {r[0] for r in con.execute(f'DESCRIBE "{name}"').fetchall()}
            rows = con.execute(f'SELECT count(*) FROM "{name}"').fetchone()[0]
            report["tables"][name] = {"rows": int(rows)}
            absent = [c for c in REQUIRED_COLUMNS.get(table, []) if c not in columns]
            if absent:
                report["ok"] = False
                report["problems"].append(f"{name}: missing columns {absent}")
        if any(p.startswith("missing table") for p in report["problems"]):
            return report
        for table in ("gold_corrections", "silver_spae_data"):
            name = _resolve_name(existing, table)
            frame = con.execute(f'SELECT * FROM "{name}"').pl()
            bad = _is_int_castable(frame, "wbs_level")
            if bad:
                report["ok"] = False
                report["problems"].append(
                    f"{name}.wbs_level: {bad} of {frame.height} values are not "
                    "integers; concatenate_data casts this column to Int64"
                )
            bad = _is_int_castable(frame, "parsid")
            if bad:
                report["ok"] = False
                report["problems"].append(
                    f"{name}.parsid: {bad} of {frame.height} values are not integers; "
                    "clean_stitch joins on parsid cast to Int64"
                )
        dtype = con.execute(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = ? AND column_name = ?",
            ["silver_project_descriptions", "parsid"],
        ).fetchone()
        if dtype and dtype[0].upper() not in (
            "BIGINT",
            "INTEGER",
            "INT8",
            "INT4",
            "HUGEINT",
            "SMALLINT",
        ):
            report["ok"] = False
            report["problems"].append(
                f"silver_project_descriptions.parsid is {dtype[0]}, "
                "expected an integer type"
            )
    finally:
        con.close()
    return report


# --------------------------------------------------------------- DB helpers
def _write_table(
    con: duckdb.DuckDBPyConnection, name: str, frame: pl.DataFrame
) -> None:
    """Source write pattern.

    CREATE OR REPLACE with all-varchar columns, TRUNCATE, then INSERT SELECT.
    """
    col_defs = ",\n    ".join(f'"{c}" varchar' for c in frame.columns)
    con.execute(f'CREATE OR REPLACE TABLE "{name}" (\n    {col_defs}\n);')
    con.execute(f'TRUNCATE TABLE "{name}";')
    con.register("_frame_to_write", frame.cast({c: pl.Utf8 for c in frame.columns}))
    con.execute(f'INSERT INTO "{name}" SELECT * FROM _frame_to_write;')
    con.unregister("_frame_to_write")


def _json_safe(value: Any) -> Any:
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    return value


@contextlib.contextmanager
def _stage_context(run_dir: Path, stage: str):
    with _LOCK:
        wbs.configure_paths(run_dir, run_dir / "outputs", WORKING_DB)
        (run_dir / "outputs").mkdir(parents=True, exist_ok=True)
        (run_dir / "logs").mkdir(parents=True, exist_ok=True)
        with (run_dir / "logs" / f"{stage}.log").open("w", encoding="utf-8") as log:
            with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                yield log


# ---------------------------------------------------------------- stage: clean
def stage_clean(runs_root: Path, run_id: str | None, source_db: Path) -> dict[str, Any]:
    """00 notebook: concatenate and clean the labelled sample and full SPAE table."""
    run_id = run_id or new_run_id()
    run_dir = run_dir_for(runs_root, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = run_dir / MANIFEST
    manifest = (
        _read_manifest(run_dir)
        if manifest_path.is_file()
        else {"run_id": run_id, "created_at": _now(), "stages": {}}
    )

    report = validate_source(source_db)
    if not report["ok"]:
        raise WBSPipelineError(
            "Source database fails the WBS input contract: "
            + "; ".join(report["problems"])
        )

    with _stage_context(run_dir, "clean"):
        working = run_dir / WORKING_DB
        shutil.copyfile(
            source_db, working
        )  # the source database itself is never opened for writing
        con = duckdb.connect(str(working))
        try:
            present = {
                r[0]
                for r in con.execute(
                    "SELECT table_name FROM information_schema.tables"
                ).fetchall()
            }
            for (
                local,
                legacy,
            ) in (
                SOURCE_TABLE_NAMES.items()
            ):  # working copy only; source is never modified
                if legacy in present and local not in present:
                    con.execute(f'ALTER TABLE "{legacy}" RENAME TO "{local}"')

            def read(table: str) -> pl.DataFrame:
                return con.execute(f'SELECT * FROM "{table}"').pl()

            abbreviations_df = read("bronze_abbreviations")  # 00 cell 8
            stop_words_df = read("silver_stop_words")  # 00 cell 10
            stop_phrases_df = read("bronze_stop_phrases")  # 00 cell 10
            project_descriptions_df = read("silver_project_descriptions")  # 00 cell 18

            sample_data = read("gold_corrections")  # 00 cell 24
            concatenated_sample = wbs.concatenate_data(
                sample_data,
                text_field=TEXT_FIELD,
                starting_level=2,
                level_field="wbs_level",
                with_dates=False,
            )  # 00 cell 27
            _write_table(con, "silver_concatenated_sample_data", concatenated_sample)
            cleaned_sample = wbs.clean_stitch(
                concatenated_sample,
                text_field=TEXT_FIELD,
                stop_words=stop_words_df,
                stop_phrases=stop_phrases_df,
                abbreviations=abbreviations_df,
                project_descriptions=project_descriptions_df,
            ).unique(subset=[TEXT_FIELD, "parsid"], maintain_order=True)  # 00 cell 31
            _write_table(con, "silver_cleaned_concat_sample", cleaned_sample)

            spae = read("silver_spae_data")  # 00 cell 12
            concatenated_full = wbs.concatenate_data(
                spae,
                text_field=TEXT_FIELD,
                starting_level=1,
                level_field="wbs_level",
                with_dates=True,
            )  # 00 cell 29
            _write_table(con, "silver_concatenated_spae_data", concatenated_full)
            cleaned_full = wbs.clean_stitch(
                concatenated_full,
                text_field=TEXT_FIELD,
                stop_words=stop_words_df,
                stop_phrases=stop_phrases_df,
                abbreviations=abbreviations_df,
                project_descriptions=project_descriptions_df,
            )  # 00 cell 32
            cleaned_full = cleaned_full.drop(
                "program_right", "project_name_right"
            ).unique(maintain_order=True)
            _write_table(con, "silver_cleaned_concat_spae", cleaned_full)
        finally:
            con.close()

    details = {
        "source_database": source_db.name,
        "data_origin": report["data_origin"],
        "concatenated_sample_rows": concatenated_sample.height,
        "cleaned_sample_rows": cleaned_sample.height,
        "concatenated_spae_rows": concatenated_full.height,
        "cleaned_spae_rows": cleaned_full.height,
    }
    manifest["stages"]["clean"] = {"status": "ok", "finished_at": _now(), **details}
    manifest["data_origin"] = report["data_origin"]
    _mark_downstream_stale(manifest, "clean")
    _write_manifest(run_dir, manifest)
    return {"run_id": run_id, "stage": "clean", **details}


def _mark_downstream_stale(manifest: dict[str, Any], stage: str) -> None:
    for later in DOWNSTREAM.get(stage, []):
        if later in manifest["stages"]:
            manifest["stages"][later]["status"] = "stale"
            manifest["stages"][later]["reason"] = f"{stage} re-run"


# ------------------------------------------------------------- sgd pipeline
def _sgd_pipeline(memory) -> Pipeline:
    """01_ml cell 4: TF-IDF vectorizer followed by hiclass per-parent-node SGD."""
    base = SGDClassifier(max_iter=5000, random_state=42)
    return Pipeline(
        [
            (
                "vectorizer",
                TfidfVectorizer(
                    lowercase=True,
                ),
            ),
            ("model", LocalClassifierPerParentNode(base)),
        ],
        memory=memory,
    )


def _cast_f1(y_true, y_pred):
    """CV scorer. predict() returns strings, so cast them to the label dtype first.

    Without the cast every fold scores 0.0, because the strings never match y.
    """
    return wbs.safe_f1(y_true, np.asarray(y_pred).astype(int))


def _level_offsets(encoder) -> np.ndarray:
    """Per-level offset that keeps each level's label codes distinct.

    Each level's codes index that level's own label list, so code 3 at level 2 and
    code 3 at level 4 were the same node for hiclass and the set-based F1. Offsetting
    each level by the number of labels in the levels above it keeps them apart.
    """
    columns = encoder.columns if encoder.columns is not None else list(encoder.encoders)
    sizes = [len(encoder.encoders[col].classes_) for col in columns]
    return np.concatenate([[0], np.cumsum(sizes)[:-1]]).astype(np.int64)


def _title_groups(titles, y):
    """Each row's title-group code, and each group's first label row."""
    _, first, codes = np.unique(titles, return_index=True, return_inverse=True)
    return codes, y[first]


def _title_grouped_split(titles, y, test_size):
    """Stratified (train, test) row masks with every title entirely on one side.

    Titles are stratified by their label rows, so a title repeated across projects
    cannot leak from train into test.
    """
    codes, group_y = _title_groups(titles, y)
    stratifier = IterativeStratification(
        n_splits=2, order=2, sample_distribution_per_fold=[test_size, 1.0 - test_size]
    )
    _, test_groups = next(stratifier.split(np.zeros((len(group_y), 1)), group_y))
    test = np.isin(codes, test_groups)
    return ~test, test


def _title_grouped_folds(titles, y, n_splits):
    """Stratified CV folds over titles, as (train, validation) row-index pairs."""
    codes, group_y = _title_groups(titles, y)
    stratifier = IterativeStratification(n_splits=n_splits, order=2)
    folds = []
    for _, held_out_groups in stratifier.split(np.zeros((len(group_y), 1)), group_y):
        held_out = np.isin(codes, held_out_groups)
        folds.append((np.flatnonzero(~held_out), np.flatnonzero(held_out)))
    return folds


# ----------------------------------------------------- stage: tune and train
def stage_tune_train(
    runs_root: Path,
    run_id: str,
    *,
    signing_key: bytes,
    n_iter: int = 10,
    cv_folds: int = 3,
    n_jobs: int = DEFAULT_N_JOBS,
    search_seed: int | None = None,
    split_seed: int | None = None,
) -> dict[str, Any]:
    """01_ml notebook: stratified split, untuned training, randomized search.

    Saves signed bundles for the untuned and tuned models.
    """
    run_dir = run_dir_for(runs_root, run_id)
    manifest = _read_manifest(run_dir)
    _require_stage(manifest, "clean")
    check_search_args(n_iter, cv_folds)
    with _stage_context(run_dir, "tune_train") as _log:
        dataframes = wbs.load_tables(
            input_dir=str(run_dir), duck_db=WORKING_DB
        )  # 01 cell 1
        cleaned_sample = wbs.clean_data(
            dataframes,
            text_field=TEXT_FIELD,
            file_type="training",
            level_field="wbs_level",
            starting_level=2,
            with_dates=False,
        )
        if cleaned_sample.height == 0:
            raise WBSPipelineError(
                "Cleaned training sample is empty; check the source labels"
            )
        y_encoded = wbs.encode_labels(str(run_dir), cleaned_sample, HIERARCHIES)[
            0
        ]  # 01 cell 1
        # Label encoder fitted exactly as encode_labels() does (encode_labels' own
        # pickle is not reloaded).
        encoder = wbs.MultiColumnLabelEncoder(columns=HIERARCHIES).fit(
            cleaned_sample.select(HIERARCHIES)
        )
        if not np.array_equal(
            encoder.transform(cleaned_sample.select(HIERARCHIES)).to_numpy(),
            y_encoded.to_numpy(),
        ):
            raise WBSPipelineError(
                "Label encoder refit does not reproduce encode_labels output"
            )

        if split_seed is not None:
            np.random.seed(split_seed)  # global RNG used by IterativeStratification
        # 01 cell 1, with titles kept whole (see _title_grouped_split).
        titles = cleaned_sample.get_column(TEXT_FIELD).to_numpy()
        y_all = y_encoded.to_numpy() + _level_offsets(encoder)
        train_mask, test_mask = _title_grouped_split(titles, y_all, test_size=0.2)
        X_train_is, y_train_is = titles[train_mask], y_all[train_mask]
        X_test_is, y_test_is = titles[test_mask], y_all[test_mask]
        for name, value in (
            ("X_train", X_train_is),
            ("y_train", y_train_is),
            ("X_test", X_test_is),
            ("y_test", y_test_is),
        ):
            joblib.dump(value, run_dir / f"{name}.pkl")

        memory = joblib.Memory(
            location=str(run_dir / "logs" / "cache"), verbose=0
        )  # 01 cell 4
        pipeline_sgd = _sgd_pipeline(memory)
        pipeline_sgd.fit(X_train_is, y_train_is)  # 01 cell 4
        untuned_scorer_f1 = wbs.f1_scorer(
            pipeline_sgd, X_test_is, y_test_is
        )  # 01 cell 4
        untuned_pred = pipeline_sgd.predict(X_test_is).astype(int)  # 01 cell 5
        untuned_test_f1 = hiclass_f1(y_test_is, untuned_pred)  # 01 cell 5

        rows_to_keep = np.ones(y_train_is.shape[0], dtype=bool)  # 01 cell 7
        for col_idx in range(y_train_is.shape[1]):
            values, counts = np.unique(y_train_is[:, col_idx], return_counts=True)
            rare_values = values[counts <= 6]
            col_mask = ~np.isin(y_train_is[:, col_idx], rare_values)
            rows_to_keep &= col_mask
        y_train_filtered = y_train_is[rows_to_keep]
        X_train_filtered = X_train_is[rows_to_keep]

        hiclass_f1_scorer = make_scorer(_cast_f1, greater_is_better=True)  # 01 cell 8
        search_kwargs = {"random_state": search_seed} if search_seed is not None else {}
        gscv = RandomizedSearchCV(  # 01 cell 8
            pipeline_sgd,
            n_iter=n_iter,
            param_distributions=PARAM_GRID,
            scoring=hiclass_f1_scorer,
            cv=_title_grouped_folds(X_train_filtered, y_train_filtered, cv_folds),
            n_jobs=n_jobs,
            verbose=1,
            **search_kwargs,
        )
        gscv.fit(X_train_filtered, y_train_filtered)  # 01 cell 8
        best_params = gscv.best_params_
        tuned_pred = gscv.predict(X_test_is).astype(int)  # 01 cell 11
        tuned_test_f1 = hiclass_f1(y_test_is, tuned_pred)  # 01 cell 11

        bundles = run_dir / "bundles"
        untuned_dir = artifacts.save_bundle(
            pipeline_sgd,
            encoder,
            bundles / "untuned",
            signing_key=signing_key,
            run_id=run_id,
            extra={
                "source_artifact": "trained_model_sgd_untuned.joblib",
                "source_cell": "01_ml cell 6",
            },
        )
        tuned_dir = artifacts.save_bundle(
            gscv,
            encoder,
            bundles / "tuned",
            signing_key=signing_key,
            run_id=run_id,
            extra={
                "source_artifact": "fitted_pipeline_sgd.joblib",
                "source_cell": "01_ml cell 8",
            },
        )
        outputs = run_dir / "outputs"
        (outputs / "best_results_sgd.json").write_text(
            json.dumps(_json_safe(best_params), indent=2, default=str), encoding="utf-8"
        )

    details = {
        "n_iter": n_iter,
        "cv_folds": cv_folds,
        "n_jobs": n_jobs,
        "search_seed": search_seed,
        "split_seed": split_seed,
        "train_rows": int(len(X_train_is)),
        "test_rows": int(len(X_test_is)),
        "rare_filter_kept": int(rows_to_keep.sum()),
        "rare_filter_original": int(rows_to_keep.size),
        "untuned_test_f1": float(untuned_test_f1),
        "tuned_cv_best_score": _json_safe(float(gscv.best_score_)),
        "tuned_test_f1": float(tuned_test_f1),
        "best_params": _json_safe(best_params),
        "bundles": {
            "untuned": str(Path("bundles") / "untuned"),
            "tuned": str(Path("bundles") / "tuned"),
        },
        "bundle_dirs": {
            "untuned": str(untuned_dir.relative_to(run_dir)),
            "tuned": str(tuned_dir.relative_to(run_dir)),
        },
        "untuned_f1_scorer": float(untuned_scorer_f1),
    }
    manifest["stages"]["tune_train"] = {
        "status": "ok",
        "finished_at": _now(),
        **details,
    }
    _mark_downstream_stale(manifest, "tune_train")
    _write_manifest(run_dir, manifest)
    return {"run_id": run_id, "stage": "tune_train", **details}


# --------------------------------------------------------------- stage: predict
def stage_predict(
    runs_root: Path, run_id: str, *, signing_key: bytes, model_variant: str = "untuned"
) -> dict[str, Any]:
    """02 notebook: load a signed bundle; predict level_2..level_8 per SPAE row."""
    if model_variant not in MODEL_VARIANTS:
        raise WBSPipelineError(f"model_variant must be one of {MODEL_VARIANTS}")
    run_dir = run_dir_for(runs_root, run_id)
    manifest = _read_manifest(run_dir)
    _require_stage(manifest, "tune_train")
    bundle_dir = run_dir / "bundles" / model_variant
    if not (bundle_dir / artifacts.MANIFEST_FILE).is_file():
        raise WBSPipelineError(
            f"No '{model_variant}' model bundle for run {run_id}; "
            "run tune_and_train_wbs first"
        )
    with _stage_context(run_dir, "predict"):
        try:
            model, label_encoder, _ = artifacts.load_bundle(
                bundle_dir, signing_key=signing_key
            )  # 02 cells 0
        except json.JSONDecodeError:
            raise  # parser detail; the tool returns the generic message
        except ValueError as exc:
            # Signature, checksum, and level checks: fixed text, no paths or values.
            raise WBSPipelineError(str(exc)) from exc
        dataframes = wbs.load_tables(
            input_dir=str(run_dir), duck_db=WORKING_DB
        )  # 02 cell 0
        cleaned_data = wbs.clean_data(
            dataframes,
            text_field=TEXT_FIELD,
            file_type="inference",
            level_field="wbs_level",
            starting_level=2,
            with_dates=True,
        )  # 02 cell 2
        prediction = model.predict(cleaned_data[TEXT_FIELD])  # 02 cell 2
        codes = prediction.astype(int) - _level_offsets(label_encoder)
        predicted = pl.DataFrame(codes, schema=PREDICTED_COLUMNS)
        predicted_data = predicted.with_columns([pl.col("*").cast(pl.Int32)])
        new_predictions = label_encoder.inverse_transform(predicted_data)
        new_predicted_df = pl.DataFrame(new_predictions, schema=PREDICTED_COLUMNS)
        cleaned_ix = cleaned_data.with_row_index("row_ix")
        pred_ix = new_predicted_df.with_row_index("row_ix")
        new_predicted_data = (
            cleaned_ix.join(pred_ix, on="row_ix", how="inner")
            .drop("row_ix")
            .sort("parsid", "wbs")
            .rename({TEXT_FIELD: "cleaned_title"})
            .select(
                "parsid",
                "wbs",
                "original_title",
                "cleaned_title",
                "parent_wbs",
                *PREDICTED_COLUMNS,
            )
        )
        pred_dir = run_dir / "predictions"
        pred_dir.mkdir(parents=True, exist_ok=True)
        new_predicted_data.write_parquet(pred_dir / "predicted_levels.parquet")

    level_counts = {
        c: int(new_predicted_data.get_column(c).n_unique()) for c in PREDICTED_COLUMNS
    }
    details = {
        "model_variant": model_variant,
        "predicted_rows": new_predicted_data.height,
        "distinct_labels_per_level": level_counts,
        "predictions_file": str(Path("predictions") / "predicted_levels.parquet"),
    }
    manifest["stages"]["predict"] = {"status": "ok", "finished_at": _now(), **details}
    _mark_downstream_stale(manifest, "predict")
    _write_manifest(run_dir, manifest)
    return {"run_id": run_id, "stage": "predict", **details}


# ------------------------------------------------------------ stage: write back
def stage_write_back(runs_root: Path, run_id: str) -> dict[str, Any]:
    """02 notebook cells 3-6: LEFT JOIN predictions into SPAE tables, export parquet.

    The export is re-read and checked against the predictions before returning.
    """
    run_dir = run_dir_for(runs_root, run_id)
    manifest = _read_manifest(run_dir)
    _require_stage(manifest, "predict")
    pred_path = run_dir / "predictions" / "predicted_levels.parquet"
    with _stage_context(run_dir, "write_back"):
        predictions = pl.read_parquet(
            pred_path
        )  # persisted predictions are the write-back source
        today = _dt.date.today().isoformat()
        export = run_dir / "predictions" / f"mapped_spae_{today}.parquet"
        con = duckdb.connect(str(run_dir / WORKING_DB))
        try:
            con.register("new_predicted_data", predictions)
            con.execute("""
                CREATE OR REPLACE TABLE gold_spae_data_mapped AS
                SELECT * FROM silver_spae_data AS s
                LEFT JOIN new_predicted_data AS np USING (parsid, wbs, parent_wbs)
                ORDER BY parsid, wbs;
            """)
            con.execute("""
                CREATE OR REPLACE TABLE gold_concatenated_spae_data_mapped AS
                SELECT * FROM silver_concatenated_spae_data AS s
                LEFT JOIN new_predicted_data AS np USING (parsid, wbs, parent_wbs)
                ORDER BY parsid, wbs;
            """)
            mapped = con.execute(
                "SELECT * FROM gold_concatenated_spae_data_mapped"
            ).pl()
            mapped_rows_db = mapped.height
            matched_db = int(
                con.execute(
                    "SELECT count(*) FROM gold_concatenated_spae_data_mapped "
                    "WHERE level_2 IS NOT NULL"
                ).fetchone()[0]
            )
        finally:
            con.close()
        mapped.write_parquet(export)

        # Read-back verification: re-read the exported file and compare with the
        # predictions.
        readback = pl.read_parquet(export)
        checks = {
            "rows_table_equals_export": mapped_rows_db == readback.height,
            "matched_rows_equal_predictions": matched_db
            == _matched_expected(readback, predictions),
            "predicted_values_equal": _values_equal(readback, predictions),
        }
        verified = all(checks.values())
        if not verified:
            raise WBSPipelineError(
                f"Write-back read-back verification failed: {checks}"
            )

    details = {
        "mapped_table": "gold_concatenated_spae_data_mapped",
        "mapped_rows": mapped_rows_db,
        "matched_rows": matched_db,
        "export_file": str(Path("predictions") / export.name),
        "export_sha256": hashlib.sha256(export.read_bytes()).hexdigest(),
        "read_back_checks": checks,
        "read_back_verified": verified,
    }
    manifest["stages"]["write_back"] = {
        "status": "ok",
        "finished_at": _now(),
        **details,
    }
    _write_manifest(run_dir, manifest)
    return {"run_id": run_id, "stage": "write_back", **details}


def _matched_expected(mapped: pl.DataFrame, predictions: pl.DataFrame) -> int:
    key = ["parsid", "wbs", "parent_wbs"]
    keys = predictions.select(key).unique()
    joined = mapped.select(key).join(keys, on=key, how="inner")
    return joined.height


def _values_equal(mapped: pl.DataFrame, predictions: pl.DataFrame) -> bool:
    key = ["parsid", "wbs", "parent_wbs"]
    left = (
        mapped.filter(pl.col("level_2").is_not_null())
        .select(key + PREDICTED_COLUMNS)
        .sort(key + PREDICTED_COLUMNS)
    )
    right = predictions.select(key + PREDICTED_COLUMNS).sort(key + PREDICTED_COLUMNS)
    left = left.with_columns([pl.col(c).cast(pl.Utf8) for c in PREDICTED_COLUMNS + key])
    right = right.with_columns(
        [pl.col(c).cast(pl.Utf8) for c in PREDICTED_COLUMNS + key]
    )
    return (
        left.unique(maintain_order=False)
        .sort(key)
        .equals(right.unique(maintain_order=False).sort(key))
    )


# ------------------------------------------------------------------ full run
def run_pipeline(
    runs_root: Path,
    source_db: Path,
    *,
    signing_key: bytes,
    run_id: str | None = None,
    n_iter: int = 10,
    cv_folds: int = 3,
    n_jobs: int = DEFAULT_N_JOBS,
    search_seed: int | None = None,
    split_seed: int | None = None,
    model_variant: str = "untuned",
) -> dict[str, Any]:
    check_search_args(n_iter, cv_folds)  # before stage_clean creates the run
    clean = stage_clean(runs_root, run_id, source_db)
    rid = clean["run_id"]
    tune = stage_tune_train(
        runs_root,
        rid,
        signing_key=signing_key,
        n_iter=n_iter,
        cv_folds=cv_folds,
        n_jobs=n_jobs,
        search_seed=search_seed,
        split_seed=split_seed,
    )
    predict = stage_predict(
        runs_root, rid, signing_key=signing_key, model_variant=model_variant
    )
    write = stage_write_back(runs_root, rid)
    return {
        "run_id": rid,
        "stages": {
            "clean": clean,
            "tune_train": tune,
            "predict": predict,
            "write_back": write,
        },
        "artifacts_dir": str(run_dir_for(runs_root, rid)),
    }
