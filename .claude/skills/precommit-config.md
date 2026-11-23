
---
name: precommit-config
description: >
  Design, generate, audit, troubleshoot, and maintain
  pre-commit hook configurations for Git repositories.
  Use when creating or modifying .pre-commit-config.yaml,
  installing pre-commit hooks, integrating Ruff, Black,
  ESLint, Prettier, mypy, pytest, secret scanning,
  shellcheck, yamllint, Terraform, or other code quality
  tools. Optimize for fast local feedback, reproducibility,
  cross-platform compatibility, and CI/CD integration.
  Follow the repository's existing conventions and
  trunk-based development practices.
---

# Pre-Commit Configuration Expert

## Mission

Create and maintain reliable pre-commit configurations
that prevent common defects from entering version control.

Optimize for:

1. Fast feedback.
2. Reproducible execution.
3. Minimal configuration.
4. Appropriate language-specific checks.
5. Dependency compatibility.
6. Security.
7. Developer experience.
8. CI consistency.
9. Maintainability.
10. Continuous integration readiness.

**The goal is to catch defects early without making
routine commits unnecessarily slow or fragile.**

---

## 1. Core Responsibilities

This skill is responsible for:

- Creating `.pre-commit-config.yaml`.
- Auditing existing hook configurations.
- Selecting appropriate hooks.
- Integrating existing project tools.
- Configuring hook execution stages.
- Managing hook ordering.
- Preventing redundant checks.
- Reducing hook execution time.
- Diagnosing failed hooks.
- Integrating hooks into CI.
- Maintaining reproducible versions.
- Avoiding unsafe automatic modifications.

Do not assume every repository requires every hook.

Select hooks based on actual project requirements.

---

## 2. Repository Discovery

Before generating configuration, inspect the repository.

### Identify Project Languages

Look for:

| File | Likely Ecosystem |
|---|---|
| `pyproject.toml` | Python |
| `uv.lock` | Python / uv |
| `requirements.txt` | Python / pip |
| `package.json` | JavaScript / TypeScript |
| `package-lock.json` | npm |
| `pnpm-lock.yaml` | pnpm |
| `yarn.lock` | Yarn |
| `go.mod` | Go |
| `Cargo.toml` | Rust |
| `*.tf` | Terraform |
| `Dockerfile` | Containers |
| `Makefile` | Project automation |
| `.pre-commit-config.yaml` | Existing hook configuration |

Also inspect:

- `AGENTS.md`
- `CLAUDE.md`
- `CONTRIBUTING.md`
- `README.md`
- CI/CD configuration
- Existing lint configuration
- Existing formatter configuration
- Existing test commands

### Inspect Git State

```bash
git status --short
git branch --show-current
git diff --check
```

Do not overwrite unrelated changes.

Do not replace an existing configuration without
first understanding its purpose.

---

## 3. Configuration Design Principles

### 3.1 Prefer Existing Project Tools

Reuse the tools already configured in the repository.

Examples:

- Ruff instead of adding Flake8 unnecessarily.
- Prettier instead of introducing another formatter.
- ESLint instead of introducing a competing JS linter.
- Existing test runners instead of duplicate scripts.

Avoid overlapping hook responsibilities.

### 3.2 Keep Hooks Fast

Use pre-commit for inexpensive, deterministic checks.

Appropriate:

- Whitespace validation.
- End-of-file normalization.
- YAML validation.
- TOML validation.
- JSON validation.
- Merge conflict detection.
- Formatting.
- Linting.
- Basic secret detection.
- Lightweight static analysis.

Potentially expensive:

- Full test suites.
- Integration tests.
- End-to-end tests.
- Container builds.
- Large dependency audits.
- Remote service checks.
- Infrastructure deployments.

Run expensive checks in CI unless the repository
explicitly requires them locally.

### 3.3 Prefer Reproducibility

Pin remote hooks to immutable revisions.

Prefer audited release tags or commit SHAs.

Use exact revisions verified from trusted sources.

Never invent version numbers.

Do not use floating branches such as:

```yaml
rev: main
```

Do not use unverified or mutable references in
security-sensitive configurations.

### 3.4 Avoid Network-Dependent Execution

Hooks should not require external services during
normal execution.

Initial environment installation may need dependency
downloads.

After installation, hooks should be able to run
reliably without accessing external APIs.

Do not upload source files to third-party services
without authorization.

### 3.5 Respect Local Tooling

Use the repository's existing:

- Package manager.
- Dependency lockfiles.
- Runtime versions.
- Virtual environment strategy.
- Tool configuration files.

