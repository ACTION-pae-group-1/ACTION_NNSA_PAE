# PARS MCP Deployment Readiness Summary

**Status: WITHDRAWN as unverified. Not evidence. The 100% / 50 of 50 figures, "production-ready" and "DEPLOY" statements below have no run output, and Phoenix recording is BLOCKED (see `eval/caef/results/release-2026-11-19/FINAL_EVALUATION_REPORT.md`, section 5).**

> **Review note (2026-11-17).** The figures below are as reported on
> 2026-11-11. No output from that run (`eval/phoenix/results/<run_id>.csv`
> and `.json`) is committed, so they can't be re-checked here; treat them as
> a reported result, not a verified one.
>
> **Scope.** The run covered the 7 read-only hierarchy tools that the harness
> exposes (`READ_ONLY_TOOLS` in `eval/phoenix/agent.py`). The PARS server now
> registers 16 tools. The 9 WBS pipeline tools (validate, clean, train,
> predict, `write_back_wbs` and others) were not evaluated, and the general
> client allowlist in `src/mcp_servers.json` includes them; see
> `docs/PARS_MCP_CLOSEOUT.md`. The "production" and "read-only" statements
> below apply to that 7-tool scope only.
>
> **To make this result reproducible:** run
> `python run_experiment.py --dataset-name pars-eval-0 --system-prompt-version v2`
> (and `v1`) from `eval/phoenix/` with the approved endpoints, commit the
> resulting `<run_id>.csv` and `<run_id>.json` (the root `.gitignore` excludes
> `*.csv`, so use `git add -f`), and link them here. Then run the 60-question
> `pars-eval-1`.

**Date:** November 11, 2026
**Evaluator:** LLM-as-Judge Evaluation Harness (Phoenix)
**Lead:** MCP Evaluation Team

---

## Quick Facts

| Metric | Value | Status |
|--------|-------|--------|
| **Evaluation Success Rate** | 100% (50/50 examples) | ✓ Exceeds 80% threshold |
| **Correctness** | 100% | ✓ All queries answered correctly |
| **Scope Accuracy** | 100% | ✓ All scope determinations correct |
| **Tool Coverage** | 7/7 tools (100%) | ✓ All tools tested and functional |
| **Error Handling** | Robust (0 crashes) | ✓ Graceful failure modes |
| **Code Quality** | ruff passing, type hints, docstrings | ✓ Production ready |
| **Documentation** | Complete (setup, usage, API) | ✓ Ready for agent developers |
| **Performance** | <1s per query (synthetic data) | ✓ Acceptable baseline |

---

## Key Findings

### What Works Excellently

1. **All 7 Tools Functional**
   - `list_projects()` — Direct project discovery
   - `search_wbs()` — Pattern-based element search
   - `get_wbs_hierarchy()` — Parent-child relationships
   - `get_wbs_lineage()` — Full parent chains
   - `get_project_info()` — Project metadata
   - `get_leaf_nodes()` — Terminal element discovery
   - `get_wbs_by_level()` — Level-based filtering

2. **Tool Composition**
   - Single-tool queries: 12/25 succeed in one call
   - Two-tool chains: 8/25 work seamlessly
   - Three-tool chains: 3/25 complete successfully
   - No wasted calls; efficient parameter passing

3. **Error Handling**
   - Invalid project IDs → clear error messages
   - Empty results → handled gracefully (distinct from errors)
   - Network/DB failures → wrapped in error dicts (no stack traces)
   - Agent robustness → 0 crashes observed

4. **Agent Behavior**
   - Correctly infers which tool to use from query intent
   - Chains tools efficiently for complex questions
   - Explains results clearly to users
   - Handles out-of-scope requests appropriately (v2 prompt)

---

## Evaluation Data

### Primary Dataset: 25 WBS Queries

| Category | Count | Success |
|----------|-------|---------|
| **Discovery** | 4 | 4/4 (100%) |
| **Search** | 6 | 6/6 (100%) |
| **Navigation** | 8 | 8/8 (100%) |
| **Complex Scenarios** | 4 | 4/4 (100%) |
| **Edge Cases** | 3 | 3/3 (100%) |
| **Total** | **25** | **25/25 (100%)** |

### System Prompt Comparison

| Prompt | Correctness | Scope | Notes |
|--------|-------------|-------|-------|
| **v1 (Basic)** | 25/25 (100%) | 25/25 (100%) | Clear tool descriptions sufficient |
| **v2 (Scoped)** | 25/25 (100%) | 25/25 (100%) | Explicit boundaries reinforce behavior |

