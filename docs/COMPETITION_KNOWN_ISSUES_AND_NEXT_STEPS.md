# Competition known issues and next steps

Status: closeout known-issues pass, 2026-11-18 to 2026-11-19, on the final source. Formal browser acceptance is NOT RUN; the rows marked "browser" below come from a local harness, not the approved MCP Apps host, and are not acceptance results. This document
lists what is open, what was verified, and what was not run. It does not present an unresolved defect as a
finished feature.

Status vocabulary: **PASS**, **FAIL**, **BLOCKED** (cannot be run or completed because of an external
decision or a missing component), **NOT RUN** (not attempted in this pass), **ACCEPTED LIMITATION** (known,
documented, and accepted for the competition). Each row says whether it is **browser-verified** (run in the
local browser harness that hosts the app's own renderer), or **backend-only** (unit or in-process tests, or a
direct HTTP check, with no browser).

The browser harness is not the approved MCP Apps host. It stubs PARS unless a row says it used a live PARS
session. It implements no host open-link bridge.

## 1. Release status

**Pencils down: NOT DECLARED.** Blocking or open items:

- The in-app **Download CSV** control in an MCP Apps host is BLOCKED (K14). The export route and the file
  content are verified (PASS). The host hop is not.
- **CAEF inference** is BLOCKED (K2, K15): packaging waits on a key decision by the user, and the packaged
  model's input contract is not met by the live PARS data (K1).
- The **full test suite** was not passed in one run against the protected directories (K11).

**Stadium release addendum (2026-11-19).** The items above record the default PARS database closeout. With `COST_INTEL_PARS_STADIUM_DB` set, PARS-to-CAEF inference ran through the application-side launcher on unseen projects 5401 (119 of 119 rows) and 5402 (99 of 99 rows). This addresses the K1 and K2 inference rows for the stadium database only. Browser acceptance for those projects is **NOT RUN**. The signed-manifest run identifier was changed from `stadium_pars_v3` to `stadium_pars_v1`, and the bundle was re-signed with the local demo key (new `model_manifest.json` SHA-256 `e34d05bd5798eb667846cea07fbff0a9dac584dbeffd7cde6383d3dfa98c2387`). Other open release gates: the Agent E audit (not run). Phoenix recording is **BLOCKED**. See `docs/CAEF_STADIUM_DEMO.md` and `eval/caef/results/release-2026-11-19/FINAL_EVALUATION_REPORT.md`.

Items that do not block, as recorded here: the 820 px scrollbar overflow (K13, ACCEPTED LIMITATION), the BLS stdio
stall (K7, ACCEPTED LIMITATION for the competition, because Search uses HTTP).

## 2. Protected components

- `src/bls_mcp/`, `src/pars_local_mcp/`, the stdio launch entries in `src/mcp_servers.json`, `uv.lock`, dependency
  versions, and the Phoenix evaluation records and reference artifacts under `eval/`: no changes in this pass.
  Hash check against `/tmp/nnsa_check/protected_baseline.sha256`: 548 OK, 1 FAILED (`src/pars_local_mcp/data/wbs.duckdb`,
  K3). No tracked or untracked change exists under `src/bls_mcp` or `src/pars_local_mcp`.
- The coordinator's isolated suite on the approved directories: 662 passed, 4 skipped, 1 xfailed, 0 failed,
  listings unchanged (reported by the coordinator).

## 3. Browser matrix (final source)

### 3.1 Basket, workflow, approval, CSV, contrast (local browser harness, not formal acceptance)

Source: `final2_closeout_run.txt` (87 PASS, 2 FAIL, 3 NOT RUN). The two FAIL rows are the in-app CSV control
(BLOCKED, K14) and the 820 px overflow (ACCEPTED LIMITATION, K13). The three NOT RUN rows are W4, W6, and the
live-PARS rows that the basket pass stubs (covered in 3.2).

