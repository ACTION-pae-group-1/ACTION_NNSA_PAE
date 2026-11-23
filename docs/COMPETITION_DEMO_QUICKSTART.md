# NNSA Cost Intelligence | Competition demonstration

This is the authoritative **no-build** startup guide for the competition demonstration. Use the existing `.venv` and installed dependencies. Do not run installers, and do not rebuild the BLS snapshot or the PARS database.

**What makes this different:** The demonstration joins project context and a complete WBS hierarchy, then lets an analyst explore an explainable, weighted economic-index scenario. **The model does not generate labels for the selectable projects proj_001 or proj_002 in this build.** The three distinctions below set out what is and is not shown. The WBS-to-BLS mapping in the third panel is an **analyst-selected candidate**, checked against PARS identity (project, WBS code, and evidence origin). It uses no CAEF or machine-learning input, is never applied automatically, and does not change weights or calculations. The manual basket is fully independent.

## Status at closeout

| Area | Status | Notes |
|---|---|---|
| Prepare CSV | PASS | Creates the export in the Data & CSV panel |
| HTTP export endpoint | PASS | Returned HTTP 200 with an attachment header |
| Direct Chrome download | PASS | 2,751 bytes; weights 15/15/45/25 |
| In-app **Download CSV** button | **BLOCKED** (accepted release limitation) | The current host does not implement the open-link handler. It needs a compatible MCP Apps host. Do not claim the button works. |
| CAEF 2.0 inference on its compatible synthetic dataset (project 100) | Backend-verified (`run_model_for_project("100")` returned loaded, 836 rows); **not browser-verified** | The packaged model and saved Parquet are present. |
| PARS-to-CAEF inference for proj_001 and proj_002 (default PARS database) | **BLOCKED** (accepted release limitation) | Missing source fields and preprocessing reference data. No labels are generated for these projects. Stadium projects 5401 and 5402 were run through the launcher; see the stadium release update below. |
| Third panel | Working | PARS project selection, WBS hierarchy, proj_001/proj_002 switching, collapse/restore, and analyst-selected WBS-to-BLS mapping candidates (verified against PARS identity; no CAEF input; never applied automatically) |
| Search follow-up "2 projects." | PASS | Accepted |
| Isolated automated test suite | 662 passed, 4 skipped, 1 xfailed, 0 failed | An isolated suite, **not a full-repository result**. The full repository suite was **not run**. |
| 820 px horizontal overflow | Noncritical | Scrollbar-only observation |
| BLS for Search | HTTP only | Runs at `http://127.0.0.1:8821/mcp` via `tools\start_bls_chat_http.cmd`. The Windows stdio launch is a limitation and is not used here. |

## Stadium release update (2026-11-19)

The rows above describe the default PARS database. The stadium release is separate. When `COST_INTEL_PARS_STADIUM_DB` points to the packaged synthetic stadium database, the app starts the application-side launcher (`src/cost_intel_app/pars_launcher.py`) on it. PARS-to-CAEF inference then ran through that launcher on unseen projects 5401 (119 of 119 rows) and 5402 (99 of 99 rows). Browser acceptance for those projects is **NOT RUN**. See `docs/CAEF_STADIUM_DEMO.md` and `eval/caef/results/release-2026-11-19/FINAL_EVALUATION_REPORT.md`.

## Three distinctions for the competition narrative

1. **PARS MCP:** the app retrieves and displays synthetic PARS WBS data for the selectable projects (project context, WBS hierarchy, proj_001/proj_002 switching). Access is read-only.
2. **CAEF 2.0:** the packaged model runs inference on its compatible synthetic dataset, project 100. This is backend-verified (not browser-verified). It is not an inference demonstration for proj_001 or proj_002.
3. **PARS-to-CAEF integration:** inference for the selectable PARS projects proj_001 and proj_002 is **BLOCKED** by missing source fields and preprocessing reference data. Do not claim the model generates labels for proj_001 or proj_002.

Two further points:

- The analyst-authored WBS-to-BLS mapping is **not machine-learning-powered**. It uses no CAEF or ML input.
- The standalone Phoenix PARS evaluation (reported 2026-11-11 as 100 percent correctness and scope, 50 of 50) is **withdrawn as unverified**. No run output is committed, and Phoenix recording is BLOCKED (arize-phoenix server not installed). It does **not** establish end-to-end CAEF integration.

## Judge-facing, five-minute tour

1. **Open the app.** Use your locally approved MCP Apps host or the FastMCP development preview. Select `ppi_basket` to open the three-pane analyst workspace. The welcome website `/` is informational, not an alternate app renderer.
2. **Explore a project.** In **Project & evidence**, choose one of the synthetic PARS demo projects. Load project context to show its ID, name, and WBS hierarchy. A project description appears only where the PARS description source has an entry; the two demo projects currently have none, and the app says so. WBS element-level narratives are *future work*.
3. **Show the CAEF status.** Project 100 inference is backend-verified but **not browser-verified**; confirm the **View saved CAEF mapping** and **Run model on bundled data** controls in the host before presenting them. Inference is backed by the packaged synthetic dataset (project 100) only. For proj_001 and proj_002 it is **BLOCKED** by missing source fields and preprocessing reference data. Do not describe these controls as producing labels for proj_001 or proj_002.
4. **Build an escalation scenario.** Change component inclusion and weight assumptions in the existing basket. Normalize, approve, and open **Component detail**, **Adjustment to base**, and **Scenario comparison**. The cost-index scenarios use synthetic observations, not live BLS figures.
5. **Prove the result.** Show **Evidence & audit**, traceable series/weights, and **Data & CSV**. Use the direct-download workaround below for the CSV. The in-app **Download CSV** button is blocked on hosts without the open-link handler.

