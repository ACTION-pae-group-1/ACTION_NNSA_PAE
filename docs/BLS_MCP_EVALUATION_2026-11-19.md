# BLS MCP Evaluation, 2026-11-19

Evidence review and deterministic gap evaluation for the NNSA Cost Intelligence closeout.
Repository `main` at commit `1718085`. Snapshot under test: `sample_pc_ci` (`data/local/snapshots/bls-sample_pc_ci.duckdb`, SHA-256 `fb61d88f90c0e414847f6dc03f5b5b2bb245fc550c675091471897f311e933ec`).

Three kinds of evidence are reported separately and are not combined into one success rate:

- **Historical**: the committed run records under `eval/bls/results/runs/`, plus lesson narratives.
- **New deterministic**: cases run on a copy of the approved snapshot, with expected values computed from the snapshot itself.
- **New Phoenix/LLM**: not run.

## 1. Disposition

| Area | Disposition |
| --- | --- |
| Historical model runs (7 committed, Ollama) | **Valid for recorded scope, with limitations.** They measure an older eval definition (fingerprint `f492beb25f0f`) and are not comparable to the current eval (`e4ee5e08af67`). 0 of 32 scored episodes passed every check. |
| Historical Ask Sage runs cited in BLS-001, BLS-002, BLS-002A, BLS-003 | **Insufficient.** Their run records are not in this checkout. Their fingerprints (`6fd3b49c23a0`, `e4ee5e08af67`) are not the committed ones. Their pass results cannot be verified here. |
| Reproduction of historical results against the approved snapshot | **Not reproduced, not attempted to claim.** The historical scenario needs series that have no observations in the approved snapshot (Section 3). |
| Deterministic gap evaluation on the approved snapshot | **45 of 46 PASS. One FAIL, which is a server defect (C04):** `calculate_index_spec` returns a silent composite factor of 1.0 when given base and target values without resolved factors. |
| New Phoenix/LLM evidence | **Not run.** No model episodes or traces were produced in this pass. |

Coverage verdict: deterministic routing, argument validation, grounding, and refusal are evidenced on the approved snapshot; spec-backed calculation is evidenced except for the open C04 defect. Model-level tool use is not evidenced by any committed run under the current eval fingerprint. Do not present the historical model results as current BLS MCP performance.

## 2. Step 1: History audit (read-only)

### 2.1 Committed runs

| Run ID | Agent | Commit | Dirty | Scored | Infra errors | All checks passed | Eval fp | Tools fp |
| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |
| 20261116T020418Z-gpt-oss-20b | gpt-oss:20b | 34eb702 | no | 1 | 2 | 0 | f492beb25f0f | c4e045d4a227 |
| 20261116T020715Z-gpt-oss-20b | gpt-oss:20b | 34eb702 | yes | 3 | 0 | 0 | f492beb25f0f | c4e045d4a227 |
| 20261116T020812Z-gpt-oss-20b | gpt-oss:20b | 34eb702 | yes | 7 | 2 | 0 | f492beb25f0f | c4e045d4a227 |
| 20261116T021406Z-qwen3-14b | qwen3:14b | 34eb702 | yes | 0 | 9 | 0 | f492beb25f0f | c4e045d4a227 |
| 20261116T021942Z-qwen3-14b | qwen3:14b | 34eb702 | yes | 9 | 0 | 0 | f492beb25f0f | c4e045d4a227 |
| 20261116T031308Z-pierreprudh-gemma4-12b-mtp-latest | gemma4-12b-mtp | 34eb702 | yes | 3 | 0 | 0 | f492beb25f0f | c4e045d4a227 |
| 20261116T031759Z-pierreprudh-gemma4-12b-mtp-latest | gemma4-12b-mtp | 34eb702 | yes | 9 | 0 | 0 | f492beb25f0f | c4e045d4a227 |

Totals: 32 scored episodes, 0 passed every check, 13 infrastructure errors excluded. These are historical counts only.

Fingerprint comparison, computed with the repository's own functions on the current tree:

- Current eval fingerprint: `e4ee5e08af67`. Current tools fingerprint: `b5e4ddcf2000`.
- Committed runs: eval `f492beb25f0f`, tools `c4e045d4a227`. These differ from the current values, so the committed runs measure a different eval and tool surface.
- The current tools fingerprint and eval fingerprint match the values cited in BLS-002A and BLS-003.

### 2.2 Confirmed earlier findings

- Per-call tool names and arguments are not in `run.json`. Each episode records only a `tool_calls` count. Transcripts (`episodes.jsonl`) are git-ignored and absent from this checkout.
- The eval world is built in `tempfile.TemporaryDirectory()` (`eval/bls/runner.py:380`). The raw source files get SHA-256 entries in a manifest (`eval/bls/world.py:230`). The built DuckDB file is not hashed, and `run.json` records only `snapshot_id: eval_synthetic_world`.
- `results/SELFTEST.md` (PASS) runs scripted oracle and flawed agents. It tests the graders, not any model.
- Lessons BLS-001, BLS-002, BLS-002A and BLS-003 cite Ask Sage models `gpt-5.4-gov` and `gpt-5.6-luna-gov` and run IDs from `20261117T221050Z` to `20261118T193935Z`. None of those run directories exist in `eval/bls/results/runs/`.
- Historical guardrail failure: `20261116T021942Z-qwen3-14b`, case `mixed-materials-and-labor`, called `get_series_data` once and failed "no live BLS API call".

### 2.3 Historical check results (committed runs only)

| Check (process) | Passed |
| --- | --- |
| result comes from calculate_index_from_bls | 1 of 9 episodes (gemma 031759), 0 elsewhere |
| calculated specification was validated first, without errors | 0 of 32 |
| asked for the target year before calculating | 0 of 2 (gpt-oss 020715), 0 of 4 (gpt-oss 020812), 1 of 6 (qwen 021942), 2 of 2 (gemma 031308), 3 of 6 (gemma 031759) |
| composite factor equals the known answer (accuracy) | 1 of 6 (gemma 031759) |
| composite matches an independent recomputation (accuracy) | 1 of 9 (gemma 031759) |
| every series was returned by catalog tools before use (guardrail) | 27 of 27 (gemma 031759); 26 of 27 (qwen 021942) |

### 2.4 Historical tool coverage matrix

Tool registrations were read from `src/bls_mcp/mcp/tools/__init__.py`. There are 15 tools.

| Tool | Historical evidence type | Correctness measured? |
| --- | --- | --- |
| get_bls_access_status | None (not referenced in `eval/bls`) | No |
| search_series | Scripted oracle (SELFTEST); indirect model evidence through the catalog-before-use guardrail | Routing only, not per call |
| describe_series | Scripted oracle only | No |
| get_series_hierarchy | Scripted oracle only | No |
| get_cached_series_data | Scripted oracle only | No |
| get_series_data | One model call in qwen 021942 (guardrail failure) | Guardrail only |
| get_index_spec | None | No |
| create_index_spec | Scripted oracle only | No |
| save_index_spec | Scripted oracle only | No |
| validate_index_spec | Graded in 32 episodes; 0 passed "validated first" | Yes, and not met |
| calculate_index_from_bls | Graded in 7 runs; 1 episode produced a composite matching the known answer | Yes, low rate |
| calculate_index_spec | Listed as a calculation tool only | No |
| calculate_component_escalation | Listed as a calculation tool only | No |
| calculate_labor_locality_factor | None | No |
| get_index_visualization | None | No |

"Scripted oracle only" means the tool is exercised by the scripted agents in SELFTEST and never by a model in a committed run.

## 3. Step 2: Reproducibility

Reproduction status: **not reproduced.** No reproduction is claimed.

Facts from a read-only query of the copy at `C:/tmp/bls_eval/bls-sample_pc_ci.duckdb`:

- `pc_series` and `series_catalog` hold the 4,510 PC series, so catalog discovery is similar to the eval world.
- Only two PC series have observations: `PCU334---334---` (14 rows, 2003-12 to 2004-M13) and `PCU334519334519S` (20 monthly rows, 2018-03 to 2026-08). Neither has annual averages for 2014 to 2026.
- CIU and CIS series have quarterly observations only (`Q01` to `Q04`). `CIU1010000000000I` runs 2014-Q1 to 2026-Q2, so there is no 2026-Q04.
- The three series in the historical basket (`PCU327320327320`, `PCU331110331110`, `PCU321113321113`) exist in the catalog with **zero observations**. The expected composites (1.4475 and 1.5700) cannot be produced from this snapshot.
- The historical world, `eval_synthetic_world`, has invented values that are not in this snapshot.