| Row | Status | Evidence |
|---|---|---|
| Step 1 "Review allocation": label, reason at 100 % ("Weights total 100%. You can still change them before approval.") | PASS | browser |
| Step 2 "Approve allocation": blocked with the exact reason at 90 % and 85 % | PASS | browser |
| Step 3 "Explore results": active only after approval; never shows "✓ DONE" while blocked | PASS | browser |
| Results use the approved basket; edit after approval hides the result and shows "Not approved" | PASS | browser |
| Approval invalidated by project switch while approved; no stale result | PASS | browser |
| Approval blocked for invalid weights (disabled button; click does nothing) | PASS | browser |
| Include and exclude, weights and totals, normalize | PASS | browser |
| Approve; Data & CSV tab; Prepare CSV; Evidence & audit (synthetic, read-only) | PASS | browser |
| Collapse and reopen the evidence panel (3 cycles; basket, approval, search text kept) | PASS | browser |
| Keyboard access to the panel control | PASS | browser |
| Refresh resets approval; PARS unavailable leaves the basket approvable | PASS | browser |
| Back and forward in the app | PASS | browser |
| Contrast audit, basket view (44 text elements; none below 4.5:1; lowest 7.45:1) | PASS | browser (automated) |
| Blocked approved result, Step 2 reason "Choose Edit approved allocation, then approve again." | NOT RUN | backend-only (`test_basket_workflow.py`); no UI fixture |
| "Result blocked" badge | NOT RUN | backend-only; same fixture gap |
| Narrow width 820 px, approved state, 15 px horizontal overflow (vertical scrollbar) | ACCEPTED LIMITATION (K13) | browser |
| CSV: Prepare, export route, file bytes, weights 15/15/45/25 | PASS | browser-level (Chrome top-level download of the route; `run_csv_verify.py`); the route is served by the app over HTTP |
| CSV: the app's own Download CSV control inside the harness host | BLOCKED | browser (no file: the host implements no open-link bridge) |

### 3.2 Third panel, live PARS (local browser harness, real PARS session, temporary database; not formal acceptance)

Source: `final2_live_run.txt` (13 PASS, 1 NOT RUN).

| Row | Status | Evidence |
|---|---|---|
| PARS catalog lists proj_001 and proj_002 from a live session | PASS | browser |
| Select proj_001, Load PARS context: header "Crescent Bay Football Stadium Construction", 34 elements, 11 WBS rows listed | PASS | browser |
| Select proj_002 drops proj_001's loaded context until Load is pressed | PASS | browser |
| Load proj_002: header "Northpoint Retractable Roof Stadium Expansion", 25 elements, 8 WBS rows listed; no proj_001 header content left; WBS list differs from proj_001 | PASS | browser |
| WBS browsing (PARS WBS elements, proj_001 and proj_002) | PASS | browser (previously verified) |
| Saved CAEF status for proj_001 after "View saved CAEF mapping": "No predictions found for this project." | PASS (honest status) | browser |
| Saved CAEF status for proj_002: "No saved CAEF 2.0 predictions are included in this build." | PASS (honest status) | browser |
| No classification counts or predictions shown for either project | PASS | browser |
| Temporary PARS databases removed after each session (0 left) | PASS | browser run plus file check |
| "Run model on bundled data" (CAEF inference) for proj_001 and proj_002, displayed status | NOT RUN | not clicked; see K2 and the CAEF status below |
| Project 100 predictions not shown under proj_001 or proj_002 | PASS for the saved view; NOT RUN for the inference view | browser |
| Analyst-authored WBS-to-BLS candidate mapping (not CAEF-powered) | NOT RUN in the browser | the review panel was not driven in this pass |

### 3.3 Search (optional chat) (local browser harness unless stated; not formal acceptance)

Common setup: the BLS HTTP service on `http://127.0.0.1:8821/mcp`, the local model `gemma4:12b-mtp` (Ollama
loopback), or the approved Ask Sage configuration from the provider settings. Example rows use fresh pages.
Typed rows use real keyboard entry. Files: `s2_ollama_*`, `s2_asksage_*`, `clear_ollama_*`, `search_*`,
`model_down_run.txt`, `bls_down_run.txt`.

