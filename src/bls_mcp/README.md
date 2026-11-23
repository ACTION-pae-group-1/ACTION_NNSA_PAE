# BLS Escalation Index MCP server

`bls_mcp` is the first operational MCP server in `mcp_group_1`. It exposes local BLS series metadata and cached observations, optional live BLS retrieval, and escalation-index specification tools.

## Tools

| Tool | Purpose | Source |
|---|---|---|
| `search_series` | Search imported series metadata | DuckDB snapshot |
| `describe_series` | Retrieve metadata for a series | DuckDB snapshot |
| `get_series_hierarchy` | Show the sub-items nested beneath a series' code, to verify what it includes | DuckDB snapshot |
| `get_cached_series_data` | Read cached historical observations | DuckDB snapshot |
| `get_series_data` | Retrieve live observations | External BLS API |
| `get_bls_access_status` | Inspect BLS API key configuration | Local configuration |
| `create_index_spec` | Create an escalation index specification | Local service |
| `validate_index_spec` | Validate an index specification | Local service |

`get_bls_access_status` can report that a key is configured without proving that BLS is reachable. A series may appear in the catalog but lack stored observations. The current imported metadata focuses on PPI and ECI; it does not yet provide universal CPI discovery.

## Development (Windows CMD)

Open the repository in VS Code's **Command Prompt** terminal. Its Python extension should activate `.venv` automatically. In a standalone CMD window:

```cmd
cd /d %USERPROFILE%\Software\GitLocal\mcp_group_1
call .venv\Scripts\activate.bat
```

Run the server directly, using the active environment:

```cmd
python -m bls_mcp.app
```

Normally you do **not** need to start it manually: the client starts the stdio server using `src/mcp_servers.json`.

For MCP tool discovery from the repository root, the two private `.env` files must be configured. New VS Code CMD terminals get their locations from `.vscode/settings.json`; a standalone CMD session can use:

```cmd
set "UV_ENV_FILE=./.env ./src/portable_llm_mcp/.env"
set "MCP_SERVERS_FILE=src/mcp_servers.json"
uv run --offline --no-sync -- python src/portable_llm_mcp/examples/check_mcp.py
```

## Tests and project structure

Keep BLS implementation under `src/bls_mcp/mcp/` and BLS-owned tests and fixtures under `src/bls_mcp/tests/`, including `harness.py`. Shared end-to-end integration tests can live under the repository's root `tests/integration/` directory. The standard BLS sample-data location is `src/bls_mcp/docs/sample_data/` where fixtures are included; do not introduce `docs/docs/`.

From the repository root with `.venv` active:

```cmd
python -m pytest -q
python -m ruff check src tests
python -m ruff format --check .
```

## Privacy and upstream

Local catalog and cached-observation tools read the active DuckDB snapshot without needing a live BLS HTTP request. The live data tool transmits selected series/year data and the configured BLS registration key to the external BLS API. The local Ollama workflow uses localhost; remote LLM providers are a separate, approved-data-flow decision.

The internal `github.doe.gov/NNSA-MB-90/mcp_group_1` repository is the authorized push destination. The GSA template upstream at `github.com/GSA-TTS/example-mcp-server` is fetch-only and must never receive pushes from this project.

See [../../QUICKSTART.md](../../QUICKSTART.md) for the end-to-end client workflow.
