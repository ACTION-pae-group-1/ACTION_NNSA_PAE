# Multiple-MCP monorepo: audit and migration plan

Assessment: 2026-10-26. Reviewed the supplied Git-aware ZIP, without ignored
files, `.env*`, local database files, or `.git` history. This is a **multi-MCP
workspace**, not a BLS-only repository. Preserve `example_server` as the
reference implementation for creating new services.

## Roles to preserve

1. **Template** (`src/example_server`): a working, copyable FastMCP skeleton
   with one example tool, resource, prompt, configuration, and optional HTTP
   health routes. Templates are *not* production servers.
2. **Servers** (`src/bls_mcp`, later more packages): each owns its domain logic,
   MCP tool interfaces, tests, configuration and deployment entry point.
3. **Client/agent** (`src/portable_llm_mcp`): provider-neutral LLM adapter and
   MCPHub; connects to approved servers, discovers tools, and applies a strict
   per-server allowlist. No BLS-specific code belongs here.
4. **Repo orchestrator** (`mcp_servers.json`, root uv workspace, CI, docs):
   specifies which servers to launch without merging their implementations.

## Target filesystem layout (future stage, NOT applied in Phase 1)

```text
repo/
  pyproject.toml                    # Root uv workspace / dev tooling
  uv.lock
  mcp_servers.json                 # Approved server registry and allowlists
  templates/
    fastmcp-server/                # Self-contained, copyable example project
      pyproject.toml
      src/example_server/{app.py,tools/,resources/,prompts/,config.py,...}
      tests/
  servers/
    bls/                           # Independent uv workspace member
      pyproject.toml
      src/bls_mcp/{app.py,server.py,mcp_impl/,services/,...}
      tests/
    future-service/                # Copy the template, customize, join workspace
      pyproject.toml
      src/future_mcp/
      tests/
  clients/
    portable-llm-mcp/             # Independent workspace member
      pyproject.toml
      src/portable_llm_mcp/
      tests/
  tests/                           # Cross-server contract/integration checks
  deploy/                          # Server-specific deployment settings and reusable recipes
  docs/
```

The template lives under `templates/`, **not** in `[tool.uv.workspace].members`;
copying it creates a package under `servers/`. The active server packages and
the client become workspace members, each with its own wheel/entry point.
Maintain one root `uv.lock` for the installed workspace. Never make a generic
"mega MCP server" that mixes all business logic into a single process.

## Confirmed issues in the supplied snapshot

- Root metadata calls the project `example-server`, but `example-server` and
  `bls-server` entry points both launch BLS. The root Hatch wheel included BLS
  *and* the client, although the client also declared its own uv workspace
  package. Package ownership was overlapping.
- The original setuptools configuration in `src/portable_llm_mcp/pyproject.toml`
  produced a 1.2-KB wheel containing metadata but **no Python source** in an
  offline build. The workspace client needs an explicit package-directory map.
- `mcp_servers.json` ran BLS by its filesystem `server.py` rather than the
  canonical `bls_mcp.app` entry point. Both client examples used a malformed
  `Path("..", "/mcp_servers.json")`, which discards the `..` path component.
- The uploaded template lacked `tools/example_tool.py`, `prompts/example.py`,
  and `resources/example.py` although its three aggregators import them. This
  made the template import fail. Phase 1 restores harmless local examples.
- Tests were spread across three locations; the original root pytest config
  collected just `tests/`. `tests/test_server.py` imported the nonexistent
  `bls_mcp.mcp.*` namespace. Root CI also ran only root tests.
- Current Dockerfile, Cloud Foundry manifest, Databricks and IBM deployment
  recipes assume `example_server` is the deployable server. These are useful
  template *recipes*, not BLS deployment configs. Retarget them explicitly per
  actual deployment, do not delete the reusable recipes.
- Root dependencies duplicate `httpx`, include several dev tools as runtime
  dependencies, and are not consistent with `requirements.txt`. Resolve this
  while migrating to per-package pyprojects and updating `uv.lock`.

## Phase 1: safe baseline patch (accompanying this plan)

