
---
name: trunk-based-development
description: >
  Enforce trunk-based development, short-lived branches,
  frequent integration, continuous testing, and safe delivery
  practices in Git repositories. Use when implementing features,
  fixing bugs, refactoring, managing branches or worktrees,
  reviewing changes, resolving merge conflicts, preparing pull
  requests, or improving continuous integration workflows.
---

# Trunk-Based Development

## Purpose

Maintain a healthy, continuously integrated, and releasable
mainline while delivering small, tested changes frequently.

Apply trunk-based development principles without assuming
a particular programming language, framework, hosting
provider, CI/CD system, or deployment platform.

**Core objective: Integrate small, verified changes frequently
while keeping the trunk in a working state.**

---

## 1. Core Principles

### Single Mainline

Use one primary integration branch, referred to as `trunk`.

The repository may name this branch:

- `main`
- `master`
- `trunk`
- Another explicitly configured name

Discover the actual default branch rather than assuming
it is named `main`.

Rules:

- The trunk is the authoritative integration branch.
- Keep the trunk healthy and releasable.
- Avoid permanent development or integration branches.
- Avoid unnecessary branching hierarchies.
- Never force-push protected branches.
- Follow repository branch protection rules.

### Small Changes

Each change should represent one coherent improvement.

Prefer changes that are:

- Independently understandable.
- Easy to review.
- Fast to test.
- Safe to integrate.
- Easy to revert.

Separate unrelated concerns into independent changes.

Avoid combining feature development, dependency upgrades,
large refactoring, and infrastructure changes without a
demonstrated need.

### Short-Lived Branches

Prefer branches lasting less than one working day.

Suggested targets:

| Branch Age | Guidance |
|---|---|
| Under 24 hours | Preferred |
| 24–48 hours | Acceptable |
| Over 48 hours | Review integration barriers |
| Over 5 working days | Split or justify the exception |

These targets are guidelines, not mandatory deadlines.

Do not merge failing or insecure changes merely to meet
a branch-age target.

### Frequent Integration

Integrate completed, verified changes into trunk at least
daily when practical.

Avoid accumulating finished work on feature branches.

For larger features, integrate backward-compatible
increments rather than waiting for full completion.

### Continuous Deployability

Keep the trunk in a state where it can be deployed
through the project's approved delivery process.

This requires:

- Passing automated tests.
- Valid configuration.
- Reproducible builds.
- Compatible dependencies.
- Controlled database migrations.
- Appropriate security validation.
- Known recovery procedures.

A successful merge does not automatically imply
production deployment is authorized.

---

## 2. Repository Discovery

Before changing repository state, inspect the project.

Determine:

1. Current branch.
2. Default integration branch.
3. Working-tree status.
4. Remote configuration.
5. Existing worktrees.
6. Branch protection and merge policies.
7. Test framework and commands.
8. Formatting and linting tools.
9. CI/CD configuration.
10. Project-specific development instructions.

Useful commands:

```bash
git status --short
git branch --show-current
git branch -a
git remote -v
git worktree list
git log -5 --oneline
```

Inspect available instruction files:

- `AGENTS.md`
- `CLAUDE.md`
- `CONTRIBUTING.md`
- `README.md`
- Relevant nested instructions

Inspect applicable CI configurations, such as:

- GitHub Actions
- GitLab CI
- Azure Pipelines
- Jenkins
- Buildkite
- CircleCI

Use the repository's actual configuration as the
source of truth.

Never invent commands or assume tools are installed.

---

## 3. Standard Development Cycle

Follow this workflow:

```text
Discover Repository
        |
        v
Synchronize Trunk
        |
        v
Create Short-Lived Branch
        |
        v
Define Small Change
        |
        v
Write or Update Tests
        |
        v
Implement Minimum Change
        |
        v
Run Focused Tests
        |
        v
Refactor Safely
        |
        v
Run Quality Gates
        |
        v
Inspect Diff
        |
        v
Commit and Push (Authorized)
        |
        v
Pull/Merge Request
        |
        v
CI and Review
        |
        v
Integrate Into Trunk
        |
        v
Verify Trunk Health
```

Direct-to-trunk development may also be supported
when explicitly permitted by repository policy.

### Step 1: Synchronize

Before creating a branch, ensure trunk is current.

For repositories using `main`:

```bash
git fetch origin
git switch main
git pull --ff-only origin main
```

Adapt commands to the actual trunk name.

Never discard uncommitted work to synchronize.

If synchronization is blocked, report the issue and
preserve existing changes.

### Step 2: Create a Branch

Use a concise, descriptive name.

Examples:

```text
feat/add-search
fix/timeout-handling
refactor/config-loading
test/parser-edge-cases
chore/update-dependencies
```

