# mcp_group_1 — Multi-MCP workspace

This repository contains independent Model Context Protocol (MCP) servers, a reusable MCP server template, and a portable LLM client that connects local or approved hosted models to MCP tools. The first operational server is `bls_mcp`, which supports Bureau of Labor Statistics (BLS) series discovery, cached and live observations, and escalation-index operations. See [the BLS component list](src/bls_mcp/docs/component_list.md) for more information.

## Quick start: build the database and run the server

On a fresh machine with [uv](https://docs.astral.sh/uv/) installed, from the
repository root. No API key, account or BLS download is needed.

| Step | Windows CMD | macOS / Linux |
| --- | --- | --- |
| 1. Install and configure | `uv sync --locked` then `copy .env.example .env` | `uv sync --locked` then `cp .env.example .env` |
| 2. Build the database (about 20 seconds, offline) | `uv run --locked poe sample-snapshot` | same |
| 3. Prove it works | `uv run --locked poe verify` | same |
| 4. Run the server (stdio) | `uv run --locked bls-server` | same |

Step 3 should end with `PASS smoke check complete`. Step 4 prints a banner
and then waits silently for an MCP client; that is correct for a stdio server.

To use the server from an MCP client such as Claude Desktop, register it with
the absolute path to this checkout:

```json
{
  "mcpServers": {
    "bls": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/mcp_group_1", "run", "--locked", "bls-server"]
    }
  }
}
```

**[QUICKSTART.md](QUICKSTART.md) has the full walkthrough**: expected output
for each step, running over HTTP, example tool calls, and troubleshooting.

## PARS MCP and cost-intelligence UI (local demonstration)

The workspace also contains a PARS WBS FastMCP server (`src/pars_local_mcp/`),
a cost-intelligence MCP App (`src/cost_intel_app/`), and a Streamlit UI
(`src/cost_intel_ui/`). These are separate interfaces, not a single server.

- **PARS server:** `python -m src.pars_local_mcp.server` from the repository
  root (inside the activated project `.venv`). The client registry launches it
  with `uv run --no-sync python -m src.pars_local_mcp.server` over stdio.
  `pars-mcp-server` is also defined as a console script.
- **PARS data:** the server initializes its local hierarchy database on startup.
  The WBS modeling tools use a separate synthetic source database, normally
  `src/pars_local_mcp/data/mock_pars_full.duckdb`; generating that source may
  require the CAEF reference workbook (`src/pars_local_mcp/data/CAEF 2.0 Standard WBS.xlsx`).
- **Stadium demonstration database:** setting `COST_INTEL_PARS_STADIUM_DB` to the
  packaged synthetic stadium database starts the application-side launcher
  (`src/cost_intel_app/pars_launcher.py`) on that database. The launcher registers the
  same 16 PARS tools. See [CAEF stadium demonstration](docs/CAEF_STADIUM_DEMO.md).
- **PARS UI:** `src/cost_intel_app/server.py` implements a FastMCP App with
  basket controls and PARS read-only panels. The panels use the MCP client in
  `src/cost_intel_app/pars_live.py` and require `PARS_REPO` to point at the
  repository checkout. Its PARS tool allowlist is intentionally read-only.
- **HTML reference:** `docs/ai_mcp_cost_intelligence_nnsa_spec_aligned.html`
  is the supplied design, not evidence that the entire design is live.

See [PARS UI wiring spec](docs/PARS_UI_WIRING_SPEC.md) and
[local integration status](docs/LOCAL_INTEGRATION_STATUS.md) for scope,
commands, and validation boundaries. Neither the user interface nor the
agent should be treated as permission to perform model write-back without
an explicit authorization decision.

## BLS data: the DuckDB snapshot

The server does not ship with a database and will not start without one. BLS
series and observations are served from a published, immutable **DuckDB
snapshot**, selected by the registry in `BLS_SNAPSHOT_REGISTRY_DIR`.
`search_series`, `describe_series`, `get_cached_series_data` and
`calculate_index_from_bls` read it and make no HTTP request.

- **Sample database (offline):** `uv run --locked poe sample-snapshot` builds
  one from the BLS files checked into `src/bls_mcp/docs/sample_data/`. It
  holds real Employment Cost Index data (506 series, about 21,000
  observations) and the PPI industry catalog with observations for two
  series. See [QUICKSTART.md](QUICKSTART.md) step 2.
- **Full monthly snapshots:** the
  [end-to-end BLS operations runbook](docs/bls/OPERATIONS.md) covers source
  acquisition, pinned-manifest audits, candidate builds, validation,
  publication, activation, and rollback.

Saved index specifications are kept in a separate DuckDB file
(`BLS_SPECS_DB_PATH`), created on first save, never in a snapshot.

`get_series_data` is the explicitly live BLS API tool. `MOCK_BLS_DATA` only
affects that live `BLSClient` path; it does not change the snapshot-backed
tools. A snapshot holds only the programs it was built from, so a series may be
discoverable without having observations for every period.

## Architecture

The workspace has independent MCP services and two distinct UI entry points.
The portable agent is optional; the MCP services do not require an LLM.

```text
Analyst / MCP-aware client
    |
    +-- Optional LLM path: src/portable_llm_mcp/ (MCPAgent + MCPHub)
    |       +-- src/mcp_servers.json (server connections + tool allowlists)
    |               +-- bls_server (stdio) --> BLS snapshot / optional live API
    |               +-- pars_mcp (stdio) --> PARS hierarchy and WBS workflows
    |
    +-- FastMCP App: src/cost_intel_app/server.py
    |       +-- basket state / approvals / synthetic PPI calculations
    |       +-- read-only PARS panels via src/cost_intel_app/pars_live.py
    |       |       +-- local PARS MCP server (project / WBS context)
    |       +-- optional chat (src/cost_intel_app/chat_mcp_servers.json)
    |       |       +-- read-only BLS + PARS tools only, via the approved
    |       |           LLM endpoint (Ask Sage) or local Ollama
    |       +-- optional CAEF 2.0 classification (src/cost_intel_app/caef_summary.py,
    |               caef_live_inference.py) against a packaged model bundle
    |               in demo_assets/ (see docs/COMPETITION_DEMO_QUICKSTART.md)
    |
    +-- Streamlit: src/cost_intel_ui/streamlit_app.py
            +-- separate cost-intelligence interface and demo data source

PARS modeling: synthetic source DuckDB --> per-run WBS workspace
    --> clean --> train/tune --> predict --> optional write-back
    (16 registered PARS MCP tools total; see eval/phoenix/run_pars_gap_eval.py
    for the deterministic tool-coverage eval)
```

**Boundaries:** The basket's local synthetic PPI calculation is not a
source-backed BLS escalation result. The PARS context panels expose only
read-only project and WBS tools; they do not authorize model training or
write-back. The FastMCP App renders inside an MCP host, which controls the
surrounding chat/navigation shell. The Streamlit interface is separate.
External requests depend on the chosen tool or LLM provider; the optional
live BLS API and remote model providers are not offline operations.

## Repository layout

```text
mcp_group_1/
├── README.md / QUICKSTART.md
├── pyproject.toml / uv.lock
├── server.json                   # MCP server identity metadata
├── .secrets.baseline              # detect-secrets allowlist
├── docs/
│   ├── ai_mcp_cost_intelligence_nnsa_spec_aligned.html  # UI reference
│   ├── PARS_UI_WIRING_SPEC.md
│   ├── LOCAL_INTEGRATION_STATUS.md
│   └── COMPETITION_DEMO_QUICKSTART.md  # cost-intel/CAEF demo release notes
├── eval/
│   ├── bls/                      # BLS conversation evals (runner, scripted agents)
│   ├── caef/                     # CAEF WBS classification held-out/inference evals
│   ├── phoenix/                  # PARS gap eval, Ask Sage agent eval harness
│   └── asksage/                  # Ask Sage endpoint tests
├── tools/                        # CAEF stadium build/eval scripts, demo-asset
│   │                              # packaging (prepare_caef_demo_assets.py,
│   │                              # check_competition_assets.py), BLS chat launcher
├── scripts/                      # repo-wide checks (manifest hashes, ruff hooks)
├── src/
│   ├── mcp_servers.json         # client registry and tool allowlists
│   ├── bls_mcp/                 # independent BLS server and snapshots
│   ├── pars_local_mcp/          # PARS server, hierarchy, WBS pipeline
│   │   ├── mcp/                 # PARS tool registration (16 tools)
│   │   ├── data/                # local synthetic data generators
│   │   └── wbs_port/            # WBS modeling pipeline (CAEF 2.0 classifier)
│   ├── cost_intel_app/          # embedded FastMCP basket + PARS panels + chat
│   │   ├── server.py
│   │   ├── basket_state.py
│   │   ├── pars_live.py
│   │   ├── chat_mcp_servers.json  # chat's own MCP server/tool allowlist
│   │   └── demo_assets/          # packaged CAEF model bundles (two large
│   │                              # files are Git LFS; see .gitattributes)
│   ├── cost_intel_ui/           # separate Streamlit interface
│   │   ├── streamlit_app.py
│   │   ├── session.py
│   │   └── fake_data.py
│   ├── portable_llm_mcp/        # optional LLM client and MCPHub (workspace member)
│   └── templates/example_server/ # reusable MCP server scaffold
└── tests/                       # shared integration tests
```

The canonical template source is `src/templates/example_server/`. Its Python
import namespace is `templates.example_server`, not a top-level
`example_server` package. Keep BLS code in `src/bls_mcp/mcp/` (not
`mcp_impl/`).

`server.json` is **server identity metadata**. `src/mcp_servers.json` is the
**client's runtime connection and tool-allowlist configuration**. They are
separate and should not be conflated.

## Approved BLS MCP tools

The server exposes 15 tools (listed in [QUICKSTART.md](QUICKSTART.md) step 4). The bundled LLM client's allowlist in `src/mcp_servers.json` includes these ten:

| Tool | Purpose | Data source | Example |
|---|---|---|---|
| `search_series` | Search imported series metadata | DuckDB snapshot | |
| `describe_series` | Describe a known series | DuckDB snapshot | |
| `get_series_hierarchy` | Show the sub-items nested beneath a series' code, to verify what an index includes | DuckDB snapshot | "What does the Sawmills index include?" |
| `get_cached_series_data` | Read previously imported observations | DuckDB snapshot | |
| `get_series_data` | Retrieve live BLS observations | External BLS API | |
| `get_bls_access_status` | Inspect access configuration | Local configuration | |
| `create_index_spec` | Create escalation index specifications | Local service | "Create an index for..." |
| `validate_index_spec` | Validate index specifications | Local service | "Validate this spec..." |
| `save_index_spec` | Save a validated specification so it can be calculated | Local service | |
| `calculate_index_from_bls` | Calculate a saved specification from snapshot values, with a ledger | DuckDB snapshot | "Escalate this basket from 2014 to 2026" |

**Choosing a series:** seeing the narrower sub-items nested beneath a parent code is the primary way to verify what an index includes. The server tells every client to call `get_series_hierarchy` before choosing a series for a component. For example, PPI "Sawmills" includes hardwood lumber, softwood lumber and wood chips, so a framing-lumber component is better matched by "Softwood lumber" or one of its own sub-items.

The local catalog may not contain every program BLS publishes. `search_series` accepts the program codes `pc`, `pd` and `wp` (PPI), `ci` (ECI), `cu` (CPI-U) and `oe` (OEWS), but a code returns matches only when the active snapshot was built with that program: the sample snapshot holds `pc` and `ci`, CPI needs a build with `--cu-manifest` (see `docs/bls/OPERATIONS.md` and `docs/bls/cu-ingestion.md`), and `oe` is accepted ahead of OEWS ingestion. Some catalog series may also lack cached observations. A successful `get_bls_access_status` result does not guarantee live BLS API connectivity.

## CMD and the virtual environment

This section and the ones after it are for developing in this repository on Windows; they are not needed to build the database or run the server. Those developer commands use Command Prompt (CMD), not PowerShell, and assume the repository's `.venv` is active.

Open the repository in VS Code using its **Command Prompt** integrated terminal. `.vscode/settings.json` chooses CMD as the default terminal and points the Python extension to `.venv\Scripts\python.exe`. Open a new terminal after opening the folder; verify the interpreter:

```cmd
cd /d %USERPROFILE%\Software\GitLocal\mcp_group_1
python -c "import sys; print(sys.executable)"
```

The output should end in `mcp_group_1\.venv\Scripts\python.exe`. If the interpreter is wrong, select `.venv\Scripts\python.exe` using **Python: Select Interpreter**, then reopen the integrated terminal. For a standalone CMD window (not opened inside VS Code), activation is not automatic:

```cmd
cd /d %USERPROFILE%\Software\GitLocal\mcp_group_1
call .venv\Scripts\activate.bat
```

Do not activate the environment again if your CMD prompt already shows the active project environment.

If `.venv` has not been created, use the approved dependency workflow, such as `uv sync --offline --locked` when all dependencies are cached. Dependency synchronization may change local environment files; `--offline` prevents package downloads.

## Configuration and `.env` files

The root `.env.example` is a safe starting point: its BLS API key and
network-fetch user agent are intentionally **commented out**. No BLS API key,
cloud credential, or user agent is required to build the sample snapshot or
use the snapshot-backed tools. To test
HTTP MCP locally, uncomment the `MCP_TRANSPORT`, `MCP_HOST`, and `MCP_PORT`
settings. Do not set `DATABRICKS_APP_PORT` or `PORT` for this local workflow;
those platform variables override the HTTP port/transport.

Keep configuration in two ignored local files: root `.env` for BLS settings and `src/portable_llm_mcp/.env` for the model/client settings. Never commit them or print their secret contents. The client `.env` should include:

```dotenv
MCP_SERVERS_FILE=src/mcp_servers.json
LLM_PROVIDER=ollama
LLM_BASE_URL=http://127.0.0.1:11434/v1
LLM_CHAT_MODEL=your-installed-tool-capable-model
```

Use your actual installed Ollama model name. In VS Code, `UV_ENV_FILE` and `MCP_SERVERS_FILE` are set for newly opened CMD terminals by `.vscode/settings.json`. In an **external CMD window**, run these once:

```cmd
set "UV_ENV_FILE=./.env ./src/portable_llm_mcp/.env"
set "MCP_SERVERS_FILE=src/mcp_servers.json"
```

**Activating `.venv` does not automatically load `.env` files.** Our `uv run` client commands below use the already-existing project environment and load both private files. Ordinary `python` commands for tests and linting do not need that `.env` loading. The second `.env` file overrides duplicate names from the first; shell environment variables take precedence. The `UV_ENV_FILE` setting uses space-separated paths supported by uv.

## Run MCP and LLM locally

From the repository root, in CMD with `.venv` active:

```cmd
uv run --offline --no-sync -- python src/portable_llm_mcp/examples/check_mcp.py
```

This lists available MCP tools without making an LLM request. Then, with your LLM configured:

```cmd
uv run --offline --no-sync -- python src/portable_llm_mcp/examples/run_agent.py "Use bls_server__search_series to find a locally imported PPI series and describe it. Do not call the live BLS API."
```

To launch the stdio BLS server manually for another MCP-aware client:

```cmd
uv run bls-server
```

The stdio server may not display a shell prompt or HTTP address; an MCP client normally launches it as a subprocess.

### Poe shortcuts

After `uv sync --group dev`, run these from the repository root (with `.venv` activated):

```cmd
poe sample-snapshot
poe verify
poe launch
poe test
poe lint
poe format-check
poe manifest-check
poe mcp-check
poe agent "Use bls_server__get_bls_access_status and explain the result. Do not retrieve live observations."
```

`poe launch` defaults to the stdio MCP server, but honors the transport
configuration in the root `.env`. In stdio mode it may not print a URL or
return a shell prompt. `poe mcp-check` and `poe agent` use the same environment variables described above (`UV_ENV_FILE` and `MCP_SERVERS_FILE`); configure them before running these shortcuts. Other existing tasks include `poe format`, `poe test-cov`, `poe test-live` (may contact BLS), and `poe check`.

`poe check` runs `lint`, `format-check`, `typecheck`, `pyright-check`,
`manifest-check`, and `test`
in that order. `manifest-check` confirms that every checksum-pinned data file
matches its manifest, hashing the bytes Git stores; `poe manifest-fix` rewrites
the recorded hashes after a deliberate change to a pinned file. It prints a labeled status for each step and stops on the first
failure with the task name, exit code, and a suggested follow-up command. For
example, if Ruff reports files that would be reformatted, run
`uv run --locked poe format` and rerun `uv run --locked poe check`.
Individual tasks remain available through Poe for focused checks.

Pyright is scoped by `pyrightconfig.json` to `eval/bls` and `tests/evals` so
missing references in the evaluation harness fail before model runs. The rest
of the repository has existing Pyright diagnostics and is not yet gated. Run
`uv run --locked poe pyright-check` to inspect the scoped check. Install the
existing pre-commit hooks with `uv run --locked pre-commit install`; commits
then run Ruff auto-fix and formatting, followed by read-only Ruff lint,
format verification, mypy, scoped Pyright, manifest checks, and the existing
fast regression/TDD gates. The full suite remains `uv run --locked poe check`
(or `uv run --locked pre-commit run pytest-full --hook-type manual --all-files`).
If a hook reformats code, review and stage the changed files before committing.


### Tests and lint

```cmd
python -m pytest -q
python -m ruff check src tests
python -m ruff format --check .
```

Keep BLS-specific helpers such as `harness.py` under `src/bls_mcp/tests/`; portable-client tests under `src/portable_llm_mcp/tests/`; and shared integration/contract tests under root `tests/`. Do not introduce another `tests/tests` directory. Flat-file integration tests should point to `src/bls_mcp/docs/sample_data/` when those fixtures are present, **not** `docs/docs/sample_data/`.

## Creating another MCP server

1. Start from `src/templates/example_server/` and copy it into a newly named Python package.
2. Update its imports, tools/resources/prompts, tests, and entry point.
3. Add the new server as another named entry in `src/mcp_servers.json` with the minimum required tool permissions.
4. Verify registration and integration with `portable_llm_mcp` without changing BLS-specific code.

## Upstream and privacy policy

**Internal GitHub Enterprise origin (read/write):** `https://github.doe.gov/NNSA-MB-90/mcp_group_1.git`. Authorized contributors may push here.

**GSA template upstream (read-only):** `https://github.com/GSA-TTS/example-mcp-server.git`. Fetch/clone and adapt upstream improvements, but **never push branches, tags, or commits to GSA**.

The default developer commands are local-first. Accessing `127.0.0.1:11434` sends model requests to local Ollama. Using `get_series_data` sends selected BLS series, dates, and configured credentials to the BLS API; using a remote LLM/provider or remote MCP may send prompts or tool results to those services. `uv --offline` only controls dependency resolution; it does not prevent application traffic. Prompt instructions such as “do not call the live BLS API” are not an enforcement boundary: disable unauthorized tools in the registry or block egress when strict local-only execution is required.
