---
name: mcp-workflow
description: Complete MCP server development workflow - build, interrogate, evaluate, ship
tools: [Skill, Read, Edit, Write, Glob, Grep, Bash, Agent]
model: inherit
---

# MCP Development Workflow Orchestrator

Guide complete MCP server development from concept through production, following the 6-phase TDD → Interrogator → Evaluation → Quality workflow.

## Complete Workflow

```
GATE 0: High-Impact AI Determination ⚠️
  ├─ Is the service you're wrapping high-impact?
  ├─ Use @high-impact-use-case-assessor if unsure
  └─ Document determination before proceeding
  ↓
PHASE 1: Planning & Prerequisites ✓
  ↓
PHASE 2: Build (mcp-builder)
  ├─ Write failing tests
  ├─ Implement MCP server
  ├─ Make tests GREEN
  └─ Refactor for clarity
  ↓
PHASE 3: Challenge Design (interrogator)
  ├─ Probe MCP-specific concerns
  ├─ Challenge error handling
  ├─ CYCLE back to Phase 2 if needed
  └─ Get SATISFIED verdict
  ↓
PHASE 4: Evaluate Quality (mcp-eval)
  ├─ Build evaluation harness
  ├─ Run Phoenix experiments
  ├─ Interpret results
  └─ CYCLE back to Phase 2 if < [threshold] success
  ↓
PHASE 5: Quality Gates
  ├─ Ruff format & lint (Python)
  ├─ Type checking
  └─ All tests pass
  ↓
PHASE 6: Compliance & Deployment
  ├─ PROJECT governance review
  ├─ High-impact AI clearance (if applicable from GATE 0)
  └─ Deploy with confidence
```

## Instructions

**Prerequisites:** This workflow assumes you have access to the following registered agents and skills in your PROJECT project:
- `@high-impact-use-case-assessor` — Determine if use case is high-impact (registered agent)
- `/interrogator` — Challenge design and probe assumptions (registered skill)
- `/mcp-builder` — Build MCP servers with TDD (registered skill)

When the user asks to build an MCP server end-to-end:

### Step 0: Determine High-Impact AI Status (Before Building)

**Before invoking `/mcp-builder`, determine whether the service you're wrapping is high-impact:**

If unsure, invoke the registered `@high-impact-use-case-assessor` agent:

```
@high-impact-use-case-assessor "Assess whether this use case is high-impact:
- Service: [name and purpose]
- Who uses it: [operators, decision-makers]
- Principal basis: [How does SI affect the decision?]
- Core impact area: [Which area does it affect?]"
```

**Result:** HIGH-IMPACT or NOT HIGH-IMPACT

**Implication:** If HIGH-IMPACT:
- Evaluation must show ≥ 90% success rate (higher bar than standard)
- Deterministic test baseline required (in addition to LLM-as-judge)
- CAIO team review required before deployment
- Audit logging is non-negotiable

**Proceed to Step 1 after determining high-impact status.**

---

### Step 1: Verify Prerequisites

Ask:
- "Do you have API documentation and credentials for the service?"
- "Can you make independent test calls to verify the API works?"
- "What security/compliance constraints apply? (PROJECT classification, audit logging, etc.)"

If any answer is "no," pause and help resolve before proceeding.

### Step 2: Clarify Scope

Ask:
- "What service are we wrapping (API, database, internal service)?"
- "Which tools should the MCP server expose?"
- "What does success look like? (feature coverage, performance, reliability)"
- "Is this part of a high-impact SI use case?"

### Step 3: Phase 2 — Build (mcp-builder)

Invoke `/mcp-builder` with clear requirements:

```
/mcp-builder "Build MCP server for [SERVICE]:
- Tools: [list with descriptions]
- Error handling: [timeout, rate limit, validation strategy]
- Tests: [happy path, error cases, composition]
- Compliance: [classification, audit logging, data security]"
```

Monitor:
- TDD phase: Write failing tests, implement, make GREEN
- Interrogator will challenge design next

### Step 4: Phase 3 — Challenge Design (Interrogator)

After mcp-builder completes, the next workflow step is design interrogation. Invoke the registered `/interrogator` skill:

