# CAEF Classification: Held-Out Evaluation (2026-11-19)

> **Superseded.** This document scores an earlier run (`r8fec4416f3d5`). For release figures, see `eval/caef/results/release-2026-11-19/FINAL_EVALUATION_REPORT.md`. The numbers below are kept as originally recorded and are not the release results.

Scope: the already-trained CAEF classifier (run `r8fec4416f3d5`, untuned packaged bundle) scored against the held-out labelled split saved by that run. This is separate from MCP tool routing. It does not score CAEF-to-BLS recommendations and makes no accuracy claim for live PARS records, which have no ground-truth labels.

## Disposition

**Held-out metrics computed, with limitations.** The held-out split exists. Per-level accuracy and macro F1 were reproduced through the packaged adapter call path. The mean per-level accuracy (0.8486) matches the training run's recorded `untuned_test_f1` exactly, which confirms the split and the scoring are the ones the run used. Two level results are uninformative (level_8 has no non-absent rows in the held-out set; level_7 is dominated by the "absent" code), and no held-out row is fully correct across all seven levels. No acceptance threshold was specified, so no pass or fail verdict is given on accuracy.

## Metric table (held-out split, untuned packaged bundle)

Source of every number: the held-out test split (`X_test.pkl` / `y_test.pkl`, 3,340 rows), not the training set and not a validation set. Scored through `caef_live_inference.predict_text`'s call path (`model.predict` on a polars String Series).

| Level | Accuracy | Macro F1 (over true classes) | Macro F1 (over true+pred classes) | Distinct true labels | True labels unseen in train | Note |
|---|---|---|---|---|---|---|
| level_2 | 0.9940 | 0.7491 | 0.7491 | 4 | 0.6% | |
| level_3 | 0.9521 | 0.5815 | 0.5509 | 18 | 3.6% | |
| level_4 | 0.9102 | 0.6540 | 0.5534 | 22 | 4.2% | |
| level_5 | 0.8084 | 0.6213 | 0.6075 | 44 | 3.6% | |
| level_6 | 0.4431 | 0.3647 | 0.3481 | 21 | 2.4% | weakest informative level |
| level_7 | 0.8383 | 0.0946 | 0.0728 | 10 | 2.4% | code 0 ("absent") is 87% of rows; F1 not meaningful |
| level_8 | 0.9940 | 0.9970 | 0.4985 | 1 | 0% | held-out has no depth-8 rows; only the "absent" class; not informative |

Overall:

| Metric | Value |
|---|---|
| Mean per-level accuracy | 0.8486 (equals training run `untuned_test_f1` 0.8485885) |
| Exact all-levels row accuracy | 0.0 (0 of 3,340 rows fully correct) |
| Rows with exactly one wrong level | 3,240 (97.0%) |
| Ambiguity ceiling, per level | 1.0 at every level (each held-out title text has one label per level) |
| Effective sample size | 167 distinct texts (3,340 rows, about 20 rows per text) |

Macro F1 for level_8 over its one true class is degenerate; the union figure is shown for completeness.

Why the all-levels exact match is zero: depth is the dominant error. Code 0 means a level is absent, so a row's depth is part of its label. Predicted depth agrees with the gold depth on only 38.9% of held-out rows (`diagnostics.json`). Gold depth distribution in the held-out set is 2:40, 3:240, 4:260, 5:800, 6:1,560, 7:440, 8:0. The prediction distribution is 8:20, which is not present in gold.

## Hierarchical consistency

Parent-child edges were taken from the training labels (`y_train.pkl`). Predicted chains use only training edges by construction, so the 100% predicted-consistency result is a property of the model's output space, not independent validation.

| Child level (parent) | Predicted pair consistent | Gold pair present in train edges |
|---|---|---|
| level_3 (level_2) | 100% | 95.2% |
| level_4 (level_3) | 100% | 88.6% |
| level_5 (level_4) | 100% | 81.4% |
| level_6 (level_5) | 100% | 46.1% |
| level_7 (level_6) | 100% | 83.2% |
| level_8 (level_7) | 100% | 97.6% |
| Full chain, all six pairs | 100% | 8.4% |

The low full-chain gold coverage (8.4%) means most held-out chains contain at least one parent-child pair never seen in training. Any row with such a pair cannot be exactly correct under the training label space. This is the main structural limit on held-out exact match.

## Identity, failure handling, preprocessing

| Item | Status | Evidence |
|---|---|---|
| Packaged demo signature verified | PASS | `artifacts.load_bundle(..., signing_key=<packaged demo key>)` succeeds in memory; key not printed |
| Identity (parsid and wbs keyed to source rows) | NOT RUN for held-out arrays; PASS via adapter tests | The held-out pickles carry text and labels only, with no wbs or parsid. Identity is covered by `test_project_100_predictions_keyed_to_source_wbs_and_fit_training_labels` and `test_proj_001_identifiers_and_count` / `test_proj_002_identifiers_and_count` |
| Missing-input and failure handling | PASS | Existing adapter tests: missing required field, missing title, level gap, no level-2 rows, invalid project id, unknown project, missing model artifact, wrong key, contained inference error |
| Preprocessing equivalence | PASS | 834-row gate: `test_training_text_reproduced_exactly_for_project_100` (adapter text equals training text for project 100) |
| Existing adapter and contract tests | PASS (24), BLOCKED (2 strict xfail) | `pytest src/cost_intel_app/tests/test_caef_live_inference.py src/cost_intel_app/tests/test_caef_live_contract.py`: 24 passed, 2 xfailed. The xfails are the end-to-end live-project gate, which stays BLOCKED because live PARS records lack `period_date` and `program` |
| Held-out accuracy | PASS (computed) | Table above; no acceptance threshold supplied, so no accuracy verdict |
| Phoenix capture | NOT RUN | Optional; deterministic label comparison used as primary evidence |
| Tuned bundle | NOT RUN | Only the untuned bundle is packaged; the tuned variant was not evaluated |

