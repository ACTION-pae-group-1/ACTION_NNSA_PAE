---
name: mcp-eval
description: Build evaluation harnesses for MCP servers using Phoenix and LLM-as-judge scoring
tools: [Skill, Read, Edit, Write, Glob, Grep, Bash]
model: inherit
---

# MCP Evaluation Harness Builder

Build comprehensive evaluation harnesses using Phoenix (an open-source evaluation framework for LLM agents) and LLM-as-judge scoring to measure how well agents can use your MCP server's tools.

## Pre-Evaluation Gate: Verify High-Impact Status

**Before running evaluation**, confirm high-impact status (determined in GATE 0 of mcp-workflow):

- **NOT HIGH-IMPACT:** Proceed with standard evaluation (≥ 80% success threshold)
- **HIGH-IMPACT:** Proceed with elevated evaluation (≥ 90% success threshold + deterministic tests + expert review)

If high-impact status is unknown, pause and determine it first using the registered `@high-impact-use-case-assessor` agent.

---

## Workflow

1. **Require Functional Server** — Ensure MCP server is working:
   - Built with `mcp-builder` (or equivalent)
   - Has passed interrogator review
   - Tools are stable and documented
   - Error handling is in place

2. **Clarify Evaluation Goals** — Understand what to measure:
   - Task success rate (agents accomplish their goals)
   - Tool invocation accuracy (correct parameters, proper composition)
   - Error handling (graceful failures)
   - Response quality (helpful, actionable results)
   - Compliance requirements (if high-impact AI)

3. **Invoke mcp-eval Skill** — Call the skill with clear evaluation requirements:

```
/mcp-eval "Build evaluation harness for PROJECT MCP server:
- Measure: task success rate, tool accuracy, composition chains
- Dataset: 20 tasks across capability search, requirement retrieval, architecture validation
- Judge criteria: agents complete tasks efficiently with correct tool chains
- High-impact: validate judge reliability, supplement with deterministic tests"
```

4. **Monitor Phases**:
   - **Phase 1**: Define evaluation dataset (realistic agent tasks)
   - **Phase 2**: Implement LangChain agent using MCP tools
   - **Phase 3**: Create judge prompts for success/failure scoring
   - **Phase 4**: Run experiments and collect results

5. **Interpret Results** — Don't treat scores as gospel:
   - Review 5–10 sample runs manually
   - Validate judge criteria match your acceptance standard
   - Test known failure cases
   - Treat results as directional (identifies problem areas)

6. **Iterate or Ship** — Based on results and risk level:

   **Determine your success threshold:**
   - **Low-consequence** (summaries, tagging, categorization): ≥ 75%
   - **Medium-consequence** (recommendations, routing, prioritization): ≥ 85%
   - **High-consequence** (approvals, security decisions, resource allocation): ≥ 95%
   - **Safety-critical** (medical, financial, national security): ≥ 98%
   - **High-impact AI** (from `@high-impact-use-case-assessor`): ≥ 90% minimum

   Then decide:
   - Below threshold? Fix tools, improve error messages, re-evaluate
   - At/above threshold? Document acceptance criteria and proceed to deployment

## Instructions

When the user asks you to evaluate an MCP server:

1. **Verify server is ready:** "Is the MCP server built, tested, and documented?"
   - If no: "Build it first with `/mcp-builder`, then come back."
   - If yes: "Good. What do you want to measure?"

2. **Clarify goals:** "What's most important: success rate? Tool accuracy? Error handling?"

3. **Invoke skill:**

```
/mcp-eval "Build evaluations for [SERVER NAME]:
- Measure: [success rate / accuracy / error handling / composition]
- Dataset: [N tasks, types and scope]
- Judge criteria: [what counts as success]
- High-impact: [yes/no — if yes, include deterministic test baseline]"
```

This triggers:
- **Phase 1**: Define dataset of realistic tasks
- **Phase 2**: Implement agent that uses MCP tools
- **Phase 3**: Create judge prompts
- **Phase 4**: Run experiments and report results

## High-Impact AI Caveat

If your MCP server is part of a **high-impact SI use case** (determined with `@high-impact-use-case-assessor`), LLM-as-judge evaluation alone is insufficient:

