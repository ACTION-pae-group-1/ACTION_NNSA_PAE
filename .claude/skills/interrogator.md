# Interrogator

**Triggers the Interrogator Agent** — A rigorous challenger that probes assumptions, identifies gaps, and systematically surfaces risks before they become problems.

## What the Interrogator Does

The interrogator agent is designed to challenge and strengthen work by relentlessly asking "what could go wrong?" It operates in four distinct modes:

### 1. **Code Review Mode**
Interrogates a diff, PR, or codebase for:
- Hidden assumptions and implicit invariants
- Untested error paths and edge cases
- Dependency chains that could break
- Logical flaws that tests might miss
- Concurrency, race conditions, state management risks
- Security implications of the design

**Output:** Ranked findings (CRITICAL → HIGH → MEDIUM → LOW) with specific failure scenarios.

### 2. **Design & Planning Mode**
Challenges specifications, designs, and architectural decisions for:
- Ambiguous or contradictory requirements
- Unstated assumptions about users, systems, or constraints
- Missing pieces: error handling, rollback, monitoring, alerting
- Feasibility gaps: timeline, resource, dependency conflicts
- Scalability and performance implications
- Fallback strategies and recovery paths

**Output:** Interrogation report with open questions, gaps, and risk assessments.

### 3. **Testing Mode**
Systematically probes requirements and specifications for:
- Boundary conditions and edge cases
- Input validation gaps
- State transitions that could fail
- Concurrency and timing issues
- Data integrity under failure
- Recovery and rollback scenarios
- Acceptance criteria completeness

**Output:** Test case recommendations and identified gaps.

### 4. **Requirements Work Mode**
Validates specs and requirements for:
- Completeness: What's missing?
- Consistency: Do requirements contradict each other?
- Feasibility: Can we actually build this?
- Testability: How will we verify success?
- Dependencies: What else needs to be done first?
- Unintended consequences: What side effects could this have?

**Output:** Requirements interrogation with recommendations for strengthening the specification.

## When to Use the Interrogator

### ✅ Use the interrogator at these gates:

| Gate | When | Why |
|------|------|-----|
| **Design phase** | Before implementation begins | Surface design flaws early, before code is written |
| **Code review** | Before merging to main | Catch hidden flaws, race conditions, edge cases |
| **Requirements review** | Before development starts | Expose ambiguity, missing pieces, assumptions |
| **Architecture review** | When proposing major changes | Identify scalability, dependency, and failure mode risks |
| **Security-critical code** | Any change to auth, crypto, data handling | Systematically probe threat vectors and assumptions |
| **Complex business logic** | Specifications with multiple rules/conditions | Find contradictions, missing cases, edge cases |
| **Test strategy review** | Before finalizing test plan | Ensure test coverage, boundary conditions, failure modes |

### ❌ Don't use the interrogator for:

- Simple documentation or minor fixes (overkill)
- Code that has already passed thorough code review
- Exploratory work where you're still figuring out what to build
- Routine maintenance or refactoring with no logic changes

## How to Use the Interrogator

### **Basic usage:**

```
Interrogate this diff for hidden assumptions and potential failure modes.

Branch: feat/ontology-persistence
Files changed: backend/services/ontology_catalog.py, tests/

Focus: Data integrity and concurrent access patterns.
```

### **For design review:**

```
Interrogate this architecture design:

We're adding a graph cache layer between PostgreSQL and the API.
- Cache is in-memory, TTL 1 hour
- Invalidation happens on write via FastAPI middleware
- Falls back to DB on cache miss

Probe: What if invalidation fails? What about distributed deploys? Stale cache scenarios?
```

### **For requirements validation:**

```
Interrogate these requirements:

User Story: "As an enterprise architect, I can explore RDF relationships and drill into entity details."

Acceptance Criteria:
- Graph displays 500+ resources with 1000+ relationships
- Entity Inspector shows IRI, provenance, and incoming/outgoing predicates
- Search and focus work without lag

Probe: Performance constraints, data source reliability, access control, edge cases.
```

### **For test strategy:**

```
Interrogate the test strategy for the ontology catalog endpoint:

We have:
- 2 unit tests (happy path, 403 error)
- No integration tests
- No tests for concurrent reads/writes or stale cache

Gaps? Missing scenarios? What could go wrong in production?
```

## What to Expect in the Report

The interrogator produces a **formal interrogation report** with:

1. **Findings** — Ranked CRITICAL → HIGH → MEDIUM → LOW
   - Each finding includes:
     - The assumption or gap discovered
     - Why it matters
     - Concrete failure scenario
     - Severity and likelihood

2. **Open Questions** — Specific probes the interrogator couldn't answer
   - What information do we need?
   - What should we verify?

3. **Risk Assessment** — Overall risk profile
   - Is this ready to merge/ship?
   - What must be fixed before proceeding?
   - What can be addressed post-merge?

4. **Recommendations** — Concrete next steps
   - Design changes
   - Additional tests
   - Documentation gaps to fill
   - Monitoring/alerting to add

## Interrogator Prompting Tips

**Be specific about context:**
```
❌ "Review this code"
✅ "Interrogate this cache invalidation logic for race conditions and stale data scenarios"
```

**Name the risk area:**
```
❌ "Find problems"
✅ "Focus on concurrent access patterns and failure modes (DB down, network latency, etc.)"
```

**Provide constraints:**
```
❌ "What could go wrong?"
✅ "We have 100 deploys running simultaneously and 10M graph nodes. What breaks? What's the worst case?"
```

**Ask about specific scenarios:**
```
❌ "Is this secure?"
✅ "Probe: What if a user modifies their JWT? What if an API key is leaked? What if we get 10K concurrent requests?"
```

## Examples

### Example 1: Code Review — RDF Graph Explorer

**Prompt:**
```
Interrogate the Graph Explorer restoration for hidden assumptions and gaps:
- GraphExplorerRoute loads authorized context before rendering TtlOntologyPreview
- TtlOntologyPreview calls ontologyCatalogClient which hits /api/v1/enterprise/ontology/catalog
- 2,372 triples verified in browser
- Tests: 4/4 passing

Probe: Data integrity, authorization, dependencies, route coverage, deep linking, edge cases, test validity, pre-existing blockers.
```

**Expected output:** CRITICAL findings about catalog unavailability, authorization gaps, test mocking vs. real data, etc.

### Example 2: Requirements Review — Specification Generation

**Prompt:**
```
Interrogate these requirements for completeness and feasibility:

User Story: "As an enterprise architect, I can generate a system specification from a use case with trustworthiness, effectiveness, and deployability dimensions."

Acceptance Criteria:
1. Specification includes all three dimensions
2. Trade-offs are explained
3. Specification can be exported as Mermaid diagram
4. Specification respects security classification (IL2-IL6)

Scope: Feature must work for use cases with 5-100 requirements. Must complete in <30 seconds.

Probe: What's missing? Edge cases? Performance constraints? Dependency issues?
```

**Expected output:** Gaps in error handling, incomplete specification scenarios, missing acceptance criteria for edge cases.

### Example 3: Architecture Review — Ontology Sync

**Prompt:**
```
Interrogate this architecture:

Design: Operator-controlled TTL catalog synchronization into PostgreSQL
- Operator runs ontology_ttl_sync.py with --check (preview) and --sync (commit)
- One transaction per sync, advisory lock prevents concurrent syncs
- API serves only active catalog, never uncommitted candidates
- No file upload or runtime TTL parsing

Assumptions:
- Operator won't accidentally corrupt the catalog
- Advisory lock prevents race conditions
- Active catalog is always valid

Probe: What if the operator makes a mistake? Recovery scenarios? Data corruption? Rollback strategy?
```

**Expected output:** Findings about operator error, recovery, rollback, and data validation gaps.

## Integration with [Project Name] Workflow

### Before merging:
1. Run code review at MEDIUM level
2. Use interrogator to challenge design assumptions and edge cases
3. Address CRITICAL findings before merge
4. Document MEDIUM/LOW findings as known risks or follow-up work

### During requirements elicitation:
1. Draft requirements with the user
2. Use interrogator to validate completeness
3. Close gaps before implementation begins

### Before shipping security-critical features:
1. Have interrogator probe threat vectors
2. Ensure all CRITICAL findings are addressed
3. Document remaining risks in runbooks

### For complex business logic:
1. Interrogate the specification for contradictions
2. Build comprehensive test suite based on findings
3. Use findings to validate acceptance criteria

## See Also

- [tdd-enforcer](./tdd-enforcer.md) — Test-driven development gate
- [code-review](./code-review.md) — Automated code review for correctness and clarity
- [minimumcd-agent](./minimumcd-agent.md) — Continuous delivery compliance audit