**Four claims we must never make:** the model generates labels for proj_001 or proj_002; no actual PARS cost baseline is escalated; CAEF predictions are not analyst-approved allocations; WBS element descriptions are not available yet. PARS source access and descriptions remain subject to the existing read-only/synthetic source controls.

## CSV download

- The in-app **Download CSV** button is **blocked** on the current host because the host does not implement the open-link handler. This is an accepted release limitation. The button needs a compatible MCP Apps host.
- **Direct-download workaround (verified at closeout):** Prepare CSV, then open the export URL in Chrome. The app builds the URL as `<app base URL>/exports/<token>`. The closeout direct download saved 2,751 bytes with weights 15/15/45/25.
- The UI does not display the export URL. The steps for obtaining it were not written down at closeout. Confirm them on the demonstration machine before presenting.

## Start order for Search and the demonstration (Windows CMD)

The repository includes the activated BLS sample snapshot in `data\local\snapshots\` (three files: `active-snapshot.json`, `bls-sample_pc_ci.duckdb`, and `bls-sample_pc_ci.duckdb.validation.json`). Standard demonstrations do not need `poe sample-snapshot`.

1. **Window A, from the repository root:** start the BLS service for Search on loopback HTTP, and leave it running.
   ```cmd
   tools\start_bls_chat_http.cmd
   ```
2. **Window B, from the repository root:** start the application (see the command below).
3. **Optional:** confirm the snapshot is active with `.venv\Scripts\bls-data.exe current --registry-dir data\local\snapshots`.

Details, the Search provider setup, and the unavailable-service behavior are in `docs/CHAT_COMPETITION_QUICKSTART.md`.

## Run from the repository root (Windows CMD)

Use your existing `.venv` and installed dependencies. Do not run unreviewed installer scripts in a restricted network environment.

```cmd
.venv\Scripts\python.exe -m ruff check src/cost_intel_app
rem Targeted checks used before the demonstration. The full test suite is not part of the judge run: some UI tests start the PARS server.
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider src\cost_intel_app\tests\test_chat_bridge.py src\cost_intel_app\tests\test_pars_view.py src\cost_intel_app\tests\test_pars_draft.py src\cost_intel_app\tests\test_basket_workflow.py
.venv\Scripts\fastmcp.exe dev apps src\cost_intel_app\server.py:mcp --no-reload --host 127.0.0.1
```

The command opens a browser window and prints a **tokenized localhost preview URL** in the console; use that URL. Opening `http://127.0.0.1:8080/` without the token returns HTTP 403. If the default ports are busy, add `--mcp-port <port>` and `--dev-port <port>`. The closeout check reported that these flags worked on ports 8100 and 8180; there is no `--port` option. The native Windows `--reload` path was previously unreliable, so this demonstration uses `--no-reload`. No hot-reload watcher is part of this repository. The launch log states `Fetching app-bridge.js from npm`, so **the preview itself is not offline**. An offline/approved MCP host is required for a genuinely zero-egress deployment.

If running the app via an HTTP MCP service, the branded informational landing page is `/`; the endpoint `/mcp` is for an MCP client, **not an ordinary website**. Documentation is at `/quickstart`, `/methodology`, `/data-sources` on that same service.

### Command verification status

| Command | Status for this document |
|---|---|
| `tools\start_bls_chat_http.cmd` | Read the script. At closeout a plain GET to `http://127.0.0.1:8821/mcp` returned HTTP 406, so the service was listening. |
| `.venv\Scripts\bls-data.exe current --registry-dir data\local\snapshots` | Entry point confirmed in `pyproject.toml` (`bls-data`). Run at this update: printed the active snapshot path ending in `bls-sample_pc_ci.duckdb`. |
| `.venv\Scripts\python.exe -m ruff check src/cost_intel_app` | `ruff.exe` present. Not run at this update. |
| Targeted `pytest` command | All four test files confirmed present. Not run at this update. The isolated suite result above is the closeout result; its exact selection is not recorded here. |
| `.venv\Scripts\fastmcp.exe dev apps ...` | `fastmcp.exe` present. Flags reported by the closeout check. Not run at this update. |

## Self-contained model asset readiness (release gate)

The current uploaded source contains the CAEF prediction pipeline but **not a trained model bundle or a completed Parquet**. Those artifacts cannot safely or truthfully be manufactured from code alone.