Classification:

| Result set | Classification | Reason |
| --- | --- | --- |
| 7 committed Ollama runs | Valid for recorded scope, with limitations | Internally consistent, fingerprinted, 32 scored episodes. Limits: old eval fingerprint, dirty trees, no per-call tool records, no hashed world, small sample, keyword-matching scripted user. |
| Ask Sage runs in BLS-001 to BLS-003 | Insufficient | Records absent from this checkout. Fingerprints differ from the committed runs, so they are not comparable. |
| Historical scenario against approved snapshot | Mismatch | Required series have no observations. |

## 4. Step 3: Deterministic gap evaluation

### 4.1 Method

- Real FastMCP server built with `create_server(Settings(...))` and called in-process through `fastmcp.Client`.
- Paths point to `C:/tmp/bls_eval`, a copy of the approved snapshot and `active-snapshot.json`. The specs database is a fresh file under `C:/tmp/bls_eval/run-gap-2026-11-19/`.
- Outbound HTTP is replaced by a transport that refuses every request and records each attempt. Recorded attempts: **0**.
- Expected values are computed from the snapshot with read-only DuckDB queries, never from the server's calculation code.
- Script: `eval/bls/results/gap-2026-11-19/gap_eval.py`. Output: `eval/bls/results/gap-2026-11-19/gap_results.json`.

### 4.2 Results

Counts: **46 cases, 45 PASS, 1 FAIL, 0 BLOCKED, 0 NOT RUN.**

| Case | Tool | Verdict | Note |
| --- | --- | --- | --- |
| C04 | calculate_index_spec | **FAIL** | Given base and target values but no `temporal_factor`, returns composite 1.0, zero warnings, all component factors 1.0. The expected result is a refusal or warning, since the supplied values imply 1.4475. |
| S01 | calculate_index_from_bls | PASS | Factor 1.4151752 equals CIU 2025-Q04 / 2014-Q04 (173.642 / 122.7). |
| S02 | calculate_index_from_bls | PASS | 0.6 x CIU + 0.4 x CIS matched within 1e-6. |
| S03 | calculate_index_from_bls | PASS | Refused: no 2026-Q04 observation. |
| S04 | calculate_index_from_bls | PASS | Refused: catalog series with zero observations. |
| S05 | calculate_index_from_bls | PASS | Refused: invented series ID. |
| S06 | calculate_index_from_bls | PASS | Refused: weights sum to 0.8. |
| G01 to G03 | get_cached_series_data | PASS | Rows identical in year, period and value to the snapshot for PCU334---334--- (14), CIU1010000000000I (50) and PCU334519334519S (20). |
| R09, R10 | get_series_data | PASS | Refused without `BLS_API_KEY`, with zero outbound HTTP, including for an invented ID. |
| C03 | calculate_index_spec | PASS | With resolved factors, composite equals 0.45 x 1.55 + 0.35 x 1.40 + 0.20 x 1.30 = 1.4475. |
| V14 to V17 | validate_index_spec | PASS | Valid spec has no findings. Weight 0.8, 2026 target, and invented series each produce the expected ERROR finding. |

All other cases (argument validation, refusals, routing, and the `calculate_labor_locality_factor` and `calculate_component_escalation` arithmetic) PASS. Full list in `gap_results.json`.

### 4.3 Counts by tool (deterministic only)

| Tool | Cases | PASS | FAIL |
| --- | ---: | ---: | ---: |
| get_bls_access_status | 1 | 1 | 0 |
| search_series | 3 | 3 | 0 |
| describe_series | 4 | 4 | 0 |
| get_series_hierarchy | 1 | 1 | 0 |
| get_cached_series_data | 6 | 6 | 0 |
| get_series_data | 3 | 3 | 0 |
| get_index_spec | 2 | 2 | 0 |
| create_index_spec | 3 | 3 | 0 |
| save_index_spec | 1 | 1 | 0 |
| validate_index_spec | 4 | 4 | 0 |
| calculate_index_from_bls | 8 | 8 | 0 |
| calculate_index_spec | 2 | 1 | 1 |
| calculate_component_escalation | 4 | 4 | 0 |
| calculate_labor_locality_factor | 3 | 3 | 0 |
| get_index_visualization | 1 | 1 | 0 |
| **Total** | **46** | **45** | **1** |

