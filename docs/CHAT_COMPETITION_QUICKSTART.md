# NNSA Cost Intelligence Search: local setup and verification

This document covers the **Search** (optional chat) panel in the Cost Intelligence app. Search uses only explicitly allowed **read-only** MCP tools. It does not approve or edit a basket, and it cannot change basket weights.

It does not replace `README.md` or `QUICKSTART.md`. Read those first for the project overview and the main app launch.

## What was evaluated, and what was not

| Area | Status | Evidence |
|---|---|---|
| Standalone BLS server (stdio, original launch in `src/mcp_servers.json`) | Competition-evaluated | Original evaluation record |
| Standalone PARS server (stdio, original launch in `src/mcp_servers.json`) | Competition-evaluated | Original evaluation record |
| BLS over loopback HTTP (`http://127.0.0.1:8821/mcp`) | **New integration, not part of the original evaluation** | Search-specific configuration only |
| Search (chat) integration with its own manifest and per-call PARS databases | **New, not part of the original evaluation** | Integration tests and browser runs |
| Ask Sage connection from Search | **New, not part of the original evaluation** | Configured provider; no live Ask Sage evaluation has been run (NOT RUN) |
| Basket UI, workflow steps, collapsible panel, CSV download | **New, not part of the original evaluation** | UI tests and local browser-harness runs (formal browser acceptance NOT RUN) |

Do not describe the HTTP transport, the Search workflow, or the Ask Sage connection as covered by the original standalone BLS or PARS evaluations.

The standalone BLS and PARS servers are **frozen**. Search does not change their code, schemas, tool names, data, or launch configuration in `src/mcp_servers.json`.

## Repository state you will see

- **BLS sample snapshot (packaged).** The repository includes the activated demonstration BLS snapshot. Its three files are included in the repository: `data/local/snapshots/bls-sample_pc_ci.duckdb` (the database), `data/local/snapshots/active-snapshot.json` (the registry), and `data/local/snapshots/bls-sample_pc_ci.duckdb.validation.json` (its validation record). Standard demonstrations do not need to rebuild it. It is demonstration data, not evaluation data. Do not regenerate, deactivate, or overwrite it. See *Verify the snapshot is active* below.
- **PARS database.** `src/pars_local_mcp/data/wbs.duckdb` is git-ignored synthetic data. An earlier PARS startup regenerated it, so byte-for-byte equivalence with the evaluated version has **not been established**. Do not rebuild or replace it. Search never opens it for writing. Each Search call gets its own temporary PARS database (see below).
- **Chat PARS database from an earlier version.** `data/local/pars_chat.duckdb` is no longer used. You can delete it, but it is not needed.

## Configuration

### Dedicated chat manifest

Search reads its own manifest, `src/cost_intel_app/chat_mcp_servers.json`. It does **not** read `MCP_SERVERS_FILE`. That variable names the shared host manifest, which also lists write and network tools.

| Server | Transport | Where | Allowed tools |
|---|---|---|---|
| `bls_server` | Loopback HTTP | `http://127.0.0.1:8821/mcp` | `search_series`, `describe_series`, `get_series_hierarchy`, `get_cached_series_data` |
| `pars_mcp` | stdio | `uv run --no-sync python -m src.pars_local_mcp.server` | `list_projects`, `get_project_info`, WBS read tools |

Every allowed tool must be on the read-only list. `*`, write-back, training, and inference tools are refused. HTTP servers must use loopback addresses.

To override the manifest for one shell, set `COST_INTEL_CHAT_MCP_MANIFEST` to a repository-relative path. Do not set it in committed files.

### Model settings (`src/portable_llm_mcp/.env`)

Search reads `src/portable_llm_mcp/.env` at request time. It does not copy those values anywhere. Explicit process environment variables override the file. Values are never printed by the setup checks. Keep the file local and do not paste it into support logs.

Supported providers:
- `LLM_PROVIDER=ollama` with a loopback endpoint and `OLLAMA_NO_CLOUD=1`.
- `LLM_PROVIDER=asksage` (or the `openai` alias) with **only** the approved NNSA Ask Sage endpoint, `https://api.nnsa.asksage.ai/server/openai/v1`.

Other endpoints are refused. TLS certificate verification stays on. The `-gov` model-name suffix is **not** enforced by the chat code, because that check was removed at the project owner's request. The approved-endpoint check still applies. Confirm the model name against agency policy before use.

## Start the BLS chat service (loopback HTTP)

