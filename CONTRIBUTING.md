# Contributing to mcp_group_1

## Development Setup

### Install Pre-Commit Hooks

Before committing code, install the pre-commit and pre-push hooks:

```bash
uv run pre-commit install
uv run pre-commit install --hook-type pre-push
```

This installs git hooks that automatically validate code before commits and pushes.
(The pre-push stage is a separate `install` — note `--hook-type`, since
`--hook-stage` belongs to `pre-commit run` — and the first command only covers
commits.)

## Pre-Commit Checks (Automatic on `git commit`)

When you commit, pre-commit automatically runs:
- **Large file check** — Blocks files over 5MB
- **Case conflict detection** — Prevents case-only filename conflicts
- **Merge conflict detection** — Ensures no unresolved conflicts
- **File ending fixes** — Adds missing final newlines
- **Trailing whitespace** — Strips trailing spaces (with documented exclusions)
- **standard-file-checks** — Repository file validation (whitespace, line endings, etc.)
- **detect-secrets** — Prevents committed secrets and credentials
- **manifest-hashes** — On every commit and push, checks that every manifest's
  `sha256` and `size_bytes` match the bytes Git stores, including after a file
  is deleted (see "`manifest-hashes` failed" under Common Issues)
- **ruff-fix-and-stage** — Python linting with auto-fix; modified files are re-staged
- **pytest-fast** — Fast regression suite (changed + companion + affected files,
  excludes slow/integration tests)
- **TDD Companion Gate** — Ensures all production code has a matching test file

## Pre-Push Checks (Automatic on `git push`)

When you push, the pre-push stage re-runs the structural checks above plus:
1. **ruff-check-verify** — Lint verification over the committed code (fix-only)
2. **ruff-format-verify** — Enforces consistent formatting (`ruff format --check`)

All checks must pass before the push completes.

The **full test suite is not a hook** — `pytest-full` lives on the `manual`
stage so it never slows a push. Run it before high-consequence pushes:

```bash
uv run pre-commit run pytest-full --hook-stage manual --all-files
# or directly: uv run python -m pytest
```

### Configuration-Only Commits

⚠️ **Important:** When committing changes to non-Python files (configuration, fixtures, data), pytest is automatically skipped because `types: [python]` filter is applied to the pytest hooks.

**Files that trigger this behavior:**
- `src/mcp_servers.json` — MCP server configuration
- `src/bls_mcp/tests/fixtures/*.json` — Test fixture data
- `.pre-commit-config.yaml` — Git hook configuration
- `manifest.yaml`, `server.json` — Data manifests
- `.gitkeep` and other non-Python files

**What this means:**
```bash
$ git add src/mcp_servers.json
$ git commit -m "Update MCP configuration"
# pytest-fast hook is SKIPPED (no Python files staged);
# pytest-full is manual-stage and never runs on commit
```

**⚠️ You must manually verify tests before pushing config-only changes:**

```bash
# Run fast regression suite
uv run python -m pytest -m "not slow and not integration"

# Or full test suite
uv run python -m pytest
```

**Why this design?**
- Config-only changes are common (docs, manifests, schemas)
- Running the full test suite on every non-Python commit adds 30-60 seconds
- Manual verification ensures critical tests run without slowing workflow

**Edge case — Modifying test fixtures:**
If you modify JSON fixture files that tests depend on, you **must** run pytest manually:
```bash
# Fixtures in src/bls_mcp/tests/fixtures/
git add src/bls_mcp/tests/fixtures/
uv run pytest src/bls_mcp/tests/  # Run tests that use this fixture
```

### Trailing Whitespace Auto-Fix Behavior

The `trailing-whitespace` hook automatically removes trailing spaces from staged text files, with exclusions for:
- `docs/vendor/` — inherited third-party documentation
- `src/bls_mcp/docs/sample_data/` — test data with intentional whitespace
- `src/bls_mcp/tests/fixtures/` — test fixture files with preserved formatting

This happens silently during pre-commit.

**On Windows with CRLF line endings:**
- Git may be configured with `core.autocrlf=true` for Windows compatibility
- The hook modifies CRLF line endings while processing trailing spaces
- This can cause unexpected line-ending normalization in subsequent commits
- If you see "entire file changed" on next commit, line endings were normalized (this is expected behavior)

