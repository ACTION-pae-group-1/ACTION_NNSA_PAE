---
name: git-safety-constraint-agent
type: workflow-orchestrator
description: Orchestrated 4-phase validation, interrogation, and repair of git safety constraint patterns
---

# Git Safety Constraint Agent

A specialized workflow agent that automates the complete lifecycle of git safety constraint validation and repair. Orchestrates analysis, interrogation, validation, and implementation in a single pass.

## Capabilities

- **Comprehensive Pattern Analysis:** Dissects regex for logical completeness, bypass vectors, edge cases
- **Design Interrogation:** Challenges enforcement layer choice, identifies flaws, suggests improvements
- **Automated Testing:** Tests patterns against bypass vectors and legitimate use cases
- **Implementation & Verification:** Applies fixes to source files and validates no regressions
- **Educational Output:** Error messages explain WHY constraints exist, not just that they do

## When to Use

**Adding a new git safety constraint:**
```
Invoke the git-safety-constraint-agent to add and validate a constraint:
Pattern: r"\bgit\s+add\b[^;&|]*(?:-f\b|--force\b)"
Intent: Block force-add to prevent accidentally committing ignored files
Context: tool_input_preflight.py in the git_policy_error function
Known issues: False positive on --force-add flag
```

**Fixing an existing constraint with known vulnerabilities:**
```
Invoke the git-safety-constraint-agent to repair a bypass:
Pattern: r"(?:^|[;&|]\s*)SKIP=\S*\s+git\b"
Intent: Prevent bypassing pre-commit hooks via SKIP environment variable
Context: tool_input_preflight.py
Known issues: SKIP=x && git commit bypasses the check (shell operator separation)
```

**Comprehensive review before merge:**
```
Invoke the git-safety-constraint-agent to validate before committing:
Pattern: <the pattern>
Intent: <what danger it prevents>
Context: <where it lives>
Known issues: <any reported bypass vectors or false positives>
Action: validate-only (do not implement fixes)
```

## Input Parameters

```
pattern (required)
  The regex pattern to validate, e.g., r"\bgit\s+add\b[^;&|]*(?:-f\b|--force\b)"

intent (required)
  What dangerous behavior is this trying to prevent?
  E.g., "Block force-add to prevent accidentally committing ignored files"

context (required)
  Where is this constraint used?
  E.g., "tool_input_preflight.py in the git_policy_error function"

knownIssues (optional)
  Any bypass vectors, false positives, or legitimate use cases already identified
  E.g., "False positive on --force-add flag; SKIP=x && git commit bypasses check"

errorMessage (optional)
  Proposed error message if fixing. Should explain WHY, not just that action is blocked.
  E.g., "Force-add bypasses gitignore protections. Stage exact filenames instead."

file (optional)
  Full path to source file, if implementing fixes
  Default: .claude/hooks/tool_input_preflight.py

function (optional)
  Function name where pattern appears
  Default: git_policy_error

actionType (optional)
  One of: validate-only, propose-fix, implement-fix
  validate-only: analyze and report issues, do not modify files
  propose-fix: suggest fixes but do not apply them
  implement-fix: apply fixes to files (default if fixes needed)
  Default: validate-only
```

## Output

The agent returns a comprehensive report with:

### 1. Pattern Analysis
```
Regex Breakdown: [breakdown of each component]
Bypass Vectors Found: [list of ways to circumvent]
False Positives: [legitimate patterns incorrectly blocked]
Edge Cases: [flag variations, stacking, quoting, environment expansion]
Missing Coverage: [dangerous patterns not caught]
Severity: CRITICAL | MEDIUM | LOW
```

### 2. Interrogation Findings
```
Enforcement Layer Assessment:
  Current: tool-level (preflight hook)
  Better: pre-commit hook (with rationale)

Design Flaws:
  [list of issues preventing effective enforcement]

Workflow Impact:
  [which legitimate developer workflows are blocked]

Error Message Quality:
  Current: [original message]
  Proposed: [improved message explaining WHY]

Design Verdict: FIXABLE | NEEDS_REDESIGN | REDESIGN_RECOMMENDED
```