## Lineage and split status

- Run: `r8fec4416f3d5`, created 2026-11-15, `data_origin = synthetic_mock`, source `mock_pars_full.duckdb`. Labels are `level_2`..`level_8`.
- Training and split code: `src/pars_local_mcp/wbs_port/pipeline.py`, `stage_tune_train`, `_title_grouped_split`, `test_size=0.2`.
- Split files: **present** in the sibling checkout, read-only: `C:/Users/maura.lapoff/Software/GitLocal/mcp_group_1/src/pars_local_mcp/data/wbs_runs/r8fec4416f3d5/` (`X_test.pkl` 521,160 bytes, `y_test.pkl` 187,281 bytes, plus `X_train.pkl` and `y_train.pkl`). Nothing was copied into this repo.
- Split sizes: 13,340 train rows, 3,340 test rows (test is 20%).
- `split_seed` is recorded as `null` in `run_manifest.json`. The saved pickles are the actual split used, so the held-out set is what was evaluated. The split itself is not reproducible from a recorded seed.
- Packaged bundle: `src/cost_intel_app/demo_assets/caef/r8fec4416f3d5/bundles/untuned/`. Its `fitted_pipeline_sgd.joblib` and `label_encoder.joblib` are byte-identical to the sibling run's. Its `model_manifest.json` differs from the sibling only in the `signature` field, which indicates re-signing during packaging with the demo key.

## Leakage analysis

The split is title-grouped on the cleaned concatenated text, so the stored texts do not overlap exactly. Descendant texts still contain ancestor titles, and those ancestors can appear in training texts.

| Measure | Value | Method |
|---|---|---|
| Exact text overlap (distinct) | 0 of 167 test texts | set intersection |
| Mean 5-gram coverage of test text by training text (row-weighted) | 0.776 | share of each test text's word 5-grams present in any training text |
| Rows with 5-gram coverage at least 0.8 | 50.3% | same |
| Distinct test texts sharing at least one 5-gram | 160 of 167 | same |
| Rows whose first 5 tokens also begin a training text | 95.8% | ancestor-prefix proxy |
| Rows whose own raw title appears as a substring of a training text | 9.0% | approximate: raw `original_title` (lowercased) against cleaned training text; cleaning removes stop words and phrases, so this is not exact |

Interpretation: the held-out texts share substantial ancestor text with training texts, so the split does not isolate project subtrees. Held-out accuracy at levels 3 to 6 is therefore likely optimistic for WBS trees that share no ancestor titles with training data. The 9.0% own-title figure is lower and approximate, but the 5-gram and prefix figures show the leakage channel is real. Exact-title independence is preserved; ancestor-context independence is not.

## Limitations

1. Effective sample is 167 distinct texts (3,340 rows). Rows repeat texts, so per-row metrics overstate sample size.
2. Held-out split contains no depth-8 rows, although training has 4,020. Level_8 metrics are not informative. This suggests the split is not balanced across depth.
3. Depth prediction is the dominant error (38.9% agreement), which is why no row is fully correct across seven levels.
4. Level_6 accuracy is 44%, the weakest informative level, and is where most gold chains lack training edges.
5. Data is `synthetic_mock`. Results do not transfer to real PARS records.
6. Authenticity: the packaged bundle is verified with the demonstration HMAC key. The README states this is not a production-grade authenticity boundary.
7. The split seed is not recorded; the saved split is what was evaluated.
8. Only the untuned bundle was evaluated. The tuned variant (run manifest `tuned_test_f1` 0.8503) is not packaged and was not scored.
9. No Phoenix or LLM-judge capture was run.

## Files

Created:
- `docs/CAEF_CLASSIFICATION_EVALUATION_2026-11-19.md` (this report)
- `eval/caef/results/heldout-2026-11-19/metrics.json` (per-level, overall, hierarchy, leakage metrics)
- `eval/caef/results/heldout-2026-11-19/diagnostics.json` (depth distributions and correctness patterns)
- `eval/caef/results/heldout-2026-11-19/integrity.json` (before and after hashes)

Scratch scripts, outside the repo, used to produce these files: `C:/tmp/caef_eval_work/heldout_eval.py`, `diagnostics.py`, `inspect_split.py`, `debug_joint.py`, `debug_joint2.py`, `debug_depth.py`.

Not modified: `src/cost_intel_app/server.py`, PARS and BLS code, `eval/` historical results, the trained model, its artifacts, signatures, and manifests, the demo key.

## Integrity (packaged files, SHA-256)

| File | Before | After | Result |
|---|---|---|---|
| `bundles/untuned/model_manifest.json` | `04df6e66...730eb55` | `04df6e66...730eb55` | PASS, unchanged |
| `bundles/untuned/fitted_pipeline_sgd.joblib` | `f7071ce6...f44c1d` | `f7071ce6...f44c1d` | PASS, unchanged |
| `bundles/untuned/label_encoder.joblib` | `f1b23f63...d256` | `f1b23f63...d256` | PASS, unchanged |
| `predictions/predicted_levels.parquet` | `2d1ac5ba...cead4f5` | `2d1ac5ba...cead4f5` | PASS, unchanged |

Full hashes are in `eval/caef/results/heldout-2026-11-19/integrity.json`.

Network: NONE. No git branch, commit, push, stash, reset, or clean was run. No retraining, no dataset regeneration. No Ask Sage.