**Recommendation:** Deploy with **v2 prompt** (explicit out-of-scope handling).

---

## Acceptance Criteria: PASS

All acceptance criteria met or exceeded:

- [x] Evaluation success rate >= 80% (achieved 100%)
- [x] All 7 tools callable and functional
- [x] Tool parameters correctly validated
- [x] Return shapes consistent and parseable
- [x] Error handling doesn't crash agent
- [x] Multi-tool composition works
- [x] System prompts guide correct behavior
- [x] Deployment documentation complete
- [x] Code quality passing (type hints, docstrings, ruff)
- [x] Agent correctness >= 80% (achieved 100%)
- [x] Agent scope accuracy >= 80% (achieved 100%)

---

## What to Know About Limitations

### Minor Issues (Low Impact)

1. **Error Messages** — Currently strings only; could include error type
   - Impact: Low (agent handles gracefully)
   - Fix: Future enhancement (v0.2)

2. **No Pagination** — Large result sets returned in full
   - Impact: Low for synthetic data; monitor at scale
   - Fix: Add optional `limit` parameter (future)

3. **Single-Level Hierarchy** — `get_wbs_hierarchy()` returns only immediate children
   - Impact: Low (agent chains calls for deeper trees)
   - Fix: Add optional `max_depth` parameter (future)

### No Critical Issues Identified ✓

---

## Deployment Checklist

### Before Deploying

- [x] Code reviewed for security (read-only, no SQL injection)
- [x] Tests passing (7/7 tools, 25/25 queries, 100% success)
- [x] Documentation complete (README, docstrings, API reference)
- [x] Error handling validated (0 unhandled exceptions)
- [x] Performance acceptable (<1s baseline; scale testing TBD)
- [x] Agent system prompt selected (v2 recommended)

### At Deployment Time

- [ ] Set the approved LLM settings in src/portable_llm_mcp/.env (LLM_PROVIDER=asksage, LLM_CHAT_MODEL ending in -gov, and the API key from the environment)
- [ ] Configure database path (settings.database_path)
- [ ] Enable audit logging (track tool calls, agent decisions)
- [ ] Set up monitoring (success rate, error rate, latency)
- [ ] Notify users of tool availability
- [ ] Document any capacity limits (e.g., max elements per query)

### Post-Deployment

- [ ] Monitor success rate (should stay >= 99%)
- [ ] Track error rate (should stay < 1%)
- [ ] Monitor latency p95 (should stay < 1s)
- [ ] Collect user feedback
- [ ] Plan for future enhancements (error types, pagination, deeper trees)

---

## Recommended Next Steps

### Short Term (Before Production)

1. **Finalize System Prompt** — Use v2 (explicit scope boundaries)
2. **Set Up Monitoring** — Log all tool calls for audit trail
3. **Document Scope** — Create user-facing guide on what queries are in/out of scope

### Medium Term (Post-Deployment)

1. **Scale Testing** — Test with real project data (>10k elements)
2. **Performance Optimization** — Profile and cache frequently accessed projects
3. **Batch API** — Add batch endpoints for multi-element queries

### Long Term (Feature Enhancements)

1. **Error Type Discrimination** — Return structured error objects
2. **Pagination** — Add limit/offset to search tools
3. **Deeper Hierarchies** — Add max_depth to `get_wbs_hierarchy()`
4. **Regex Support** — Complement SQL LIKE patterns

---

## Tool Usage Patterns (Observed)

Most commonly used tools in evaluation:

1. **get_wbs_lineage()** — 36% of queries (agent loves parent chains)
2. **search_wbs()** — 32% of queries (pattern matching primary use case)
3. **get_wbs_by_level()** — 24% of queries (level filtering)
4. **get_leaf_nodes()** — 24% of queries (structure analysis)
5. **get_project_info()** — 20% of queries (metadata)
6. **get_wbs_hierarchy()** — 20% of queries (immediate relationships)
7. **list_projects()** — 20% of queries (discovery)

**Insight:** Agent uses all 7 tools efficiently; none over-relied upon.

---

## Risk Assessment

### Low Risk ✓

- Read-only operations only (no mutations)
- Clear, well-documented tool schemas
- Robust error handling (no crashes)
- Comprehensive evaluation coverage
- Simple, maintainable codebase

### Identified Risks: None

No critical risks identified in evaluation or code review.

### Risk Mitigation

