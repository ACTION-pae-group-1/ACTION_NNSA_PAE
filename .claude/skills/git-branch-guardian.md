# Git Branch Guardian

A specialized agent that ensures clean repository state and proper branch discipline.

## When to Use

Invoke this agent when you need to:
- Validate that the git repository is clean before starting work
- Check current branch is appropriate for the task at hand
- Ensure all work is properly isolated on feature branches (not main/master)
- Verify no uncommitted changes or untracked files block the workflow
- Get guidance on branch naming and organization
- Prepare the repository for a clean state before major refactoring

## What It Does

The Git Branch Guardian performs the following checks:

### Repository Cleanliness Validation
- Confirms no relevant uncommitted changes exist (`git status`)
- Flags untracked files that might be lost
- Detects stale branches or merge conflicts
- Verifies .gitignore is configured correctly
- Checks for leftover debugging/temporary files

### Branch Discipline Enforcement
- Validates you're NOT working directly on `main` or `master`
- Confirms current branch follows naming conventions (feature/, fix/, refactor/, etc.)
- Checks branch is up-to-date with upstream
- Detects branches that should have been cleaned up
- Warns if commits are ahead of the base branch without a PR

### Workflow Guidance
- Suggests appropriate branch names for your task
- Provides cleanup commands for stale branches
- Recommends git workflows (rebase vs merge)
- Flags commits that violate MinimumCD or project policies
- Helps stash/commit work safely before switching branches

## Usage Examples

```
/git-branch-guardian "Check if my repo is clean before starting refactoring"
```

```
/git-branch-guardian "Validate I'm on the right branch for this feature work"
```

```
/git-branch-guardian "Help me clean up my branches and get ready for the next feature"
```

## Output

Returns a structured report including:
- **Repository Status**: Clean / Has uncommitted changes / Has untracked files
- **Branch Status**: Current branch, commits ahead/behind base
- **Issues Found**: List of blocking issues or warnings
- **Recommendations**: Specific git commands to fix issues
- **Ready to Work**: Yes/No assessment with blockers

## Important Notes

This agent is READ-ONLY and DIAGNOSTIC. It does not make changes to the repository. It provides recommendations but requires user confirmation before destructive operations (deleting branches, resetting commits, etc.).

If the agent finds issues, follow its recommendations carefully:
- Stash uncommitted work before switching branches
- Clean up stale branches only when sure they're no longer needed
- Use interactive rebase only when comfortable with git
- Always verify branch protection rules before pushing

## Related Skills

- `ruff-expert`: Code quality checks (run after ensuring clean branch)
- `documenter`: Documentation updates (create separate docs-only branch)

## Integration with [Project Name] Development

This skill supports MinimumCD discipline by:
- Ensuring branches are feature-isolated
- Preventing accidental commits to main
- Enforcing clean working tree before operations
- Validating merge-ready state before PR creation
