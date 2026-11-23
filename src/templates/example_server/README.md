# Reusable MCP server template

`src/templates/example_server/` is the canonical scaffold for creating additional independent MCP servers in `mcp_group_1`. It is **not** the operational BLS server and should not be registered as `bls_server`.

## Create the next server

1. Copy the template to a new package with a unique name under `src/`.
2. Rename the Python package and imports so they no longer refer to `templates.example_server`.
3. Replace example tools, resources, prompts, and configuration with the new server's implementation.
4. Add component-owned tests alongside the new server and shared integration tests under root `tests/` as needed.
5. Register the new server under a unique name in `src/mcp_servers.json` with a minimal `allowed_tools` list.

The template's in-repository Python import path is `templates.example_server`, not a top-level `example_server` package. Keep the existing BLS server under `src/bls_mcp/`.

## Windows CMD workflow

From the repository root with its `.venv` active:

```cmd
cd /d %USERPROFILE%\Software\GitLocal\mcp_group_1
python -m pytest -q
python -m ruff check src tests
python -m ruff format --check .
```

The repository's VS Code settings select CMD and activate `.venv` automatically for new integrated terminals. In a standalone CMD window, activate once with `call .venv\Scripts\activate.bat`.

## Upstream policy

The GSA MCP example project (`https://github.com/GSA-TTS/example-mcp-server.git`) is a **fetch-only** reference source. **Never push** this project to GSA. Authorized pushes may go to the internal repository at `https://github.doe.gov/NNSA-MB-90/mcp_group_1.git`.
