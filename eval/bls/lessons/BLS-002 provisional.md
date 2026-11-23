# BLS-002: Catalog Search Relevance and Efficiency

**Status:** Partially mitigated; verification pending
**Classification:** Production MCP search behavior
**Affected tool:** `search_series`
**Mitigation:** Hyphen/whitespace search normalization
**Verification revision:** `d45b07e`
**Snapshot:** `eval_synthetic_world`

## BLUF: Problem, Mitigation, Effect, Conclusion

**Problem:** Initial evaluations revealed that commodity searches sometimes returned zero results for relevant descriptions, search results used non-discriminating relevance scores, and models performed repeated searches to identify suitable PPI series. These behaviors increased tool usage and created risks of selecting inappropriate indexes or failing to complete escalation calculations.

**Mitigation:** Introduced a targeted production search change to normalize hyphenated and space-separated commodity terminology. Added a deterministic regression test intended to protect the new behavior. The existing nine evaluation scenarios and numerical oracles were preserved.

**Effect:** In the uploaded post-change evaluations, GPT-5.4 passed 3/3 episodes and GPT-5.6 Luna passed 3/3, with all required process, accuracy, format, and guardrail checks passing. The combined success rate was 100% (6/6). However, GPT-5.6 still performed nine catalog searches in one episode, and the returned relevance scores remained non-discriminating. The evaluation fingerprint differed from the earlier baseline, so the pass-rate increase cannot yet be attributed to the MCP change.

**Conclusion:** Retain the targeted normalization change provisionally. The evaluation confirms successful end-to-end behavior in six episodes but does not independently establish that the normalization fix improved retrieval. BLS-002 remains open pending deterministic retrieval verification and fingerprint investigation. Broader ranking improvements should be considered separately.

## 1. Original failure and root-cause hypothesis

The initial investigation identified zero-result searches for semantically relevant commodity descriptions and repeated catalog searches.

The search implementation used constant relevance scores for text matches, limiting the information available to agents when comparing candidate series.

Hyphenation and whitespace differences were identified as one plausible retrieval weakness.

The working hypothesis was that normalizing these variations would improve catalog discovery without changing the economic suitability or hierarchy of the returned indexes.

## 2. Implemented mitigation

The targeted patch modifies the catalog search implementation to treat hyphens and spaces equivalently during literal matching.

A deterministic regression test was added to cover the affected query behavior.

The change does not intentionally modify:

- PPI series definitions or observations.
- Hierarchy relationships.
- Escalation calculations.
- Existing evaluation scenarios or numerical oracles.
- Simulated-user confirmation behavior.

## 3. Post-change evaluation results

| Run | Model | Passes | MCP calls |
|---|---|---:|---|
| `20261118T180714Z-gpt-5.4-gov` | GPT-5.4 | 3/3 | 15, 12, 13 |
| `20261118T181135Z-gpt-5.6-luna-gov` | GPT-5.6 Luna | 3/3 | 14, 18, 13 |

Both runs reported:

- Git revision: `d45b07e`
- Evaluation fingerprint: `e4ee5e08af67`
- Tooling fingerprint: `b5e4ddcf2000`
- System-prompt fingerprint: `f504a44b8aad`
- Snapshot: `eval_synthetic_world`
- Infrastructure errors: 0

All six episodes satisfied every required grader check.

The calculated composite factor was `1.5650`, corresponding to 56.50% escalation from 2014 to 2026 annual averages.

## 4. Search behavior observations

GPT-5.4 performed four `search_series` calls in each episode.

GPT-5.6 performed four, nine, and four searches across its three repetitions.

The nine-search episode included alternate terminology for ready-mix concrete, demonstrating continued query reformulation despite successful eventual completion.

Catalog results also continued to report constant relevance scores of `1.0` for multiple text matches.

These observations establish that search efficiency and candidate ranking remain areas for investigation.

They do not, by themselves, demonstrate a defect in the normalization patch.

## 5. Before-and-after comparison

| Model | Earlier baseline | Post-change |
|---|---:|---:|
| GPT-5.4 | 2/3 | 3/3 |
| GPT-5.6 Luna | 3/3 | 3/3 |
| Combined | 5/6 | 6/6 |

The apparent improvement is descriptive rather than a validated causal effect.

The earlier evaluation fingerprint was `6fd3b49c23a0`; the new fingerprint is `e4ee5e08af67`.

The tooling fingerprint remained unchanged at `b5e4ddcf2000`.

These differences require investigation before the results can be used as a controlled MCP before-and-after comparison.

## 6. Remaining verification

Before closing BLS-002:

1. Confirm that hyphenated and space-separated queries return the expected catalog candidates under the same synthetic snapshot.
2. Record deterministic before-and-after retrieval outcomes.
3. Verify the focused regression test and repository checks.
4. Investigate the changed evaluation fingerprint and unchanged tooling fingerprint.
5. Determine whether the nine-search GPT-5.6 episode represents avoidable search behavior or reasonable candidate exploration.
6. Run appropriate broader regression evaluations if the targeted change is retained.

## 7. Regression risks

- Normalization may introduce false-positive matches.
- Existing exact series-ID searches must remain correct.
- Search results may remain poorly ranked even when recall improves.
- Broad and narrow series may be confused.
- Search improvements may change model tool-use patterns without improving economic suitability.

## 8. Disposition

**Decision:** Retain provisionally; do not close BLS-002 yet.

The post-change evaluation demonstrates successful calculation workflows but does not isolate the effect of the normalization change.

The next action is a focused deterministic retrieval comparison, followed by a documentation update recording confirmed outcomes.

Additional evaluation scenarios remain queued until the current MCP improvement is verified.

## 9. Evidence

**Post-change runs:**

- `20261118T180714Z-gpt-5.4-gov`
- `20261118T181135Z-gpt-5.6-luna-gov`

**Evidence files:** `run.json`, `episodes.jsonl`, `summary.md`

**Git revision:** `d45b07e`

**Documentation commit:** Pending.