| Row | Local model (Ollama) | Approved Ask Sage | Status / note |
|---|---|---|---|
| E1 "List PARS projects" fills the empty input and does not submit | PASS | PASS | browser |
| E1 answer lists proj_001 and proj_002 with trace `pars_mcp__list_projects` | PASS | PASS | browser |
| E2 "WBS for proj_001" fills and answers with a PARS WBS tool (`pars_mcp__get_wbs_by_level`) | PASS | PASS | browser |
| E3 "Steel price series" fills and answers with `bls_server__search_series` | PASS | PASS | browser |
| Example click after typing (variants A "Tab then click", B "wait 3 s then click", C "delete to empty then click") | PASS (after the fix) | not re-run | browser (`variants_fixed_run.txt`); defect K12 fixed |
| Follow-up "How many projects did you just list?" → "2 projects." with no new tool call | PASS (accepted wording, see K17) | PASS | browser |
| Unsupported question ("What is the weather in Paris today?") → the fixed unsupported message, no tools | PASS | PASS | browser |
| Modification request ("Change the basket weights…") → the read-only message | PASS | PASS | browser |
| Partial question (WBS for proj_001 and the contract award date) → WBS answered; award date stated as not provided | PASS | PASS | browser |
| Clearing after close and reopen the chat: the pre-state answer had no tool call; after reopening, the old answer is not reused (reply: the fixed unsupported message, no tool call) | PASS (non-reuse; the wording is the unsupported message, see K18) | NOT RUN (Ask Sage not re-run for clearing) | browser (`clear_ollama_*`) |
| Clearing after loading a PARS project: the same non-reuse test | PASS (non-reuse, see K18) | NOT RUN | browser (`clear_ollama_*`) |
| Clearing after switching the basket project: a fresh `pars_mcp__list_projects` call | PASS | PASS | browser |
| BLS down: Search fails in 3.0 s with "The MCP server 'bls_server' did not start or is not reachable. Check that its service is running…"; basket weights unchanged | PASS (observed) | — | browser (`bls_down_run.txt`); BLS restarted afterwards and answers HTTP 200 |
| Model down (a model name that does not exist, set for that run only): "The configured model or endpoint was not found. Check LLM_CHAT_MODEL and LLM_BASE_URL."; basket weights unchanged | PASS (observed) | — | browser (`search_model_down.txt`). The run's own check expected other wording, so its row reads FAIL; the observed text is the evidence |
| Search answers use only the displayed results (no invented IDs); model may paraphrase titles | ACCEPTED LIMITATION (K15) | — | backend-only regression (coordinator): 25/25 IDs, 25/25 titles exact, no frequency claim |
| Full Search matrix with a live PARS session, Ollama path | PARTIAL: 16 PASS, 3 FAIL | — | browser (`s2_ollama_run.txt`). The 3 FAIL rows are the PARS-load and clearing rows; their harness helper was corrected and re-tested in `run_clear.py` (rows above). Those re-test results supersede the 3 FAIL rows |

### 3.4 Other rows

| Row | Status | Note |
|---|---|---|
| Startup of the FastMCP dev preview (alternate ports 8100 and 8180) | ACCEPTED LIMITATION (K22) | the coordinator's launch; the preview fetches app-bridge.js from npm and is not offline |
| Dev preview: CSV in the FastMCP dev preview | BLOCKED (K14) | the coordinator's run; no file reached the download folder; the dev host's launch page has no open-link handler |
| Export URL obtained through a plain MCP client | BLOCKED (K14) | `export_analysis_csv` is an app-only tool; a plain MCP client gets "Unknown tool" (see 4.2) |

## 4. Known issues

Each issue lists: severity, component, reproduction, current behaviour, expected behaviour, workaround,
next step, demo impact, and whether a fix touches evaluated components.

### K1. PARS-to-CAEF input contract is not met by the live PARS data (HIGH)
- **Component:** CAEF classification (`src/cost_intel_app/caef_summary.py`, the packaged model in
  `demo_assets/caef/`, the WBS input schema in the frozen PARS code).
- **Reproduction:** run CAEF inference for proj_001 or proj_002 from the third panel (not done in this pass).
  Inference for project 100 (the packaged synthetic run) passed in the backend only (coordinator).
- **Current behaviour:** the packaged model needs `period_date`, `program`, and text-cleaning reference
  tables that the live proj_001 and proj_002 stores do not supply. Inference for proj_001 and proj_002 is BLOCKED.
- **Expected:** the live project's WBS mapped to the model's input contract, or a documented incompatibility.
- **Workaround:** none in the UI. Project 100 inference is backend-only evidence and does not apply to proj_001 or proj_002.
- **Next step:** align the input adapter (period_date, program, reference tables) to the live stores, and
  re-run the contract test before any inference claim.
