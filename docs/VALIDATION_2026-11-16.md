# Partial offline validation — 2026-11-16

Source: supplied `root.zip`, `tests.zip`, `src.zip`, and `docs.zip`.
Executed in an isolated Linux environment with Python and pytest, **without**
installing packages or contacting network services. The user's Windows project
`.venv` was not accessible. This is not full acceptance testing.

| Check | Result | Evidence / limitation |
| --- | --- | --- |
| PARS registry contract (new) | PASS | `2 passed` |
| PARS UI panel logic | PASS | `80 passed` |
| PARS read-only manifest checks | PARTIAL | `2 passed, 3 skipped` (no `PARS_REPO`) |
| PARS workspace + live client unit tests | PARTIAL | `23 passed, 1 skipped, 3 failed` due to missing `fastmcp` package |
| Syntax of PARS, cost-intelligence app, and Streamlit UI | PASS | `python -m compileall -q` completed |
| Real FastMCP tool discovery/invocation | NOT RUN | FastMCP and DuckDB not installed in isolated environment |
| Generator outputs and WBS training/prediction | NOT RUN | Missing DuckDB, Polars, local CAEF workbook |
| Supplied HTML file connected to MCP | NOT DONE | HTML is a standalone offline fixture; existing `cost_intel_app` has separate Prefab app UI |
| BLS and whole-repository suite | NOT RUN | Dependencies missing; network-capable tests must be separately controlled |

## Changes in this patch

- Align the `pars_mcp` stdio command in `src/mcp_servers.json` with the existing
  `cost_intel_app.pars_live.PARS_COMMAND` (`--no-sync`).
- Add dependency-free tests to prevent registry launch command drift and
  duplicate allowlist entries.
- Update `README.md` to describe the multiple existing server and UI packages,
  without claiming the HTML reference is already live.
- Reconcile the historical closeout document's statements about
  `write_back_wbs` with the current manifest (it is allowed to the general
  client but prohibited in the read-only UI).
- Document the current integration boundaries and local validation commands.

## Remaining priority work

1. Run actual FastMCP protocol calls under the user's activated `.venv` and
   verify each registered/allowlisted tool. Do not use static registration as
   a substitute for protocol interrogation.
2. Generate and validate the seeded Faker-based capital acquisition mock data
   on the user's machine, including all required local reference files.
3. Connect the specified HTML UX to the existing FastMCP App/backend. Keep its
   write-back preview read-only, keep basket tools separate from PARS read tools,
   and avoid a third application stack.
4. Run integration and UI tests, then update this report with actual results.

## Egress and data-handling

The code and validation commands used for this patch read local unpacked
repository files and write changed files, test caches, bytecode caches and ZIP
artifacts locally. No software was installed and no outbound network calls
were executed. No user source or content was transmitted to services. Running
`uv sync` later may **download** dependencies; that is separate from sending
repository data, and was not performed here. BLS live tools and LLM-backed
agent workflows could contact external services and were not executed.

## Follow-up — protocol smoke harness and testing guide

Added `scripts/verify_pars_mcp.py` (in-process FastMCP Client with isolated temporary
DuckDB hierarchy DB), `tests/integration/test_pars_smoke_contract.py`, and
`docs/TESTING_MCP_AND_UI_LOCAL.md` (Windows CMD commands and precise boundaries).
The smoke harness is **not executed here** because the isolated environment
lacks `fastmcp` and `duckdb`. Its syntax and non-mutating call contract were
checked. Offline verification of the new contract and UI logic ran:

- `tests/integration/test_pars_registry_contract.py`
- `tests/integration/test_pars_smoke_contract.py`
- `src/cost_intel_app/tests/test_pars_panels.py`
- `src/cost_intel_app/tests/test_pars_workspace.py`
- `src/cost_intel_app/tests/test_pars_mock.py`

Result: **105 passed**. No full HTML integration or live subprocess validation
was performed in this environment. The mock source generators still require the
CAEF XLSX reference file; the hierarchy-only MCP smoke does not require it.