Do not create a branch if the task only requires
analysis or documentation review.

### Step 3: Define the Change

Identify:

- Objective.
- Acceptance criteria.
- Affected components.
- Expected behavior.
- Relevant tests.
- Compatibility requirements.
- Risks.

If the scope is too large, decompose it into
independently integrable increments.

### Step 4: Test First

Prefer Red-Green-Refactor for behavior changes.

RED:

1. Write a failing test.
2. Run the test.
3. Confirm the expected failure.

GREEN:

1. Implement the smallest correction.
2. Rerun the test.
3. Confirm success.

REFACTOR:

1. Improve the implementation.
2. Preserve behavior.
3. Rerun tests.

For documentation-only, configuration-only, or
non-code changes, use appropriate validation
rather than inventing meaningless tests.

### Step 5: Run Quality Gates

Discover the project's required commands.

Typical checks include:

- Unit tests.
- Integration tests.
- Static analysis.
- Linting.
- Formatting.
- Type checking.
- Security scanning.
- Build validation.
- Schema validation.

Run focused tests first.

Run broader tests when the change scope or repository
policy requires them.

Do not claim a check passed unless it was executed
and its result observed.

### Step 6: Inspect Changes

```bash
git diff --check
git diff --stat
git diff
git status --short
```

Check for:

- Unrelated modifications.
- Accidental generated files.
- Secrets or credentials.
- Debug artifacts.
- Unnecessary dependencies.
- Missing tests.
- Compatibility issues.
- Unexpected configuration changes.

Keep the diff focused.

### Step 7: Integrate

When authorized:

1. Stage intended files.
2. Create an atomic commit.
3. Push the branch.
4. Open a pull or merge request.
5. Run required CI checks.
6. Obtain required approvals.
7. Resolve conflicts.
8. Merge through approved mechanisms.
9. Verify the trunk pipeline.

Never bypass repository protections.

---

## 4. Git Worktree Management

Use Git worktrees when independent tasks benefit
from separate working directories.

Worktrees are particularly useful for parallel
coding agents.

Example:

```bash
git fetch origin

git worktree add \
  -b feat/example \
  ../project-example \
  origin/main
```

Replace `main` with the actual integration branch.

Rules:

- One branch per worktree.
- Avoid shared writable files.
- Do not create duplicate worktrees unnecessarily.
- Preserve uncommitted work.
- Never remove a dirty worktree automatically.
- Keep parallel tasks independently integrable.

Inspect worktrees:

```bash
git worktree list
```

Remove a completed, clean worktree only when
authorized:

```bash
git worktree remove ../project-example
```

Worktrees provide file isolation, not independent
repositories or security boundaries.

---

## 5. Parallel Agent Development

Parallel development is permitted when tasks are
sufficiently independent.

Recommended approach:

1. Identify independent work units.
2. Assign clear ownership boundaries.
3. Give each agent a separate branch or worktree.
4. Avoid concurrent modification of shared files.
5. Run independent read-only reviews in parallel.
6. Integrate completed changes frequently.
7. Validate the combined result.

When two agents must change the same component,
prefer sequential execution.

Parallelism must not compromise correctness or
integration safety.

---

## 6. Feature Flags

Use feature flags to integrate incomplete but safe
functionality incrementally.

A feature flag should have:

- Clear purpose.
- Responsible owner.
- Defined default state.
- Controlled activation.
- Removal criteria.

Rules:

- Keep unfinished behavior disabled.
- Preserve existing application behavior.
- Test enabled and disabled paths.
- Avoid permanent unused flags.
- Remove flags after rollout completes.

Feature flags do not excuse broken tests,
security vulnerabilities, or invalid configuration.

---

## 7. Backward Compatibility

Prefer changes that allow old and new versions
to coexist during deployment.

Important areas:

- Public APIs.
- Database schemas.
- Event schemas.
- Configuration formats.
- Persisted data.
- External integrations.

For database changes, prefer:

Expand -> Migrate -> Contract

Expand:

Introduce compatible schema changes.

Migrate:

Move consumers and data to the new contract.

Contract:

Remove obsolete structures only when safe.

Avoid combining destructive changes and new
dependencies in a single unverified deployment.

---

## 8. Continuous Integration

CI should provide fast, reliable feedback.

A healthy CI pipeline should:

- Run automatically for relevant changes.
- Use reproducible dependencies.
- Validate required behavior.
- Report failures clearly.
- Avoid unnecessary duplication.
- Prevent integration of known failing changes.
- Protect trusted build artifacts.
- Support safe recovery.

Prefer fast, deterministic tests.

Run expensive tests selectively when appropriate.

