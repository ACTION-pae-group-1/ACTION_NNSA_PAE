# Workflow Comprehensive Test Results & Reference

> **For PARS MCP-specific guidance:** See [`.claude/docs/MCP_DEVELOPMENT_WORKFLOW.md`](../docs/MCP_DEVELOPMENT_WORKFLOW.md) for decision trees, complete examples, and pre-commit/pre-push safety gates.

## Quick Reference - Workflow Selection Table

| Workflow Name | Use Case | Time | Parallelization |
|---|---|---|---|
| feature-implementation | Simple features | 15-50m | None (serial) |
| feature-implementation-parallel | Single-stack (BE or FE) | 15-40m | 2-way (review+quality) |
| feature-implementation-fullstack | Full-stack (BE + FE) | 25-60m | 3-way (interrogate+ruff+lint) |
| mcp-development-parallel | MCP server development | 40-85m | 2x 2-way (design+quality, build+eval) |

### Phase Structure

```
feature-implementation:         TDD → Interrogation → Ruff → Verification
feature-implementation-parallel: TDD → [Interrogation || Ruff] → Verification
feature-implementation-fullstack: TDD → [Interrogation || Backend || Frontend] → Verification
mcp-development-parallel:       TDD → [Design || Quality] → [Build || Eval] → Verification
```

## Agent Types Available

- **tdd-enforcer** - Enforces Red→Green→Refactor TDD methodology
- **interrogator** - Challenges design assumptions and contracts
- **code-reviewer** - Code quality, security, styling, complexity
- **mcp-builder** - MCP server build, discovery, metadata
- **mcp-eval** - Phoenix-based evaluation harness

## Detailed Workflow Reference

### 1. FEATURE-IMPLEMENTATION (Serial)

**Location:** `.claude/workflows/feature-implementation.js`
**Best for:** Simple features where each phase informs the next

**Phases:**
1. TDD Implementation - Write failing tests, implement, verify GREEN
2. Design Interrogation - Challenge tool contracts and assumptions
3. Code Quality (Ruff) - Format, lint, type check, security audit
4. Final Verification - Merge readiness and deployment checklist

**Time Estimate:** 15-50 minutes (no parallelization)

**Use when:**
- Feature is small to medium complexity
- Each phase should inform the next
- You prefer sequential, deliberate feedback

### 2. FEATURE-IMPLEMENTATION-PARALLEL (Single-Stack, 2-Way Parallel)

**Location:** `.claude/workflows/feature-implementation-parallel.js`
**Best for:** Backend OR Frontend only features (not both)

**Phases:**
1. TDD Implementation - Write failing tests, implement, verify GREEN
2. Parallel Review & Quality - [Interrogation || Ruff] run simultaneously
3. Final Verification - Merge readiness and deployment checklist

**Time Estimate:** 15-40 minutes

**Use when:**
- Single-stack feature (backend OR frontend only)
- Design review and quality checks are independent
- Want faster execution with parallel review

### 3. FEATURE-IMPLEMENTATION-FULLSTACK (3-Way Parallel)

**Location:** `.claude/workflows/feature-implementation-fullstack.js`
**Best for:** Full-stack changes (Backend + Frontend together)

**Phases:**
1. TDD Implementation - Backend + Frontend tests & implementation
2. Parallel Review & Quality - [Interrogation || Backend Ruff || Frontend Lint]
3. Final Verification - Merge readiness and deployment checklist

**Backend Quality:** Python formatting, ruff checks, security
**Frontend Quality:** TypeScript/JavaScript linting, type checking

**Time Estimate:** 25-60 minutes

**Use when:**
- Feature requires backend + frontend changes
- Need unified quality gates for both stacks
- Backend and frontend reviews can be independent

### 4. MCP-DEVELOPMENT-PARALLEL (MCP Server, 2x 2-Way Parallel)

**Location:** `.claude/workflows/mcp-development-parallel.js`
**Best for:** Building MCP servers with evaluation

**Phases:**
1. TDD Implementation - Tool tests & implementation
2. Parallel Review & Quality - [Design Challenge || Code Quality]
3. Parallel Build & Evaluation - [Build & Discover || Phoenix Eval]
4. Final Verification - Production readiness checklist

**Time Estimate:** 40-85 minutes

**Use when:**
- Building an MCP server from scratch
- Need tool discovery and metadata verification
- Want LLM-as-judge evaluation results
- Need production readiness metrics

## Configuration & Customization

All workflows support `parseArgs()` for feature description and config:

**Simple usage:**
```javascript
Workflow({
  name: 'feature-implementation',
  args: 'Add user authentication with JWT'
})
```

**With custom configuration:**
```javascript
Workflow({
  name: 'feature-implementation-parallel',
  args: {
    feature: 'Add real-time notifications',
    config: {
      backendRoot: '.',
      backendTestDir: 'app/tests'
    }
  }
})
```

**MCP-specific config (PARS example):**
```javascript
Workflow({
  name: 'mcp-development-parallel',
  args: {
    feature: 'Add WBS hierarchy search tool to PARS MCP',
    config: {
      framework: 'FastMCP',
      serverRoot: '.',
      toolsDir: 'src/pars_local_mcp/mcp/tools.py',
      testsDir: 'src/pars_local_mcp/mcp',
      evalDir: 'eval/phoenix',
      entryPoint: 'src/pars_local_mcp/mcp/server.py'
    }
  }
})
```

## Result Structure

Each workflow returns an object keyed by phase. Values are the raw output of each `agent()` call; no phase passes a schema, so there is no fixed `summary`/`status`/`findings` shape.

**feature-implementation:** `tdd`, `interrogator`, `ruff`, `verification`

**feature-implementation-parallel:** `tdd`, `interrogator`, `ruff`, `verification`

**feature-implementation-fullstack:** `tdd`, `interrogator`, `backendRuff`, `frontendLint`, `verification`

**mcp-development-parallel:** `tdd`, `design`, `quality`, `build`, `eval`, `verification`

## Error Handling

All workflows implement comprehensive error handling:

**Phase-level:**
- The design interrogation phase catches the error when the `interrogator` agent type is missing and retries with `code-reviewer`
- Other phases do not catch agent errors: an exception propagates and ends the run
- The feature-implementation-* workflows wrap their phases in one outer try/catch that logs the error and rethrows

**Fallback handling:**
- If `interrogator` agent type unavailable → falls back to `code-reviewer` (the only fallback implemented)
