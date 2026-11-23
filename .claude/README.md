# Claude Code Configuration for [Project Name]

This directory contains custom agents, skills, and hooks that enforce development standards, security guardrails, and TDD practices for [Project Name].

## 🏗️ Architecture

The system implements a multi-layer enforcement strategy:

1. **Expert Skills** (guidance): Specialized domain expertise for TDD, data governance, high-impact use cases, etc.
2. **Structured Agents** (specialized subagents): Domain-specific agents for TDD enforcement, architecture planning, code review, etc.
3. **Guard Hooks** (automated gates): PreToolUse and PostToolUse Python/Bash scripts that block unsafe actions or provide feedback.
4. **Pre-commit Hooks** (.pre-commit-config.yaml): Mandatory tests, linting, and code quality checks that run on every commit.
5. **SDK Wiring** (settings.json): Configuration that connects hooks to tool calls and defines when they fire.

---

## 📁 Component Inventory

### Skills (`/skills`)
Markdown files that prime agents with specialized domain expertise and operational constraints.

| Skill | Purpose |
| :--- | :--- |


### Agents (`/agents`)
Specialized subagents for specific tasks (referenced via the Agent tool).

| Agent | Purpose |
| :--- | :--- |
=

### Active Hooks (`/hooks`)

Three lightweight hooks enhance tool handling:

| Event | Hook | Purpose |
| --- | --- | --- |
| `SessionStart` | `tool_call_context.py session` | Injects exact tool contract and project rules before code generation. |
| `UserPromptSubmit` | `tool_call_context.py prompt` | Refreshes tool schemas reminder before each user prompt. |
| `PreToolUse` | `tool_input_preflight.py` | Repairs/normalizes tool input: fixes file paths, validates payloads, finds unique Edit blocks. |
| `PostToolUseFailure` | `tool_failure_recovery.py` | Provides concise, tool-specific recovery guidance on failure. |


### Pre-commit Hooks (.pre-commit-config.yaml)
Mandatory checks that run before every commit.

| Hook | Purpose | Blocking? |
| :--- | :--- | :--- |
| `mypy` | Type checking | ✅ Yes |
| `ruff`, `ruff-format` | Linting & formatting | ✅ Yes |
| `pytest` | Unit tests (`-m "not integration"`) | ✅ Yes |
| `license-check` | Dependency license audit | ✅ Yes |
| `duplicate-code-check` | Cross-file duplication detection | ✅ Yes |
| (pre-commit standard hooks) | Format, secrets, conflicts | ✅ Yes |
---

### Preventive behavior

The preflight hook covers `Read`, `Edit`, `Write`, `Glob`, `Grep`, `NotebookEdit`, `TodoWrite`, and `Bash`.

For calls that reach `PreToolUse`, it:

- converts recoverable aliases such as `path` to the required `file_path` field;
- resolves project paths to canonical absolute paths and rebases mistaken `/.claude/...` paths under the repository;
- requires complete string content for `Write`, creates safe parent directories, adds final newlines, and checks common source syntax;
- requires `file_path`, `old_string`, and `new_string` for `Edit`, prefers the smallest exact unique block (usually 1-5 lines), safely trims stale unchanged outer context when the intended changed hunk is uniquely identifiable, and blocks ambiguous matches before native Edit executes;
- normalizes Todo items to `content`, `status`, and `activeForm`;
- converts backend `pytest`, `ruff`, and related Python commands to `uv --directory <backend> run ...`;
- blocks broad Git staging, bypass flags, force pushes, repository escapes, and unapproved network destinations;
- applies the TDD companion and Minimum CD policies described below.

Claude Code may reject malformed JSON, an unknown tool name, or a missing required field before `PreToolUse` runs. Session and prompt context reduce those upstream failures, but a literal guarantee requires schema-constrained decoding or an upstream tool-call repair proxy.


## 🔐 Security & Integrity Enforcement