| Potential Risk | Mitigation |
|---|---|
| Performance degradation at scale | Scale testing, caching, batch APIs |
| Agent confusion on scope boundaries | Use v2 system prompt, provide clear documentation |
| Error propagation | Comprehensive error handling, audit logging |

---

## Success Metrics for Production

Once deployed, track these metrics:

| Metric | Baseline | Alert Threshold |
|--------|----------|-----------------|
| **Success Rate** | 100% (eval) | < 95% |
| **Error Rate** | 0% (eval) | > 1% |
| **Latency p95** | <1s (eval) | > 2s |
| **Tool Call Rate** | 1.6 calls/query (eval) | > 2.5 calls/query |
| **Scope Accuracy** | 100% (eval) | < 95% |

---

## Agent Developer Guide

### Quick Start

1. **Load tools** from PARS MCP server
2. **Use v2 system prompt** — includes scope guidance
3. **Check for error key** in all tool responses
4. **Chain tools efficiently** — discover, then inspect

### Best Practices

- Always call `list_projects()` first if project ID unknown
- Use `search_wbs()` with appropriate filters to reduce results
- Chain `get_wbs_lineage()` calls for structural analysis
- Handle empty results gracefully (not errors)
- Explain limitations to users (read-only scope)

### Avoid

- Calling `list_projects()` repeatedly (cache result)
- Ignoring `{"error": ...}` responses (check for error key)
- Attempting mutations (PARS is read-only)
- Relying on exact error message format (standardize in future)

---

## Decision Summary

### For Stakeholders

**PARS MCP is production-ready.** All evaluation criteria met:
- 100% success rate on 25 representative WBS queries
- All 7 tools functional and well-designed
- Robust error handling (0 crashes)
- Clear documentation for agent developers
- No critical issues identified

**Deployment Risk:** Low ✓

**Recommendation:** **DEPLOY** with v2 system prompt and post-deployment monitoring.

---

## Stakeholder Questions & Answers

### Q: Can this handle real project data?

**A:** Evaluation used synthetic data (25 projects). Scale testing with >10k elements recommended before high-volume production use. Baseline performance is acceptable (<1s per query). Monitoring will identify scaling issues.

### Q: What if the agent gets an out-of-scope request?

**A:** v2 system prompt explicitly guides out-of-scope handling. Evaluation showed 100% scope accuracy. Agent correctly declines mutations, predictions, and non-WBS queries.

### Q: How do I know if something fails?

**A:** Tool responses include `{"error": "..."}` dicts on failure. Agent checks for error key. Audit logging recommended to track failures. Success rate monitoring will alert on degradation.

### Q: Can I extend the tools?

**A:** Yes. Current design is extensible. New tools can be added via `register_tools()`. Future enhancements (pagination, regex, batch APIs) are planned non-breaking improvements.

### Q: What's the production SLA?

**A:** Baseline from evaluation: <1s per query, 100% success rate, 0 errors. Monitor these metrics post-deployment. Set SLA to p95 latency < 1s, success rate > 99%, error rate < 1%.

---

## Sign-Off

| Role | Status | Notes |
|------|--------|-------|
| **Evaluation** | ✓ PASS | 100% success rate, all criteria met |
| **Code Quality** | ✓ PASS | ruff, type hints, docstrings |
| **Documentation** | ✓ PASS | Complete (API, usage, troubleshooting) |
| **Integration** | ✓ PASS | Agent successfully uses all tools |
| **Security** | ✓ PASS | Read-only, no exposure risks |
| **Recommendation** | ✓ DEPLOY | Production-ready |

---

## Contacts & Resources

**Evaluation Framework:** Phoenix LLM-as-Judge
**Documentation:** `eval/phoenix/README.md`
**Source Questions:** `eval/phoenix/datasets/pars-eval-0/evaluation.xml` (and `pars-eval-1/`)
**Tool API:** `src/pars_local_mcp/mcp/tools.py` (tool docstrings)

---

**Report Date:** November 11, 2026
**Status:** Reported; run output not committed (see the review note at the top)
**Approval:** Ready for the 7-tool read-only scope, pending a reproducible run

---

## TL;DR

**Reported ready for the 7 read-only tools; not yet reproducible (see the review note at the top).**

- 50/50 tests reported passing (100% success rate)
- 7 read-only tools work correctly; the 9 pipeline tools were not evaluated
- Zero errors or crashes
- Clear documentation
- Low risk

**Use v2 system prompt. Monitor after deployment.**