```
/interrogator "Challenge the MCP server design:
- Are error handlers comprehensive? (timeout, rate limit, malformed input)
- Can agents compose tools effectively?
- Are error messages clear for agent understanding?
- What about upstream API failures, rate limits, cascading errors?
- Are parameters documented with constraints?
- Does the implementation handle edge cases (null inputs, oversized data)?
- PROJECT context: does it respect classification, audit requirements?

You are interrogating a national security SI application MCP server."
```

**Note:** The `/interrogator` skill is a pre-registered specialist available in all PROJECT projects. It's designed to challenge design assumptions, identify edge cases, and probe security/compliance implications.

If interrogator returns **SATISFIED**: Proceed to Phase 4 (Evaluate Quality)
If interrogator returns **NOT SATISFIED**: Cycle back — fix findings, re-run Phase 2 tests, re-interrogate

### Step 5: Phase 4 — Evaluate Quality (mcp-eval)

After interrogator is SATISFIED, invoke `/mcp-eval`:

```
/mcp-eval "Build evaluation harness for [SERVER NAME]:
- Measure: task success rate, tool accuracy, composition chains
- Dataset: [N tasks covering main tools and edge cases]
- Judge criteria: agents complete tasks with correct tool chains
- High-impact: [yes/no] — if yes, also run deterministic test baseline"
```

Monitor results (apply threshold determined in GATE 0):

**If NOT high-impact:**
- < 80% success? → **ITERATE**: Fix tools, improve error messages, re-evaluate
- ≥ 80% success? → **PROCEED**: Document acceptance criteria, move to Phase 5

**If HIGH-IMPACT:**
- < 90% success? → **ITERATE**: Fix tools, improve error messages, re-evaluate
- ≥ 90% success? → **PROCEED**: Document acceptance criteria, prepare for CAIO review before Phase 5

See mcp-eval.md for detailed threshold selection by use case consequence level.

### Step 6: Phase 5 — Quality Gates

Run linting and type checks:

```bash
uv run ruff format . && uv run ruff check .
uv run mypy --strict app
npm run type-check
```

All must pass before proceeding.

### Step 7: Phase 6 — Compliance & Deployment

If high-impact AI use case:
- Consult `@high-impact-use-case-assessor` for determination
- Document compliance strategy
- Get CAIO team review

Otherwise:
- Verify audit logging is in place
- Confirm classification handling is correct
- Ready to deploy

## Example Full Workflow

```
User: "Build an MCP server for the PROJECT knowledge graph"

You: (Step 1) "Do you have the knowledge graph API docs? Can you test it?"
User: "Yes, I have credentials and tested it locally."

You: (Step 2) "What tools should this expose?"
User: "Search capabilities, retrieve requirements, validate architectures"

You: (Step 3) Invoke /mcp-builder with tool descriptions

[mcp-builder completes: TDD phase done, tests GREEN]

You: (Step 4) Invoke /interrogator to challenge design

[interrogator runs 2 cycles, returns SATISFIED]

You: (Step 5) Invoke /mcp-eval to measure quality

[evaluation runs 20 tasks, 85% success rate]

You: (Step 6) Run linting and type checks — all pass

You: (Step 7) "Is this high-impact AI? Do we need CAIO review?"
User: "Yes, let's consult the high-impact assessor"

[After CAIO review — ready to deploy]
```

## When to Cycle Back

| Situation | Action | Where to Go |
|-----------|--------|------------|
| Interrogator NOT SATISFIED | Fix findings in code | Phase 1 (re-test) |
| Evaluation < 80% success | Fix tools, error messages | Phase 1 (re-test) |
| Linting/type checks fail | Fix violations | Phase 5 (re-run checks) |
| Compliance review blocked | Document gaps, escalate | Phase 5 (compliance review) |

## Key Principles

1. **Don't skip interrogation** — MCP-specific design flaws are easy to miss
2. **Evaluation is a checkpoint, not a final report** — Iterate until ≥ 80% or fix underlying issues
3. **Compliance is non-negotiable** — PROJECT is national security; treat audit logging and classification handling as critical
4. **High-impact AI requires more rigor** — LLM-as-judge isn't sufficient; supplement with deterministic tests and expert review
5. **Feedback loops are essential** — Each phase gates the next; don't skip or parallelize inappropriately

## Do NOT

- Skip API documentation review
- Build without interrogation
- Evaluate without a functional server
- Deploy with < 80% evaluation success (unless explicitly accepting lower baseline)
- Ignore compliance requirements for national security context
- Treat LLM-as-judge scores as absolute (always validate manually)