### 3. Validation Results
```
Bypass Vector Tests:
  [Input] → [Expected] → [Actual] → [Status: ✓ PASS | ✗ FAIL]

Legitimate Use Case Tests:
  [Input] → [Should NOT match] → [Actual] → [Status]

Edge Case Tests:
  [Flag stacking, quoting, expansion] → [Results]

Overall Verdict: ALL_TESTS_PASS | ISSUES_FOUND
```

### 4. Implementation Report (if actionType == implement-fix)
```
File: [path to modified file]
Location: [line numbers of changes]
Changes Applied:
  - Pattern fix: [old] → [new]
  - Error message: [old] → [new]

Post-Implementation Tests:
  [Verification that Python syntax is correct]
  [Verification that regex works as intended]

Status: READY_TO_COMMIT | NEEDS_FIXES
```

## Phase-by-Phase Execution

### Phase 1: Analysis (Agent)
- Breaks down regex pattern component by component
- Identifies bypass vectors (shell operators, flag variations, environment expansion)
- Tests against known attack scenarios
- Reports false positives (legitimate patterns incorrectly blocked)

### Phase 2: Interrogation (Agent)
- Challenges whether tool-level enforcement is the right approach
- Identifies design flaws (incomplete operator coverage, false positives)
- Assesses workflow impact (which developer workflows are broken)
- Evaluates error message clarity and educational value
- Returns design verdict: FIXABLE, NEEDS_REDESIGN, or REDESIGN_RECOMMENDED

### Phase 3: Validation (Agent)
- Tests the proposed fix against all bypass vectors
- Verifies legitimate use cases are not blocked
- Tests edge cases (flag stacking, quoting, multi-command chains)
- Provides pass/fail results for each test case
- Returns overall verdict: ALL_TESTS_PASS or ISSUES_FOUND

### Phase 4: Implementation (Agent)
- Locates the pattern in the source file
- Applies the fix (if actionType == implement-fix)
- Runs Python syntax validation
- Tests the regex against sample commands
- Provides file location, line numbers, and readiness status

## Example: Fixing the SKIP Bypass

```
Pattern: r"(?:^|[;&|]\s*)SKIP=\S*\s+git\b"
Intent: Prevent SKIP environment variable from bypassing pre-commit hooks
Context: tool_input_preflight.py, git_policy_error function
Known Issues: SKIP=test && git commit bypasses the check
Action: implement-fix

PHASE 1: ANALYSIS
─────────────────
Regex Breakdown:
  (?:^|[;&|]\s*)     = Start of string OR semicolon/ampersand/pipe with space
  SKIP=\S*           = SKIP= followed by non-space characters
  \s+                = One or more spaces
  git\b              = The word "git" followed by word boundary

VULNERABILITY: Pattern expects SKIP= immediately before git (after space).
But shell operators like && come AFTER SKIP=test, not before.
So SKIP=test && git commit is NOT matched.

Bypass Vector: SKIP=x && git commit (shell operator separation)

PHASE 2: INTERROGATION
──────────────────────
Design Flaw: Pattern assumes command continuity.
Shell separators (&&, ||, ;, |) break the pattern's assumption.

Legitimate Use Cases Blocked: None (SKIP is only used to bypass hooks)

Error Message: Too vague. Doesn't explain why SKIP is dangerous.

Proposed Fix: Refactor pattern to handle shell operators:
r"(?:^|[;&|]\s*)(?:SKIP|HUSKY|LEFTHOOK)=\S*\s*(?:&&|\|\||;|\|)\s*git\b"

Verdict: FIXABLE

PHASE 3: VALIDATION
───────────────────
Test: SKIP=test && git commit
  Expected: MATCH (should be blocked)
  Actual: MATCH ✓ PASS

Test: SKIP=test || git commit
  Expected: MATCH
  Actual: MATCH ✓ PASS

Test: SKIP=test; git commit
  Expected: MATCH
  Actual: MATCH ✓ PASS

Test: SKIP=test git commit (no operator)
  Expected: MATCH
  Actual: MATCH ✓ PASS

Test: git add file.txt (no SKIP)
  Expected: NO MATCH
  Actual: NO MATCH ✓ PASS

Verdict: ALL_TESTS_PASS ✓

PHASE 4: IMPLEMENTATION
───────────────────────
File: .claude/hooks/tool_input_preflight.py
Location: Line 1468

Applied:
  Old: r"(?:^|[;&|]\s*)SKIP=\S*\s+git\b"
  New: r"(?:^|[;&|]\s*)(?:SKIP|HUSKY|LEFTHOOK)=\S*\s*(?:&&|\|\||;|\|)\s*git\b"

  Old error: "SKIP environment variable with git commands is not allowed."
  New error: "Hook-bypass environment variables (SKIP, HUSKY, LEFTHOOK) cannot be used with git commands. Use explicit hook configuration instead."

Python Syntax: ✓ Valid
Regex Syntax: ✓ Valid
Test Results: ✓ All bypass vectors blocked

Status: READY_TO_COMMIT ✓
```

