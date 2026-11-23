# Final evaluation report, release 2026-11-19

Scope: synthetic stadium PARS data and the frozen CAEF release model. Labels are
**accepted synthetic reference labels** (crosswalk v4, 31 rules). They are not independently
validated, and no production accuracy is claimed. BLS MCP evaluation is deferred and not
included. No external telemetry or network egress besides the approved Ask Sage endpoint.

**Update, 2026-11-19 (later the same day):** one bounded, approved Ask Sage run was made against
`pars-eval-1` (15 of 60 examples) — see section 4.1. The "No Ask Sage calls were made" line above
described the state as of the original closeout and is no longer accurate; left in place for
provenance of that earlier pass.

## Summary table

| Component | Cases | PASS | FAIL | XFAIL | BLOCKED | Evidence |
|---|---:|---:|---:|---:|---:|---|
| CAEF classification (held-out) | 141 WBS records | metrics only | 0 | 0 | 0 | Newly executed. Deterministic scoring with `wbs.safe_f1`. Model-driven predictions. |
| PARS-to-CAEF inference (2 unseen projects) | 2 projects | 2 | 0 | 0 | 0 | Newly executed through the live PARS MCP launcher (stdio). Model-driven. Not Phoenix-recorded. Not browser-verified. |
| Search chatbot replay and regression | see note | all | 0 | 1 | 0 | Newly executed. Deterministic, scripted model and hub. No Ask Sage calls. |
| PARS MCP interface | 16 tools | 16 registered | 0 | 0 | 0 | Newly verified through the final launcher. The 81/81 deterministic and 13/13 Ollama results were **reused historical evidence** at original closeout; both were **re-executed** (not reused) 2026-11-19 with identical pass counts — see section 4.1. |
| Phoenix recording | n/a | n/a | n/a | n/a | 0 | Not blocked — JSONL fallback by design (see section 5). `arize-phoenix` import still fails (fastmcp version conflict, scoped as future work), but no eval run was prevented by it. |
| Basket regression and third panel | see note | all | 0 | 0 | 0 | Newly executed. Deterministic application tests. |
| Browser acceptance (2 unseen projects) | 2 | 0 | 0 | 0 | 0 | **NOT RUN.** No browser automation library is installed. Chrome and Edge exist, but installing a driver needs a network download, which is not approved. Unmet release gate. |

Notes on counts:
- **Application suites (Search, basket, third panel, CAEF adapter, launcher):** the combined
  deterministic run gave 189 passed, 9 skipped, and 4 xfailed. The 9 skips were the
  packaged-database tests. Re-run after the database path fix, they passed (21 passed for the
  two files that hold them). Combined result: **198 passed, 4 xfailed, 0 skipped.**
- **The 4 xfails** are strict xfails that record known gaps in the Search and CAEF contract
  suites. They are not hidden passes. They include the g2 write-refusal messaging gap.
- **Search XFAIL (g2):** a refused write shows a configuration error, not the read-only message.
  The refusal itself is enforced. Only the message is wrong. Unresolved.

## 1. CAEF classification (frozen release model, held-out projects 5301 and 5302)

- Held-out WBS records: **141**
- `wbs.safe_f1`: **0.8288** (previously reported 0.829, consistent)
- Exact all-level accuracy: **0.5390** (previously reported 0.539, consistent)
- Per-level accuracy and macro F1 (true classes):
  - level 2: 1.000 / 1.000 (1 class)
  - level 3: see `caef_release_heldout.json`, `per_level`
  - level 5: macro F1 about 0.50 (previously reported)
  - level 7: high accuracy, few classes
  - level 8: 1.000 / 1.000 (1 class)
- Per-class support and predicted-class counts: in `caef_release_heldout.json`, `support_by_code`.
- Hierarchical consistency: predicted parent-child pairs are seen in training edges. This holds
  **by construction**, because the predictions come from training edges.
- Overlap with training: exact text duplicates **0**; near-duplicate share at Jaccard ≥ 0.8 is
  recorded in the JSON.
- Hashes (before and after the run, unchanged): model manifest, fitted pipeline, label encoder,
  split manifest, taxonomy, and database. Full values in `caef_release_heldout.json`.
- Discrepancy check: none. The re-run matches the previously reported values within rounding.

**Caveats:**
- Level-2 group and phase rows are classified at inference but were **never labeled** in training.
  Their predictions are not validated and must not be presented as classifications.
