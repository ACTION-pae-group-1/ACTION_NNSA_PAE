"""Inference-only CAEF text adapter for live PARS WBS records.

Target representation: the text the packaged model was fit on, i.e.
concatenate_data(starting_level=2, with_dates=False) followed by clean_stitch with the
approved global reference tables. Only read-only data is used. Nothing is trained,
no target labels are features, and no period_date or program values are invented.
The packaged S=1 demo predictions are not read or overwritten by this module.
"""

from __future__ import annotations

import contextlib
import io
import re
import threading
from pathlib import Path
from typing import Any

import duckdb
import polars as pl

from cost_intel_app.caef_summary import empty_caef_summary, summarize_predictions

STARTING_LEVEL = 2
TEXT = "wbs_title"
LEVELS = [f"level_{n}" for n in range(2, 9)]
PREDICTED_COLUMNS = LEVELS
SOURCE_LIVE = "Live adapter predictions (training-compatible text, starting level 2)"
MAX_PROJECT_ROWS = 5000
SURROGATE_PARSID = (
    1  # clean_stitch joins on an integer parsid; the real id is restored after cleaning
)
_PROJECT_ID = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")
_CODE = re.compile(r"^\d{2}(\.\d{2})*$")
_DEMO_DIR = Path(__file__).resolve().parent / "demo_assets" / "caef"
_RUN_ID = "r8fec4416f3d5"
_MODEL_LOCK = threading.Lock()
_CACHE: dict[str, Any] = {}


class CAEFAdapterError(ValueError):
    """Controlled error with a message that is safe to show in the UI."""


def _bundle_dir(root: Path = _DEMO_DIR) -> Path:
    return root / _RUN_ID / "bundles" / "untuned"


def _load_model(root: Path = _DEMO_DIR, key: bytes | None = None) -> tuple[Any, Any]:
    """Load the packaged untuned bundle, verified with the demo key. Cached once."""
    from pars_local_mcp.wbs import artifacts

    bundle = _bundle_dir(root)
    if not (bundle / artifacts.MANIFEST_FILE).is_file():
        raise CAEFAdapterError("The packaged CAEF model is not available.")
    if key is None:
        key_file = root / "demo_verification.key"
        if not key_file.is_file():
            raise CAEFAdapterError("The packaged CAEF model is not available.")
        key = key_file.read_bytes()
    try:
        model, encoder, _ = artifacts.load_bundle(bundle, signing_key=key)
    except (
        Exception
    ) as exc:  # signature, checksum, or load failure: no paths in message
        raise CAEFAdapterError("The CAEF model could not be verified.") from exc
    return model, encoder


def _model() -> tuple[Any, Any]:
    with _MODEL_LOCK:
        if "model" not in _CACHE:
            _CACHE["model"] = _load_model()
        return _CACHE["model"]


def _refs(root: Path = _DEMO_DIR) -> dict[str, pl.DataFrame]:
    """Approved global cleaning references from the packaged working DB (read-only)."""
    with _MODEL_LOCK:
        if "refs" in _CACHE and root == _DEMO_DIR:
            return _CACHE["refs"]
    con = duckdb.connect(str(root / _RUN_ID / "working.duckdb"), read_only=True)
    try:
        refs = {
            "abbreviations": con.execute(
                "SELECT abbreviation, definition FROM bronze_abbreviations"
            ).pl(),
            "stop_words": con.execute("SELECT word FROM silver_stop_words").pl(),
            "stop_phrases": con.execute("SELECT word FROM bronze_stop_phrases").pl(),
        }
    finally:
        con.close()
    if root == _DEMO_DIR:
        with _MODEL_LOCK:
            _CACHE["refs"] = refs
    return refs


def _empty_project_descriptions() -> pl.DataFrame:
    """Empty name list: no project names removed. Training used 20 mock names."""
    return pl.DataFrame(
        schema={"parsid": pl.Int64, "project_name": pl.Utf8, "program": pl.Utf8}
    )