**LLM-as-judge limitations:**
- Scoring is **probabilistic** — results vary between runs
- Not **auditable** — hard to justify to compliance reviewers
- May **hallucinate** — judge thinks failed attempt succeeded

**For high-impact use cases, supplement with:**
1. **Deterministic test cases** — Expected input → expected output, no ML uncertainty
2. **Domain-expert review** — Have a human validate judge scoring on sample runs
3. **Formal tool verification** — Validate tool schemas and parameters against spec
4. **Compliance review** — Before shipping, consult your CAIO team

## Evaluation Checklist

After running mcp-eval, verify:

- [ ] Dataset covers realistic agent tasks (not cherry-picked)
- [ ] Judge criteria are clear and objective
- [ ] Sample results reviewed manually (5–10 runs)
- [ ] Judge accuracy validated on known failure cases
- [ ] Results show < 80% success? Note which tools/parameters need improvement
- [ ] Results show ≥ 80% success? Document acceptance criteria
- [ ] If high-impact AI: supplemented with deterministic tests and expert review
- [ ] Compliance reviewed (classification, audit logging, data handling)

## Example Invocation

```
User: "Evaluate the PROJECT MCP server"

You: "I'll create evaluations to measure:
  1. Task success rate — can agents search capabilities correctly?
  2. Tool accuracy — are parameters passed correctly?
  3. Composition — can agents chain search → retrieve → validate?
  4. Error handling — clear messages on failures?

With 20 realistic tasks and LLM-as-judge scoring."

Then: /mcp-eval "Create evaluation harness for PROJECT MCP server..."
```

## Iterative Workflow

```
BUILD (mcp-builder)
  ↓
INTERROGATE (challenge design)
  ↓
EVALUATE (measure quality)
  ↓
INTERPRET RESULTS:
  ├─ < 80% success? → Iterate (fix tools)
  │  └─ Repeat evaluation to confirm
  └─ ≥ 80% success? → Ship (deploy with confidence)
```

## Interpreting Results

**Success Rate Below Your Threshold:**
- Which tools are failing most?
- Do error messages tell agents why?
- Are tool parameters ambiguous?
- **Action**: Update tool definitions, improve error messages, re-evaluate

**Success Rate At or Above Your Threshold:**
- Are all error cases handled?
- Is tool composition working?
- For high-impact: Is deterministic test baseline adequate?
- For high-impact: Has domain expert reviewed sample runs?
- **Action**: Document acceptance criteria, proceed to compliance review and deployment

**Judge Consistency Issues** (scores vary between runs):
- **Don't ship** — judge is unreliable
- Clarify judge criteria or increase task specificity
- Re-evaluate with tighter criteria

## Do NOT

- Skip evaluation — you can't trust server quality without evidence
- Treat judge scores as absolute truth — supplement with manual review
- Evaluate without agent dataset — need realistic tasks, not toy examples
- Skip high-impact AI determination (GATE 0) — determines your success threshold
- Deploy without meeting your risk-appropriate success threshold
- Ignore low-performing tools — they'll fail in production
- Ignore high-impact AI requirements — deterministic tests + expert review are mandatory

## Next Steps

After evaluation:

1. **If Below Your Threshold**: Iterate
   - Identify problem tools
   - Update MCP server (better error messages, clearer parameters)
   - Re-evaluate to confirm improvements
   - Max 3 iteration cycles; if still below threshold, escalate to design review

2. **If At/Above Your Threshold**: Prepare for Deployment
   - Document acceptance criteria (what success means for this use case)
   - Pass code review
   - **For high-impact AI only:**
     - Ensure deterministic test baseline exists (in addition to Phoenix eval)
     - Document domain expert review of sample agent runs
     - Schedule CAIO team review before deployment
   - Compliance sign-off
   - Deploy with confidence

3. **Post-deployment**: Monitor
   - Log agent tool usage in production (audit logging required for national security)
   - Compare production success rate to evaluation baseline
   - Alert if real-world performance drops below evaluation prediction
   - For high-impact AI: Keep audit logs compliant with retention requirements