- **Demo impact:** yes. No CAEF predictions for the two demonstration projects.
- **Touches evaluated components:** possibly (`src/pars_local_mcp` schema). Needs a decision.

### K2. CAEF 2.0 status: three separate criteria (HIGH)
| Criterion | Status | Evidence |
|---|---|---|
| 1. Model artifacts packaged and verified | BLOCKED | packaging (`tools/prepare_caef_demo_assets.py`) waits on the user's key decision. No packaged run in `demo_assets/` (listing unchanged) |
| 2. Inference executed | BLOCKED for proj_001 and proj_002 (K1); PASS for project 100 in the backend only; NOT RUN in the browser | a browser "Run model on bundled data" click was dispatched once during this pass and the run was stopped during the wait; no output was observed and no file was written (listing unchanged) |
| 3. Predictions available per project | BLOCKED for proj_001 and proj_002 | browser: "No predictions found for this project." (proj_001) and "No saved CAEF 2.0 predictions are included in this build." (proj_002). Criterion 3 is not PASS merely because criteria 1 and 2 pass for project 100 |
- **Reproduction:** third panel, select proj_001 or proj_002, View saved CAEF mapping; Run model is the inference step.
- **Current behaviour:** no per-project predictions are shown. Nothing is invented.
- **Expected:** saved classifications shown for the selected project with run identity.
- **Next step:** user decision on packaging; then K1 and re-verification of each criterion separately.
- **Demo impact:** yes (CAEF labels cannot be shown for the demonstration projects).

### K3. PARS database regenerated before the freeze (MEDIUM; provenance)
- **Component:** `src/pars_local_mcp/data/wbs.duckdb` (git-ignored synthetic data).
- **Reproduction:** `sha256sum -c /tmp/nnsa_check/protected_baseline.sha256`: one FAILED entry.
- **Current behaviour:** differs from the protected baseline; matches the hash recorded at 22:12 on 2026-11-18, so
  this closeout did not change it. Earlier startups regenerated it before the freeze. Byte equivalence with the
  evaluation baseline is not established.
- **Expected:** the evaluated database.
- **Workaround:** none needed for function. Each PARS session uses a temporary database.
- **Next step:** restore only from an approved copy, or re-run the evaluation. Neither was done.
- **Demo impact:** no functional impact; limits claims about "the evaluated database".
- **Touches evaluated components:** yes.

### K4. BLS stdio stall (ACCEPTED LIMITATION for the competition)
- **Component:** BLS over stdio (`src/bls_mcp`, frozen; launch in `src/mcp_servers.json`).
- **Reproduction:** `/tmp/nnsa_check/bls_stdio_direct.py` and `/tmp/nnsa_check/bls_fastmcp_stdio.py`
  (logs: `bls_stdio_direct.log`, `bls_fastmcp_stdio.log`).
- **Current behaviour:** `search_series`, `describe_series`, and `get_cached_series_data` stall over stdio (more
  than 40 s). The same calls succeed in-process (about 0.3 to 2.2 s) and over loopback HTTP.
- **Expected:** a response within the tool timeout.
- **Workaround:** Search uses loopback HTTP on 8821 (`tools\start_bls_chat_http.cmd`). The evaluated stdio launch is unchanged.
- **Next step:** diagnose the stdio transport under an approved change window; re-run the BLS evaluation after any fix.
- **Demo impact:** none for Search (HTTP). The evaluated stdio configuration remains affected.
- **Touches evaluated components:** yes.

### K5. Project descriptions unavailable for live PARS projects (MEDIUM)
- **Reproduction:** load proj_001 or proj_002 (live browser pass).
- **Current behaviour:** "Project description unavailable in the current read-only source." for both. Cause:
  `silver_project_descriptions.parsid` is numeric, so the `proj_NNN` lookup never matches.
- **Expected:** the description.
- **Workaround:** none; the message is accurate.
- **Next step:** map `proj_NNN` to the numeric `parsid`, or supply a description source. The lookup may be in the app.
- **Demo impact:** medium.
- **Touches evaluated components:** only if the lookup lives in `src/pars_local_mcp`.

