# CAEF stadium demonstration: packaging, setup, and limitations

Status: synthetic proof of concept. All PARS records are synthetic. The CAEF labels are
assumed human-labeled synthetic reference labels (crosswalk v4, 31 rules). They are not
independently validated, and no production accuracy is claimed.

## What is packaged

| Item | Path (repository-relative) | Notes |
|---|---|---|
| Synthetic stadium PARS database | `src/cost_intel_app/demo_assets/caef_stadium/stadium_pars.duckdb` | Zero-padded WBS codes (`01`, `01.01`), copied from the release build. SHA-256 `483175113e148d68…`. |
| release CAEF model bundle | `src/cost_intel_app/demo_assets/caef_stadium/bundles/untuned/` | `fitted_pipeline_sgd.joblib` (SHA-256 `97534f5c9c27bfe3810694cdc3f0461bef2aec16808051a419565fd8e28079cf`), `label_encoder.joblib` (`c6721cf79ec1…`), `model_manifest.json` (`e34d05bd5798…`). |
| Shared cleaning references | `src/cost_intel_app/demo_assets/caef/r8fec4416f3d5/working.duckdb` | Abbreviation, stop-word, and stop-phrase tables from the original packaged run. |
| Original demo model (project 100 route) | `src/cost_intel_app/demo_assets/caef/` | Unchanged. Historical manifest integrity incident is preserved, not re-signed. |
| Build and evaluation scripts | `tools/build_stadium_pars_dataset.py`, `tools/build_stadium_pars_v2_wording.py`, `tools/build_and_evaluate_stadium.py`, `tools/train_stadium_caef.py` | Reproduce the data and model from the approved seed. |
| Labeling methodology | `data/local/caef_stadium/crosswalk_v4.csv` (local, not committed) | 31 rules, 20 supported and 11 educated guesses, all accepted as demo reference labels. |
| Metrics | `data/local/caef_stadium/model_release/metrics.json` | v1, v2, and release results, with leakage notes. |

The CAEF 2.0 taxonomy is unchanged: `src/pars_local_mcp/data/CAEF 2.0 Standard WBS.xlsx`,
SHA-256 `e23146ee888594b9ac38abf385ef108975a1a5fe916588bfc211f10f7c09d0c6`.

Judges do not generate data, label records, train, or run evaluations. The packaged
files above are sufficient to run the demonstration.

## Required environment

```
COST_INTEL_PARS_STADIUM_DB=<repo>/src/cost_intel_app/demo_assets/caef_stadium/stadium_pars.duckdb
```

When this variable is set, the app starts the application-side launcher
(`src/cost_intel_app/pars_launcher.py`) on that database. The launcher registers the same
16 PARS tools and never calls `initialize_database()`, so the packaged database is not
regenerated. If the variable is unset, the app uses the default PARS path, which does not
contain the stadium projects.

CAEF inference for any project other than `100` retrieves its WBS elements through
PARS MCP (`get_wbs_by_level`, levels 1 to 8) and passes those records to the adapter. The
adapter does not open any database directly.

## Local signing-key provisioning

The model bundle and the PARS database are not signed with a key in Git. The bundle
manifest is HMAC-signed with a local demonstration key.

- **Expected location:** `src/cost_intel_app/demo_assets/caef/demo_verification.key`.
  This path is gitignored (`.gitignore`, CAEF section) and must never be committed or
  printed.
- **Fresh installation:** obtain the existing demonstration key from the repository
  maintainer through an approved out-of-band channel, and place it at the expected
  location. Do not generate a new key in place. The packaged bundle is signed with the
  existing key, so a new key would make verification fail.
- **Verification (this is the test of the procedure):**

  ```
  .venv/Scripts/python.exe -I -c "import sys; sys.path.insert(0,'src'); from pathlib import Path; from pars_local_mcp.wbs import artifacts; artifacts.load_bundle(Path('src/cost_intel_app/demo_assets/caef_stadium/bundles/untuned'), signing_key=Path('src/cost_intel_app/demo_assets/caef/demo_verification.key').read_bytes()); print('verified')"
  ```

  Results on this machine: the correct key prints `verified`. A 32-byte wrong key is
  rejected with `ValueError`. With no key present, the adapter returns the controlled
  message "The packaged stadium CAEF model is not available." Verification is never
  bypassed.
- **Maintainer re-signing:** re-signing with a new key is a release action, not a setup
  step. It must be recorded in the release notes, and the historical manifests must be
  preserved alongside the new ones.

## Evaluation results (synthetic reference labels)

Held-out projects 5301 and 5302, after the release correction, scored by the retrained release model:

- `wbs.safe_f1`: **0.829**
- Exact all-level row accuracy: **0.539**
- Level 5 macro F1: **0.50**
- Exact text duplicates between training and held-out: **0**
- Near-duplicate held-out texts with Jaccard similarity at or above 0.8: **0**

Validation projects score 1.0 because their wording matches training. That is an
in-distribution check, not a generalization result.

The earlier v1 and v2 scores of 1.0 are not valid evidence. Group and phase titles carried
the work-type label into the input text. release removes that leak and retrains.

## Limitations

1. **Level-2 group rows are classified but were not labeled.** Group and phase rows never
   carried reference labels in training. Inference still produces predictions for them.
   Those predictions are not validated and must not be presented as classifications.
2. **Repeated titles inside a project are dropped at training only.** The cleaning step
   removes rows whose cleaned text repeats. Training drops them deliberately, to limit
   overtraining. Inference keeps every WBS code, so costs can be summed.
3. **Labels are assumed, synthetic, and template-driven.** Each work type has a small set of
   phrasings, so the held-out score measures the rules as written, not stadium practice.
4. **Historical manifest incident.** The predict stage of the historical packaged run
   (`r8fec4416f3d5`) was rewritten on 2026-11-19, and its write-back stage is stale. This
   is recorded, not repaired. The active release package is independently verified above.
5. **Project 100 uses its own route.** It is not in the PARS tables, so its legacy demo
   route is kept.
6. **Browser acceptance is NOT RUN.** No browser automation library is installed, and
   installing one needs a network download that has not been approved. This is an unmet
   release gate.
7. **PARS MCP agent evaluation is partial.** 10 of 60 cases were run (9 PASS, 1 judge
   timeout). The endpoint is Ollama `gemma4:12b-mtp` for both agent and judge, so the
   scores are self-judged and directional only. Traces are JSONL fallback, not
   Phoenix-recorded. Phoenix recording is BLOCKED. See `FINAL_EVALUATION_REPORT.md`.
8. **Run identifier changed.** The run ID was changed from `stadium_pars_v3` to
   `stadium_pars_v1`, and the bundle was re-signed with the local demo key. The new
   `model_manifest.json` SHA-256 is `e34d05bd5798eb667846cea07fbff0a9dac584dbeffd7cde6383d3dfa98c2387`.
