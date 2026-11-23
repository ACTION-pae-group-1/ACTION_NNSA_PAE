"""Final CAEF held-out evaluation of the frozen release model. Evaluation only.

Loads the signed release bundle as is (no training), reads the held-out projects from
the
packaged stadium database read-only, scores with the original scoring implementation
(wbs.safe_f1, hiclass), and writes
eval/caef/results/release-2026-11-19/caef_release_heldout.json.
Labels are accepted synthetic reference labels (crosswalk v4).
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import duckdb
import numpy as np
from sklearn.metrics import accuracy_score, f1_score

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "src"))

import train_stadium_caef as T  # noqa: E402

from cost_intel_app import caef_live_inference as A  # noqa: E402
from pars_local_mcp.wbs import artifacts  # noqa: E402
from pars_local_mcp.wbs_port import functions as wbs  # noqa: E402
from pars_local_mcp.wbs_port import pipeline as P  # noqa: E402

DB = REPO / "src/cost_intel_app/demo_assets/caef_stadium/stadium_pars.duckdb"
BUNDLE = REPO / "src/cost_intel_app/demo_assets/caef_stadium/bundles/untuned"
KEY = REPO / "src/cost_intel_app/demo_assets/caef/demo_verification.key"
SPLITS = REPO / "data/local/caef_stadium/stadium_pars_release.manifest.json"
TAXONOMY = REPO / "src/pars_local_mcp/data/CAEF 2.0 Standard WBS.xlsx"
OUT = REPO / "eval/caef/results/release-2026-11-19/caef_release_heldout.json"
_TOK = re.compile(r"[a-z0-9]+")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    hashes_before = {
        "database": sha(DB),
        "model_manifest": sha(BUNDLE / "model_manifest.json"),
        "fitted_pipeline": sha(BUNDLE / "fitted_pipeline_sgd.joblib"),
        "label_encoder": sha(BUNDLE / "label_encoder.joblib"),
        "taxonomy": sha(TAXONOMY),
        "split_manifest": sha(SPLITS),
    }
    manifest = json.loads(SPLITS.read_text(encoding="utf-8"))
    heldout = manifest["splits"]["heldout"]
    train_ids = manifest["splits"]["training"]
    con = duckdb.connect(str(DB), read_only=True)
    model, encoder, _ = artifacts.load_bundle(BUNDLE, signing_key=KEY.read_bytes())
    test_text, test_lab = T.build(con, heldout, with_labels=True)
    train_text, _ = T.build(con, train_ids, with_labels=True)
    con.close()
    test = test_text.join(test_lab, on=["parsid", "wbs"], how="inner")
    train_texts = set(train_text[A.TEXT].to_list())
    offs = np.asarray(P._level_offsets(encoder)).astype(int)
    y = encoder.transform(test.select(P.HIERARCHIES)).to_numpy().astype(int) + offs
    X = test[A.TEXT].to_numpy()
    pred = model.predict(X).astype(int)
    pc, yc = pred - offs, y - offs
    per_level = {}
    for k, lv in enumerate(A.LEVELS):
        t, p = yc[:, k], pc[:, k]
        labs = sorted(set(t.tolist()))
        counts = {int(c): int((t == c).sum()) for c in labs}
        per_level[lv] = {
            "accuracy": float(accuracy_score(t, p)),
            "macro_f1_true_classes": float(
                f1_score(t, p, labels=labs, average="macro", zero_division=0)
            ),
            "true_classes": len(labs),
            "pred_classes": len(set(p.tolist())),
            "support_by_code": counts,
        }
    # Hierarchical consistency: predicted parent-child pairs seen in training edges.
    train_edges = {}
    tr_lab = T.build(
        duckdb.connect(str(DB), read_only=True), train_ids, with_labels=True
    )[1]
    tr_codes = encoder.transform(tr_lab.select(P.HIERARCHIES)).to_numpy().astype(int)
    for k in range(1, 7):
        train_edges[k] = set(zip(tr_codes[:, k - 1].tolist(), tr_codes[:, k].tolist()))
    chain_ok = np.ones(len(X), dtype=bool)
    for k in range(1, 7):
        chain_ok &= np.array(
            [(a, b) in train_edges[k] for a, b in zip(pc[:, k - 1], pc[:, k])]
        )
    # Overlap against training text: exact and near-duplicate (Jaccard over tokens).
    exact = sum(1 for t in X if t in train_texts)
    tr_tok = [frozenset(_TOK.findall(t.lower())) for t in train_texts]
    near = []
    for t in X:
        tt = frozenset(_TOK.findall(t.lower()))
        near.append(
            max((len(tt & s) / len(tt | s) if (tt | s) else 0.0) for s in tr_tok)
        )
    near = np.array(near)
    hashes_after = {
        "database": sha(DB),
        "model_manifest": sha(BUNDLE / "model_manifest.json"),
        "fitted_pipeline": sha(BUNDLE / "fitted_pipeline_sgd.joblib"),
        "label_encoder": sha(BUNDLE / "label_encoder.joblib"),
        "taxonomy": sha(TAXONOMY),
        "split_manifest": sha(SPLITS),
    }
    result = {
        "evidence_category": "newly executed; deterministic scoring; model-driven "
        "predictions; accepted synthetic reference labels",
        "heldout_projects": heldout,
        "heldout_wbs_records": int(len(X)),
        "wbs_safe_f1": float(wbs.safe_f1(y, pred)),
        "exact_all_levels_row_accuracy": float(np.mean(np.all(pc == yc, axis=1))),
        "per_level": per_level,
        "hierarchical_consistency": {
            "predicted_chain_in_training_edges_rate": float(chain_ok.mean()),
            "note": "predictions use training edges, so this holds by construction",
        },
        "overlap_with_training": {
            "exact_text_duplicates": int(exact),
            "near_duplicate_share_jaccard_ge_0_8": float(np.mean(near >= 0.8)),
            "median_max_jaccard": float(np.median(near)),
        },
        "hashes_before": hashes_before,
        "hashes_after": hashes_after,
        "hashes_unchanged": hashes_before == hashes_after,
        "previously_reported": {
            "wbs_safe_f1": 0.829,
            "exact_all_levels_row_accuracy": 0.539,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "heldout_wbs_records",
                    "wbs_safe_f1",
                    "exact_all_levels_row_accuracy",
                    "hashes_unchanged",
                )
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