### Network Egress
- **Allowed**: `localhost`, `127.0.0.1`, NNSA GitLab (`gitlab.aws.juce.nnsa.doe.gov`, `github.doe.gov`)
- **Blocked**: Public GitHub, all other external hosts, WebSearch, WebFetch
- **Enforcement**: `.claude/settings.json` `permissions.deny` clause (tool-level access control)

### Git Integrity & Safe Commands
- **Forbidden**: `git add -A`, `git add -all`, `git add .`, `git add -f` (use explicit file names)
- **Forbidden**: `--no-verify`, `-n` (with git commit), `SKIP=` prefix, `git config core.hooksPath`
- **Forbidden**: Force-push operations
- **Enforcement**: `tool_input_preflight.py` blocks these patterns in Bash commands before execution

### Minimum CD & Commit Testing
- **Rule**: Commits must be ≤500 lines, branches ≤48 hours old. All unit tests run on **every commit** (integration tests excluded; they run in CI).
- **Enforcement**: `tool_input_preflight.py` validates commit scope; pre-commit hooks run tests unconditionally

### Code Quality (Pre-commit)
- **Syntax**: Python via `ast.parse`, TypeScript via `tsc --noEmit`
- **Formatting**: ruff (Python), Biome (TypeScript)
- **Type checking**: mypy (Python)
- **Tests**: pytest
- **Licenses**: Exact SPDX matching against `config/allowed-licenses.yaml`
- **Duplication**: 3+ identical lines detected
- **Enforcement**: Pre-commit hooks with no `files:` filters (run on every commit)

---

## 🔧 Configuration & Customization

### Hook Configuration (settings.json / settings_hooks_template.json)
All hooks are configured in `.claude/settings.json` under the `hooks` block, organized by event type (SessionStart, UserPromptSubmit, PreToolUse, PostToolUseFailure).

To customize:
- Edit `.claude/settings.json` to add/remove hooks or adjust `matcher` patterns
- Adjust timeouts if needed (currently 10–30s per hook)
- Set `permissions.allow` / `permissions.deny` for tool access control (e.g., `["WebSearch", "WebFetch"]`)
- Reference [settings_hooks_template.json](./settings_hooks_template.json) for the reference configuration

### License Allowlist (config/allowed-licenses.yaml)
Edit to change which licenses are approved for both Python and Node dependencies. Exact SPDX identifier matching is used (no substrings).

### Test Enforcement (.pre-commit-config.yaml)
Modify the `pytest` entries to adjust test command options (e.g., parallelization, coverage thresholds). Always ensure they remain unconditional (no `files:` filter) and run on every commit.

---

## 🚀 How Hooks Work

The three active hooks work together in this flow:

1. **SessionStart / UserPromptSubmit**: `tool_call_context.py` supplies the exact tool contract (parameters, field requirements, command examples) before code generation begins. This eliminates ambiguity about Read vs. Write vs. Edit syntax, path requirements, etc.

2. **PreToolUse**: `tool_input_preflight.py` inspects each tool call before execution and repairs common mistakes: incorrect paths, unfenced code blocks, malformed payloads. It also validates Git safety and Minimum-CD rules within the same pass.

3. **PostToolUseFailure**: `tool_failure_recovery.py` provides concise, tool-specific recovery guidance (e.g., "Edit old_string didn't match — here's what's actually in the file").

This lightweight approach avoids the overhead of per-file linting, syntax checking, and test invocation on every tool call — those checks run only at logical checkpoints (pre-commit, explicit test invocations).

## 🔄 Extending This Setup

### Adding a New Skill
1. Create `.claude/skills/my-skill.md` with purpose, constraints, and domain patterns
2. Reference in your prompt: `"Use the 'my-skill' skill to..."`

### Adding a New Hook
Hooks should be **narrow in scope** and **fast** to keep latency low. Consider these patterns:

- **Normalization** (like `tool_input_preflight.py`): Repair common mistakes before tool execution
- **Context injection** (like `tool_call_context.py`): Provide schemas or rules at key lifecycle points
- **Recovery** (like `tool_failure_recovery.py`): Suggest next steps after failures

**Steps:**
1. Create `.claude/hooks/my_hook.py` with a `main()` function that reads stdin (hook payload) and exits 0 or 1
2. Wire it in `.claude/settings.json` under the appropriate event (SessionStart, PreToolUse, PostToolUseFailure, etc.)
3. Set a reasonable timeout (10–30 seconds)
4. Test locally: `echo '{"tool":"Edit",...}' | python3 .claude/hooks/my_hook.py`

---

## 📋 Troubleshooting

| Problem | Action |
| :--- | :--- |
| **Hook reports unrecognized error** | Check `tool_input_preflight.py` for detailed path validation or payload checks; see error message for guidance |
| **Tool call fails during recovery** | `tool_failure_recovery.py` provides next steps; check tool output for root cause |
| **Hook not firing** | Verify it's wired in `.claude/settings.json` with correct `matcher` pattern and timeout is sufficient |
| **Hook timeout (>30s)** | May indicate slow filesystem or large file; reduce matcher scope or increase timeout |
| **Tests fail locally** | Run focused tests: `cd backend && uv run pytest app/tests/services/my_service_test.py` (not affected by hooks) |

For project-specific development workflows and testing commands, see [CLAUDE.md](../CLAUDE.md).

---

## 🔄 Syncing Changes Back to Template

1. Review the enhancement to confirm it's domain-generic (not [Project Name]-specific)
3. Update the template's `.claude/README.md` to document the new/improved component
4. Note the sync in the commit message: "sync: [improved hook/skill] back to template"

This ensures the template improves over time and future projects benefit from lessons learned in [Project Name].

### TDD companion gate

The shared default is:

```json
{
  "CLAUDE_TDD_COMPANION_MODE": "strict"
}
```

Production files require a matching test before they can be written or edited. Test files, Python `__init__.py` files, migrations, generated files, and declaration files are excluded.

At `git commit` time, every staged production source change must have a staged matching test change.

Modes:

- `strict`: block production changes and commits without matching tests;
- `advisory`: allow them but return a warning in `additionalContext`;
- `off`: disable the companion check.

The gate enforces presence and staging. It does not manufacture a RED result. The workflow remains:

```text
write or update focused test
-> run it and observe a genuine assertion failure
-> implement the smallest change
-> rerun focused and affected suites
```

### Minimum CD

The shared defaults are:

```json
{
  "CLAUDE_MIN_CD_MODE": "advisory",
  "CLAUDE_MAX_COMMIT_FILES": "25",
  "CLAUDE_MAX_COMMIT_LINES": "500",
  "CLAUDE_MAX_BRANCH_AGE_HOURS": "48"
}
```

The check runs only for real `git commit` and `git push` commands.

For commits it checks:

- staged changes exist;
- staged file count;
- added plus deleted text lines;
- feature-branch age.

For pushes it checks feature-branch age. The trunk branch is taken from `CLAUDE_TRUNK_BRANCH`, `origin/HEAD`, `main`, or `master`.

Modes:

- `advisory`: allow an oversized commit or old branch and return a warning;
- `strict`: block it before Git executes;
- `off`: disable Minimum CD.

Git safety remains strict regardless of Minimum CD mode.

## Reliable Edit strategy

Claude Code Edit is exact and unique. Use the smallest exact block that identifies the intended location, normally 1-5 lines around the change. Avoid sending a whole function or class when only one line changes.

When a large requested Edit differs only in stale unchanged outer context, preflight reduces it to the smallest uniquely matching changed block and rewrites both `old_string` and `new_string` before execution. It never performs fuzzy replacement. If the reduced block is absent or appears more than once, the call is blocked and must be retried after a fresh Read with just enough unchanged context for one match.

