## Using Specialized Agents

This repository includes the specialized Claude Code agents defined in `.claude/agents/` (`README.md` there is an index, not an agent). Use these agents when appropriate:

### feature-builder Agent
**When to use:**
- Building one feature end to end, from plan to commit, with TDD and quality gates
- Work that already has a plan in `.claude/plans/`
- Features that touch both backend and frontend

**Examples:**
- "Build the feature described in .claude/plans/<feature>.md"
- "Add a backend endpoint and the form that calls it, with tests first"

The feature-builder asks for a plan and clarifies scope, then picks a feature-implementation skill (basic, fullstack, or parallel) to run TDD, quality checks, and a verification summary. Its output is a summary of changes and a readiness checklist. The next steps it names are `/code-review medium`, then a commit that passes the hooks.

### tdd-enforcer Agent
**When to use:**
- New features or functionality that need strict test-driven development
- New API endpoints or business logic
- New UI components or flows
- Any change that needs broad test coverage

**Examples:**
- "Add an endpoint that validates the request body and returns 422 on bad input, test first"
- "Implement a React form with validation, starting from failing component tests"

The tdd-enforcer follows red, green, refactor. It writes failing tests first, then the minimum code to pass them, then suggests refactors, and it will not write implementation before failing tests exist. It asks for 10+ component tests and 10+ backend tests per feature and 0-3 E2E tests. Its stack notes (FastAPI, React, Podman) and `[Project Name]` placeholders come from a template, so check them against this repo. It defines no separate report; its output is the test and code changes.

### slice-orchestrator Agent
**When to use:**
- A testable, independently deployable slice (feature, bug fix, refactor, or API change) that should go from TDD to commit in one run
- Work that needs the interrogator gate and the MinimumCD checks

**Examples:**
- "Implement the slice: add a result limit parameter to the search tool; success is green tests and an interrogator SATISFIED verdict"
- "Fix the bug where an empty query returns a 500, with a reproducing test first"

The slice-orchestrator runs six phases: TDD (red to green), an interrogator loop until SATISFIED, lint and type checks, a MinimumCD check (commits at most 500 lines, branch at most 48 hours old), the pre-commit gate, and commit and push to `feat/<slice>`. It forbids `--no-verify`. The file has no approval step before its push, so review the staged changes before letting it reach the push phase. Its output is per-phase status and the pushed branch.

### interrogator Agent
**When to use:**
- Before merging a significant or security-critical change
- Challenging a design, spec, or architecture decision before building it
- Probing a diff for hidden assumptions, dependencies, and failure modes

**Examples:**
- "Interrogate this diff for assumptions, dependencies, and potential failure modes"
- "Challenge this design: what happens with malformed input, and what are we assuming about upstream rate limits?"

The interrogator challenges assumptions, maps dependencies, tests boundaries and failure modes, and checks security and compliance. It assumes the tests are already green and does not do style review. Its output groups findings as Critical, High, Medium, or Low, each with remediation, and ends with `## FINAL VERDICT: SATISFIED` or `NOT SATISFIED`. SATISFIED requires every critical finding fixed or formally accepted. Its frontmatter grants Edit and Write, and its file does not forbid edits. Its `[Project Name]` placeholder is unfilled.

### code-reviewer Agent
**When to use:**
- Before committing or opening a PR, to catch bugs and correctness problems in pending changes
- A quick spot-check (low effort) or a deeper pass (high effort) on risky code
- Security-sensitive changes that need a thorough review

**Examples:**
- "Review my authentication changes"
- "Review my pending changes at high effort, with at most 10 findings"

The code-reviewer runs the `/code-review` skill at the effort level you choose (low, medium, high, xhigh, or max) and reports findings ranked by severity with suggested fixes. `--comment` posts inline PR comments, `--fix` applies non-complex fixes to the working tree, and `--max-findings` caps the count. Its rules say not to review uncommitted work on main, so use a feature branch.

### ontologist Agent
**When to use:**
- Modeling the entities and relationships behind software components or enterprise assets
- Defining classes, properties, and constraints for a data model or knowledge graph
- Checking a model against existing ontology files (`data/*.ttl`)

**Examples:**
- "Model the relationships between MCP tools, the data sources they wrap, and the capabilities they expose"
- "Check whether this entity model is consistent with the existing ontologies in data/"

The ontologist applies formal ontology principles (the file cites CCO and NIST AI RMF) in four steps: identify entities, define relationships, establish constraints, and verify alignment with existing ontologies. It defines no output format. Its frontmatter sets no tools or model, so confirm what it can use before relying on it.

### git-safety-constraint-agent Agent
**When to use:**
- Adding a new git safety pattern
- Repairing a known bypass in an existing git safety regex
- Validating a regex before merging a change to it