- Repeated titles within a project are dropped at training only, on purpose, to limit
  overtraining. Inference keeps every WBS code.
- Labels are template-driven synthetic reference labels. The score measures the rules as written,
  not stadium practice.

## 2. PARS MCP-to-CAEF inference (unseen projects 5401 and 5402)

Run through `pars_live.live_session` with the application-side launcher on the packaged stadium
database. Tool calls were recorded.

| Check | 5401 | 5402 |
|---|---|---|
| Discovered through `list_projects` (MCP) | yes | yes |
| WBS retrieved through `get_wbs_by_level`, levels 1 to 8 | yes | yes |
| Model state | loaded | loaded |
| Classified rows (level ≥ 2) | 119 of 119 | 99 of 99 |
| Every WBS code classified exactly once, matching the database | yes | yes |
| Each row carries its project ID | yes | yes |
| Output fields present (`level_2` to `level_8`) | yes | yes |

- Tool inventory of the launcher: **16**.
- Stadium database SHA-256 unchanged after the run: **yes**.
- Protected PARS database SHA-256 unchanged: **yes**.
- The inference path does not reference the crosswalk or the labeled table: **yes**.
- Result file: `pars_mcp_inference.json`.

## 3. Search chatbot (deterministic replay and regression)

Current suites: `test_search_replay_eval.py`, `test_chat_bridge.py`. Covered: numeric grounding
against tool evidence; unsupported figures withheld; project switching with no stale follow-ups;
forged caller grounding state rejected; off-topic follow-ups without tool evidence withheld;
read-only write refusal; tool failure and unavailable service handling.

- Caller-supplied grounding reuse is **disabled**, so a forged grounding flag cannot authorize an
  answer. Regression test in place.
- Known gap, recorded as XFAIL: g2 refusal messaging.
- No Ask Sage calls were made. The existing authorization covers no additional evaluation calls.
- Ollama probing: not re-run in this round.

## 4. PARS MCP evaluation (reused and verified)

- Registered tools in the final stadium launcher: **16**, matching the allowlist.
- Historical, reused: **81/81** deterministic cases and **13/13** local Ollama tool-call cases on
  the post-incident baseline. These are **reused historical evidence**, not re-executed here.
- Phoenix-recorded executions: **0**.
- Agent-driven `pars-eval-1` run (partial): **10 of 60 cases** run. **9 PASS**, 1 judge timeout.
  The agent and the judge both used the Ollama endpoint `gemma4:12b-mtp`, so the scores are
  self-judged and weak evidence. Traces are JSONL fallback, not Phoenix-recorded. The requested
  `claude-haiku-sonnet` judge was **not** used. Treat this as a partial, self-judged, directional
  run. Results: `mcp_eval_pars-eval-1_v1_tools_20261119T080654Z.csv` and `.json` in this folder.
- Historical pars-eval reproduction: not reproducible, as recorded earlier.
- Launcher database unchanged during the safe read-only run: **yes**.
- Default PARS initialization against the protected database was **not** called.

### 4.1 Update, 2026-11-19 (this session, non-bls_mcp evals only; `src/bls_mcp` and `eval/bls` excluded)

Re-executed (not reused) the two deterministic PARS evals and ran one bounded Ask Sage pass:

- `eval/phoenix/run_pars_gap_eval.py` (all 16 registered PARS MCP tools, no LLM judge): **81/81
  rows pass, 0 fail.** `protected_files_unchanged: true`. No code defects found; nothing in
  `src/pars_local_mcp` needed changing.
- `eval/phoenix/run_pars_gap_agent.py` (tool-call order via local Ollama `gemma4:12b-mtp`, pinned,
  no LLM judge): **13/13 cases pass, 0 fail.** `protected_files_unchanged: true`.
- CAEF deterministic re-run (`caef_release_heldout.py`, `pars_mcp_inference_eval.py`): reproduced
  the section 1 and section 2 numbers above bit-for-bit (`wbs_safe_f1 = 0.8288`,
  `exact_all_levels_row_accuracy = 0.5390`; projects 5401/5402 fully classified). Hashes unchanged.
  `eval/phoenix/tests/` and `eval/caef/tests/`: 74 passed, 0 failed.
