# PARS MCP — Work Breakdown Structure Classification and Hierarchy Query

Standalone MCP server for WBS (Work Breakdown Structure) classification and hierarchical querying using a hierarchical SGD classifier trained through the pipeline tools.

## Overview

**PARS MCP** provides sixteen tools for:
- **ML Classification**: Predict WBS hierarchy levels (2–8) from titles using TF-IDF + hiClass + SGD
- **Model Training**: Train/retrain classifiers with hyperparameter tuning through the pipeline tools
- **Hierarchy Navigation**: Query WBS structure, search by pattern/level, get ancestor lineage
- **Database Inspection**: Inspect DuckDB schema and table metadata

All operations use **synthetic stadium and sports-venue capital project data** suitable for testing and development. The WBS hierarchy labels are retained from the CAEF reference; project names, titles, and costs are fictional.

## Installation

From the repository root with `uv`:

```cmd
uv sync --locked
```

Dependencies include:
- `fastmcp>=3.2.0` — MCP server framework
- `scikit-learn`, `hiclass`, `mlflow` — ML pipeline
- `duckdb`, `polars`, `pandas` — Data layer
- `joblib`, `numpy` — ML utilities

## Quick Start

### Launch the Server

```cmd
python -m pars_local_mcp.mcp.server
```

The chat client starts this server from its entry in `src/mcp_servers.json`. See [Use the tools from the chat client](#use-the-tools-from-the-chat-client).

### Use the tools from the chat client

The chat client in `src/portable_llm_mcp` starts `pars_mcp` from `src/mcp_servers.json`, gives the tool list to the configured LLM, and runs the tool calls the model asks for. It does not use Claude Code.

One-time setup:

1. Run `uv sync --locked` from the repository root (see Installation).
2. Check `src\portable_llm_mcp\.env`. If it is missing, copy `.env.example` to it. Select one provider and set its values there. Keep API keys only in this file. Do not paste them into chat or commit them.

The client starts the servers listed in its registry file. To exercise only PARS,
create a local copy of `src/mcp_servers.json` with only the `pars_mcp` entry.
Do not edit the shared registry solely for this test.

Each Command Prompt window:

```cmd
cd /d C:\path\to\mcp_group_1
set "UV_ENV_FILE=./.env ./src/portable_llm_mcp/.env"
set "MCP_SERVERS_FILE=%USERPROFILE%\pars_mcp_servers.json"
```

Check tool discovery (no LLM call):

```cmd
uv run --offline --no-sync -- python src/portable_llm_mcp/examples/check_mcp.py
```

The output should list the `pars_mcp__` tools, such as `pars_mcp__list_projects`.

Ask the model to use a PARS tool:

```cmd
uv run --offline --no-sync -- python src/portable_llm_mcp/examples/run_agent.py "Use pars_mcp__list_projects to list the projects. Give each project's ID and name."
```

Expected: synthetic stadium capital projects. The startup query database uses `proj_001` and `proj_002`; the larger generated source uses numeric PARS IDs.

Notes:

- The configured provider receives the prompt, the tool descriptions, and the tool results. Use only a provider you are authorized to use.
- `tune_and_train_wbs` and `run_wbs_pipeline` are slow with the defaults. Pass `n_iter=2`, `cv_folds=3`, `n_jobs=1` for a quick run.
- If a run fails with a configuration error, check that `UV_ENV_FILE` and `MCP_SERVERS_FILE` are set in the current window.

### Use the server from Python

The tools are an MCP interface. Calling the functions in `src/pars_local_mcp/wbs` directly needs the model signing key, which the server keeps outside the model directory. Use an MCP client, as shown above.

## Tools Reference

PARS exposes 16 MCP tools in two groups. An MCP client sees each one as `pars_mcp__<name>`. Project IDs match ignoring case, so call `list_projects` first.

### Project and hierarchy tools (read-only)

| Tool | Arguments | Returns |
|---|---|---|
| `list_projects` | none | projects with ID, name, element count, and hierarchy depth |
| `get_project_info` | `project_id` | one project's metadata |
| `search_wbs` | `project_id`, `wbs_pattern` (SQL LIKE, for example `01.%`), `min_level`, `max_level` (1 to 8) | matching elements |
| `get_wbs_hierarchy` | `project_id`, `wbs_code` | one element and its immediate children |
| `get_wbs_lineage` | `project_id`, `wbs_code` | the element's ancestors, up to the root |
| `get_leaf_nodes` | `project_id` | leaf elements |
| `get_wbs_by_level` | `project_id`, `level` (1 to 8) | elements at one level |

The project tools do not paginate yet. A large project returns every match.

### WBS pipeline tools

| Tool | Arguments | Notes |
|---|---|---|
| `validate_wbs_inputs` | none | read-only check of the source database; returns counts and problems |
| `clean_wbs_data` | `run_id` (optional) | creates or reuses a run and runs the cleaning stage |
| `tune_and_train_wbs` | `run_id`, `n_iter` (default 10, max 100), `cv_folds` (default 3, max 10), `n_jobs` (default 4; -1 or 1 to 8), `search_seed`, `split_seed` | slow: the search takes a long time at the defaults |
| `predict_wbs` | `run_id`, `model_variant` (`untuned` or `tuned`) | predicts levels 2 to 8 for every source row |
| `write_back_wbs` | `run_id` | writes predictions back and exports parquet |
| `run_wbs_pipeline` | `run_id` (optional), the same search arguments as `tune_and_train_wbs`, `model_variant` | runs clean, tune and train, predict, and write back |
| `get_wbs_run_status` | `run_id` | status of each stage in a run |
| `get_wbs_project_descriptions` | `limit` (1 to 500, default 20) | read-only; synthetic source only |
| `get_wbs_rows` | `limit` (1 to 500, default 20) | read-only; synthetic source only |

The pipeline tools write files under the run directory. The read tools return rows only when the source is documented as synthetic. For a quick pipeline run, pass `n_iter=2`, `cv_folds=3`, `n_jobs=1`.

## Data and Configuration

### Fake Data Directory

Located at `src/pars_local_mcp/data/`:

- `CAEF 2.0 Standard WBS.xlsx` — Real CAEF 2.0 hierarchy reference (837 elements)

### Setup: build the stadium WBS source database

`mock_pars_full.duckdb` is the source database for the WBS pipeline tools (`validate_wbs_inputs`, `clean_wbs_data`, `run_wbs_pipeline`, `get_wbs_rows`, `get_wbs_project_descriptions`). It is gitignored, so a fresh checkout must build it once (and rebuild it after generator changes):

```bash
uv run python -m pars_local_mcp.data.generate_full_mock
```

Until it exists, those tools report that the source database is missing.

### Environment Configuration

Set via `.env` file or environment variables:

- `DATABASE_PATH` — synthetic query database (default: `src/pars_local_mcp/data/wbs.duckdb`)
- `WBS_SOURCE_DB` — large synthetic PARS source database (default: `src/pars_local_mcp/data/mock_pars_full.duckdb`)
- `MODEL_DIR` — trained model output directory
- `WBS_RUNS_DIR` — per-run pipeline artifacts
- `MODEL_SIGNING_KEY_PATH` — signing key file (outside the model directory)

The default database paths point to local synthetic data. Override them only with
paths you control. The generator deliberately refuses to write the full mock
outside its own data directory.

## Training Workflow

The WBS pipeline runs through five MCP tools, in order. Each run has its own directory and a `run_manifest.json` that records each stage's status.

1. `validate_wbs_inputs` checks the source database against the input contract. It reads only.
2. `clean_wbs_data` concatenates and cleans the labelled sample and the full source table. It creates a new run unless you pass a `run_id`.
3. `tune_and_train_wbs(run_id, n_iter=10, cv_folds=3, n_jobs=4, search_seed, split_seed)` splits the labelled data, trains an untuned model, runs a randomized search, and saves signed untuned and tuned bundles.
4. `predict_wbs(run_id, model_variant="untuned")` predicts level_2 to level_8 for every source row.
5. `write_back_wbs(run_id)` writes the predictions back, exports them to parquet, and reads the export back to check it.

`run_wbs_pipeline` runs stages 2 to 5 in one call. `get_wbs_run_status` shows where a run stands.

The bundled source is synthetic dummy data. Its metrics show that the pipeline runs, not how well the model performs.

## ML Pipeline Details

- **Features:** TF-IDF over the cleaned element text, which is the chain of ancestor titles.
- **Model:** a hierarchical classifier (hiclass `LocalClassifierPerParentNode`) around `SGDClassifier(max_iter=5000, random_state=42)`.
- **Labels:** one integer code per level. Each level is offset past the levels above it, so a code always names one label at one depth.
- **Split:** a stratified split by title (20% test). The same title never appears on both sides.
- **Search:** `RandomizedSearchCV` over the source parameter grid, scored by hiclass F1 on title-grouped folds.
- **Signing:** bundles are signed with the model signing key. A bundle whose signature or checksum fails is refused before it is loaded.

## Testing

To run the package-local regression suite from the repository root:

```cmd
pytest -q src/pars_local_mcp/tests -m "not slow and not live"
```

The suite covers MCP tool registration, query/storage safety, synthetic data
contracts, WBS hierarchy behavior, and pipeline utilities. The slow model
training and external/live tests are opt-in.

To check tool discovery locally, use the MCP client smoke tests rather than
starting a second background server:

```cmd
pytest -q src/pars_local_mcp/tests/mcp/test_mcp_server.py
```

## Troubleshooting

### ModuleNotFoundError: No module named 'fastmcp'

Run `uv sync --locked` from the repository root to install dependencies.

### FileNotFoundError: DuckDB database not found

Ensure `DATABASE_PATH` and `WBS_SOURCE_DB` point to the intended local databases. Run `python -m pars_local_mcp.data.generate_full_mock` to recreate the stadium-themed source mock.

## Architecture

```
User/Client
    |
    v
FastMCP Server (mcp/server.py)
    |
    +-- Query Tools (search_wbs, list_projects)
    |       |
    |       +-- storage.queries (PARSStore)
    |
```

## References

- [PARS MCP Status](../../docs/PARS_MCP_STATUS.md) — Current implementation status
- [PARS MCP Train/Tune/Predict Guide](../../docs/PARS_MCP_TRAIN_TUNE_PREDICT.md) — Step-by-step workflow examples
- [Root README](../../README.md) — Repository-level documentation