def _check_input(rows: pl.DataFrame) -> None:
    required = {"wbs", "wbs_title", "wbs_level"}  # project id is supplied by the caller
    missing = sorted(required - set(rows.columns))
    if missing:
        raise CAEFAdapterError(
            f"Input is missing required WBS fields: {', '.join(missing)}."
        )
    if rows.height == 0:
        raise CAEFAdapterError("No WBS elements were provided.")
    if rows.height > MAX_PROJECT_ROWS:
        raise CAEFAdapterError("The selected project exceeds the WBS size limit.")
    if rows.filter(
        pl.col("wbs").is_null() | (pl.col("wbs").cast(pl.Utf8).str.strip_chars() == "")
    ).height:
        raise CAEFAdapterError("A WBS element has no WBS code.")
    if rows["wbs"].n_unique() != rows.height:
        raise CAEFAdapterError("WBS codes must be unique within a project.")
    if rows.filter(
        pl.col("wbs_title").is_null()
        | (pl.col("wbs_title").cast(pl.Utf8).str.strip_chars() == "")
    ).height:
        raise CAEFAdapterError("A WBS element has no title.")
    levels = rows.select(pl.col("wbs_level").cast(pl.Int64, strict=False)).to_series()
    if levels.null_count() or (levels < 1).any():
        raise CAEFAdapterError("A WBS element has an invalid level.")


def prepare_text(
    rows: pl.DataFrame,
    refs: dict[str, pl.DataFrame] | None = None,
    validate: bool = True,
    keep_all: bool = False,
) -> pl.DataFrame:
    """Cleaned hierarchical text for one project, at starting_level=2, without dates.

    Input: wbs, wbs_title, wbs_level (required); parent_wbs (optional).
    Returns one row per input WBS with level >= 2, in the order the model expects.
    validate=False is used only by the training-source equivalence gate, whose
    table repeats WBS codes; live input always uses validate=True.
    """
    if validate:
        _check_input(rows)
    refs = refs or _refs()
    df = rows.select(
        pl.lit(SURROGATE_PARSID, dtype=pl.Int64).alias("parsid"),
        pl.col("wbs").cast(pl.Utf8),
        pl.col("wbs_title").cast(pl.Utf8),
        pl.col("wbs_level").cast(pl.Int64),
        (
            pl.col("parent_wbs").cast(pl.Utf8)
            if "parent_wbs" in rows.columns
            else pl.lit(None, dtype=pl.Utf8)
        ).alias("parent_wbs"),
    )
    if df.filter(pl.col("wbs_level") >= STARTING_LEVEL).height == 0:
        raise CAEFAdapterError("No WBS elements at level 2 or below.")
    # concatenate_data builds wbs_level_k columns only for levels that are present.
    present = set(
        df.filter(pl.col("wbs_level") >= STARTING_LEVEL)["wbs_level"].unique().to_list()
    )
    top = max(present)
    if any(lv not in present for lv in range(STARTING_LEVEL, top + 1)):
        raise CAEFAdapterError(
            "The WBS hierarchy has a missing level and cannot be assembled."
        )
    with contextlib.redirect_stdout(io.StringIO()):
        cc = _concatenate(df)
        cl = _clean_keeping_all(cc, refs) if keep_all else _clean(cc, refs)
    return cl


def _clean_keeping_all(cc: pl.DataFrame, refs: dict[str, pl.DataFrame]) -> pl.DataFrame:
    """Clean every row. Training drops repeated cleaned rows; inference must not.

    A dropped row is cleaned on its own, using the same cleaning steps, so its output is
    exactly what the cleaning gives it. Every WBS code therefore keeps a prediction.
    """
    cl = _clean(cc, refs)
    kept = set(cl["wbs"].to_list())
    missing = [w for w in cc["wbs"].to_list() if w not in kept]
    if not missing:
        return cl
    extras = [_clean(cc.filter(pl.col("wbs") == w), refs) for w in missing]
    return pl.concat([cl, *extras]).sort("wbs")


def _concatenate(df: pl.DataFrame) -> pl.DataFrame:
    from pars_local_mcp.wbs_port import functions as wbs

    return wbs.concatenate_data(
        df,
        text_field=TEXT,
        starting_level=STARTING_LEVEL,
        level_field="wbs_level",
        with_dates=False,
    )


def _clean(cc: pl.DataFrame, refs: dict[str, pl.DataFrame]) -> pl.DataFrame:
    from pars_local_mcp.wbs_port import functions as wbs

    cl = wbs.clean_stitch(
        cc,
        text_field=TEXT,
        abbreviations=refs["abbreviations"],
        stop_words=refs["stop_words"],
        stop_phrases=refs["stop_phrases"],
        project_descriptions=_empty_project_descriptions(),
    )
    cl = cl.drop(
        [c for c in ("program_right", "project_name_right") if c in cl.columns]
    )
    return cl.unique(maintain_order=True)


