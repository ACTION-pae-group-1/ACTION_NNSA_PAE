# Quickstart — Cost Intelligence App, BLS MCP, and PARS MCP

**For the standalone BLS MCP server, steps 1–4 are all you need.** They take a few

minutes on a fresh machine, need **no API key, no account and no BLS

download**, and end with a running MCP server backed by a local database.

| Step | What it does | Command |

| --- | --- | --- |

| 1 | Install dependencies and create the config file | `uv sync --locked` + copy `.env.example` to `.env` |

| 2 | Build the database | `uv run --locked poe sample-snapshot` |

| 3 | Prove it works | `uv run --locked poe verify` |

| 4 | Run the server | `uv run --locked bls-server` |

Run every command from the **repository root**. The server reads `.env` and

the database from the directory it starts in.

## Primary Cost Intelligence FastMCP App — competition readiness checklist

**Primary interface:** FastMCP App, aligned with `docs/ai_mcp_cost_intelligence_nnsa_spec_aligned.html`. **Backup interface:** Streamlit. The BLS server setup in steps 1–4 below remains available independently and must not be replaced by the App preview.

**Review status (November 18, 2026):** The App opens in the browser. A local test run reported 477 passed and 4 skipped in the Cost Intelligence UI suites, but browser testing found contrast, discoverability, and interaction problems. Automated tests do not close those browser defects. Formal browser acceptance is NOT RUN for the release (see `docs/CAEF_STADIUM_DEMO.md`). Keep the FastMCP design and existing HTML features; the stadium workflow is complementary.

**Update (November 19, 2026):** full suite now 512 passed, 4 skipped, 4 xfailed (count grew from new CAEF/eval tests; the xfail set is unchanged). Several items below were fixed at the code level this session and need browser re-verification, not re-opened as unknown:

- **A3 / E1 (black-on-dark text):** fixed for the workflow-step badges, every outline-variant `Badge` (chat/WBS level badges, "Awaiting basket approval", results meta chips, mapping WBS-code badge), and the results-table column headers (`Period`, `Component`, `Weight`, `Normalized factor`, `Composite factor`). This was a missing `<th>` contrast rule alongside an existing `<td>` one — not a one-off. **Not a full audit**: other contrast defects may still exist outside what was reported.
- **Workflow step logic:** redesigned so Step 1 ("Review allocation") stays the current step through the whole review-and-approval flow instead of flipping to "Done" the moment weights total 100%; a step not yet reached now reads "NEXT STEP" (neutral), reserving "BLOCKED" (red) for an approved result that actually fails its data check.
- **Future work:** A2 (project-switching clicks) and the ribbon component-selector buttons under "Custom PPI escalation index" (e.g. "Electrical equipment") were reported broken and investigated, but no root cause was confirmed or fixed — the backend `explore_basket` tool and its tests are green, so if these are still broken live, it's not caught by the current test suite. Re-test and report the exact symptom (error vs. silent no-op) when picked up.

### Launch checklist (Windows CMD)

- [ ] Run commands from the repository root with dependencies already installed. Confirm `.venv\Scripts\python.exe` and `.venv\Scripts\fastmcp.exe` exist.
- [ ] If using CMD, run `call .venv\Scripts\activate.bat`; in PowerShell, call the `.venv` executable directly, or use a repository launcher. Do not change PowerShell execution policy just to run the App.
- [ ] Check that ports 8000 (MCP) and 8080 (preview) are not occupied by another FastMCP instance. Stop only processes identified as belonging to the prior App instance.
- [ ] For the currently verified Windows fallback, launch with `.venv\Scripts\fastmcp.exe dev apps src/cost_intel_app/server.py:mcp --no-reload --host 127.0.0.1`. Open the `FastMCP dev UI` URL printed in the console; it includes a `?token=` value, and the bare `http://127.0.0.1:8080` returns `403`. If the console shows `[Errno 10048]` on port 8080, an App instance is already running: find it with `netstat -ano | findstr :8080`, confirm the owning process's command line is this `fastmcp dev apps` command, and open its URL instead of starting a second copy.
- [ ] **Hot reload is not yet verified on Windows:** `--reload` previously raised `FileNotFoundError: [WinError 2]` inside FastMCP 3.4.11 subprocess startup. Do not state that a PATH-only launcher fixes it until tested on a fresh checkout.
- [ ] **Network restriction:** `fastmcp dev apps` reports `Fetching app-bridge.js from npm`. Do not treat this mode as offline. Obtain approval and a locally packaged bridge/approved runtime before using it in a restricted environment; no user data upload is intended, but the exact request/telemetry properties are unverified.
- [ ] **Corporate TLS inspection (`SSL: CERTIFICATE_VERIFY_FAILED ... self-signed certificate in certificate chain`):** the app-bridge fetch is made by Python `httpx` to `esm.sh` (the log line says "from npm", but the request is not made by Node). `httpx` trusts only its bundled `certifi` CAs, so a corporate root is rejected. Do **not** disable verification. Instead: (1) obtain the corporate root CA as a PEM file from IT; (2) build a combined bundle: `mkdir C:\certs`, `copy .venv\Lib\site-packages\certifi\cacert.pem C:\certs\combined.pem`, then `type <corporate-root>.pem >> C:\certs\combined.pem`; (3) run `set "SSL_CERT_FILE=C:\certs\combined.pem"` in the same CMD window before the launch command above. Check first with `.venv\Scripts\python.exe -c "import httpx; print(httpx.get('https://esm.sh/', timeout=20).status_code)"`. `NODE_EXTRA_CA_CERTS` and `NODE_USE_SYSTEM_CA` do not affect this fetch.

