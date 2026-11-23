# Local integration and validation status

Baseline: supplied ZIPs from the `fix/pars-launch-closeout` worktree, reviewed
on 2026-11-16. This is a current handoff note, not a historical branch report.

## Wiring

- `src/mcp_servers.json` is the portable client registry. PARS runs via stdio
  with `uv run --no-sync python -m src.pars_local_mcp.server` from the checkout.
  The `--no-sync` flag matches `cost_intel_app.pars_live.PARS_COMMAND` and avoids
  a dependency sync during server launch.
- `src/pars_local_mcp/server.py` and `src/pars_local_mcp/mcp/server.py` both
  initialize the local hierarchy database and register the PARS and WBS tools.
  The registry uses the first; the `pars-mcp-server` console script uses the
  second. Do not merge or rewrite these without a demonstrated need.
- `src/cost_intel_app/server.py` is a FastMCP App using `prefab_ui`; the
  `cost_intel_ui` package is a separate Streamlit implementation. The supplied
  standalone HTML file is the **design reference**; its controls are not
  automatically connected to the server.
- PARS UI panels are read-only and use `GuardedClient` with `READ_ONLY_TOOLS`.
  The general MCP client registry currently allows `write_back_wbs`, while
  the UI blocks it. This difference is intentional as implemented but needs
  a separate authorization decision before production use.

## Local validation commands (Windows CMD, activated project .venv)

From the repository root, after dependencies are already installed:

```cmd
python -m pytest tests/integration/test_pars_registry_contract.py
python -m pytest src/cost_intel_app/tests/test_pars_panels.py
python -m pytest src/pars_local_mcp/tests/mcp/test_mcp_server.py
python -m pytest
```

To check registry-to-UI drift against a running PARS checkout:

```cmd
set "PARS_REPO=%CD%"
python -m pytest src/cost_intel_app/tests/test_pars_read_tools.py
```

This last test may initialize a synthetic database. Before running WBS
model pipeline tests, generate the synthetic source data using the existing
`src/pars_local_mcp/data/generate_full_mock.py` and
`generate_caef_training.py` scripts. They require the configured local CAEF
reference workbook. The mock generators are not replacements for the WBS
model's training and prediction functions.

## Boundaries

- No live BLS/API/LLM tests were run in the offline handoff environment.
- The standalone HTML design has not yet been converted into a connected UI.
- WBS parity against the original modeling repository is deferred.
- Do not claim that compilation, a pure-Python test, or a UI mock test proves
  live MCP transport, WBS training, write-back, or the HTML application.
- `uv sync` may download dependencies and should only be used intentionally;
  the runtime commands above do not intentionally contact external services.