## Model and timeout defaults

Override an alias in `settings.local.json` only after that model is healthy. The output-token ceiling is 8192 so larger structured Write calls are less likely to be truncated, while thinking remains bounded for local latency.

Bash defaults are:

```text
BASH_DEFAULT_TIMEOUT_MS=600000
BASH_MAX_TIMEOUT_MS=900000
CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR=1
```

### Pre-commit Hooks (.pre-commit-config.yaml)
Mandatory checks that run before every commit.

| Hook | Purpose | Blocking? |
| :--- | :--- | :--- |


---


## 🔧 Configuration & Customization

### Hook Configuration (settings.json / settings_hooks_template.json)
All hooks are configured in `.claude/settings.json` under the `hooks` block, organized by event type (SessionStart, UserPromptSubmit, PreToolUse, PostToolUseFailure).

To customize:
- Edit `.claude/settings.json` to add/remove hooks or adjust `matcher` patterns
- Adjust timeouts if needed (currently 10–30s per hook)
- Set `permissions.allow` / `permissions.deny` for tool access control (e.g., `["WebSearch", "WebFetch"]`)
- Reference [settings_hooks_template.json](./settings_hooks_template.json) for the reference configuration

### License Allowlist (config/allowed-licenses.yaml)
Edit to change which licenses are approved for both Python and Node dependencies. Exact SPDX identifier matching is used (no substrings).

### Test Enforcement (.pre-commit-config.yaml)
Modify the `pytest` and `vitest` entries to adjust test command options (e.g., parallelization, coverage thresholds). Always ensure they remain unconditional (no `files:` filter) and run on every commit.


## Agents, skills, and memory/resources

Agents and skills remain independent of the hook pipeline:

```text
.claude/agents/
.claude/skills/
CLAUDE.md
```

The preflight matcher does not intercept `Skill`, `Agent`, `ToolSearch`, `ListMcpResourcesTool`, or `ReadMcpResourceTool`. The permissions do not deny those tools. Project guidance, skills, agents, and connected memory/resource providers therefore remain available subject to the host and provider configuration.

`Agent` is the native delegation tool. Use an Explore subtype through `Agent` only when the live host exposes it; otherwise use `Glob`, `Grep`, and `Read`. When Agent times out, continue the task in the main session instead of abandoning it.

---

## 🚀 Using This Setup

### Adding a New Skill
1. Create `.claude/skills/my-skill.md`
2. Define the skill's purpose, constraints, and domain rules
3. Reference it in your prompt: "Use the `my-skill` skill to..."

### Adding a New Hook
1. Create `.claude/hooks/my_hook.py` with a `main()` function that calls `sys.exit(0 | 1)`
2. Add a matching entry in `.claude/settings.json` `preToolUse` or `postToolUse`
3. Test with a simulated payload: `echo '{"tool_name":"Edit",...}' | python3 .claude/hooks/my_hook.py`

### Running Tests Locally
```bash
# All pytests
uv run pytest

# Unit tests (what the pre-commit hook runs)
xxx

# Component tests
xxx

# All pre-commit hooks on current changes
uv run pre-commit run

# All pre-commit hooks on all files
uv run pre-commit run --all-files
```

---

## 📋 Debugging

### A hook is blocking my commit
1. Check the error message for the hook name and reason
2. Review the hook code in `.claude/hooks/`
3. For syntax errors: ensure your code follows the required format (ast.parse for Python, tsc for TypeScript)
4. For duplicate detection: remove redundant code or refactor into a shared module
5. For test failures: ensure all tests pass locally before committing

### A hook is not running
1. Verify it's wired in `.claude/settings.json` with the correct `toolName` and `matchPattern`
2. Check that the hook file is executable and has a valid `main()` function
3. Test the hook in isolation: `echo '...' | python3 .claude/hooks/my_hook.py`