- Agent-driven `pars-eval-1` run against the **approved Ask Sage endpoint** (`api.nnsa.asksage.ai`,
  model `gpt-5.6-luna-gov`), bounded to 15 of 60 examples, 1 trial, deliberately **not** repeated to
  chase a higher score: **correctness 0.80, scope 0.9333, 15/15 scored, 0 errors.** Manual review of
  the 4 rows marked incorrect/out-of-scope suggests at least some are judge-rubric noise rather than
  real agent defects (e.g. a correct WBS element count marked `incorrect` against a loosely-worded
  reference answer). Treat 0.80/0.93 as directional, not precise, and as a signal to tighten the
  judge rubric before trusting the number, not as a verdict on the agent. Results:
  `eval/phoenix/results/pars-eval-1_v1_tools_20261119T095914Z.{csv,json,traces.jsonl}`.

This supersedes the "reused historical evidence" framing above for the specific cases re-run here;
the original partial 10/60 self-judged Ollama run in this section is left as-is for provenance.

## 5. Phoenix recording

**JSONL fallback (by design), not BLOCKED.** Updated 2026-11-19 — the state below has changed since
this section was first written:

1. `arize-phoenix` **is installed** in `.venv` (20.6.0, per the `pyproject.toml` pin). The earlier
   "not installed" finding is no longer accurate.
2. Importing it fails anyway: `phoenix/trace/dsl/filter.py` gives two dataclass fields
   (`boolean_names`, `iterables`) a bare `MappingProxyType({})` default, which this Python's
   `dataclasses` module rejects as mutable (`ValueError: mutable default ... not allowed: use
   default_factory`). `phoenix/__init__.py` imports that module eagerly, so any `import phoenix`
   fails, including `phoenix.otel` and `phoenix.client`.
3. `arize-phoenix` 20.27.0 and 21.0.0 both fix this (`field(default_factory=...)`), but both require
   `fastmcp-slim>=4,<5`, conflicting with this repo's `fastmcp>=3.4.10,<4`. A real fix is a
   project-wide `fastmcp` 3→4 (and `mcp` 1→2) upgrade — scoped and attempted this session, reverted
   after it regressed 22 tests in `bls_mcp` and `cost_intel_app`. See `eval/phoenix/README.md` for
   the full investigation.
4. `eval/phoenix/tracing.py` already catches this: `setup_tracing()` wraps the import/register call
   in `try/except Exception` and falls back to a local JSONL trace file, which is what every run in
   this report and section 4.1 actually used. This is working-as-designed graceful degradation, not
   a broken feature — no eval run in this document was blocked by it.

Nothing listens on 127.0.0.1:6006 in this environment either way, so Phoenix UI recording (as
opposed to the underlying import) was never going to be live for these runs regardless of the
dataclass bug.

Fixing the import needs the fastmcp 3→4 upgrade above. It was attempted this session and reverted
after regressing `bls_mcp`/`cost_intel_app` tests; it should be scoped as its own slice rather than
retried as part of an eval run. JSONL fallback traces are not Phoenix-recorded and are not described
as such here.

## 6. Basket regression

Deterministic application tests, all passing in the combined run: basket workflow, CSV download,
third-panel independence, and draft handling. The basket calculations do not depend on CAEF
predictions. Third-panel and CAEF output do not change basket values automatically.

## Release gates

| Gate | Status |
|---|---|
| Browser acceptance (2 unseen projects) | **NOT RUN** (unmet) |
| Active release package verified independently | done, see below |
| Demo key provisioning documented and tested | done (`docs/CAEF_STADIUM_DEMO.md`) |
| Agent E independent audit | **not run as a separate agent.** Core integrity facts were checked directly: protected database and taxonomy hashes match, the signing key is ignored, no secret patterns in the new files, and the staged set is only the three BLS snapshot files. |
| Commit and push | **not done.** Blocked by the browser gate. |

Package verification: the release bundle loads with the local demo key. A 32-byte wrong key is
rejected. The bundle files match the frozen values.

The run identifier was changed from `stadium_pars_v3` to `stadium_pars_v1`, and the bundle was
re-signed with the local demo key. The new `model_manifest.json` SHA-256 is
`e34d05bd5798eb667846cea07fbff0a9dac584dbeffd7cde6383d3dfa98c2387`.

## Not claimed

- Browser acceptance, Phoenix-recorded evaluation, production accuracy, independently validated
  labels, or any overall success percentage.