Do not weaken essential checks simply to
improve pipeline duration.

---

## 9. Broken Trunk Policy

Treat failures on trunk as high priority.

Response:

1. Identify the failed check.
2. Determine whether the failure is reproducible.
3. Locate the responsible change if possible.
4. Fix or safely revert the change.
5. Run relevant tests.
6. Restore trunk health.
7. Verify the pipeline.

Avoid merging unrelated changes while trunk
is failing unless explicitly authorized.

Never hide failures by disabling tests.

---

## 10. Merge Readiness

A change is ready for integration when:

- Scope is coherent.
- Acceptance criteria are met.
- Required tests pass.
- Quality checks pass.
- Security requirements are satisfied.
- Compatibility is preserved.
- No unintended changes remain.
- Required CI checks pass.
- Required reviews are complete.
- Recovery strategy is understood.

Do not treat a green CI pipeline as proof of
correctness beyond the checks it actually performed.

---

## 11. Release and Recovery

Separate integration from deployment.

A merge into trunk may:

- Trigger a build.
- Produce an artifact.
- Deploy to a test environment.
- Deploy automatically to production.
- Await a deployment approval.

Follow the repository's configured delivery policy.

Prefer immutable release artifacts.

Use approved deployment mechanisms.

For failed releases:

- Determine the failure impact.
- Prefer the safest supported recovery method.
- Revert code when appropriate.
- Restore a prior artifact when supported.
- Handle database changes separately when necessary.

Do not assume rollback is always safe.

---

## 12. Security Rules

Never:

- Commit secrets.
- Publish sensitive data.
- Bypass authorization.
- Disable required security checks without approval.
- Execute untrusted scripts automatically.
- Force-push protected branches.
- Delete uncommitted work.
- Push, merge, or deploy without authorization.

Use least-privilege access.

Respect the project's security and compliance
requirements.

Do not introduce external services or dependencies
without checking applicable project policies.

---

## 13. Agent Operating Rules

An agent using this skill must:

### Before Changes

- Inspect repository state.
- Read applicable project instructions.
- Determine the trunk branch.
- Understand the intended change.
- Preserve existing work.

### During Changes

- Keep scope small.
- Prefer test-first development.
- Make minimal corrections.
- Avoid unrelated refactoring.
- Validate incrementally.
- Report failures accurately.

### Before Integration

- Run applicable tests.
- Run quality checks.
- Inspect the diff.
- Identify risks.
- Confirm required approvals.
- Report merge readiness.

### Authorization Boundaries

Do not automatically:

- Commit.
- Push.
- Merge.
- Rebase published branches.
- Reset branches.
- Delete branches.
- Remove worktrees.
- Deploy.

These operations require explicit authorization
or a clearly established controlling workflow.

Read-only Git commands and local validation may
be performed without additional authorization.

---

## 14. Anti-Patterns

### Long-Lived Branches

Avoid prolonged isolation from trunk.

### Big-Bang Integration

Break large changes into smaller increments.

### Broken Mainline

Restore trunk health promptly.

### Testing Only at the End

Validate continuously.

### Unrelated Refactoring

Keep changes focused.

### Unnecessary Abstractions

Prefer simple, maintainable implementations.

### Excessive CI Complexity

Add checks only when they provide meaningful value.

### Silent Failures

Report failures with evidence.

### Unsafe Automation

Never let agents perform destructive Git operations
without authorization.

---

## 15. Required Output

For branch, implementation, or integration tasks,
report the following when relevant.

### Change Summary

What changed and why.

### Repository State

Current branch and trunk status.

### Tests

Commands executed and observed results.

### Quality Checks

Passed, failed, and unexecuted checks.

### Integration Risks

Conflicts, compatibility concerns, and unresolved
dependencies.

### Merge Readiness

Use one of:

- READY
- NOT READY
- BLOCKED
- NOT VERIFIED

### Next Action

Identify the smallest safe next step.

Never claim work was committed, merged, or deployed
unless the operation actually completed.

---

## 16. Definition of Done

A change is complete when:

1. Requirements are satisfied.
2. Appropriate tests pass.
3. Quality gates pass.
4. Required reviews are complete.
5. The change is integrated into trunk.
6. Trunk remains healthy.
7. Release status is accurately reported.

If integration has not occurred, describe the
work as implementation complete but integration pending.

---

## Guiding Principle

**Keep trunk healthy by integrating small,
verified changes frequently.**

Favor:

- Small changes over large changes.
- Frequent integration over prolonged isolation.
- Automated evidence over assumptions.
- Simple solutions over speculative complexity.
- Fast feedback over delayed validation.
- Safe recovery over risky shortcuts.
