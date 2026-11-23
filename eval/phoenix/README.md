# PARS MCP Evaluation Harness

This directory contains the LLM-as-judge evaluation harness for the PARS MCP server (Work Breakdown Structure classification and hierarchy querying).

## Overview

The evaluation harness measures how well an LLM agent with no other context can use the PARS MCP tools to answer realistic WBS queries. It consists of:

- **Dataset** (`pars-eval-0`: 25 queries, frozen; `pars-eval-1`: 60 queries)
- **Agent** (the portable `MCPAgent` from `src/portable_llm_mcp`, which launches the PARS MCP server over stdio and uses only its seven read-only tools)
- **Judges** (LLM-as-judge evaluators that score correctness and relevance)
- **System Prompts** (two versions: basic and scoped)
- **Tracing** (Phoenix when a local server is reachable, otherwise a local JSONL file)

Every model call (agent and judges) goes through the approved portable client.
Only Ask Sage -gov models and local Ollama are allowed; public Anthropic and OpenAI
endpoints are refused when the configuration loads. No LangChain is used, and
`tests/test_approved_imports.py` enforces that.

## Directory Structure

```
eval/phoenix/
├── agent.py                          # PARSAgent (portable MCPAgent + MCPHub)
├── llm_endpoint.py                   # Approved-endpoint settings and judge client
├── tracing.py                        # Phoenix tracing with JSONL fallback
├── create_dataset.py                 # CLI: upload CSV to a local Phoenix
├── run_experiment.py                 # CLI: run evaluation experiments
├── datasets.yaml                     # Dataset registry
├── judges/                           # LLM-as-judge evaluators
│   ├── __init__.py
│   ├── correctness_judge.py         # Match expected responses
│   └── relevance_judge.py           # Check in-scope answers
├── prompts/                          # System prompts
│   ├── system_prompt_v1.txt         # Basic analyst role
│   └── system_prompt_v2.txt         # + scope boundaries
├── tests/                            # Offline tests (everything mocked)
└── datasets/
    ├── pars-eval-0/                  # 25 questions (frozen)
    │   ├── evaluation.xml
    │   └── examples/pars-eval-0.csv
    └── pars-eval-1/                  # 60 questions (pars-eval-0 + 35)
        ├── evaluation.xml            # Category, expected tools, difficulty
        └── examples/pars-eval-1.csv  # query,responses
```

## Setup

### Install Dependencies

```bash
# From repository root
uv sync --group dev
```

LLM settings come from the portable client configuration (`LLM_PROVIDER`,
`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_CHAT_MODEL`); see
`src/portable_llm_mcp/README.md`. Optional:

```env
# Judge model; for Ask Sage it must be a -gov model
JUDGE_MODEL=gpt-5.4-gov

# Phoenix endpoint (must be a loopback address; default http://localhost:6006)
PHOENIX_ENDPOINT=http://localhost:6006
```

### Verify Installation

```bash
python eval/phoenix/create_dataset.py --list
python eval/phoenix/create_dataset.py --dataset-name pars-eval-1 --dry-run

# Offline tests (no network, no model calls), from the repository root
PYTHONPATH=src:. python -m pytest eval/phoenix/tests eval/phoenix/judges/tests -q -p no:phoenix
```

## Evaluation Workflow

> **Status (2026-11-19):** Phoenix recording is **BLOCKED**. The `arize-phoenix` server and the `phoenix.otel` tracing extra are not installed in `.venv`, so the command below does not start a server. The partial `pars-eval-1` run (10 of 60 cases) wrote JSONL fallback traces, not Phoenix traces. See `eval/caef/results/release-2026-11-19/FINAL_EVALUATION_REPORT.md`.

### Step 1: Start Phoenix (Optional)

Phoenix provides a UI for reviewing traces and results.

```bash
uv run arize-phoenix serve
```

Phoenix will be available at `http://localhost:6006`. If it is not running (or
cannot be imported), `run_experiment.py` writes one JSON object per span to
`results/<run_id>.traces.jsonl` instead and records the reason in the run's
metadata JSON under `tracing.fallback_reason`. Use `--no-phoenix` to skip Phoenix
entirely, or `--trace-jsonl PATH` to choose the file. Traces are never sent to a
non-loopback host.

### Step 2: Create Dataset in Phoenix (One-Time)

```bash
cd eval/phoenix
python create_dataset.py --dataset-name pars-eval-0
```

**Note**: If Phoenix is not available, use `--dry-run` to validate the CSV without uploading:

```bash
python create_dataset.py --dataset-name pars-eval-0 --dry-run
```

### Step 3: Run Evaluation Experiment

```bash
cd eval/phoenix
python run_experiment.py --dataset-name pars-eval-0
```

For v2 system prompt (with scope boundaries):

```bash
python run_experiment.py --dataset-name pars-eval-0 --system-prompt-version v2
```

Limit to N examples for faster iteration:

```bash
python run_experiment.py --dataset-name pars-eval-0 --max-examples 5
```

### Step 4: Review Results

Each run writes to `results/`:

- `<run_id>.csv`: one row per example and trial (see `COLUMNS` in
  `run_experiment.py`), including the agent and judge provider, endpoint host,
  and model, the tool calls, the latency, and both judge verdicts
- `<run_id>.json`: run metadata, summary metrics, and where the traces went
- `<run_id>.traces.jsonl`: span records, only when Phoenix was unavailable

In the Phoenix UI (if running):
- Navigate to `http://localhost:6006`
- View experiment traces
- Drill into failing examples
- Inspect agent tool calls and LLM responses

## PARS MCP Tools

The agent has access to 7 WBS hierarchy tools:

1. **list_projects()** — List all projects with metadata
2. **search_wbs()** — Search WBS elements by pattern, level range
3. **get_wbs_hierarchy()** — Get element and immediate children
4. **get_wbs_lineage()** — Get full parent chain (root to element)
5. **get_project_info()** — Get project metadata
6. **get_leaf_nodes()** — Find terminal elements
7. **get_wbs_by_level()** — Get all elements at specific level

## Dataset

All rows use synthetic data only (`proj_001` Project Alpha, 34 elements;
`proj_002` Project Beta, 25 elements; both 7 levels deep, from
`src/pars_local_mcp/storage/initialization.py`).

`pars-eval-0` (25 queries) is frozen because earlier results refer to it:

- **Discovery** (4 queries): List projects, get project info
- **Search** (6 queries): Pattern matching, level filtering
- **Navigation** (8 queries): Hierarchy relationships, parent chains
- **Complex Scenarios** (4 queries): Multi-step chains, comparisons
- **Edge Cases** (3 queries): Boundary conditions, non-leaf nodes

`pars-eval-1` (60 queries) is pars-eval-0 in its original order plus 35 more: discovery 8,
search 14, navigation 16, complex 11, edge cases 8, out of scope 3. The new rows
cover `proj_002`, cross-project comparisons, missing projects and elements, and
requests the v2 prompt should decline.

Known issue inherited from pars-eval-0: two rows ask about WBS code `02`
(the parent of `'02.01'` and the pattern `'02%'`), but neither project has a
`02` branch, so those reference answers are wrong for the synthetic data.

Expected answers describe what the agent *should* find, allowing for reasonable
formatting differences. They are reference answers, not human labels.

## System Prompts

### v1 (Basic)

The agent understands its domain (WBS analyst), tool names/signatures, and WBS code conventions. No explicit scope boundaries.

### v2 (Scoped)

v1 + explicit in-scope vs. out-of-scope guidance:
- **In scope**: Discovery, search, navigation
- **Out of scope**: Modifications, predictions, cost/schedule, execution

## Judges

### match_expected_response

Compares agent responses to ground truth. Returns `correct` or `incorrect`.

Tolerates:
- Formatting differences (extra whitespace, punctuation)
- Extra context (as long as key facts are correct)
- Different phrasing (same information, different words)

### check_answer_scope

Determines if the agent appropriately handled the query. Returns `within_scope` or `out_of_scope`.

## Performance Thresholds

For PARS (low-consequence tool for discovering and navigating WBS structures):

- **< 80% success**: Fix tools, improve error messages, re-evaluate
- **≥ 80% success**: Acceptable; document and deploy with caution
- **≥ 90% success**: High confidence; safe to deploy

Key metrics:
- **Scope accuracy** (within_scope rate) — should be ~100% for in-scope queries
- **Correctness** (correct rate) — should be ≥ 80%

## Troubleshooting

### Agent fails to initialize

Check that the PARS MCP server can be launched:

```bash
cd /path/to/repo
python -m src.pars_local_mcp.mcp.server
```

### Judge gives wrong scores

1. Review 5-10 failing examples manually
2. Check judge prompt in `judges/correctness_judge.py`
3. Check if expected answers in CSV are clear and accurate
4. Re-run with adjusted judge prompt

### Phoenix connection errors

The run continues with JSONL traces; the reason is printed at startup and
stored in the metadata JSON. In the current venv, `arize-phoenix` 20.6.0 fails
to import under Python 3.11.7 (`ValueError: mutable default ... boolean_names`),
so the JSONL fallback is what you will get there. For `create_dataset.py`, use
`--dry-run` to validate without Phoenix.

**2026-11-19 investigation:** `arize-phoenix` 20.27.0 and 21.0.0 both fix the
mutable-default bug (`field(default_factory=...)` instead of a bare
`MappingProxyType({})`), but both now require `fastmcp-slim>=4,<5`, which
conflicts with this repo's `fastmcp>=3.4.10,<4` pin (used by `bls_mcp`,
`pars_local_mcp`, and `cost_intel_app`). A real fix needs a project-wide
`fastmcp` 3→4 upgrade (and, transitively, `mcp` 1.x→2.x for
`portable_llm_mcp`), scoped as its own slice rather than a dependency bump —
confirmed the import surface (`Client`, `FastMCP`, `Context`, exceptions,
transports, `get_http_request`) and constructor signatures are compatible in
4.1.8/4.2.2, but a full `fastmcp>=4,<5` + `mcp>=2,<3` bump regressed 22 tests
across `bls_mcp` and `cost_intel_app` (tool-call dispatch returned empty/wrong
results under the new MCP SDK) when tried and reverted in this session. Until
that upgrade is scoped and done properly, the JSONL fallback above is the
supported path — it is not a workaround of last resort, it is correct
behavior per `tracing.py`'s own design.

## Common Modifications

### Add More Test Queries

Edit `datasets/pars-eval-0/examples/pars-eval-0.csv`:

```csv
query,responses
"Your new question","Expected answer description"
```

Re-run `create_dataset.py --dataset-name pars-eval-0` to upload.

### Adjust System Prompt

Edit `prompts/system_prompt_v1.txt` or `prompts/system_prompt_v2.txt`.

To test new prompts, add a `system_prompt_v3.txt` file, update `run_experiment.py` choices, and run:

```bash
python run_experiment.py --dataset-name pars-eval-0 --system-prompt-version v3
```

### Change Judge Criteria

Edit `judges/correctness_judge.py` or `judges/relevance_judge.py` to adjust the prompt template or scoring rubric.

## References

- [Phoenix Documentation](https://docs.arize.com/phoenix)
- [Portable LLM + MCP client](../../src/portable_llm_mcp/README.md)
- [PARS MCP README](../../src/pars_local_mcp/README.md)