Do not automatically install a competing toolchain.

---

## 4. Default Configuration

Use this as a minimal baseline for repositories
where the Python `pre-commit` framework is installed.

The configuration below deliberately relies on
local Python execution rather than external hooks,
so it does not invent remote hook revisions.

It assumes Python is installed.

```yaml
repos:
  - repo: local
    hooks:
      - id: check-merge-conflicts
        name: Check merge conflict markers
        entry: python scripts/hooks/check_merge_conflicts.py
        language: system
        types: [text]

      - id: check-trailing-whitespace
        name: Check trailing whitespace
        entry: python scripts/hooks/check_whitespace.py
        language: system
        types: [text]
```

**Important:** This example requires the referenced
scripts to exist.

Do not generate this configuration without also
providing the scripts.

For ordinary projects, prefer the established
`pre-commit-hooks` repository and pin its verified
release revision.

A typical configuration is:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: <verified-release-or-commit>
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-json
      - id: check-merge-conflict
      - id: check-added-large-files
```

Replace the revision placeholder before installation.

This is a template, not a runnable final configuration
until the revision is resolved.

---

## 5. Python Projects

### Preferred Ruff Integration

When Ruff is already part of the repository, prefer:

- `ruff check`
- `ruff format`

Example using a local environment:

```yaml
repos:
  - repo: local
    hooks:
      - id: ruff-check
        name: Ruff lint
        entry: uv run --no-sync ruff check
        language: system
        types_or: [python, pyi]
        require_serial: true

      - id: ruff-format
        name: Ruff format
        entry: uv run --no-sync ruff format
        language: system
        types_or: [python, pyi]
        require_serial: true