**Status at closeout:** `src\cost_intel_app\demo_assets\caef\` now holds `README.md`, `demo_run.json`, `demo_verification.key`, `predicted_levels.parquet`, and `r8fec4416f3d5\`. Running `.venv\Scripts\python.exe -I tools\check_competition_assets.py` reports **NOT READY** for one reason only: the saved mapping does not include both bundled demo projects (proj_001 and proj_002). This is the live-project coverage gap. The file preflight passes; project 100 inference is backend-verified but not browser-verified. The CAEF release gate is therefore **not met**.

IMPORTANT: This build does **not** yet implement inference on newly refreshed PARS WBS records. The optional model run reuses the packaged prepared synthetic inputs. A read-only PARS retrieval and model-input adapter, with model/schema compatibility tests and versioned snapshots, remains required for the monthly-refresh requirement. Do not claim that clicking Run reclassifies the latest PARS data.

The application automatically searches `src/cost_intel_app/demo_assets/caef/` for the saved Parquet and packaged synthetic demo model. Analysts configure no run paths or signing keys. For a release, an engineer must place an **existing, verified synthetic-origin** run in that folder using `tools/prepare_caef_demo_assets.py`:

```cmd
.venv\Scripts\python.exe tools\prepare_caef_demo_assets.py --run "C:\absolute\path\to\synthetic\r0123456789ab" --demo-key "C:\absolute\path\to\dedicated_demo.key" --confirm-synthetic-only
```

The script's flags (`--run`, `--demo-key`, `--confirm-synthetic-only`) were confirmed from its argument parser. It was not run at this update.

These are **one-time packaging inputs for a release engineer**, not settings or files judges must supply. Never use a production signing secret or restricted PARS data. The packaging tool checks the HMAC manifest and file checksums without loading model pickle files; it copies only the needed synthetic run artifacts and saved Parquet. The distributed synthetic demo key is not a production trust mechanism.

If packaging reports that the prediction Parquet is absent, regenerate predictions within the trusted source environment, rerun packaging, and **verify the packaged results reference the bundled demo projects**. Do not label invented data as model-produced output.

Before release run `.venv\Scripts\python.exe tools\check_competition_assets.py`. This check must report READY; it also checks that the saved Parquet contains both `proj_001` and `proj_002`. A passing file preflight is **not** proof that the actual model run or browser works.

**Release must be blocked unless:** saved parquet opens for the demo project(s); the model run actually executes with the bundled dependencies and returns project classifications; manual basket and approval work; labels and tabs meet contrast standards; CSV export works in a compatible host; no external network access is needed by the approved host.

### Git LFS: verify the push, don't trust it

`src/cost_intel_app/demo_assets/caef/r8fec4416f3d5/working.duckdb` and
`.../bundles/untuned/fitted_pipeline_sgd.joblib` are tracked with Git LFS
(`.gitattributes`) because they exceed the pre-commit size limit.

**2026-11-19 incident:** the commit with both LFS pointers was pushed, but
the actual object data never reached the LFS server. A teammate's
`git lfs pull` failed with `Object does not exist on the server: [404]` for
both OIDs. `git lfs push origin main` was then run to fix it and reported
success (exit 0, no error output) — **but the objects still were not on the
server.** `git lfs push` can silently no-op without uploading anything; its
local state tracking is not reliable evidence of what the server actually
has.

**What actually worked:** uploading both objects directly through the LFS
HTTP batch API (`POST .../info/lfs/objects/batch` with
`"operation": "upload"`, then `PUT` each file's bytes to the returned
`actions.upload.href`), and confirming the fix with a **download** batch
request afterward — the same check `git lfs pull` performs. Only a 200
response with no per-object `error` field on a fresh `download` batch
request is real confirmation; a clean `git lfs push` exit code is not
sufficient evidence by itself.

If a teammate hits a 404 on `git lfs pull` again, re-run the **download**
batch check first to see whether the object is genuinely missing before
assuming a local networking problem on their end.

## What the app reads, executes, contacts and writes

- **Reads:** local synthetic project/WBS data, the local scenario observations, and, when present, the packaged Parquet; optional prediction reads a verified signed model and the synthetic prepared DuckDB.
- **Executes:** existing FastMCP/Prefab code; on explicit request only, the existing WBS `stage_predict` code. Does not retrain the model.
- **Contacts:** these new CAEF/homepage features call no remote service. Existing PARS bridge and FastMCP preview may have separate processes/dependencies; review their configuration before claiming offline behavior. The BLS service for Search listens on `127.0.0.1` only. Search contacts the configured provider (the approved Ask Sage endpoint, or a loopback Ollama model) only when a question is submitted.
- **Writes:** optional inference writes `predictions/predicted_levels.parquet`, the prediction stage manifest, and local logs under the packaged synthetic run folder. It does not write to the PARS system.

## Scope of the demonstration

Project descriptions appear only where the source has an entry, which is not the case for the two demo projects; WBS element descriptions, validated PARS cost allocations, and real project baseline escalation are future work. WBS-to-BLS mapping candidates are analyst-selected only and use no CAEF or machine-learning input. Each candidate carries the disclaimer "Synthetic BLS series. Mapping candidate only; no PARS baseline costs were used, no escalation was applied, and no PARS records were modified." Source-labeled synthetic scenario observations must not be represented as current BLS data.