### K6. Evidence gate and displayed WBS come from different databases (MEDIUM)
- `validate_wbs_inputs` checks `mock_pars_full.duckdb` (numeric parsids); the panel shows the temporary live
  database (`proj_NNN`). The CAEF input contract is therefore not checked against the displayed data.
- **Next step:** align the sources and add a test that fails when they diverge.
- **Demo impact:** low while CAEF is blocked (K1, K2).

### K7. A project with no WBS elements shows no message (LOW)
- Documented, not implemented (agreed by the coordinator). The expected-failure test is
  `test_project_with_no_wbs_elements_shows_a_message` in `test_pars_third_panel.py`.
- No demonstration project is affected (both have WBS elements).

### K8. Unknown project IDs fetch WBS data before rejection (LOW)
- Documented, not implemented. The UI shows "PARS could not load this project." and no WBS data.

### K9. Typed invalid project IDs are not possible in the UI (LOW)
- The project ID comes only from search results. Invalid IDs were checked through the tool path only (backend-only).

### K10. Late responses not guarded when the project changes (MEDIUM)
- A load started for one project is not cancelled when another project is selected, so a late response could show
  the earlier project. Not tested in the browser.
- **Next step:** tag loads by project ID and add a browser test with a delayed stub.

### K11. Full test suite not passed in one closeout run against the protected directories (MEDIUM)
- Results on the final tree in this session:
  - `src/cost_intel_app/tests/test_chat_bridge.py` and `src/portable_llm_mcp/tests`: 89 passed (backend-only).
  - `src/cost_intel_app/tests` with PARS process start blocked by a guard plugin: 447 passed, 1 failed, 4 skipped,
    1 xfailed (453 collected).
  - The failing test is `test_pars_live.py::test_project_context_uses_local_pars_fallback_when_env_is_unset`. It
    needs a real PARS process start, which the guard refuses. Running it without the guard was denied by the
    permission check. **NOT RUN.**
  - The coordinator's isolated run on the approved directories: 662 passed, 4 skipped, 1 xfailed, 0 failed.
- **Next step:** run the full suite once in the approved isolation and record the counts. Do not quote older counts.

### K12. Example buttons did not fill the chat input after the user typed (HIGH; FIXED, re-verified)
- **Component:** chat card in `src/cost_intel_app/server.py`.
- **Reproduction:** open Ask Cost Intelligence, type `abc`, click "List PARS projects". Variants: type then Tab then
  click; type, wait, click; type, delete to empty, click. A reload was the only workaround that worked before the fix.
- **Before the fix:** the field kept the typed text (or stayed empty).
- **Fix:** the chat input has `name="chat_question"`, so typed text and examples share one state key. Regression
  tests in `test_pars_view.py`.
- **After the fix (browser):** variants A, B, C and the close-and-reopen and reload workarounds all fill the field (PASS).

### K13. 15 px horizontal overflow at 820 px, approved state (ACCEPTED LIMITATION, noncritical)
- **Reproduction:** viewport 820 px, open the panel, approve. The document is 820 px inside an 805 px content box
  because of the 15 px vertical scrollbar. The coordinator measured no control past the content width.
- **Demo impact:** none at the 1440 px layout used for the demonstration.
- **Possible next step (a proposal for the integration owner, not applied):** size the app root from the content box
  (`width: 100%` rather than the viewport width).

### K14. CSV download: direct export PASS; in-app control BLOCKED (ACCEPTED LIMITATION for the competition; BLOCKED for the host)
- **Verified (PASS, browser-level, backend route):** Prepare CSV from the approved view; the export route returns HTTP 200
  with `Content-Disposition: attachment; filename="nnsa_escalation_basket_y12_....csv"`; Chrome downloads the export
  when the URL is opened as a top-level navigation; the downloaded bytes equal the prepared export (2,751 bytes); the
  weights are Steel mill products 15.00%, Concrete products 15.00%, Electrical equipment 45.00%, General purpose
  machinery 25.00%.
- **Not verified (BLOCKED):** the app's own Download CSV control. The renderer calls `openLink`; the harness host and
  the FastMCP dev preview's launch page implement no open-link handler, so the renderer falls back to
  `window.open(url, "_blank", "noopener,noreferrer")`. No file reached the download folder.
