# Local PARS MCP and UI verification (Windows CMD)

Baseline: `main`; use the activated project `.venv` and run from the repository root. This guide tests the existing code, not the original WBS repository. **WBS parity is deferred.** Do not claim a full end-to-end pass unless the final steps pass on your machine.

## 1. Apply the closeout files

First compare each supplied patch file against your checkout before copying it. Copy the updated files into the matching repository-relative paths. Do not copy the packaged ZIP over your entire repository, and do not switch branches or merge worktrees. Keep a backup or commit first. The patch does not contain a generated database or secrets.

## 2. Confirm local environment (no dependency installation)

Open Windows **CMD**, not PowerShell:

```cmd
cd /d "C:\Users\maura.lapoff\Software\GitLocal\mcp_group_1-pars-integration"
.venv\Scripts\activate.bat
python --version
python -c "import fastmcp, duckdb, faker; print('FastMCP, DuckDB, Faker imports OK')"
```

If any import fails, STOP: the existing environment is missing a required dependency. `uv sync --locked` **may download packages**, so only run it if you approve installation-time network access. No dependencies need to be installed to read the patch or run its dependency-free tests.

## 3. Offline tests before changing data

```cmd
python -m pytest -q tests/integration/test_pars_registry_contract.py tests/integration/test_pars_smoke_contract.py
python -m pytest -q src/cost_intel_app/tests/test_pars_panels.py src/cost_intel_app/tests/test_pars_workspace.py src/cost_intel_app/tests/test_pars_mock.py
```

Expected: both commands exit with code zero. These are unit/contract tests; they do **not** prove MCP transport, UI visual fidelity, or model training.

## 4. Test actual FastMCP calls without touching the checked-out database

```cmd
python scripts\verify_pars_mcp.py
```

The new smoke script builds an isolated temporary synthetic hierarchy database, registers the actual PARS FastMCP server, inspects all `pars_mcp` allowed tools using a real FastMCP Client, and calls seven read-only hierarchy tools via the MCP protocol. It deletes its temporary database on exit. No training or write-back is invoked. **PASS** means the registry tools are discoverable and the selected hierarchy tools returned valid payloads; it does not mean every tool was executed.

If this fails, retain the exact command, exception class, and the failing tool name for debugging. Do not publish logs containing passwords or project-specific secrets.

## 5. Validate the live stdio subprocess and existing PARS UI contract

```cmd
set "PARS_REPO=%CD%"
python -m pytest -q src/cost_intel_app/tests/test_pars_read_tools.py
python -m pytest -q src/pars_local_mcp/tests/mcp/test_mcp_server.py
```

`PARS_REPO` is **only** a local path, not a URL. The live test spawns the actual stdio server via `uv run --no-sync`; that local subprocess uses its existing environment and may initialize a local *temporary* synthetic hierarchy DuckDB database. Confirm that all of the tests that require `PARS_REPO` actually ran; `SKIPPED` is not `PASSED`. `uv run --no-sync` avoids dependency synchronization, but does not guarantee that optional third-party libraries have no startup telemetry; run with network access blocked if strict offline enforcement is required.

## 6. Generate the capital-acquisition mock source (after the Faker update)

Check this prerequisite before running either generator:

```cmd
if exist "src\pars_local_mcp\data\CAEF 2.0 Standard WBS.xlsx" (echo CAEF workbook present) else (echo CAEF workbook MISSING - generator cannot run)
```

The existing source generator **requires** the workbook at that exact path (sheet `WBS`); Faker alone cannot reconstruct its reference hierarchy. If it is missing, record the generation as BLOCKED and continue with the independent smoke tests above. If present:

```cmd
python -m pars_local_mcp.data.generate_full_mock
python -m pars_local_mcp.data.generate_caef_training
python -m pytest -q src/pars_local_mcp/data/test_generate_full_mock.py src/pars_local_mcp/data/test_generate_caef_training.py
```

These write a synthetic DuckDB source database and CAEF labeled training database into the repository's `src/pars_local_mcp/data/` directory. They do not download datasets or transmit records. The Faker patch should be applied separately and checked before running; seeded output is reproducible. The generators may replace existing *generated* files with those default names; back those files up if needed.

## 7. Check the existing FastMCP App (UI/backend)

The current FastMCP App is `src/cost_intel_app/server.py`, with the model-visible tool `ppi_basket`; the PARS panels and the write-back draft are backend tools (`pars_panel`, `pars_draft`), not a separate app; it is not the same as the standalone HTML prototype.

```cmd
python -m pytest -q src/cost_intel_app/tests/test_server.py src/cost_intel_app/tests/test_pars_view.py
```

If `prefab_ui` is installed in the current environment, inspect the UI with the local FastMCP development application:

```cmd
set "PARS_REPO=%CD%"
fastmcp dev apps src/cost_intel_app/server.py:mcp
```

This is a development preview command, **not** a production deployment. Inspect the printed address and confirm it binds to loopback before opening it. The preview should show a PPI basket and a PARS project workspace. Check the latter for synthetic project context, hierarchy, search, empty/error states, and a tool-call log. The app does not currently reproduce the supplied HTML screen pixel-for-pixel; HTML design integration remains a separate UI task. Never interpret a preview-only write-back modal as a real write-back action.

## 8. Acceptance record

| Check | Expected outcome | Record |
| --- | --- | --- |
| Contract tests | No registry/command drift | PASS / FAIL |
| PARS panel tests | Read-only and state logic passes | PASS / FAIL |
| FastMCP in-process smoke | Discovery + seven MCP calls pass | PASS / FAIL |
| FastMCP stdio tests | Live server exposes all UI read tools | PASS / FAIL / SKIP |
| Faker mock generation | Source + labeled output exist | PASS / FAIL / BLOCKED |
| FastMCP App tests | App tools/resources render as expected | PASS / FAIL / BLOCKED |
| HTML design fidelity | Supplied HTML represented in connected app | NOT COMPLETE |
| WBS tune/predict/write-back | Actual end-to-end execution | NOT RUN |
| Original WBS parity | Comparison with original repository | DEFERRED |

## Local execution and data-egress description

All shown `python` and `pytest` commands load local source code, configuration, and test fixtures. The smoke script creates and removes a temporary DuckDB file; the generators read the local JSON schema and CAEF workbook and write local DuckDB files. The UI preview starts a local development server (loopback must be confirmed). None of these commands intentionally calls BLS, a hosted LLM, or any external service. Dependency *installation* with `uv sync` is a separate network-capable operation, not required by the commands above. Third-party package telemetry/update behavior has **not** been verified; use an OS-level network block for a strict offline test.