```

This example assumes:

- `uv` is available.
- Dependencies are synchronized.
- Ruff is declared as a project dependency.
- The repository supports the selected commands.

Do not assume these conditions without inspection.

### Ruff Configuration

Prefer centralized settings in `pyproject.toml`.

Example:

```toml
[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "I"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

Adapt target versions and lint rules to the project.

Do not overwrite existing Ruff settings without
understanding their effect.

### Avoid Duplicate Formatters

Do not configure Black and Ruff Format together
without an explicit compatibility requirement.

Do not introduce isort if Ruff already handles
import sorting.

Avoid redundant Flake8 checks when Ruff covers
the relevant rules.

---

## 6. JavaScript and TypeScript Projects

Prefer the project's existing package manager.

Supported tools may include:

- ESLint.
- Prettier.
- TypeScript.
- Biome.
- Stylelint.

### Example Local Hooks

```yaml
repos:
  - repo: local
    hooks:
      - id: eslint
        name: ESLint
        entry: npm exec -- eslint
        language: system
        types_or: [javascript, jsx, ts, tsx]
        pass_filenames: true

      - id: prettier-check
        name: Prettier check
        entry: npm exec -- prettier --check
        language: system
        types_or:
          - javascript
          - jsx
          - ts
          - tsx
          - json
          - yaml
          - markdown
        pass_filenames: true
```

Verify that:

- Commands exist.
- Dependencies are installed.
- Commands work from the hook's working directory.
- Nested package layouts are supported.
- The configured package manager matches the repository.

For monorepos, use wrappers or project-specific
configuration where necessary.

Do not assume npm is appropriate when the project
uses pnpm, Yarn, or another package manager.

### Type Checking

TypeScript type checking generally requires
project-wide context.

Prefer running:

```bash
npm run type-check
```

in CI or a separately configured hook with:

```yaml
pass_filenames: false
```

Avoid passing individual filenames to
`tsc --project`, which expects project-level input.

---

## 7. Go Projects

Use existing Go tooling.

Typical checks:

- `gofmt`
- `go vet`
- `golangci-lint`, if configured

Prefer formatting checks before expensive analysis.

Verify tool versions and project compatibility.

Use full-project checks in CI when appropriate.

---

## 8. Rust Projects

Use:

- `cargo fmt`
- `cargo clippy`
- `cargo test`

Prefer `cargo fmt --check` as a lightweight hook.

Run Clippy or tests locally only when their
execution cost is acceptable.

Ensure commands run from the correct workspace root.

---

## 9. Infrastructure Projects

For infrastructure repositories, inspect the tools
actually used.

Potential checks include:

- Terraform formatting.
- Terraform validation.
- OpenTofu formatting.
- YAML validation.
- Kubernetes manifest validation.
- Dockerfile linting.
- ShellCheck.
- Hadolint.

Do not automatically execute:

- `terraform apply`
- `tofu apply`
- `kubectl apply`
- Helm deployments
- Cloud provisioning
- Production migrations

Pre-commit checks should validate, not deploy.

Avoid requiring production credentials during hooks.

---

## 10. Secret Detection

Configure secret detection where practical.

Potential tools:

- Gitleaks.
- detect-secrets.
- TruffleHog, when approved.

Selection depends on:

- Existing repository configuration.
- Tool availability.
- Licensing.
- Security policy.
- CI integration.

Secret detection should:

- Inspect relevant staged changes.
- Avoid uploading source code.
- Avoid printing full secret values.
- Support reviewed allowlists or baselines.
- Report findings clearly.

Never silently suppress a detected secret.

Do not treat secret scanning as a substitute
for credential management or repository access controls.

---

## 11. Hook Ordering

Prefer the following logical execution order:

1. Structural checks.
2. Whitespace and file normalization.
3. Formatters.
4. Linters.
5. Secret scanning.
6. Lightweight static checks.

Example:

```text
Check configuration syntax
          |
          v
Normalize whitespace
          |
          v
Format code
          |
          v
Lint code
          |
          v
Scan for secrets
          |
          v
Commit allowed if all pass
```

Do not depend on separate hook ordering when
correctness requires strict sequential execution.

For tightly coupled operations, use one wrapper
that executes steps in the required order.

---

## 12. Hook Stages

Select stages according to the intended use.

Typical stages include:

- `pre-commit`
- `pre-push`
- `commit-msg`
- `manual`

Use the stage names supported by the installed
pre-commit version.

### Pre-Commit

Best for:

- Formatting.
- Linting.
- File checks.
- Lightweight security checks.

### Pre-Push

May be appropriate for:

- Targeted test suites.
- More expensive static analysis.
- Build validation.

### Commit Message

May enforce:

- Conventional Commit formatting.
- Required issue references.
- Repository-specific commit policies.

### Manual

Useful for:

- Dependency audits.
- Full test suites.
- Expensive validation.

Do not put slow, unrelated checks in every commit
without an explicit project requirement.

---

## 13. Handling Auto-Fixing Hooks

Some hooks modify files automatically.

Examples:

- Ruff Format.
- Prettier.
- Trailing whitespace cleanup.
- End-of-file normalization.

Rules:

1. Inspect modifications after hook execution.
2. Never assume a formatter preserves intended semantics.
3. Rerun tests when formatting changes are substantial.
4. Do not stage changes automatically.
5. Do not retry committing without inspecting results.
6. Preserve unrelated user edits.

A hook may exit unsuccessfully because it modified files.

This is not always a defect.

Report:

- Which hook ran.
- Which files changed.
- Whether the hook subsequently passed.

---

## 14. CI/CD Integration

Use the same configuration locally and in CI.

Typical execution:

```bash
pre-commit run --all-files
```

In CI, prefer:

- Clean environments.
- Pinned dependencies.
- Cached hook environments.
- Read-only validation where feasible.
- Explicit exit-code handling.

When caching, include relevant configuration and
runtime information in cache keys.

Do not allow CI hooks to silently modify files
without reporting the resulting diff.

Do not assume local pre-commit success guarantees
CI success.

CI may include additional:

- Tests.
- Build validation.
- Security scanning.
- Dependency analysis.
- Integration tests.

---

## 15. Monorepo Support

For monorepos:

- Identify package boundaries.
- Respect nested environments.
- Avoid unnecessary full-repository scans.
- Scope language-specific hooks.
- Use path filtering where appropriate.
- Handle shared configuration consistently.

Example:

```yaml
repos:
  - repo: local
    hooks:
      - id: backend-ruff
        name: Backend Ruff
        entry: bash scripts/hooks/backend-ruff.sh
        language: system
        files: ^backend/.*\.py$
        pass_filenames: false

      - id: frontend-lint
        name: Frontend lint
        entry: bash scripts/hooks/frontend-lint.sh
        language: system
        files: ^frontend/
        pass_filenames: false
```

The referenced scripts must exist and be verified.

Do not use `pass_filenames: false` blindly.

It is useful for project-wide commands, but may
increase hook execution time.

---

## 16. Troubleshooting

### Hook Command Not Found

Check:

- Tool installation.
- PATH configuration.
- Virtual environment.
- Package manager.
- Hook execution environment.

### Hook Works Locally but Fails in CI

Check:

- Runtime versions.
- Dependency installation.
- Working directory.
- File permissions.
- Line endings.
- Missing environment variables.
- Configuration differences.

### Hook Modifies Files Repeatedly

Check:

- Conflicting formatters.
- Incompatible versions.
- Different local and CI configuration.
- Non-idempotent scripts.

Run the hook twice on the same files.

The second run should not produce additional changes.

### Hook Runs Too Slowly

Check:

- Unnecessary full-project execution.
- Duplicate checks.
- Expensive dependency initialization.
- Repeated package installation.
- Missing caches.
- Excessive hook scope.

Move expensive checks to CI where appropriate.

### Hook Fails on Generated Files

Inspect generated-file conventions.

Exclude generated paths when justified.

Do not exclude security-sensitive files
merely to make checks pass.

### Hook Cannot Find Files

Check:

- Relative paths.
- Working directory.
- Repository root assumptions.
- Nested package boundaries.
- Quoting and filenames with spaces.

---

## 17. Configuration Validation

After creating or modifying the configuration,
validate it.

Recommended commands:

```bash
pre-commit validate-config
pre-commit run --all-files
```

When specifically testing hook installation:

```bash
pre-commit install
```

Only install hooks after authorization.

Review the actual execution results.

If a hook modifies files:

```bash
git diff --check
git diff --stat
git diff
```

Do not discard changes automatically.

If configuration validation fails, diagnose
the specific issue before further execution.

---

## 18. Testing Strategy

Apply test-driven configuration changes where practical.

For a new hook:

1. Define the defect it should catch.
2. Create a harmless test fixture.
3. Run the hook against the fixture.
4. Confirm the expected failure.
5. Correct the fixture.
6. Confirm the hook passes.
7. Verify clean files remain unchanged.

For formatter hooks:

- Verify formatting is deterministic.
- Verify repeated execution is idempotent.
- Verify unrelated files remain unchanged.

For security hooks:

- Use synthetic test secrets.
- Never use real credentials.
- Confirm findings are reported without exposing
  sensitive values.

---

## 19. Trunk-Based Development Integration

Pre-commit supports trunk-based development by
providing fast validation for short-lived changes.

Recommended workflow:

```text
Small Change
    |
    v
Focused Tests
    |
    v
Pre-Commit Checks
    |
    v
Review Diff
    |
    v
Commit
    |
    v
Push
    |
    v
CI Validation
    |
    v
Merge Into Trunk
```

Do not rely exclusively on pre-commit.

Required CI gates must still run independently.

Never bypass failing hooks to accelerate integration
without explicit authorization and documentation.

---

## 20. Agent Safety Rules

The agent may:

- Inspect repository configuration.
- Recommend appropriate hooks.
- Generate configuration files.
- Explain hook failures.
- Run non-destructive validation.
- Suggest performance improvements.

The agent must not automatically:

- Disable security hooks.
- Remove existing required checks.
- Install unapproved external dependencies.
- Execute unknown remote scripts.
- Stage modified files.
- Commit changes.
- Push branches.
- Merge pull requests.
- Delete repository files.
- Modify protected branches.

Always preserve existing user work.

---

## 21. Required Output

When creating or changing pre-commit configuration,
provide:

### Configuration Summary

Hooks selected and reasons for selection.

### Files Changed

List configuration and support files.

### Dependencies

Required tools and versions when known.

### Validation Results

Report:

- Configuration validation.
- Hook execution results.
- Files modified by hooks.
- Any failed checks.

### Performance Considerations

Identify expensive hooks or redundant checks.

### Security Considerations

Explain secret detection and relevant exclusions.

### Remaining Issues

Identify missing tools, unresolved failures,
or compatibility concerns.

Do not claim checks passed unless executed.

---

## 22. Definition of Done

Pre-commit configuration is complete when:

1. The configuration matches repository tooling.
2. Remote hook versions are pinned and verified.
3. All referenced scripts exist.
4. Configuration validation succeeds.
5. Hooks execute successfully on representative files.
6. Formatting is deterministic.
7. Hook execution time is reasonable.
8. No essential security checks are weakened.
9. CI integration is consistent.
10. Changes are documented.

If validation has not been run, report the
configuration as NOT VERIFIED.

---

## Guiding Principle

**Use pre-commit to catch inexpensive, deterministic
defects early. Use CI to provide broader integration
and release confidence.**

Prefer:

- Existing tools over new dependencies.
- Minimal configuration over complexity.
- Verified versions over floating versions.
- Fast hooks over slow commit cycles.
- Deterministic checks over environment-dependent checks.
- Explicit failures over silent bypasses.
- Safe automation over destructive convenience.
