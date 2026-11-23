# BLS-###: [Concise issue title]

**Status:** [Open / Diagnosed / Mitigation pending / Verification pending / Resolved / Partially resolved]
**Classification:** [Production MCP defect / Evaluation-design defect / Model behavior / Infrastructure / Undetermined]
**Models and cases:** [Identifiers]
**Original run and trace:** [Run ID; Phoenix trace ID]
**Original Git revision:** [SHA]
**Verification revision:** [SHA, if applicable]
**Evaluation / tooling / prompt fingerprints:** [Values]
**Snapshot:** [Identifier]
**Expected oracle:** [If applicable]

## BLUF: Problem, Mitigation, and Effect

**Problem:** [Describe what the initial run actually showed, the first workflow divergence, and the impact. Distinguish observation from hypothesis.]

**Mitigation:** [Describe the specific change, its location, and whether it modifies evaluation design or production MCP tooling. If no mitigation has been implemented, state "Proposed; not implemented."]

**Effect:** [Report measured post-change outcomes with denominators, models, run counts, and residual failures. If not yet verified, state "Not yet measured." Avoid implying causal improvement when fingerprints differ.]

**Conclusion:** [State disposition, what the evidence supports, what remains unresolved, and whether before/after results are comparable.]

## 1. Original observed behavior

[Run IDs, exact observed tool calls and outputs, failed grader checks, and first divergence. Quote only the minimum relevant transcript evidence.]

## 2. Root-cause analysis

**Confirmed observations:** [Evidence]
**Hypotheses:** [Possible causes, separately labeled]
**Classification and rationale:** [Evaluation / MCP / model / infrastructure / undetermined]

## 3. Mitigation or proposed intervention

[Files and behavior changed; why this is the smallest justified intervention; numerical oracles and other invariants preserved. Distinguish proposed from implemented.]

## 4. Verification and comparison

| Run ID | Model | Revision | Evaluation fingerprint | Tooling fingerprint | Passed / Scored | Infrastructure errors |
|---|---|---|---|---|---|---|
| [Run] | [Model] | [SHA] | [Fingerprint] | [Fingerprint] | [n/N] | [n] |

[Record focused tests, quality checks, evaluator self-test, grader-level outcomes, tool calls, latency, and broader regression results. Mark unexecuted checks "Not run." Treat infrastructure failures as unscored.]

## 5. Residual failures and follow-up

[Describe each materially distinct remaining failure and its evidence. Cross-reference existing issues before proposing new evaluation cases.]

## 6. Regression risks

[Document concrete risks introduced by the change and corresponding deterministic checks. Do not add evaluation cases solely to increase coverage.]

## 7. Comparability and interpretation

[Explicitly state whether model, case, snapshot, evaluation fingerprint, prompt fingerprint, and tooling conditions permit a defensible before/after comparison. An evaluation-design change is not a production MCP gain.]

## 8. Outcome and disposition

**Decision:** [Retain / Revise / Revert / Pending]
**Status:** [Current status]
**Next action:** [One prioritized action; new evaluation work remains queued until the current MCP improvement is verified.]

## 9. Evidence references

[Original and verification run IDs, Phoenix traces, episode records, run.json, summary.md, snapshot ID, Git SHAs, and approved evidence-store location. Do not commit generated runs or credentials.]

## 10. Commit record

**Change type:** [Evaluation-only / Production MCP / Documentation-only]
**Commit message:** [One focused commit per update]
**Commit SHA:** [SHA after commit]
**Scope:** [Confirm evaluation-suite and production MCP changes were not mixed in the same experiment.]