Note: `get_index_visualization` is checked for a successful response only. Its values are not graded.

### 4.4 Method notes

- The first run of the harness had four harness-side errors: I used `limit=200` (the tool caps at 100, so the refusal was correct), read the wrong factor field, omitted `weight` from `component_values`, and did not map annual `M13` rows. I fixed these in the harness. The expected values were not changed.
- C03 originally passed only base and target values. That exposed C04. I then added resolved factors to C03 (expected value unchanged) and kept the no-factor call as C04.
- These are deterministic tool checks. They do not measure how a model uses the tools.

## 5. Step 4: LLM/Phoenix (optional)

**NOT RUN.** I prioritized the deterministic cases. No Ollama episode was started, and no Phoenix traces were captured. There are no Ask Sage results and none were requested.

## 6. Counts (kept separate by evidence type)

| Evidence type | Cases or episodes | PASS | FAIL | BLOCKED | NOT RUN |
| --- | ---: | ---: | ---: | ---: | ---: |
| Historical, committed runs (episodes, scored) | 32 scored (13 infra excluded) | 0 episodes passed every check | 32 | n/a | n/a |
| New deterministic (approved snapshot copy) | 46 cases | 45 | 1 | 0 | 0 |
| New Phoenix/LLM (Ollama only) | 0 | n/a | n/a | n/a | 0 (not started) |

## 7. Recommended follow-ups

1. **C04 (fix before closeout):** `calculate_index_spec` should refuse or warn when a component's factors are defaulted, or derive the factors from base and target values. The current silent 1.0 contradicts the "no caller-supplied floats" design in `calculate_index_from_bls`.
2. Make the historical scenario runnable on the approved snapshot. Either seed annual observations for the three basket series or build a dedicated eval snapshot, and record its hash.
3. Record per-call tool name and arguments in `run.json`, and hash the built eval snapshot.
4. Re-run any model evaluation under the current fingerprints (eval `e4ee5e08af67`, tools `b5e4ddcf2000`). Use local Ollama only, unless the user separately authorises Ask Sage.
5. Commit the raw run records cited in BLS-001 to BLS-003, or mark those lesson results as unverifiable in this checkout.

## 8. Integrity

- Snapshot SHA-256 before the run (source file): `fb61d88f90c0e414847f6dc03f5b5b2bb245fc550c675091471897f311e933ec`.
- Snapshot SHA-256 after the run, on the copy used by the harness: `fb61d88f90c0e414847f6dc03f5b5b2bb245fc550c675091471897f311e933ec`. The harness records before and after values in `gap_results.json`.
- Source snapshot opened read-only for copying only. Not written to.
- Not modified: `src/bls_mcp/`, `src/pars_local_mcp/`, `src/cost_intel_app/server.py`, `eval/bls/results/runs/`, existing lesson files, and the approved snapshot.
- No commits, branches, stashes, resets, or cleans. No new dependencies.

## 9. Files

Created in the repository:

- `docs/BLS_MCP_EVALUATION_2026-11-19.md` (this report)
- `eval/bls/results/gap-2026-11-19/gap_results.json` (46 cases, with expected and actual values)
- `eval/bls/results/gap-2026-11-19/gap_eval.py` (the harness; it expects the snapshot copy under `C:/tmp/bls_eval/`)

Created outside the repository, in `C:/tmp/bls_eval/`: the snapshot copy, its validation JSON and `active-snapshot.json`, probe and harness scripts, and the per-run specs database. Importing `bls_mcp` may also have written `__pycache__` files under `src/`. These are git-ignored.

## 10. Network

**NONE.** Everything ran in-process. The HTTP transport refuses all requests, and 0 attempts were recorded. No Ask Sage prompt was sent. No Ollama call was made.