- **Workaround that is not a usable UI alternative:** the URL is returned only to the app view. `export_analysis_csv` is
  app-only: a plain MCP client gets "Unknown tool" (checked over the loopback HTTP server on 8741, then stopped). The
  export URL therefore cannot be obtained outside the app, and this document does not offer a constant or static URL.
  The route can be checked only as a technical step, not as a reviewer procedure.
- **Next step:** test the Download CSV control in the approved MCP Apps host, which must implement open-link. If the host
  fails, implement its open-link handling per its documentation.
- **Demo impact:** the CSV export cannot be demonstrated in the approved host until the host hop is verified.
- **Touches evaluated components:** no.

### K15. CAEF inference: see K1 and K2 (BLOCKED)

### K16. Search answers can paraphrase or add unsupported attributes (MEDIUM; ACCEPTED LIMITATION)
- **Observed (backend regression, coordinator):** E3 listed the 15 series IDs, and the truncation note was correct,
  but the answer added "All returned series are monthly" (the catalog has no periodicity field) and shortened one title
  to "Primary products". Final re-verification: 25 of 25 cited IDs in the catalog, 25 of 25 titles exact, no frequency claim.
- **Observed (C3, exact steel prompt):** the model reported no exact match and labelled related titles as related. Accepted.
- **Next step:** keep the grounding rule; add a deterministic check for periodicity and title paraphrase.

### K17. Follow-up wording differs from the expected sentence (LOW; accepted by the coordinator as PASS)
- The answer is "2 projects." (after the first answer "I listed 2 projects." was observed in one run, so both wordings occur).
  The content is correct and no new tool call was made.

### K18. Search memory is one previous turn; cleared on close, project change, and PARS load (LOW)
- **Browser evidence:** clearing after closing and reopening: the pre-state answer had no tool call; after reopening,
  the old answer was not reused. The reply was the fixed unsupported message (no tool call; no "2 projects" claim).
  Clearing after loading a PARS project: the same result.
- **Wording:** the cleared context gives the unsupported message rather than a re-listed answer. The coordinator
  should decide whether that wording is acceptable. Recorded here as non-reuse PASS.
- **Clearing after switching the basket project** showed a fresh `pars_mcp__list_projects` call (PASS).
- Ask Sage was not re-run for the two clearing rows.

### K19. Broad Search results are truncated at 20,000 characters (LOW)
- The result is cut and the answer says so. No hang observed.

### K20. Local model and MCP limits (LOW; documented)
- Ollama must serve `gemma4:12b-mtp` on loopback with `OLLAMA_NO_CLOUD=1`. The BLS HTTP service must run on 8821.
  The Search call has a 60 s tool limit and a 240 s total limit. Chat uses read-only tools only.
- Failure messages are in 3.3 (BLS down, model down).

### K21. `-gov` model suffix is not enforced by code (LOW; policy)
- The approved-endpoint check still applies. Confirm the model name against agency policy.

### K22. The FastMCP development preview is not offline (MEDIUM for any offline claim)
- `fastmcp dev apps` fetched `app-bridge.js` from npm. On alternate ports (`--mcp-port 8100 --dev-port 8180`, because 8000
  and 8080 were in use) the dev UI returned 200 with its token and `ppi_basket` was the only model-visible tool. An
  unauthenticated request to the dev UI returns 403. Do not claim the preview works offline.

### K23. Data handling for Ask Sage (restriction)
- **Destination:** `api.nnsa.asksage.ai` only, over HTTPS, with the configured credentials.
- **Sent:** question text, system prompt, tool schemas, and tool results, which include synthetic PARS demonstration
  records and BLS series metadata.
- **Not sent by the closeout runs:** actual NNSA project records, CUI, or unrelated repository content.
- **Restriction:** do not transmit project data beyond synthetic demonstration data unless agency approval covers it.
  Vendor retention is governed by the vendor's policy.

### K24. Blocked approved-result states have no UI fixture (LOW)
- The "Result blocked" badge and the "Choose Edit approved allocation, then approve again." reason are covered by unit
  tests only (backend-only). See 3.1.

### K25. The Step 3 "✓ DONE" label is unreachable (LOW)
- `workflow_steps` never returns a complete state for Step 3, so the static label is not shown. No misleading display seen.