def predict_text(
    cleaned: pl.DataFrame, project_id: str, model_encoder: tuple[Any, Any] | None = None
) -> pl.DataFrame:
    """Run the packaged classifier on cleaned text; only the text is an input."""
    from pars_local_mcp.wbs_port import pipeline as P

    model, encoder = model_encoder or _model()
    with _MODEL_LOCK:
        pred = model.predict(cleaned[TEXT])
    codes = pred.astype(int) - P._level_offsets(encoder)
    predicted = pl.DataFrame(codes, schema=PREDICTED_COLUMNS).with_columns(
        [pl.col("*").cast(pl.Int32)]
    )
    labels = pl.DataFrame(
        encoder.inverse_transform(predicted), schema=PREDICTED_COLUMNS
    )
    ix = cleaned.with_row_index("row_ix")
    lx = labels.with_row_index("row_ix")
    out = (
        ix.join(lx, on="row_ix", how="inner")
        .drop("row_ix")
        .with_columns(pl.lit(project_id, dtype=pl.Utf8).alias("parsid"))
        .rename({TEXT: "cleaned_title"})
        .select(
            "parsid",
            "wbs",
            "original_title",
            "cleaned_title",
            "parent_wbs",
            *PREDICTED_COLUMNS,
        )
        .sort("wbs")
    )
    return out


def predict_rows(project_id: str, rows: pl.DataFrame) -> pl.DataFrame:
    """Full adapter path for one project rows (any source with required fields)."""
    if not _PROJECT_ID.match(project_id or ""):
        raise CAEFAdapterError("Choose a valid PARS project first.")
    cleaned = prepare_text(rows)
    return predict_text(cleaned, project_id)


def load_live_project(project_id: str, db_path: Path | None = None) -> pl.DataFrame:
    """Read one project's WBS records from the live store, read-only, in tree order."""
    if not _PROJECT_ID.match(project_id or ""):
        raise CAEFAdapterError("Choose a valid PARS project first.")
    if db_path is None:
        from pars_local_mcp.config import get_settings

        db_path = Path(get_settings().database_path)
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        exists = con.execute(
            "SELECT COUNT(*) FROM projects WHERE parsid = ?", [project_id]
        ).fetchone()[0]
        if not exists:
            raise CAEFAdapterError(
                "The selected project was not found in the PARS store."
            )
        rows = con.execute(
            "SELECT parsid, wbs_code AS wbs, title AS wbs_title, "
            "level AS wbs_level, parent_wbs "
            "FROM wbs_elements WHERE parsid = ?",
            [project_id],
        ).pl()
    finally:
        con.close()
    if rows.height == 0:
        raise CAEFAdapterError("The selected project has no WBS elements.")
    if (
        not rows.filter(pl.col("wbs").str.contains(r"^\d{2}(\.\d{2})*$")).height
        == rows.height
    ):
        raise CAEFAdapterError("WBS codes are not in the expected hierarchical format.")
    segs = rows.select(
        (pl.col("wbs").str.count_matches(r"\.") + 1).alias("s"),
        pl.col("wbs_level").cast(pl.Int64),
    ).to_series(0)
    if (segs != rows["wbs_level"].cast(pl.Int64)).any():
        raise CAEFAdapterError("WBS levels do not match WBS codes.")
    return rows.sort("wbs")


def predict_live_project(project_id: str) -> dict[str, Any]:
    """Summary for the third panel, same shape as caef_summary summaries."""
    try:
        rows = load_live_project(project_id)
        out = predict_rows(project_id, rows)
    except CAEFAdapterError as exc:
        return empty_caef_summary(str(exc))
    except Exception:  # no paths, data or model internals in the UI
        return empty_caef_summary(
            "Prediction did not complete. Check the packaged demonstration model."
        )
    summary = summarize_predictions(out.to_dicts(), project_id, SOURCE_LIVE)
    summary["rows"] = out.to_dicts()
    return summary