### Browser feature acceptance checklist

Mark each item **Pass / Fail / N/A** and record *actual behavior, screenshots, and error output*. A passing Python test is not a substitute for checking the visible application.

| ID | Check / tester action | Expected result | Status / observed behavior |
| --- | --- | --- | --- |
| A1 | Open or refresh the FastMCP App | App and all three panes render without an error | Previously Pass; retest: ____ |
| A2 | Switch between Y-12, Pantex, and Los Alamos example projects | Selection changes immediately; data and selection state update coherently | **Fail:** clicks did not work; investigate event binding and round-trip; do not assume the new stadium data caused it |
| A3 | Read all three workflow cards | Light, readable foreground on dark cards; 01→02→03 in order | **Fail:** black text on dark background |
| B1 | Change basket presets | Weight values and selection indicators update promptly | **Fail:** working but delayed |
| B2 | Edit a weight field | Total and approval state reflect the edit promptly | **Fail:** slow |
| B3 | Uncheck and recheck a component | **On uncheck: effective weight and contribution become 0% immediately, excluded row visibly disabled, total revalidates. On recheck: an explicit, predictable weight is shown; no silent approval.** | **Fail:** excluded rows grey out but retain a nonzero visible value; verify after fix |
| B4 | Enter weights not totaling 100%, then Normalize | Selected active weights normalize to 100% | Previously Pass; retest: ____ |
| B5 | Approve a valid basket | Approval succeeds; calculated results appear | Previously Pass; retest: ____ |
| B6 | Edit after approval | **Edit approved allocation** reopens editing; edits invalidate prior approval until reapproved | Previously unclear; verify new control: ____ |
| C1 | Open result summary | Composite factor, context, and data origin are visible | Previously Pass; retest: ____ |
| C2 | Open Component detail | Components and chart render and remain readable | Previously Pass; retest: ____ |
| C3 | Open Adjustment to base | Calculation and waterfall/adjustment context are visible | Previously Pass; retest: ____ |
| C4 | Open Data & CSV | Data table visible; a working CSV download exists **or export is explicitly marked unavailable** | **Fail:** location/export unclear; CSV download not confirmed |
| C5 | Open Evidence & audit | Tab easily found; shows allocation approval, provenance, PARS evidence state | **Fail:** tab not discoverable; verify after approval |
| C6 | Open Scenario comparison | Easily found, allows meaningful comparison with labels and assumptions | **Fail:** controls/location unclear; verify result tabs |
| D1 | Load a PARS project ID returned by the PARS tool | Correct project and WBS evidence load; no inferred project-ID mapping | Not tested: ____ |
| D2 | Enter invalid PARS project ID | Informative error, no crash or stale evidence | Not tested: ____ |
| D3 | Review a WBS→BLS mapping candidate with rationale | Review recorded; mapping clearly labeled as candidate, not cost allocation | Not tested: ____ |
| D4 | Inspect BLS series provenance | Cached/live/synthetic distinguished, with series and dates | Not tested: ____ |
| D5 | Complete PARS WBS cost → BLS index → escalation result | Traceable formula, baseline, dates, index series, and evidence; if unimplemented, explicitly indicated | Not yet verified: ____ |
| E1 | Review all dark and light cards, badges, inputs and buttons | **No white-on-white or black-on-dark text.** Text contrast ≥ 4.5:1 for ordinary text, control boundaries ≥ 3:1 where applicable | **Open critical defect:** white text on white controls and dark text on dark surfaces |
| E2 | Check at normal zoom, different window widths, and scroll | No clipped primary actions or overlapping controls | Not tested: ____ |
| E3 | Refresh page after changes | Recovery is understandable; no misleading approval | Not tested: ____ |