**Examples:**
- "Validate the pattern \bgit\s+add\b[^;&|]*(?:-f\b|--force\b): intent block force-add, action validate-only"
- "Repair the SKIP bypass in the git safety pattern, action implement-fix"

The git-safety-constraint-agent analyzes a regex for bypass vectors and false positives, challenges the enforcement layer, and runs bypass and legitimate-use tests. It edits files only with `implement-fix`; the default action is `validate-only`. The default target is `.claude/hooks/tool_input_preflight.py` in `git_policy_error`. Its output covers pattern analysis, an interrogation verdict (FIXABLE, NEEDS_REDESIGN, or REDESIGN_RECOMMENDED), validation results, and an implementation report when it edits. Its frontmatter sets `type: workflow-orchestrator` and no tools or model.

### mcp-builder Agent
**When to use:**
- Starting a new MCP server that wraps an external API
- Adding tools to a FastMCP server with validation, error handling, and audit logging
- The build step that comes before interrogation and evaluation

**Examples:**
- "Build a FastMCP server for the cost-intelligence API with search, details, and validation tools, with timeouts and audit logging"
- "Add a tool to the PARS server with input validation, and tests for the error cases"

The mcp-builder checks that you have API docs and credentials, then builds with FastMCP (Python): tests first for each tool, then the implementation, then format, lint, and type checks. It checks the server against a list covering validation, error messages, rate limits, audit logging, and composition tests. Its output is server code and tests. The file names the interrogator and mcp-eval as the next steps, not deployment.

### mcp-eval Agent
**When to use:**
- Measuring whether agents can finish realistic tasks with an MCP server's tools
- Building a Phoenix-based evaluation harness with LLM-as-judge scoring
- Deciding whether a server meets its success threshold

**Examples:**
- "Build an evaluation harness for the PARS MCP server: measure task success rate and tool accuracy across 20 tasks"
- "Evaluate the server's composition chains, with a judge rubric for task success"

The mcp-eval checks high-impact status first (GATE 0), then applies a pass bar: 80% by default and 90% for high-impact use cases. High-impact work also needs deterministic tests and expert review, and judge scores should be checked by hand on 5 to 10 runs. Its output is experiment results and a pass or iterate decision, with at most three iteration cycles before design review. Its consequence-tier table (75% to 98%) does not line up with the 80% default.

### mcp-workflow Agent
**When to use:**
- Taking an MCP server from concept to ship in one orchestrated run
- Running build, interrogation, evaluation, and quality gates in order
- When you want the phase gates enforced rather than run by hand

**Examples:**
- "Build an MCP server end to end for the cost-intelligence API, following the full workflow"
- "Run the MCP workflow for the new PARS tool set, starting with the high-impact check"

The mcp-workflow runs the phases in order: GATE 0 high-impact determination, build (mcp-builder), interrogation (must reach SATISFIED), evaluation (mcp-eval, against the GATE 0 threshold), quality gates (`uv run ruff format .`, `uv run ruff check .`, `uv run mypy --strict app`, `npm run type-check`), and compliance and deployment. Failures cycle back to an earlier phase. It defines no single report format. It also names `@high-impact-use-case-assessor`, which is not in `.claude/agents/`.

### minimumcd-agent Agent
**When to use:**
- Auditing a repo, pipeline, or workflow for MinimumCD (continuous delivery) compliance
- Checking trunk discipline, pipeline determinism, and deployability criteria
- Validating artifact immutability, environment parity, rollback readiness, and configuration separation

**Examples:**
- "Check our repo for MinimumCD compliance."
- "Validate whether our build artifacts are immutable."
- "Review our trunk-based development discipline."

The minimumcd-agent audits against the MinimumCD practices in four phases: branches and flow, pipeline determinism, deployability and artifacts, and rollback. It does not change business logic. Its output is a minimumcd_report (violations, severity, fixes), a pipeline_report (determinism findings, flaky tests, risk areas), and a deployability_report. Its frontmatter name is `minimumcd-agent`, but the file is `agentic-minimum-cd-guru.md` and its own examples use that file name.

### token-minimizer Agent
**When to use:**
- Quick factual lookups (config values, file locations, function names)
- Targeted searches where you want the answer, not the exploration
- Small, well-scoped edits where token use matters

**Examples:**
- "Which file initializes the PARS database?"
- "Find all references to the allowlist check in the PARS server."

The token-minimizer reads only the lines it needs, answers in the fewest words, and skips preamble and summaries. Its output is the bare answer: a path, value, or line number. It has no web access and must not use WebSearch, WebFetch, or any network tool. It asks one question when a short answer would be a guess. Its file cites CLAUDE.md sections on web search and LLM endpoints that are not in this project's CLAUDE.md files.

## graphify

- **graphify** (`.claude/skills/graphify/SKILL.md`) - any input to knowledge graph. Trigger: `/graphify`
When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.