# --- Stadium model served through PARS MCP ---------------------------------------
# The selected project's WBS arrives as records returned by the PARS MCP tool
# get_wbs_by_level, one call per level. The adapter does not open the PARS
# database. The model is the packaged release stadium bundle (see the release notes).
SOURCE_MCP = "PARS MCP retrieval, packaged stadium CAEF model release"
NO_MODEL_MESSAGE = (
    "The packaged CAEF model is not included. "
    "Saved results remain available if provided."
)
STADIUM_MODEL_DIR = _DEMO_DIR.parent / "caef_stadium"
STADIUM_BUNDLE = STADIUM_MODEL_DIR / "bundles" / "untuned"
_CODE_PADDED = re.compile(r"^\d{2}(\.\d{2})*$")


def _stadium_model() -> tuple[Any, Any]:
    """The packaged release bundle, verified with the local demo key. Cached once."""
    from pars_local_mcp.wbs import artifacts

    with _MODEL_LOCK:
        if "stadium_model" in _CACHE:
            return _CACHE["stadium_model"]
    if not (STADIUM_BUNDLE / artifacts.MANIFEST_FILE).is_file():
        raise CAEFAdapterError(NO_MODEL_MESSAGE)
    key_file = _DEMO_DIR / "demo_verification.key"
    if not key_file.is_file():
        raise CAEFAdapterError(NO_MODEL_MESSAGE)
    try:
        model, encoder, _ = artifacts.load_bundle(
            STADIUM_BUNDLE, signing_key=key_file.read_bytes()
        )
    except Exception as exc:  # no paths or key material in the message
        raise CAEFAdapterError("The CAEF model could not be verified.") from exc
    with _MODEL_LOCK:
        _CACHE["stadium_model"] = (model, encoder)
    return model, encoder


def rows_from_mcp(session: Any, project_id: str) -> pl.DataFrame:
    """The project's WBS records, as returned by PARS MCP get_wbs_by_level."""
    if not _PROJECT_ID.match(project_id or ""):
        raise CAEFAdapterError("Choose a valid PARS project first.")
    records = []
    for level in range(1, 9):
        result = session.call(
            "get_wbs_by_level", {"project_id": project_id, "level": level}
        )
        if "error" in result or not isinstance(result.get("elements"), list):
            raise CAEFAdapterError("PARS did not return WBS records for the project.")
        for element in result["elements"]:
            records.append(
                {
                    "parsid": project_id,
                    "wbs": str(element["wbs_code"]),
                    "wbs_title": str(element["title"]),
                    "wbs_level": level,
                    "parent_wbs": element.get("parent_wbs"),
                }
            )
    if not records:
        raise CAEFAdapterError("The selected project has no WBS elements.")
    rows = pl.DataFrame(
        records,
        schema={
            "parsid": pl.Utf8,
            "wbs": pl.Utf8,
            "wbs_title": pl.Utf8,
            "wbs_level": pl.Int64,
            "parent_wbs": pl.Utf8,
        },
    )
    if rows.filter(~pl.col("wbs").str.contains(_CODE_PADDED.pattern)).height:
        raise CAEFAdapterError("WBS codes are not in the expected hierarchical format.")
    segs = rows.select(
        (pl.col("wbs").str.count_matches(r"\.") + 1).alias("s")
    ).to_series(0)
    if (segs != rows["wbs_level"]).any():
        raise CAEFAdapterError("WBS levels do not match WBS codes.")
    if rows.unique(subset=["wbs"]).height != rows.height:
        raise CAEFAdapterError("WBS codes are not unique within the project.")
    return rows.sort("wbs")


def predict_retrieved_project(project_id: str, session: Any) -> dict[str, Any]:
    """Summary for the third panel from WBS records retrieved through PARS MCP."""
    try:
        rows = rows_from_mcp(session, project_id)
        cleaned = prepare_text(rows, keep_all=True)
        out = predict_text(cleaned, project_id, model_encoder=_stadium_model())
    except CAEFAdapterError as exc:
        return empty_caef_summary(str(exc))
    except Exception:  # no paths, data or model internals in the UI
        return empty_caef_summary(
            "Prediction did not complete. Check the packaged demonstration model."
        )
    summary = summarize_predictions(out.to_dicts(), project_id, SOURCE_MCP)
    summary["rows"] = out.to_dicts()
    # Elements at level 2 or below that the cleaning step merged or dropped (the
    # cleaning joins on title text). They are reported, not silently omitted.
    expected = rows.filter(pl.col("wbs_level") >= STARTING_LEVEL).height
    missing = expected - out.height
    if missing > 0:
        summary["coverage"] = (
            f"{summary['coverage']}; {missing} WBS element(s) not classified "
            "(title repeated within the project)"
        )
    return summary
