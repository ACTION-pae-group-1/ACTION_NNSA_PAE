# Evaluations

**Built so far:** two harnesses cover the two eval styles in this repo.

- [`eval/bls/`](bls/README.md) holds conversation evals for the
  BLS escalation server: two deterministic cases (a known basket, and a mixed
  materials-plus-labor basket that exercises quarterly-to-annual alignment) and
  an open-ended negotiated one, graded programmatically on process, accuracy,
  answer format and guardrails. Run `uv run --locked poe eval-selftest` (no
  model needed). Agent runs are recorded under `eval/bls/results/runs/`.
- [`eval/phoenix/`](phoenix/README.md) is the LLM-as-judge Phoenix harness for
  the PARS MCP server (`PARSAgent`, datasets `pars-eval-0`/`pars-eval-1`).
  It launches the server over stdio through the portable MCP agent and scores
  answers with a correctness judge and a scope judge.

[`eval/asksage/`](asksage/README.md) contains standalone Ask Sage smoke/eval
scripts against the live approved endpoint.

This template does **not** include an evaluation harness — but building one is
the single best way to know whether your MCP server actually works well.

## Why evaluate?

The quality of an MCP server is **not** how many tools it has — it's how well an
LLM with no other context can use those tools (their names, schemas, docstrings,
and return shapes) to answer realistic, difficult questions. An eval harness
measures exactly that and shows you *where* to fix things (tool schema, docstring,
or system prompt).

## How to build one

Use the **`mcp-eval` skill** (`.claude/skills/mcp-eval/SKILL.md`, mirrored at
`.agents/skills/mcp-eval/`). It walks you through a reusable
[Arize Phoenix](https://docs.arize.com/phoenix) harness that:

1. Launches your MCP server over stdio and connects the repo's portable MCP
   agent to it (no LangChain).
2. Feeds the agent a dataset of natural-language questions with known answers.
3. Scores each answer with LLM-as-judge evaluators and logs traces to Phoenix.

The companion **`mcp-builder` skill** (`.claude/skills/mcp-builder/`) covers
Phase 4 — writing the 10 gold questions (`evaluation.xml`) that become the
harness's dataset.

## Actual `eval/phoenix/` layout

```
eval/phoenix/
├── agent.py            # PARSAgent — launches your server over stdio
├── create_dataset.py   # CLI: upload a CSV dataset to Phoenix
├── run_experiment.py   # CLI: run agent + judges against a dataset
├── llm_endpoint.py     # Approved-endpoint client (Ask Sage / Ollama) + judge runner
├── tracing.py          # OTLP to loopback Phoenix, JSONL fallback
├── datasets.yaml       # Dataset registry
├── judges/             # LLM-as-judge evaluators (correctness, scope)
├── prompts/            # Versioned agent system prompts (v1, v2)
├── datasets/<name>/    # evaluation.xml (source) + examples/<name>.csv
└── tests/              # harness tests (incl. the no-langchain import gate)
```

Add the eval-only dependencies to the `dev` dependency group in
`pyproject.toml` when you scaffold it (the skill lists the exact versions), then
`uv sync --group dev`.