**Tip:** If you want to verify what the hook will change before committing:
```bash
uv run pre-commit run trailing-whitespace --all-files
```

### Manual Pre-Push Validation

To test pre-push checks locally before pushing:

```bash
uv run pre-commit run --hook-stage pre-push --all-files
```

## Test-Driven Development (TDD) Practices

This project enforces TDD principles through automated checks at commit and push time:

### TDD Requirements

1. **Companion Tests** — All production code must have matching test files
   - For `src/mymodule/foo.py`, create `src/mymodule/tests/test_foo.py` or `tests/src/mymodule/test_foo.py`
   - The TDD Companion Gate blocks your commit if tests are missing

2. **Test Naming Conventions** — Test files and functions should follow conventions
   - Test files: `test_*.py`, `*_test.py`, or `*_spec.py`
   - Test functions: `test_*`, `should_*`, or `*_test`
   - The companion gate verifies test *files* exist; run `uv run poe check` to catch naming drift

3. **Coverage Thresholds** — New code should have 80%+ test coverage
   - Coverage is not enforced by a hook; check it yourself before pushing
   - Run `uv run poe test-cov` to see coverage details

4. **Performance** — Tests must be fast and appropriately marked
   - Pre-commit runs fast tests only (`pytest-fast`, excludes slow/integration)
   - Use `@pytest.mark.slow` or `@pytest.mark.integration` for slower tests
   - This enables quick feedback during development

5. **WBS/CAEF Tests** — Labeled training data tests must pass
   - Found in `src/pars_local_mcp/tests/fixtures_caef_*.py`
   - These run in the full suite — run it manually before high-consequence pushes
     (`uv run pre-commit run pytest-full --hook-stage manual --all-files`)

### Manual TDD Validation

You can validate the TDD gate manually before committing:

```bash
# Companion-test check (what pre-commit runs)
uv run pre-commit run tdd-companion-gate --all-files

# Full validation: lint, formatting, types, and tests
uv run poe check
```

### Coverage Reports

Generate a detailed coverage report:

```bash
# Terminal report with missing lines highlighted
uv run poe test-cov

# Focus on a specific module
uv run pytest --cov=bls_mcp --cov-report=term-missing
```

## Common Issues

**Hook installation issues?**
```bash
uv run pre-commit install
uv run pre-commit install --hook-type pre-push
```

**Want to skip hooks temporarily?**

```bash
git commit --no-verify  # possible, but discouraged — the project's workflow forbids --no-verify
git push --no-verify    # same: fix the failing check instead
```

**Tests failing before push?**
- Review the test output
- Fix the failing tests
- Re-run checks: `uv run pre-commit run --hook-stage pre-push --all-files`

**TDD Companion Gate says tests are missing?**
- Ensure each production file has a companion test
- Check that tests are in expected locations (src/*/tests/ or tests/src/*/)
- Run: `uv run pre-commit run tdd-companion-gate --all-files` to validate

**`manifest-hashes` failed, or `bls-data build` reports a SHA-256 mismatch?**

Manifests such as `src/bls_mcp/docs/sample_data/*-input.json` pin each data
file by SHA-256 and size, and the snapshot build refuses a file that doesn't
match. Hashes must describe the bytes Git stores, not a working copy whose line
endings were converted (the cause of the CRLF/LF drift fixed in November 2026).
- Run `uv run --locked poe manifest-check` to see each mismatch and its likely cause.
- A "working copy differs from Git's copy" message usually means your checkout
  was converted to CRLF before `-text` applied, and `git status` may still call
  the file unchanged. Delete the file (or the folder) and run
  `git checkout -- <path>` to restore Git's bytes. Don't use
  `git add --renormalize`: with `-text` it would stage the CRLF bytes.
- After deliberately changing a pinned file: `git add` it, run
  `uv run --locked poe manifest-fix`, review the manifest diff, and commit both.
- A new manifest must be registered in `MANIFESTS` in
  `scripts/check_manifest_hashes.py`, and its text files need `-text` in `.gitattributes`.

**Coverage below 80%?**
- Write tests for uncovered code paths
- Run: `uv run poe test-cov` to see which lines lack coverage
- Remember: coverage is a tool, not a goal — focus on meaningful tests

## See Also

- `.pre-commit-config.yaml` — Pre-commit configuration
- `.git/hooks/pre-push` — Pre-push hook script