Search needs the BLS service running on loopback HTTP. Use the helper script from the repository root in a Windows CMD window:

```cmd
tools\start_bls_chat_http.cmd
```

The script runs the unmodified `bls_mcp` code. It sets `MCP_TRANSPORT=streamable-http`, binds `127.0.0.1` on port `8821`, sets `BLS_SNAPSHOT_REGISTRY_DIR=data\local\snapshots` so it does not depend on a local `.env` file, clears `PORT` and `DATABRICKS_APP_PORT`, keeps bytecode out of the source tree, and stores its specs database under `data\local`. It stops with a message if `data\local\snapshots\active-snapshot.json` is missing. It does not change the evaluated stdio launch.

Start this service **before** the application. Keep its window open while you use Search.

### Verify the snapshot is active

From the repository root, in CMD:

```cmd
.venv\Scripts\bls-data.exe current --registry-dir data\local\snapshots
```

The output is the active snapshot's path. It should end in `bls-sample_pc_ci.duckdb`. This command only reads the registry.

### Start the NNSA application

From the repository root, in a separate CMD window:

```cmd
.venv\Scripts\fastmcp.exe dev apps src\cost_intel_app\server.py:mcp --no-reload --host 127.0.0.1
```

The defaults are `--mcp-port 8000` and `--dev-port 8080`. If another program already uses 8080, add `--dev-port <free port>`. There is no `--port` option. The preview opens a browser window and loads the app bridge from the network, so the preview is not an offline deployment. The flags were confirmed from the command's `--help` output. The closeout check ran this command with `--mcp-port 8100 --dev-port 8180`: the dev UI returned HTTP 200 with its token, the MCP endpoint listed `ppi_basket` as the only model-visible tool, and the launch log showed the npm fetch. The browser-level acceptance of the screens is recorded in `docs/COMPETITION_KNOWN_ISSUES_AND_NEXT_STEPS.md`.

### Test Search with the configured provider

With the BLS service and the application running:

1. Open the app page and choose **Ask Cost Intelligence (optional chat)**.
2. Enter a question, for example *List the available PARS projects, then search the BLS catalog for steel series.*
3. Choose **Search**.
4. Expect an answer, plus a list of the MCP tools that ran (for example `pars_mcp__list_projects` and `bls_server__search_series`).

The chat card has three example buttons, **List PARS projects**, **WBS for proj_001**, and **Steel price series**. A button only fills the question box; it does not submit. Press **Search** to ask. Questions stay editable. The results below come from the closeout regression. They were not re-run for this document update. They are not a live Ask Sage evaluation and are not Phoenix-recorded.

- *List the available PARS projects.* Answers from `pars_mcp__list_projects`: proj_001 (34 WBS elements) and proj_002 (25).
- *Show the top-level WBS elements for proj_001.* Answers from `pars_mcp__get_wbs_by_level`: one level-1 element, `01`.
- *Search the BLS catalog for steel price series.* Answers from `bls_server__search_series`. The answer labels steel series as related, not exact, and says when the result was truncated.
- *Follow-up.* A follow-up question that asks how many projects there are, after the first example, returned `2 projects.` at closeout. This is accepted as a pass.

Fixed messages (the exact text the app shows; the model text is not used for these):

- **No permitted tool answered** (for example, the capital of France): *"I'm sorry, that information isn't available through the connected project and cost-data sources. I can help with available PARS project information, WBS details, and BLS price-index data."*
- **A request to change data** (for example, update, delete, approve, or save): *"Search is read-only. It cannot modify PARS records, WBS data, machine learning labels, basket weights, or approvals. I can help with available PARS project information, WBS details, and BLS price-index data."* No tool runs.
- **Provider or model failure:** *"Search could not complete. Check the configured model, LLM provider, model endpoint, and MCP server configuration."*
- **MCP server unavailable:** *"The MCP server '<name>' did not start or is not reachable. Check that its service is running and its local data is available. For BLS over localhost HTTP, see the chat quickstart."*

The provider and model come from `src\portable_llm_mcp\.env`. Nothing is shown from that file. With `LLM_PROVIDER=asksage`, the question and the tool results are sent to the approved Ask Sage endpoint. With `ollama`, they stay on the loopback model.

To check the unavailable path, stop the BLS service. Search then returns "The MCP server 'bls_server' did not start or is not reachable..." within a few seconds, and the basket still works. Browser-level verification status for each feature is recorded in `docs/COMPETITION_KNOWN_ISSUES_AND_NEXT_STEPS.md`.