### K26. Format and lint (LOW)
- `ruff check` passes on the changed Python files (including the new tests).
- `ruff format --check` reports `src/cost_intel_app/server.py`: a blank-line hunk near the module end. Not changed
  because the integration owner limited `server.py` edits.
- The unused `workspace_state` import was removed.

### K27. Presentation materials (LOW)
- The deck PDF shows the old branch name until it is regenerated. Slides cite older test counts; re-verify before reuse.
- Unverified "1,191 passing tests" claims were removed from `criteria.html` and the `reliability.html` heading by the
  coordinator; the dated 2026-11-17 record on `reliability.html` line 29 is kept.

### K28. The BLS sample snapshot is demonstration data (LIMITATION)
- Price-index figures come from the activated sample snapshot (`data/local/snapshots/`), created by the documented
  `poe sample-snapshot`. It is not evaluation data and was not regenerated. The app states that no BLS observations are
  represented as verified.

### K29. The browser evidence is from a local harness (LIMITATION)
- The harness hosts the app's renderer in a minimal page, stubs PARS unless a row says it used a live session, and
  implements no open-link bridge. It is not the approved MCP Apps host, which is the release source of truth.

## 5. Next steps (ordered)

1. Verify the in-app Download CSV control in the approved MCP Apps host (K14).
2. Decide on CAEF packaging (user key decision), then fix the input contract (K1) and verify the three CAEF criteria separately (K2).
3. Run the full test suite once in the approved isolation and record counts (K11).
4. Re-run Search clearing with Ask Sage (K18) and record it as its own row.
5. Address project descriptions (K5) and evidence-source alignment (K6).
6. Decide on the BLS stdio stall (K4) as a separate change with re-evaluation (frozen component).
7. Confirm the protected PARS database (K3) against an approved copy, or schedule a re-evaluation.
8. Apply the proposed `server.py` items only through the integration owner: the 820 px root width (K13), the format
   hunk (K26), and the unreachable Step 3 label (K25).
9. Phoenix evaluation of other MCP packages (section 6) only after separate authorization.

## 6. Remaining MCP servers: inventory only (no Phoenix evaluation was run)

Excluded: `src/bls_mcp/` and `src/pars_local_mcp/`.

| Package | Entry point or registration | Tools | Launches | Safe test data | External endpoints or credentials | Phoenix configuration it would need |
|---|---|---|---|---|---|---|
| `src/cost_intel_app/` (basket app) | `server.py`: `mcp = FastMCP("NNSA cost intelligence (basket app)")` | `choose_demo_project`, `update_basket`, `reopen_allocation`, `normalize_basket`, `approve_basket`, `choose_preset`, `explore_basket`, `export_analysis_csv` (app-only), `search_pars_projects`, `load_pars_context`, `load_caef_mapping_summary`, `run_caef_mapping_model`, `review_wbs_bls_mapping`, `ask_cost_intelligence`, `pars_panel`, `pars_draft` | Yes (FastMCP; dev preview and HTTP) | Synthetic basket data and synthetic PARS demo projects | Chat: the approved Ask Sage endpoint or local Ollama; PARS through a temporary database; BLS over HTTP on 8821 | Not evaluated. Needs a task set, a judge rubric, and authorization for Ask Sage use |
| `src/cost_intel_ui/` | `streamlit_app.py` (Streamlit adapter); no FastMCP registration | none (view models) | Streamlit, not MCP | Fake data (`fake_data.py`) | none | Not an MCP server; no evaluation |
| `src/portable_llm_mcp/` | Library (`agent.py`, `mcp_client.py`, `llm_client.py`); examples `local_echo_server.py` (FastMCP `local-echo`) and `check_mcp.py` | `echo` (example only) | The example server launches over stdio | Echo only | none for the echo; the agent uses the configured LLM provider | Library, not a server; the echo example could serve only as a smoke test |
| `src/templates/example_server/` | `app.py` (FastMCP "Example MCP Server"), `tools/example_tool.py` (`register`) | `example_echo` | Yes (`main()` chooses stdio or HTTP) | Echo only | none | A template; not a product server. Not evaluated |

`pyproject.toml` lists `example-server = "bls_mcp.app:main"`, which is the frozen BLS package.