**Questions to report:** Which control was clicked? What project/preset was selected? What values were visible before and after? Did the MCP Log show a call or error? How many seconds did the response take? At what browser zoom? Attach a cropped screenshot with no secrets.

### Immediate UI defect acceptance rules

- **P0 — Contrast:** Fix white-on-white controls *and* black-on-dark labels across workflow cards, buttons, text inputs, disabled rows, results tabs and PARS evidence rail. Use the approved NNSA PA&E palette (PMS 282 navy, PMS 193 red, PMS 408 gray tint and secondary tints); don't assign the same foreground and background or rely on opacity for essential labels.
- **P0 — Excluded component:** Checkbox off must zero the component's **effective** weight, index contribution, and approved-calculation participation immediately. Display `0%` or a clearly disabled zero field, update total and validation, and revoke approval on edits. On recheck, require an explicit/defined weight policy; do not invisibly reinstate a prior approved value. Add model/state tests and browser verification.
- **P0 — Project switching and latency:** Measure tool-call latency separately from browser rendering and verify project switch state. Do not claim the stadium Faker data caused the symptom without evidence.
- **P1 — Results discoverability:** Clearly locate `Data & CSV`, `Evidence & audit`, and `Scenario comparison` within approved results; make CSV export real or unambiguously identify it as not yet implemented.
- **P1 — Wording and trust:** Use **Analysis result**, **Scenario results**, **Cost escalation analysis**, or **Illustrative calculation**, *not* “demo result.” Clearly label synthetic observations and avoid suggesting that they came from live BLS or were applied to PARS baseline costs if that has not occurred.

### Browser pass/fail handoff

Record the checklist statuses above and capture a screenshot for any failed item. Exit criteria for a competition-ready primary UI: A1–A3, B1–B6, C1–C6, and E1–E3 verified; no contrast or approval-state defects; D1–D5 verified if the integrated PARS/BLS analysis is presented as operational. Keep Streamlit as backup, not the primary design target.

---

## Before you start