- Keep `example_server`; restore one local-only sample tool, resource, prompt,
  and add a template registration test.
- Keep BLS and the client logically separate, fix portable package wheel and
  root wheel ownership, correct BLS local manifest entry point and client
  manifest-path lookup.
- Configure root pytest/CI to collect every active test suite, excluding live
  requests by default; repair stale BLS imports.
- Document multi-server intent, current boundaries, privacy and transport.

**Intentionally unchanged:** existing BLS MCP tool names/schema and services,
model defaults, tool allowlist, remote provider support, database behavior,
existing deployment recipes, root dependency metadata, and `uv.lock`.

## Phase 2: extract packages into the workspace

- Move `src/example_server` to `templates/fastmcp-server/src/example_server`;
  add a minimal standalone `pyproject.toml` and runnable smoke tests. Ensure a
  new service can be copied/renamed without editing the existing BLS package.
- Move BLS to `servers/bls/src/bls_mcp`, give it `servers/bls/pyproject.toml`
  and `bls-server`; move client to `clients/portable-llm-mcp/src/...` with its
  own pyproject. Convert the repository root to uv workspace orchestration.
- Define workspace dependencies and dev groups once and regenerate `uv.lock`
  offline if the cache is sufficient, otherwise only with explicit approval
  for dependency downloads. Keep a compatibility entry point if required.
- Retarget launcher config and tests. Ensure `uv run --package bls-mcp ...`
  can discover tools and run with no model or external API requests.

## Phase 3: new-server onboarding and CI

Create a second local-only sample server from the template. Show that it can
be installed independently, starts via stdio, and appears alongside BLS in
`mcp_servers.json` with an explicit `allowed_tools` subset. Test a collision
case where both servers expose the same native tool name: MCPHub already
qualifies names as `<server>__<tool>`.

Provide contract tests for each server: import/create, enumerate tools, check
stable schema/annotations, safe resource/prompt registration, and absence of
unauthorized egress during read-only smoke tests. Add a CI matrix over server
packages, plus one cross-server MCPHub integration test.

For small local models, default to a minimal read-only allowlist and expose
only workflow-relevant tools rather than the whole registry. Prefer improving
a specific tool schema over inventing another agent/orchestration layer.

## Phase 4: deployments (only on explicit target selection)

Treat IBM / Databricks / Cloud Foundry assets as deployment *templates* until
a specific service and environment is selected. Each live configuration must
name the targeted server package and transport, with explicit ports, network
boundaries, and secret injection. The template should not be the implicit
production server. No cloud build, upload, deployment or telemetry activation
is included in Phase 1.

## Verification and network/egress policy

Phase 1 changes write only local source files/docs; applying its patch does not
make external requests. Adding/restoring the example modules adds no network
calls; the echo tool simply returns its supplied string. Offline checks in the
review container can validate JSON/TOML syntax, Python parsing and selected
mocked tests; full FastMCP tests cannot run there because `fastmcp`/`mcp` and
Python 3.11 are unavailable, and nothing was downloaded for review.

Commands/operators have different possible egress:

- `uv sync`: may contact dependency registries and download packages; not a
  repository upload operation. Use pre-provisioned or offline cache to avoid.
- `check_mcp.py`: launches the approved stdio MCP service and enumerates local
  tools; BLS startup opens the active DuckDB snapshot, but does not perform a
  live BLS query merely to list tools.
- `run_agent.py`: sends prompts, exposed tool definitions and tool results to
  the configured LLM endpoint. Default Ollama is localhost; setting a remote
  model endpoint sends that content to a third party, so do not switch without
  explicit user approval and retention review.
- BLS retrieval tools, **when invoked**, call `https://api.bls.gov` with
  relevant series IDs, years and any configured API key. The opt-in BLS
  flat-file downloader calls `https://download.bls.gov` when run.

Do not put `.env`, tokens, database files or user data in tracked config or
in an MCP template. The reviewed ZIP intentionally omitted `.env*` and ignored
files; secrets embedded in other source files are not automatically detected.