## Invoking the Agent

```bash
# Validate only (no file modifications)
Use the git-safety-constraint-agent to validate this pattern:
Pattern: r"\bgit\s+add\b[^;&|]*(?:-f\b|--force\b)"
Intent: Block force-add
Context: tool_input_preflight.py
Known issues: False positive on --force-add flag
Action: validate-only

# Propose fixes (analyze but don't modify)
Use the git-safety-constraint-agent to analyze and propose fixes:
Pattern: r"(?:^|[;&|]\s*)SKIP=\S*\s+git\b"
Intent: Block SKIP environment variable with git
Context: tool_input_preflight.py
Known issues: Shell operator separation allows bypass
Action: propose-fix

# Implement fixes (full cycle with file modifications)
Use the git-safety-constraint-agent to add and validate this constraint:
Pattern: r"\bgit\s+add\b[^;&|]*(?:-f\b|--force\b)"
Intent: Block force-add to prevent ignored file commits
Context: tool_input_preflight.py
Error message: Force-add bypasses gitignore protections. Stage exact filenames instead.
Action: implement-fix
```

## Related Resources

- **Pattern Reference:** Regex patterns for common git safety constraints (available on request)
- **Bypass Vector Checklist:** Complete list of shell operators, quoting, environment expansion techniques
- **Testing Harness:** Automated test suite for validating git patterns
- **Workflow Reference:** `.claude/WORKFLOW_QUICK_REFERENCE.md` includes git safety section
- **Source File:** `.claude/hooks/tool_input_preflight.py` contains all git safety constraints

## Design Principles

1. **Security First:** All bypass vectors must be blocked. False positives are acceptable if unavoidable.
2. **Educational:** Error messages must explain WHY the constraint exists, enabling developers to understand the intent.
3. **Right Layer:** Tool-level (preflight) vs. pre-commit hook choice is intentional. Tool-level blocks faster; pre-commit hook integrates better with git workflows.
4. **Legitimate Workflows:** Constraints should not prevent legitimate developer workflows. If they do, a workaround should exist.
5. **Comprehensive Testing:** Patterns are validated against bypass vectors, edge cases, and legitimate use cases before merge.

## Troubleshooting

**False Positive on legitimate flag:**
→ Use negative lookahead/lookbehind: `(?<!-)-f\b` blocks `-f` but not `--force-add`

**Bypass via shell operator:**
→ Include operator patterns: `(?:&&|\|\||;|\|)\s*git\b`

**Environment variable expansion:**
→ Pattern cannot catch `$SKIP` or `${SKIP}`. Document as out-of-scope (env expansion is shell-specific)

**Command chain evasion:**
→ Ensure pattern matches operators between var assignment and git command

## Success Criteria

- ✅ All identified bypass vectors are blocked
- ✅ No false positives on legitimate patterns
- ✅ Error message explains the intent and rationale
- ✅ Pattern syntax is valid and performant
- ✅ Tests pass before and after implementation
- ✅ Workflow is documented in WORKFLOW_QUICK_REFERENCE.md
