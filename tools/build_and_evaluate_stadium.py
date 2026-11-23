"""Stadium CAEF release: remove the work-type leak, score v1 on the corrected set,
retrain once.

Why release exists: in v1 each WBS group is named after its work type (for example
"Primary facility substructure"), and every leaf under it inherits that group title in
its hierarchical text. The input text therefore contains the label. The v1 and v2 scores
of 1.0 come from that leak, not from classification.

release changes only the WBS titles:
  - phase and group titles become neutral ("Work package N", "Work group N.K");
  - held-out and demonstration leaf titles use the v2 wording (unfamiliar phrasings).
Work types, codes, hierarchy, labels, and project splits are unchanged. Training and
validation leaf titles keep the v1 wording. v1 and v2 files are not modified.

Steps (each run once, no tuning):
  1. Build data/local/caef_stadium/stadium_pars_release.duckdb and its manifest.
  2. Score the existing v1 model (unchanged) on release held-out, with duplicate checks.
  3. Retrain the same untuned architecture on release training data; score validation
  and held-out.
  4. Save bundle to data/local/caef_stadium/model_release/ and write metrics.

Usage:  python tools/build_and_evaluate_stadium_release.py
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

import duckdb
import numpy as np
from sklearn.metrics import accuracy_score, f1_score

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "src"))

import build_stadium_pars_dataset as v1  # noqa: E402
import build_stadium_pars_v2_wording as v2  # noqa: E402
import train_stadium_caef as T  # noqa: E402

from cost_intel_app import caef_live_inference as A  # noqa: E402
from pars_local_mcp.wbs import artifacts  # noqa: E402
from pars_local_mcp.wbs_port import functions as wbs  # noqa: E402
from pars_local_mcp.wbs_port import pipeline as P  # noqa: E402

OUT = REPO / "data/local/caef_stadium"
V1_DB = v1.DB_PATH
RELEASE_DB = OUT / "stadium_pars_release.duckdb"
RELEASE_MANIFEST = OUT / "stadium_pars_release.manifest.json"
MODEL_DIR = OUT / "model_release"
V1_BUNDLE = OUT / "model_v1/bundles/untuned"
DEMO_KEY = REPO / "src/cost_intel_app/demo_assets/caef/demo_verification.key"
_TOKEN = re.compile(r"[a-z0-9]+")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tokens(text: str) -> frozenset:
    return frozenset(_TOKEN.findall(str(text).lower()))


def build_release() -> dict:
    if RELEASE_DB.exists():
        raise SystemExit(f"Refusing to overwrite {RELEASE_DB}")
    v1_before = _sha(V1_DB)
    shutil.copyfile(V1_DB, RELEASE_DB)
    nodes = v1.load_taxonomy()
    crosswalk = {
        r["work_type"]: r
        for r in __import__("csv").DictReader(v1.CROSSWALK.open(encoding="utf-8"))
    }
    splits = json.loads(v1.MANIFEST.read_text(encoding="utf-8"))["splits"]
    roles = {p: role for role, ps in splits.items() for p in ps}
    con = duckdb.connect(str(RELEASE_DB))
    neutral_rows = 0
    rewritten = {}
    for parsid, role in roles.items():
        rng = __import__("random").Random(f"{v1.SEED}-{parsid}")
        elements, _ = v1.build_project(parsid, role, rng, crosswalk, nodes)
        for code, parent, level, title, work in elements:
            if work == "phase":
                con.execute(
                    "UPDATE wbs_elements SET title = ? WHERE parsid = ? AND wbs_code = "
                    "?",
                    [f"Work package {code}", parsid, code],
                )
                neutral_rows += 1
            elif work == "group":
                con.execute(
                    "UPDATE wbs_elements SET title = ? WHERE parsid = ? AND wbs_code = "
                    "?",
                    [f"Work group {code}", parsid, code],
                )
                neutral_rows += 1
        if role in ("heldout", "demo_unseen"):
            work_by_code = {
                c: w for c, _p, _l, _t, w in elements if w not in ("phase", "group")
            }
            rng2 = __import__("random").Random(f"v2-{parsid}")
            n = 0
            for code, work in sorted(work_by_code.items()):
                title = rng2.choice(v2.PHRASES_V2[work]).format(
                    z=f"{rng2.choice(v1.ZONES)} zone", s=rng2.choice(v1.SYSTEM_WORDS)
                )
                con.execute(
                    "UPDATE wbs_elements SET title = ? WHERE parsid = ? AND wbs_code = "
                    "?",
                    [title, parsid, code],
                )
                con.execute(
                    "UPDATE labeled_wbs SET title = ? WHERE parsid = ? AND wbs_code = "
                    "?",
                    [title, parsid, code],
                )
                n += 1
            rewritten[parsid] = n
    con.close()
    manifest = {
        "artifact": RELEASE_DB.name,
        "version": "stadium_pars_release",
        "base": {"file": V1_DB.name, "sha256": v1_before},
        "change": (
            "phase and group WBS titles made neutral (removes the work-type label leak "
            "in v1/v2); "
            "held-out and demonstration leaves use the v2 wording; work types, codes, "
            "hierarchy, labels, "
            "and project splits unchanged; training and validation leaves unchanged"
        ),
        "neutral_title_rows": neutral_rows,
        "rewritten_leaves_by_project": rewritten,
        "v1_unchanged": v1_before == _sha(V1_DB),
        "label_status": "assumed human-labeled synthetic reference labels (crosswalk "
        "v4, 31 rules)",
        "splits": splits,
        "database": {"file": RELEASE_DB.name, "sha256": _sha(RELEASE_DB)},
    }
    RELEASE_MANIFEST.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def score(model, encoder, X, y_codes, offs):
    pred = model.predict(X).astype(int)
    pc, yc = pred - offs, y_codes - offs
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
    return {
        "rows": int(len(X)),
        "wbs_safe_f1": float(wbs.safe_f1(y_codes, pred)),
        "exact_all_levels_row_accuracy": float(np.mean(np.all(pc == yc, axis=1))),
        "levels": levels,
    }, pred


def dup_checks(train_texts, test_texts) -> dict:
    train_set = set(train_texts)
    exact = sum(1 for t in test_texts if t in train_set)
    train_tok = [_tokens(t) for t in train_texts]
    near = []
    for t in test_texts:
        tt = _tokens(t)
        near.append(
            max((len(tt & s) / len(tt | s) if (tt | s) else 0.0) for s in train_tok)
        )
    arr = np.array(near)
    return {
        "exact_text_duplicates_with_training": int(exact),
        "near_duplicate_jaccard_max_over_training": {
            "median": float(np.median(arr)),
            "share_ge_0_8": float(np.mean(arr >= 0.8)),
            "share_ge_0_6": float(np.mean(arr >= 0.6)),
        },
    }


def main() -> int:
    manifest = build_release()
    splits = manifest["splits"]
    con = duckdb.connect(str(RELEASE_DB), read_only=True)
    train_text, train_lab = T.build(con, splits["training"], with_labels=True)
    val_text, val_lab = T.build(con, splits["validation"], with_labels=True)
    test_text, test_lab = T.build(con, splits["heldout"], with_labels=True)
    con.close()
    train = train_text.join(train_lab, on=["parsid", "wbs"], how="inner")
    val = val_text.join(val_lab, on=["parsid", "wbs"], how="inner")
    test = test_text.join(test_lab, on=["parsid", "wbs"], how="inner")

    # Step 2: existing v1 model on release held-out (loaded, not retrained).
    key = DEMO_KEY.read_bytes()
    v1_model, v1_encoder, _ = artifacts.load_bundle(V1_BUNDLE, signing_key=key)
    v1_offs = np.asarray(P._level_offsets(v1_encoder)).astype(int)
    y_test_v1 = (
        v1_encoder.transform(test.select(P.HIERARCHIES)).to_numpy().astype(int)
        + v1_offs
    )
    v1_held, _ = score(
        v1_model, v1_encoder, test[A.TEXT].to_numpy(), y_test_v1, v1_offs
    )
    v1_dups = dup_checks(train[A.TEXT].to_list(), test[A.TEXT].to_list())

    # Step 3: retrain the same untuned architecture on release training data.
    encoder = wbs.MultiColumnLabelEncoder(columns=P.HIERARCHIES).fit(
        train.select(P.HIERARCHIES)
    )
    offs = np.asarray(P._level_offsets(encoder)).astype(int)
    y_train = (
        encoder.transform(train.select(P.HIERARCHIES)).to_numpy().astype(int) + offs
    )
    y_val = encoder.transform(val.select(P.HIERARCHIES)).to_numpy().astype(int) + offs
    y_test = encoder.transform(test.select(P.HIERARCHIES)).to_numpy().astype(int) + offs
    model = P._sgd_pipeline(memory=None)
    model.fit(train[A.TEXT].to_numpy(), y_train)
    val_m, _ = score(model, encoder, val[A.TEXT].to_numpy(), y_val, offs)
    held_m, _ = score(model, encoder, test[A.TEXT].to_numpy(), y_test, offs)
    release_dups = dup_checks(train[A.TEXT].to_list(), test[A.TEXT].to_list())

    # Step 4: package bundle (signed with the local demo key; never printed) and write
    # metrics.
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    bundle = artifacts.save_bundle(
        model,
        encoder,
        MODEL_DIR / "bundles" / "untuned",
        signing_key=key,
        run_id="stadium_pars_release",
        extra={
            "training_projects": splits["training"],
            "label_status": manifest["label_status"],
        },
    )
    del key
    result = {
        "v1_model_on_release_heldout": {"metrics": v1_held, "duplicates": v1_dups},
        "release_model_validation": val_m,
        "release_model_heldout": {"metrics": held_m, "duplicates": release_dups},
        "training_rows": int(len(train)),
        "validation_rows": int(len(val)),
        "heldout_rows": int(len(test)),
        "bundle": str(bundle.relative_to(REPO)).replace("\\", "/"),
        "label_status": manifest["label_status"],
        "v1_unchanged": manifest["v1_unchanged"],
    }
    (MODEL_DIR / "metrics.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "v1_model_on_release_heldout_safe_f1": round(v1_held["wbs_safe_f1"], 4),
                "v1_model_on_release_heldout_exact": round(
                    v1_held["exact_all_levels_row_accuracy"], 4
                ),
                "release_model_validation_safe_f1": round(val_m["wbs_safe_f1"], 4),
                "release_model_heldout_safe_f1": round(held_m["wbs_safe_f1"], 4),
                "release_model_heldout_exact": round(
                    held_m["exact_all_levels_row_accuracy"], 4
                ),
                "heldout_exact_text_duplicates": release_dups[
                    "exact_text_duplicates_with_training"
                ],
                "heldout_near_dup_share_ge_0_8": round(
                    release_dups["near_duplicate_jaccard_max_over_training"][
                        "share_ge_0_8"
                    ],
                    4,
                ),
                "v1_unchanged": manifest["v1_unchanged"],
            },
            indent=2,
        )
    )
    for lv in A.LEVELS:
        print(
            lv,
            "release heldout acc",
            round(held_m["levels"][lv]["accuracy"], 3),
            "macroF1",
            round(held_m["levels"][lv]["macro_f1_true_classes"], 3),
            "classes true/pred",
            held_m["levels"][lv]["true_classes"],
            held_m["levels"][lv]["pred_classes"],
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
