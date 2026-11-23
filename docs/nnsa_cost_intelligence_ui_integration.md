# NNSA Cost Intelligence UI: PARS / WBS + BLS integration

Scope: UI worktree `mcp_group_1-mcp-app`, branch `feat/mcp-app`.
Canonical design: `docs/ai_mcp_cost_intelligence_nnsa_spec_aligned.html`.

## What these drop-ins implement

The FastMCP `ppi_basket` remains a three-zone interface: synthetic NNSA
example-project/basket selection, analysis/results, and PARS/evidence rail. The
palette is copied from the design reference: background `#12171d`, panel
`#202a33`, evidence card `#1b2730`, border `#33414d`, mint `#8be6c9`.
The PARS workspace's cards use the same local palette and typography classes.
No external stylesheets, fonts, scripts, or telemetry are added.

The application retains its existing `pars_live` stdio MCP connector. To use
PARS project context, the analyst enters an **actual PARS project ID** and
loads verified read-only context. The analyst may then pick a WBS root, select
one of the synthetic BLS/PPI series in the basket, enter a rationale (12–500
characters), and request a **review-only mapping candidate**. The candidate
verifies the PARS project and WBS code against `get_project_info`,
`validate_wbs_inputs`, and `get_wbs_hierarchy` using `GuardedClient`.

The mapping is not saved, used in basket calculations, or exported as an
approved cost estimate. The result records the PARS project/WBS identity,
synthetic BLS series ID, analyst rationale, and clear source labels.

## Critical data limits

- Only synthetic PARS origins allowed by the existing `pars_panels` guard are
  shown in the read-only UI; unapproved origins are refused.
- All BLS values here are synthetic `DEMO-...` fixtures, **not** downloaded BLS
  observations or authoritative BLS series mappings.
- The existing Decimal index calculations and approval rules are unchanged.
  There is no monetary WBS cost baseline in this workflow, so no escalated
  project cost is produced.
- No training, prediction, or PARS write-back tools are called.
- The mapping is transient per Prefab UI state. Changing project input clears
  prior PARS context and mapping, and changing WBS/series/rationale clears the
  previous reviewed candidate.
- The independent HTML proof-of-concept is not replaced by these drop-ins. It
  remains the visual design reference. The MCP host controls its outer chat
  shell, so this Prefab app cannot make that host shell pixel-identical.
- Exact hex styles in Prefab use Tailwind arbitrary-value utility classes with
  slate fallbacks. Their rendering depends on the MCP host's CSS support;
  visual QA in the target host is required before claiming pixel fidelity.

## Local configuration

`PARS_REPO` may point to a trusted local PARS checkout (for example, a synced
local `mcp_group_1` worktree). This starts its MCP server as a local **stdio**
child process through the existing `uv run --no-sync` command. It receives a
minimal inherited environment and a temporary database path. The existing
PARS read-only evidence guard still applies. With `PARS_REPO` unset, the UI
shows an explicit unavailable state rather than fake live project results.

Do not set `PARS_REPO` to an untrusted checkout. Do not provide production PARS
credentials to this synthetic demonstration.

## Files changed by this replacement

- `src/cost_intel_app/server.py` — coordinated Prefab layout, demo-project
  navigation, PARS/WBS-to-BLS review UI, tool, and result provenance.
- `src/cost_intel_app/wbs_bls_mapping.py` — pure validation and candidate
  representation; no I/O.
- `src/cost_intel_app/tests/fake_pars.py` — fixture response now matches the
  selected WBS root, so UI verification tests exercise the correct identity.
- `src/cost_intel_app/tests/test_pars_view.py` — integration tests for review,
  failure, state bindings, and HTML palette tokens.
- `src/cost_intel_app/tests/test_wbs_bls_mapping.py` — isolated review tests.

No `src/pars_local_mcp/`, `src/bls_mcp/`, root `README.md`, or `QUICKSTART.md`
files are overwritten.

## Verification in the UI worktree (PowerShell)

```powershell
Set-Location "C:\Users\maura.lapoff\Software\GitLocal\mcp_group_1-mcp-app"
git branch --show-current
git status --short
& ".venv\Scripts\python.exe" -m pytest -q src/cost_intel_app/tests/test_wbs_bls_mapping.py src/cost_intel_app/tests/test_pars_view.py --tb=short
& ".venv\Scripts\python.exe" -m pytest -q src/cost_intel_ui/tests src/cost_intel_app/tests --tb=short
& ".venv\Scripts\ruff.exe" check src/cost_intel_app src/cost_intel_ui
& ".venv\Scripts\ruff.exe" format --check src/cost_intel_app src/cost_intel_ui
git diff --check
```

No test command above deliberately uses a live provider. The existing PARS
integration tests can opt into a local PARS process if `PARS_REPO` is set. For
strictly offline unit testing, leave `PARS_REPO` unset. Tests may write local
cache files. There is no public API egress in the added code.
