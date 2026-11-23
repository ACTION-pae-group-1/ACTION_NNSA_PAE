"""Score the existing v1 CAEF model on the v2 held-out wording, with duplicate checks.

Evaluation only. No training, no tuning, no label changes. The model is the signed v1
bundle; it is loaded and used as is. Writes
data/local/caef_stadium/model_v1/heldout_v2_eval.json.

Usage:  python tools/eval_stadium_v2_heldout.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import duckdb
import numpy as np
from sklearn.metrics import accuracy_score, f1_score

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "src"))

import train_stadium_caef as T  # noqa: E402

from cost_intel_app import caef_live_inference as A  # noqa: E402
from pars_local_mcp.wbs import artifacts  # noqa: E402
from pars_local_mcp.wbs_port import functions as wbs  # noqa: E402
from pars_local_mcp.wbs_port import pipeline as P  # noqa: E402

V2_DB = REPO / "data/local/caef_stadium/stadium_pars_v2.duckdb"
V2_MANIFEST = REPO / "data/local/caef_stadium/stadium_pars_v2.manifest.json"
BUNDLE = REPO / "data/local/caef_stadium/model_v1/bundles/untuned"
OUT = REPO / "data/local/caef_stadium/model_v1/heldout_v2_eval.json"
DEMO_KEY = REPO / "src/cost_intel_app/demo_assets/caef/demo_verification.key"

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> frozenset:
    return frozenset(_TOKEN.findall(str(text).lower()))


def _jaccard(a: frozenset, b: frozenset) -> float:
    return len(a & b) / len(a | b) if (a | b) else 0.0


def main() -> int:
    splits = json.loads(V2_MANIFEST.read_text(encoding="utf-8"))
    v1_splits = json.loads(T.STADIUM_MANIFEST.read_text(encoding="utf-8"))["splits"]
    assert splits.get("v1_unchanged") is True
    con = duckdb.connect(str(V2_DB), read_only=True)
    key = DEMO_KEY.read_bytes()
    model, encoder, _manifest = artifacts.load_bundle(BUNDLE, signing_key=key)
    del key

    train_text, train_lab = T.build(con, v1_splits["training"], with_labels=True)
    test_text, test_lab = T.build(con, v1_splits["heldout"], with_labels=True)
    con.close()
    train = train_text.join(train_lab, on=["parsid", "wbs"], how="inner")
    test = test_text.join(test_lab, on=["parsid", "wbs"], how="inner")

    offs = np.asarray(P._level_offsets(encoder)).astype(int)
    codes = encoder.transform(test.select(P.HIERARCHIES)).to_numpy().astype(int)
    y_test = codes + offs
    X_test = test[A.TEXT].to_numpy()
    pred = model.predict(X_test).astype(int)
    pc, yc = pred - offs, y_test - offs

    levels = {}
    for k, lv in enumerate(A.LEVELS):
        t, p = yc[:, k], pc[:, k]
        labs = sorted(set(t.tolist()))
        levels[lv] = {
            "accuracy": float(accuracy_score(t, p)),
            "macro_f1_true_classes": float(
                f1_score(t, p, labels=labs, average="macro", zero_division=0)
            ),
            "true_classes": len(labs),
            "pred_classes": len(set(p.tolist())),
        }

    train_titles = set(train[A.TEXT].to_list())
    test_titles = test[A.TEXT].to_list()
    exact_overlap = sum(1 for t in test_titles if t in train_titles)
    train_tokens = [_tokens(t) for t in train[A.TEXT].to_list()]
    near = []
    for t in test_titles:
        tt = _tokens(t)
        near.append(max((_jaccard(tt, s) for s in train_tokens), default=0.0))
    near_arr = np.array(near)

    result = {
        "bundle": "data/local/caef_stadium/model_v1/bundles/untuned (existing v1 "
        "model, unchanged)",
        "heldout_source": "stadium_pars_v2.duckdb (held-out projects, new wording)",
        "heldout_projects": v1_splits["heldout"],
        "heldout_rows": int(len(X_test)),
        "wbs_safe_f1": float(wbs.safe_f1(y_test, pred)),
        "exact_all_levels_row_accuracy": float(np.mean(np.all(pc == yc, axis=1))),
        "levels": levels,
        "exact_text_duplicates_with_training": int(exact_overlap),
        "near_duplicate_jaccard_max_over_training": {
            "median": float(np.median(near_arr)),
            "share_ge_0_8": float(np.mean(near_arr >= 0.8)),
            "share_ge_0_6": float(np.mean(near_arr >= 0.6)),
        },
        "label_status": "assumed human-labeled synthetic reference labels (crosswalk "
        "v4, 31 rules)",
        "note": "Evaluation only. Model not retrained or tuned in this step.",
    }
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "heldout_rows",
                    "wbs_safe_f1",
                    "exact_all_levels_row_accuracy",
                    "exact_text_duplicates_with_training",
                    "near_duplicate_jaccard_max_over_training",
                )
            },
            indent=2,
        )
    )
    for lv, v in levels.items():
        print(
            lv,
            round(v["accuracy"], 3),
            round(v["macro_f1_true_classes"], 3),
            v["true_classes"],
            v["pred_classes"],
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