### Rebuild the snapshot only if necessary

The packaged snapshot is the standard demonstration input. Rebuilding it with `uv run --locked poe sample-snapshot` publishes a new file with a new timestamp, so the tracked bytes change. Do that only when you intend to replace the packaged snapshot. Then stage the three files again deliberately. Do not rebuild it just to start the demonstration.

Check that it is up, from a second CMD window:

```cmd
curl -s -o nul -w "%{http_code}\n" http://127.0.0.1:8821/mcp
```

Any HTTP code other than `000` means the service is listening. `406` is normal for a plain GET. Stop the service with **Ctrl+C** in its window.

If the service is not running, Search fails within a few seconds with: *"The MCP server 'bls_server' did not start or is not reachable..."* The basket still works.

## Search behavior and limits

- **One previous turn.** A follow-up question sends the previous question (up to 1,000 characters) and the previous answer (up to 2,000 characters). A follow-up is answered from the previous answer only when that answer came from a successful tool result. Closing the chat, choosing a demo project in the basket, or loading PARS context clears this context. A new question after one of those actions does not see the old answer.
- **Grounded answers.** Answers use only successful MCP tool results. If no permitted tool answers a question, the fixed unsupported message is shown instead of model text. Partial answers state which part is unavailable.
- **Related versus exact.** A catalog search that finds no exact title returns related series, labelled as related. Titles are reproduced as the catalog returned them.
- **Result size.** The model sees each tool result up to 20,000 characters. A longer result is cut and marked with `[tool result truncated]`, and the answer says the list is incomplete. Narrow the question to see the rest.
- **Search scope.** The model is asked to search every catalog programme unless you name one, and to retry once with fewer core terms before it reports no match. This is an instruction to the model, not a guarantee; check the tool trace and the cited series IDs.
- **Per-call PARS database.** Each call creates a new temporary directory in the system temp area (outside the repository). It starts the PARS server against a fresh synthetic database in that directory, and deletes the directory afterward. Concurrent calls do not share a database. Neither the checkout's `wbs.duckdb` nor another call's data is touched.
- **Time limits.** A single tool call is limited to 60 seconds. The whole Search call is limited to 240 seconds. A timed-out call returns a message, not a hang.
- **Failure behavior.** If any configured MCP server is unavailable, Search returns an error and does not run a partial search. The basket is unaffected.
- **Tool trace.** The panel lists the MCP tools that actually ran.
- **Synthetic data.** PARS and BLS data here are synthetic or sample data. PARS dollar escalation is not claimed.

## Data egress

With Ollama, the loopback model receives the system prompt, the question, bounded previous context, tool schemas, and tool results. Nothing leaves the machine.

With Ask Sage, the same categories are sent over HTTPS to the approved endpoint, using the configured authentication. This includes tool results, which can contain PARS project records. Do not submit sensitive, controlled, or actual project data unless agency approval covers it. Retention and telemetry on the vendor side are governed by the service's policies, not by this package.

Local MCP servers receive tool arguments. Stdio server processes may have their own I/O, so review them separately.

## Verify from Windows CMD (existing `.venv`)

Offline checks, no network:

```cmd
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider src\cost_intel_app\tests\test_chat_bridge.py
.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider src\portable_llm_mcp\tests
.venv\Scripts\python.exe -m ruff check src\cost_intel_app\chat_bridge.py src\cost_intel_app\tests\test_chat_bridge.py src\portable_llm_mcp
.venv\Scripts\python.exe -m ruff format --check src\cost_intel_app\chat_bridge.py src\cost_intel_app\tests\test_chat_bridge.py src\portable_llm_mcp
git diff --check
git status --short
```

Configuration check, without printing keys:

```cmd
python -c "import sys; sys.path.insert(0,'src'); from cost_intel_app.chat_bridge import CHAT_MANIFEST, _chat_environment; e=_chat_environment(); print('Provider:', e.get('LLM_PROVIDER','ollama')); print('Manifest:', CHAT_MANIFEST.name)"
```

The commands in this section were not re-run for this document update. The BLS service responded at closeout (HTTP 406 to a plain GET at `http://127.0.0.1:8821/mcp`).

A live Search needs the BLS service running (above) and the configured model available. A live Ask Sage check sends data to the approved endpoint. Run it only when that is approved.

Do not run the full `src/cost_intel_app/tests` suite against the checkout unless you have checked that it does not rebuild protected data. Some older UI tests start the PARS server.