You need **Git** and [uv](https://docs.astral.sh/uv/). uv installs the

right Python (3.11) for you if it is missing.

- Windows (CMD or PowerShell): `pip install uv`, or `py -m pip install uv` if

  `pip` is not on your path

- macOS / Linux: `pip install uv`, or see the

  [uv install page](https://docs.astral.sh/uv/getting-started/installation/)

Confirm with `uv --version` in a new terminal.

## 1. Install and configure (one time)

Windows CMD:

```cmd
git clone <repository-url> mcp_group_1
cd mcp_group_1
uv sync --locked
copy .env.example .env
```

macOS / Linux:

```bash
git clone <repository-url> mcp_group_1
cd mcp_group_1
uv sync --locked
cp .env.example .env
```

`.env.example` works exactly as copied: no API key, stdio transport, and the

database location that step 2 writes to. Do not edit it for the steps below.

**If `uv sync` fails with `invalid peer certificate: UnknownIssuer`**, your

network inspects HTTPS traffic. Tell uv to trust the system certificate

store, then rerun the sync in the same terminal:

```cmd
set "UV_SYSTEM_CERTS=true"
set "UV_NATIVE_TLS=true"
uv sync --locked
```

(On macOS / Linux use `export UV_SYSTEM_CERTS=true`.) `UV_NATIVE_TLS` is the

older name for the same setting; setting both covers old and new uv releases.

To keep it for future Windows terminals, run `setx UV_SYSTEM_CERTS true` once

and open a new terminal. Putting these names in `.env` has no effect: uv does

not apply its own settings from that file. Do not disable certificate

verification.

## 2. Build the database (one time, offline, about 20 seconds)

```cmd
uv run --locked poe sample-snapshot
```

The server reads BLS series and observations from a **published DuckDB

snapshot** and will not start without one. This one command builds that

snapshot from BLS files checked into `src/bls_mcp/docs/sample_data/`,

validates it, publishes it, and makes it the active one. Nothing is

downloaded.

It is finished when the last line printed is the path of the active database:

```text
...\data\local\snapshots\bls-sample_pc_ci.duckdb
```

`data/local/` is ignored by Git. What the sample database holds:

- **ECI (`ci`):** real data. 506 current-dollar index series with about

  21,000 quarterly observations from 2014 through 2026 Q2, for example

  `CIU2012300000000I` (total compensation, private construction industry).

  Percent-change, constant-dollar and response-rate ECI series are left out

  on purpose; see [docs/bls/ci-ingestion.md](docs/bls/ci-ingestion.md).

- **PPI industry (`pc`):** the full catalog of 4,510 series but only **34

  observations across two series** (`PCU334---334---` and

  `PCU334519334519S`). Enough to prove the setup, not to calculate a real

  materials index.

It contains no PPI commodity (`wp`/`pd`) or CPI data.

<details>

<summary>What that command runs, and how to rebuild</summary>

`poe sample-snapshot` runs these five commands in order:

```cmd
uv run --locked bls-data build --candidate data/local/build-sample.duckdb --snapshot-id sample_pc_ci --pc-manifest src/bls_mcp/docs/sample_data/pc-sample-input.json --ci-manifest src/bls_mcp/docs/sample_data/ci-sample-input.json
uv run --locked bls-data validate --candidate data/local/build-sample.duckdb --pc-manifest src/bls_mcp/docs/sample_data/pc-sample-input.json --ci-manifest src/bls_mcp/docs/sample_data/ci-sample-input.json
uv run --locked bls-data publish --candidate data/local/build-sample.duckdb --registry-dir data/local/snapshots
uv run --locked bls-data activate --registry-dir data/local/snapshots --snapshot-id sample_pc_ci
uv run --locked bls-data current --registry-dir data/local/snapshots
```

The registry path must match `BLS_SNAPSHOT_REGISTRY_DIR` in `.env`

(`./data/local/snapshots` by default).

The builder never overwrites a database. Running the command a second time

stops with `Refusing to overwrite an existing DuckDB`, which means the

database is already built. To start over, delete the `data/local` folder and

run the command again.

</details>

**For full BLS data**, follow [docs/bls/OPERATIONS.md](docs/bls/OPERATIONS.md).

That PowerShell runbook covers the owner-invoked monthly downloads, overlap

audits, build, validation, publication, activation and rollback. Publish into

the same registry directory and the server uses the newly activated snapshot

at its next start.

## 3. Prove it works

```cmd
uv run --locked poe verify
```

This starts the server inside the command, calls it through a real MCP

client, and exits. It makes no network request. Expected output:

```text
PASS discovery: 15 tools, 3 resources, 1 resource templates
PASS access status (configuration only; key not verified)
PASS setup and methodology resources
PASS snapshot catalog: found series PCU32791-32791-
PASS calculation: 110 / 100 = 1.1
PASS smoke check complete; no BLS requests or specification writes
```

The `snapshot catalog` line confirms the server is reading the database from

step 2. If you see `FAIL`, the message names the cause; see

[Troubleshooting](#troubleshooting).

## 4. Run the server

**From an MCP client (the usual way).** The server speaks MCP over stdio, so

the client starts it. Add this to your client's MCP server configuration

(for example Claude Desktop's `claude_desktop_config.json`), replacing the

path with the absolute path to your checkout:

```json
{
  "mcpServers": {
    "bls": {
      "command": "uv",
      "args": ["--directory", "C:\\\path\\\to\\\mcp_group_1", "run", "--locked", "bls-server"]
    }
  }
}
```

`--directory` makes the server start in the repository root, where `.env` and

the database are. On macOS / Linux use a path such as

`/home/you/mcp_group_1`.

**By hand, over stdio:**

```cmd
uv run --locked bls-server
```

This is a **stdio MCP protocol process**, not a web server or an interactive

shell. It prints a startup banner and then waits silently for a client on

standard input. That is the expected behaviour. Stop it with Ctrl+C.

**Over HTTP (for a browser-based or remote client).** Windows CMD:

```cmd
set "MCP_TRANSPORT=streamable-http"
uv run --locked poe serve
```

macOS / Linux:

```bash
MCP_TRANSPORT=streamable-http uv run --locked poe serve
```

The MCP endpoint is `http://127.0.0.1:8000/mcp` and the health check is

`http://127.0.0.1:8000/health`. To check the running HTTP server, run

`uv run --locked poe smoke` in a second terminal.

The results explorer is at `http://127.0.0.1:8000/ui`. It lists the saved

specifications, lets you review their weights, and charts the index the

server calculates (the same payload `get_index_visualization` returns). Its

NNSA example projects are offline demonstrations.

### What to try

The server exposes 15 tools. These work offline against the sample database:

| Tool | Try it with |

| --- | --- |

| `search_series` | `{"request": {"query": "construction", "programs": ["ci"]}}` |

| `describe_series` | series ID `CIU2012300000000I` |

| `get_series_hierarchy` | series ID `CIU2012300000000I` (shows that total compensation includes wages and salaries, and benefits) or `PCU321113321113` (Sawmills: hardwood lumber, softwood lumber, wood chips…) |

| `get_cached_series_data` | series ID `CIU2012300000000I` |

| `create_index_spec`, `validate_index_spec`, `save_index_spec`, `get_index_spec` | build and store an escalation basket |

| `calculate_index_from_bls` | a saved spec whose series and periods are in the database |

| `get_index_visualization` | a saved spec; add `start_year` for a longer annual history |

| `calculate_component_escalation`, `calculate_index_spec`, `calculate_labor_locality_factor` | calculations from values you supply |

| `get_bls_access_status` | no arguments |

`get_series_data` is the one **live** tool: it calls the external BLS API and

needs `BLS_API_KEY` in `.env`. It is not required for anything above.

Setting `MOCK_BLS_DATA=false` does **not** make it offline.

## Troubleshooting

| Symptom | Cause and fix |

| --- | --- |

| `BLS_SNAPSHOT_REGISTRY_DIR ... Field required` | `.env` is missing, or the command was not run from the repository root. Copy `.env.example` to `.env` (step 1) and `cd` to the repository root. |

| `No active BLS snapshot; activate one first` | The database has not been built. Run step 2. |

| `SHA-256 mismatch for <file>` or `Byte size mismatch for <file>` during step 2 | A sample file no longer matches its manifest, usually because its line endings were converted. Run `uv run --locked poe manifest-check`: it names the file and says whether the hash was taken from a CRLF copy. If it reports a working copy that differs from Git's, delete that file and run `git checkout -- <file>`; if the files are right, run `uv run --locked poe manifest-fix` and commit the updated manifest. |

| `Refusing to overwrite an existing DuckDB` | The database is already built; continue to step 3. To rebuild, delete `data/local` first. |

| `invalid peer certificate: UnknownIssuer` during `uv sync` | See the certificate note in step 1. |

| `uv run bls-server` prints a banner and then nothing | Correct. A stdio server waits for an MCP client; use `poe verify` to test it. |

| A series is found but has no observations | The sample database holds observations for ECI and two PPI series only; see step 2. |

**---**

## PARS WBS modeling — analyst quickstart (local demo)

This section is for analysts who want to **prepare, tune/train, predict, and

optionally write predictions** using the existing PARS MCP server. The BLS steps

above are independent. These tools run in Python through FastMCP; you do not

need to launch the basket UI or configure an LLM to validate the server.

**Start in Windows Command Prompt (CMD)** at the repository root:

```cmd
cd /d "C:\path\to\mcp_group_1"
call .venv\Scripts\activate.bat
python -c "import sys, fastmcp; print(sys.executable)"
```

The printed interpreter must be inside this checkout's `.venv`. If it points

to `C:\Program Files\Python` or a user-wide Python installation, activate

the project environment again. Otherwise native imports (such as

`pydantic_core`) may fail even when the project itself is sound.

### A. Generate local synthetic data (once)

The capital-acquisition demonstration uses synthetic projects and WBS titles.

The generator uses **Faker** with a repeatable seed, the checked-in schema, and

the CAEF WBS reference; it does not use the original WBS Modeling repository.

Before running it, confirm the reference workbook exists at:

`src/pars_local_mcp/data/CAEF 2.0 Standard WBS.xlsx`

```cmd
if exist "src\pars_local_mcp\data\CAEF 2.0 Standard WBS.xlsx" (echo CAEF reference found) else (echo CAEF reference missing)
python -m pars_local_mcp.data.generate_full_mock
```

The generated source is

`src/pars_local_mcp/data/mock_pars_full.duckdb` (Git-ignored).

The workbook supplies the standard hierarchy labels; the project records and

titles are synthetic. Do **not** substitute production PARS data for this demo.

If the workbook is absent, obtain the authorized local reference first rather

than creating or guessing its contents.

### B. Check the MCP server before modeling

```cmd
python scripts\verify_pars_mcp.py
set "PARS_REPO=%CD%"
python -m pytest -q src/cost_intel_app/tests/test_pars_read_tools.py
```

The smoke check discovers the **16 allowlisted PARS tools** and exercises seven

read-only hierarchy tools; it **does not train or predict**. The second command

checks a real local stdio MCP connection. Both are separate from the WBS model

pipeline. If either fails, resolve that failure before relying on model output.

### C. Validate the WBS source and choose a workflow

In your MCP client, connect to the `pars_mcp` server specified in

`src/mcp_servers.json`. Its stdio launch uses `uv run --no-sync` and the

project's local environment. The following are **MCP tool names**; some clients

show them with a `pars_mcp__` prefix.

**First call:** `validate_wbs_inputs` with `{}`. Proceed only when its result

contains `"ok": true`. If it reports missing tables or columns, rebuild or

inspect the synthetic database before continuing.

**Option 1 — one-call demo:** Call `run_wbs_pipeline` with:

```json
{"n_iter": 2, "cv_folds": 3, "n_jobs": 1, "model_variant": "untuned"}
```

This runs **clean → tune/train → predict → write-back** in that order. It can

still take considerable time. Save the returned `run_id`; check any `error`

field and the per-stage results. For a run that completed, call

`get_wbs_run_status` with `{"run_id": "<returned-run-id>"}`.

**Option 2 — review each stage before continuing:**

| Order | MCP tool | Arguments | Check before next step |

| --- | --- | --- | --- |

| 1 | `clean_wbs_data` | `{}` | Save returned `run_id`; inspect cleaned row counts. |

| 2 | `tune_and_train_wbs` | `{"run_id":"<id>","n_iter":2,"cv_folds":3,"n_jobs":1}` | Review reported scores, best parameters, and bundle paths. |

| 3 | `predict_wbs` | `{"run_id":"<id>","model_variant":"untuned"}` | Review predicted row and label counts. |

| 4 (optional) | `write_back_wbs` | `{"run_id":"<id>"}` | Confirm `read_back_verified` is true and inspect output paths. |

| Any time | `get_wbs_run_status` | `{"run_id":"<id>"}` | Review stage status and errors. |

Replace `<id>` with the **actual** run ID from step 1, not the literal

placeholder. `untuned` is the default prediction model; choose `tuned` only

when you intend to use the tuned model from the completed run. The smaller

search settings above are **demo settings**, not recommended model-quality

settings. Never describe a run as successful merely because the tool was

discovered: inspect its returned results and status.

The run data, signed model bundles, working DuckDB database, logs, and

predictions live under `src/pars_local_mcp/data/wbs_runs/<run_id>/` by default.

Write-back updates the **per-run working database**, and exports a Parquet file;

it does **not** overwrite the original `mock_pars_full.duckdb` source.

Write-back changes local run artifacts, so review the run before calling it.

The one-call option includes write-back automatically.

### D. Tool access from the portable client

The repository's portable client can list and invoke MCP tools, but

`run_agent.py` also sends the analyst's prompt and selected tool results to the

configured LLM provider. That provider could be external. For a strictly

local-only demonstration, use an authorized local client/provider or a direct

FastMCP client. **No LLM is required to run or test PARS tools.**

To inspect the registered tools without an LLM request, use:

```cmd
set "UV_ENV_FILE=./.env ./src/portable_llm_mcp/.env"
set "MCP_SERVERS_FILE=src/mcp_servers.json"
uv run --offline --no-sync -- python src/portable_llm_mcp/examples/check_mcp.py
```

`--offline` blocks uv package downloads; it **does not** block network requests

made by other programs or a selected LLM provider. The registry may start both

BLS and PARS servers. For model training, use the PARS tools above; no live BLS

API access is required. The training tool can be CPU-intensive and may take a

while even with the small demo settings.

### E. FastMCP App preview and known limitations

The existing embedded basket/PARS app is started with:

```cmd
fastmcp dev apps src/cost_intel_app/server.py:mcp
```

This is the **primary Cost Intelligence UI development preview**, not the WBS training interface. The browser acceptance checklist above governs its readiness.

It requires an activated `.venv` so its subprocess launcher can find `uv` and

`python`. The FastMCP preview has printed `Fetching app-bridge.js from npm`;

therefore **do not run this command in an environment that prohibits outbound

network access** until its bridge is packaged locally. The HTML-design

closeout and browser interactions remain separate validation work.

### F. Troubleshooting and evidence

| Symptom | What to check |

| --- | --- |

| `fastmcp` command not found | Activate `.venv`; alternatively use `.venv\Scripts\fastmcp.exe`. |

| `pydantic_core` DLL load failure | Verify `python` points into the project's `.venv`, not system Python. |

| `PARS did not start` | Check the interpreter and `uv` PATH; rerun the real stdio test. |

| `validate_wbs_inputs` reports a missing source | Generate `mock_pars_full.duckdb` and check the CAEF workbook. |

| Tuning is slow | Use `n_iter=2`, `cv_folds=3`, `n_jobs=1` for the demo; don't equate speed with accuracy. |

| Write-back did not run | Check the `run_id`, preceding stage statuses, and `read_back_verified`. |

Successful validation reported on **November 16, 2026** included 16 tool

registrations, seven read-only MCP calls, and five live stdio tests. These

results do **not** independently establish successful tuning, prediction,

write-back, or HTML interaction in every environment. WBS source-parity work is

deferred; keep it outside the merge acceptance criteria for this closeout.

**---**

# Developer workflow (optional)

Everything below is for people developing in this repository on Windows with

the bundled LLM client. **It is not needed to build the database or run the

server.** These commands use **Windows Command Prompt (CMD)** with the

repository's `.venv` active, and the client needs a second config file:

```cmd
copy src\portable_llm_mcp\.env.example src\portable_llm_mcp\.env
```

## 5. Open CMD in the repository (one time)

VS Code's `.vscode/settings.json` should set **Command Prompt** as the default integrated terminal and select the repository `.venv`. Open a **new** terminal after selecting the interpreter.

```cmd
cd /d %USERPROFILE%\Software\GitLocal\mcp_group_1
python -c "import sys; print(sys.executable)"
```

The Python path should end in `.venv\Scripts\python.exe`. If not, select that interpreter in VS Code and open a fresh terminal. For **standalone CMD** outside VS Code, activate it manually:

```cmd
call .venv\Scripts\activate.bat
```

Do not activate the environment again if your CMD prompt already shows the active project environment.

## 6. Check the local configuration files

Run the following commands; each should display its filename:

```cmd
cd /d %USERPROFILE%\Software\GitLocal\mcp_group_1
if exist .env (echo Root .env found) else (echo Root .env missing)
if exist src\portable_llm_mcp\.env (echo Client .env found) else (echo Client .env missing)
if exist src\mcp_servers.json (echo MCP registry found) else (echo MCP registry missing)
if exist .vscode\settings.json (echo VSCode Settings found) else (echo VSCode Settings missing)
```

Refer to the two `.env.example` files for how to set up your `.env` files.

Keep actual credentials only in the ignored `.env` files. The client `.env` should contain `MCP_SERVERS_FILE=src/mcp_servers.json` and preferred LLM settings similar to:

```dotenv
LLM_PROVIDER=your_provider
LLM_BASE_URL=your_base_url
LLM_CHAT_MODEL=your-installed-tool-capable-model
MCP_SERVERS_FILE=src/mcp_servers.json
```

Replace the model placeholder with a model.

Set these two variables in **every new CMD window** before the client commands below. The tracked `.vscode/.gitkeep` template sets `SSL_CERT_FILE` for VS Code's integrated terminal, but **only after** you copy it to your local `.vscode/settings.json` (gitignored) and run `scripts\build_ca_bundle.ps1` once. Until `%USERPROFILE%\certs\combined.pem` exists, that variable points at a missing file and Python HTTPS calls in those terminals can fail, so remove the `SSL_CERT_FILE` entry from your local settings if you don't need it. Terminals outside VS Code, and Run-button or launch-configuration starts, still need the variables set themselves. The other two variables still need to be set in each terminal:

```cmd
set "UV_ENV_FILE=./.env ./src/portable_llm_mcp/.env"
set "MCP_SERVERS_FILE=src/mcp_servers.json"
```

`.venv` activation does not load `.env` variables by itself. For the following two MCP client commands, `uv run --offline --no-sync` uses the existing project environment and loads the configured `.env` files. It does **not** install packages or contact a package index.

## 7. Check that the MCP tools are discoverable

```cmd
uv run --offline --no-sync -- python src/portable_llm_mcp/examples/check_mcp.py
```

You should see the ten BLS tools and the 16 PARS tools on the client

allowlist in `src/mcp_servers.json`, possibly in a different order. Both

servers start from that one file. The BLS server exposes 15 tools; the

allowlist exposes ten of them. The BLS tools are:

```text
bls_server__get_bls_access_status
bls_server__search_series
bls_server__describe_series
bls_server__get_series_hierarchy
bls_server__get_series_data
bls_server__get_cached_series_data
bls_server__create_index_spec
bls_server__validate_index_spec
bls_server__save_index_spec
bls_server__calculate_index_from_bls
```

The PARS tools are `pars_mcp__list_projects`, `pars_mcp__search_wbs`, `pars_mcp__validate_wbs_inputs`, and the rest of the `pars_mcp__` names in the allowlist. Their full reference is in [src/pars_local_mcp/README.md](src/pars_local_mcp/README.md).

This confirms local MCP registration for both servers, **not** LLM or live BLS API access. PARS starts with `uv` on your PATH, and this command runs from the repository root, which is where PARS expects to start.

## 8. A note on running the server alongside the client

The `check_mcp.py` and `run_agent.py` commands **start their own stdio MCP

subprocesses**, so you do not need to leave `bls-server` (step 4) running.

## 9. Ask the LLM to use BLS MCP

```cmd
uv run --offline --no-sync -- python src/portable_llm_mcp/examples/run_agent.py "Use bls_server__get_bls_access_status and explain the result. Do not retrieve live observations."
```

To look up a series without knowing its ID:

```cmd
uv run --offline --no-sync -- python src/portable_llm_mcp/examples/run_agent.py "Use bls_server__search_series to find a locally imported PPI series. Return its ID and description. Do not call the live BLS API."
```

The snapshot catalog includes only the programs it was built from, not every BLS series; the sample snapshot has PPI industry (`pc`) and ECI (`ci`) series only. If the agent returns HTTP `404` from `127.0.0.1:11434/v1/chat/completions`, check the exact Ollama model name and the HTTP endpoint rather than changing MCP server imports.

### Ask the LLM to use PARS MCP

```cmd
uv run --offline --no-sync -- python src/portable_llm_mcp/examples/run_agent.py "Use pars_mcp__list_projects to list the projects. Give each project's ID and name."
```

Expected: `proj_001` (Project Alpha) and `proj_002` (Project Beta). The PARS source data has to be built once. The setup section in [src/pars_local_mcp/README.md](src/pars_local_mcp/README.md) explains how. The PARS pipeline tools (`tune_and_train_wbs`, `run_wbs_pipeline`) are slow with default settings, so pass `n_iter=2`, `cv_folds=3`, `n_jobs=1` for a quick run.

## 10. Retrieve cached observations

The live BLS API is **not needed** to read observations stored in the active snapshot. For example, this series has observations in the sample snapshot from step 2:

```cmd
uv run --offline --no-sync -- python src/portable_llm_mcp/examples/run_agent.py "Use bls_server__get_cached_series_data for CIU2012300000000I. Report up to 3 stored observations with dates. Do not invent values or call the live BLS API."
```

This only returns observations if that series has observations in the active snapshot. Prompt instructions alone cannot enforce no network access while the live retrieval tool is allowed; use allowlists or network controls for strict offline operation.

## 11. Run tests and quality checks

With `.venv` active:

```cmd
python -m pytest -q
python -m ruff check src tests
python -m ruff format --check .
```

**Test locations:** BLS helpers and component-owned tests are under `src/bls_mcp/tests/` (including `harness.py`); portable-client tests under `src/portable_llm_mcp/tests/`; shared integration tests under `tests/integration/`. Use `src/bls_mcp/docs/sample_data/` for checked-in BLS sample fixtures when available.

## 12. Add more MCP servers

Use the template under **`src/templates/example_server/`**. Copy it into a newly named server package, give that server its own tests and entry point, then add another named configuration to `src/mcp_servers.json`. The Python template import namespace is `templates.example_server`, not `example_server`.

`server.json` is server identity metadata; `src/mcp_servers.json` configures the client connections.

## Network and Git policy

Local CLI checks and tests operate on local source and fixtures, though test code is not network-sandboxed. Python may write temporary test databases and caches. The local Ollama agent sends prompts and tool results to `127.0.0.1:11434` when configured that way. The live BLS tool can contact the external BLS API. Other providers may send data to remote services. `--offline` prevents `uv` package downloads, **not** program-initiated HTTP requests.

Authorized pushes to the internal `github.doe.gov/NNSA-MB-90/mcp_group_1` repository are allowed. The GSA template source `github.com/GSA-TTS/example-mcp-server` is **fetch-only: never push to it**.

See [README.md](README.md) for architecture and [src/portable_llm_mcp/README.md](src/portable_llm_mcp/README.md) for client configuration details.

## Optional Poe shortcuts

With `.venv` activated, `poe sample-snapshot` builds the sample database, `poe verify` checks the server in-process, `poe launch` runs the BLS stdio server, `poe test` runs the non-live pytest suite, and `poe mcp-check` checks local MCP tool discovery. `poe agent "your prompt"` runs the portable LLM agent. The client shortcuts require the same `UV_ENV_FILE` and `MCP_SERVERS_FILE` configuration shown above. Run `poe` to list all available tasks.
