"""Train and evaluate the existing CAEF architecture on the synthetic stadium PARS data.

Untuned, single training run, no hyperparameter search. Training uses only the
historical training projects. Validation projects are reported (no selection is made
from them). Held-out projects are scored once. Labels are the assumed human-labeled
synthetic reference labels from crosswalk v4.

Text is built by the same adapter path the application uses (prepare_text), so
training and inference text match.

Writes under data/local/caef_stadium/model_v1/. Does not touch the packaged demo model.

Usage:  python tools/train_stadium_caef.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import duckdb
import numpy as np
import polars as pl
from sklearn.metrics import accuracy_score, f1_score

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from cost_intel_app import caef_live_inference as A  # noqa: E402
from pars_local_mcp.wbs import artifacts  # noqa: E402
from pars_local_mcp.wbs_port import functions as wbs  # noqa: E402
from pars_local_mcp.wbs_port import pipeline as P  # noqa: E402

STADIUM_DB = REPO / "data/local/caef_stadium/stadium_pars_v1.duckdb"
STADIUM_MANIFEST = REPO / "data/local/caef_stadium/stadium_pars_v1.manifest.json"
OUT = REPO / "data/local/caef_stadium/model_v1"
DEMO_KEY = REPO / "src/cost_intel_app/demo_assets/caef/demo_verification.key"
PACKAGED_DEMO_BUNDLE = (
    REPO / "src/cost_intel_app/demo_assets/caef/r8fec4416f3d5/bundles/untuned"
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project_texts(con, parsid: str) -> pl.DataFrame:
    rows = con.execute(
        "SELECT wbs_code AS wbs, title AS wbs_title, level AS wbs_level, parent_wbs "
        "FROM wbs_elements WHERE parsid = ? ORDER BY wbs_code",
        [parsid],
    ).pl()
    rows = rows.with_columns(pl.col("wbs_level").cast(pl.Int64))
    cleaned = A.prepare_text(rows)
    cleaned = cleaned.with_columns(pl.lit(parsid).alias("parsid"))
    return cleaned


def labels_for(con, parsid: str) -> pl.DataFrame:
    return con.execute(
        "SELECT wbs_code AS wbs, caef_level_2 AS level_2, caef_level_3 AS level_3, "
        "caef_level_4 AS level_4, caef_level_5 AS level_5, caef_level_6 AS level_6, "
        "caef_level_7 AS level_7, caef_level_8 AS level_8 "
        "FROM labeled_wbs WHERE parsid = ?",
        [parsid],
    ).pl()


def build(
    con, parsids: list[str], with_labels: bool
) -> tuple[pl.DataFrame, pl.DataFrame | None]:
    texts, labels = [], []
    for parsid in parsids:
        cleaned = project_texts(con, parsid)
        texts.append(cleaned)
        if with_labels:
            labels.append(
                labels_for(con, parsid).with_columns(pl.lit(parsid).alias("parsid"))
            )
    text_df = pl.concat(texts)
    label_df = pl.concat(labels) if with_labels else None
    return text_df, label_df


def main() -> int:
    manifest = json.loads(STADIUM_MANIFEST.read_text(encoding="utf-8"))
    splits = manifest["splits"]
    con = duckdb.connect(str(STADIUM_DB), read_only=True)
    key = DEMO_KEY.read_bytes()  # used only to sign the bundle; never printed

    train_text, train_lab = build(con, splits["training"], with_labels=True)
    val_text, val_lab = build(con, splits["validation"], with_labels=True)
    test_text, test_lab = build(con, splits["heldout"], with_labels=True)
    demo_text, _ = build(con, splits["demo_unseen"], with_labels=False)
    con.close()

    def join_labels(text_df, lab_df):
        joined = text_df.join(lab_df, on=["parsid", "wbs"], how="inner")
        return joined

    train = join_labels(train_text, train_lab)
    val = join_labels(val_text, val_lab)
    test = join_labels(test_text, test_lab)

    encoder = wbs.MultiColumnLabelEncoder(columns=P.HIERARCHIES).fit(
        train.select(P.HIERARCHIES)
    )
    offs = np.asarray(P._level_offsets(encoder)).astype(int)

    def encode(df):
        codes = encoder.transform(df.select(P.HIERARCHIES)).to_numpy().astype(int)
        return codes + offs

    y_train = encode(train)
    y_val = encode(val)
    y_test = encode(test)
    X_train = train[A.TEXT].to_numpy()
    X_val = val[A.TEXT].to_numpy()
    X_test = test[A.TEXT].to_numpy()

    model = P._sgd_pipeline(memory=None)
    model.fit(X_train, y_train)

    def evaluate(X, y, name):
        pred = model.predict(X).astype(int)
        pc, yc = pred - offs, y - offs
        out = {
            "rows": int(len(X)),
            "wbs_safe_f1": float(wbs.safe_f1(y, pred)),
            "levels": {},
        }
        for k, lv in enumerate(A.LEVELS):
            t, p = yc[:, k], pc[:, k]
            labs = sorted(set(t.tolist()))
            out["levels"][lv] = {
                "accuracy": float(accuracy_score(t, p)),
                "macro_f1_true_classes": float(
                    f1_score(t, p, labels=labs, average="macro", zero_division=0)
                ),
                "true_classes": len(labs),
                "pred_classes": len(set(p.tolist())),
            }
        out["exact_all_levels_row_accuracy"] = float(np.mean(np.all(pc == yc, axis=1)))
        return out, pred

    val_metrics, _ = evaluate(X_val, y_val, "validation")
    test_metrics, test_pred = evaluate(X_test, y_test, "heldout")

    # Save an unsigned-by-default bundle with the local demo signing key.
    OUT.mkdir(parents=True, exist_ok=True)
    bundle_dir = artifacts.save_bundle(
        model,
        encoder,
        OUT / "bundles" / "untuned",
        signing_key=key,
        run_id="stadium_pars_v1",
        extra={
            "training_projects": splits["training"],
            "label_status": manifest["label_status"],
        },
    )
    del key

    # Project separation and leakage checks.
    roles = {role: set(p) for role, p in splits.items()}
    overlaps = {
        f"{a}~{b}": sorted(roles[a] & roles[b]) for a in roles for b in roles if a < b
    }
    text_overlap = len(set(X_test.tolist()) & set(X_train.tolist()))
    demo_in_training = bool(
        set(demo_text["parsid"].to_list()) & set(train["parsid"].to_list())
    )

    result = {
        "model": "untuned TF-IDF + LocalClassifierPerParentNode(SGDClassifier), "
        "starting_level=2",
        "label_status": "assumed human-labeled synthetic reference labels (crosswalk "
        "v4, 31 rules)",
        "training_projects": splits["training"],
        "validation_projects": splits["validation"],
        "heldout_projects": splits["heldout"],
        "demo_unseen_projects": splits["demo_unseen"],
        "training_rows": int(len(X_train)),
        "validation_rows": int(len(X_val)),
        "heldout_rows": int(len(X_test)),
        "project_overlap_between_roles": overlaps,
        "demo_projects_in_training_or_labels": demo_in_training,
        "heldout_exact_text_overlap_with_training": text_overlap,
        "validation": val_metrics,
        "heldout": test_metrics,
        "bundle": str(bundle_dir.relative_to(REPO)).replace("\\", "/"),
        "packaged_baseline_bundle": str(PACKAGED_DEMO_BUNDLE.relative_to(REPO)).replace(
            "\\", "/"
        ),
        "baseline_packaged_model_sha256_model_manifest": sha(
            PACKAGED_DEMO_BUNDLE / "model_manifest.json"
        ),
    }
    (OUT / "metrics_v1.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "training_rows",
                    "validation_rows",
                    "heldout_rows",
                    "demo_projects_in_training_or_labels",
                    "heldout_exact_text_overlap_with_training",
                )
            },
            indent=2,
        )
    )
    print("heldout wbs_safe_f1:", round(test_metrics["wbs_safe_f1"], 4))
    print("validation wbs_safe_f1:", round(val_metrics["wbs_safe_f1"], 4))
    return 0


if __name__ == "__main__":
    sys.exit(main())
