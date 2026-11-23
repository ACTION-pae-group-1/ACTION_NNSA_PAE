# BLS-002A: Catalog Search Normalization and Relevance Ranking
**Status:** Substantially mitigated; production changes retained, residual risks documented
**Classification:** Production MCP tooling (catalog search)
**Affected tool:** `search_series`
**Snapshot:** `eval_synthetic_world`
**Production revisions:** `3bf1ac4` (normalization/ranking), `fd67f78` (parent discovery)
**Evaluation case:** `commodity-series-selection` (unchanged)

## BLUF: Problem, Mitigation, Effect, Conclusion
**Problem:** Initial commodity-selection runs exposed zero-result searches for plausible descriptions, uniform `match_score=1.0` values, and repeated search/hierarchy calls. The six-query deterministic baseline returned the expected series within ten results for only 3/6 queries (50.0%) and returned no results for 2/6 (33.3%).

**Mitigation:** Implemented dependency-free query normalization, token matching, deterministic relevance ranking, and match explanations in production MCP tooling (`3bf1ac4`). Added hierarchy-backed broader-parent candidate discovery (`fd67f78`) without new dependencies or public tool-schema changes. The nine evaluation cases and numerical oracles were unchanged.

**Effect:** Deterministic Recall@10 improved from 3/6 (50.0%) to 5/6 (83.3%) after ranking and 6/6 (100.0%) after parent discovery. Zero-result queries fell from 2/6 to 0/6. The broad gypsum series `PCU327420327420` became discoverable at rank 3. Under the unchanged evaluation fingerprint, complete model episodes rose from 4/6 (GPT-5.4: 1/3; GPT-5.6: 3/3) before parent discovery to 6/6 (3/3 for each model) afterward. The latter comparison is descriptive, not proof of causation. Parent expansion increased observed search latency and model episodes still contained some zero-result searches.

**Conclusion:** Retain both targeted production improvements. Deterministic retrieval gains are verified and the final six model episodes all passed; nevertheless, small model samples, latency increases, and the GPT-5.4 post-change dirty-working-tree flag limit conclusions. Track search efficiency and period-availability-aware selection as residual risks; do not add a new evaluation case until justified independently.

## 1. Original observations and baseline

The original `search_series` implementation returned indistinguishable relevance scores for text hits. Models sometimes reformulated plausible queries or navigated the hierarchy to find suitable commodities. The initial 8- and 17-tool-call observations also included a separate simulated-user confirmation defect (BLS-001), so they cannot isolate search quality.

The standalone benchmark uses the rebuilt `eval_synthetic_world` snapshot, six expected-series queries, one empty-query browsing control, and three latency repetitions per query. It is a retrieval diagnostic, not a new model evaluation scenario.

| Query | Original expected-series rank | After ranking | After parent discovery |
|---|---:|---:|---:|
| `fabricated structural metal` | 1 | 1 | 1 |
| `structural metal products` | Not found | 6 | 6 |
| `ready-mix concrete` | 2 | 2 | 2 |
| `ready mixed concrete` | Not found | 2 | 2 |
| `gypsum products` | Not found | Not found | 3 |
| `PCU332312332312` (exact ID) | 1, with related hits | 1, exact only | 1, exact only |

Empty-query catalog browsing continued to return results in all three benchmark versions. The benchmark does not independently exercise every filter or invalid-argument path; focused tests and existing contracts cover those separately.

## 2. Changes and verification

- `3bf1ac4` (`feat(bls): improve catalog search normalization and relevance ranking`): normalized query and catalog matching, token retrieval, ranked scores, match explanations, and regression tests.
- `fd67f78` (`fix(bls): include broader parent series in catalog search`): hierarchy-backed parent candidate inclusion and regression coverage. Parent inclusion is an additional discovery signal, not a statement of economic suitability or guaranteed observation availability.
- The user reported focused tests passing after both interventions, and repository checks and evaluator self-test passing before the ranking commit. This lesson does not independently reproduce those local test logs.

| Deterministic metric | Original | After ranking | After parent discovery |
|---|---:|---:|---:|
| Recall@10 | 3/6 (50.0%) | 5/6 (83.3%) | 6/6 (100.0%) |
| Zero-result rate | 2/6 (33.3%) | 0/6 | 0/6 |
| Broad gypsum series rank | Not found | Not found | 3 |
| Exact series ID | Related results included | Exact only | Exact only |

The gypsum-query median latency increased from approximately 287 ms after ranking to 616 ms after parent expansion. The `ready-mix concrete` query increased from approximately 286 ms to 756 ms. Each median uses only three samples; these are diagnostic indications of additional work, not a statistically established latency regression.

## 3. Controlled model evaluations

| Stage | Git revision | GPT-5.4 | GPT-5.6 Luna | Combined |
|---|---|---:|---:|---:|
| Before ranking, post-confirmation workflow | `d45b07e` | 3/3 | 3/3 | 6/6 |
| After ranking, before parent discovery | `3bf1ac4` | 1/3 | 3/3 | 4/6 |
| After parent discovery | `fd67f78` | 3/3 | 3/3 | 6/6 |

The compared runs report evaluation fingerprint `e4ee5e08af67`, system-prompt fingerprint `f504a44b8aad`, tooling fingerprint `b5e4ddcf2000`, and snapshot `eval_synthetic_world`. The tooling fingerprint did not distinguish the production source revisions; Git SHAs and actual artifacts are therefore necessary to identify the code tested.

The intermediate GPT-5.4 failures selected the narrower gypsum series `PCU327420327420P`, which lacked the required 2014 observation, and did not complete recovery. The calculation tool's rejection of unavailable observations was appropriate. After parent discovery, all six episodes completed the expected source-backed calculation, with composite factor `1.5650` (56.50%) and all process, accuracy, format, and guardrail checks passing. There were zero infrastructure errors in the final two runs.

Final run evidence:

| Model | Run ID | Passes | Phoenix trace IDs |
|---|---|---:|---|
| GPT-5.4 | `20261118T191205Z-gpt-5.4-gov` | 3/3 | `26ef525082222fbacddd571095ff9a8e`, `0e81e60c24da03bc669660d6f0a8675a`, `318f349e8b47dba8a92e2b7d42eec1d1` |
| GPT-5.6 Luna | `20261118T192008Z-gpt-5.6-luna-gov` | 3/3 | `2ffe611c76cd66cd39b698f4900e322a`, `c058c29ec61196dc9dc948afd193715a`, `136c6297ef31def014c522c99ff7c4d7` |

The GPT-5.4 run records `git.dirty=true`; the GPT-5.6 run records `git.dirty=false`. Both report SHA `fd67f78`. The exact uncommitted changes, if any, are not established by the run record, so avoid claiming perfect checkout equivalence. Episode-level tool usage and intermittent zero-result searches remain diagnostic; the six successful episodes do not imply zero search failures.

## 4. Residual risks and follow-up

- **Availability:** A textually relevant narrow series can lack observations for the requested base/target period. The parent candidate is discoverable but is not automatically the right economic index.
- **Latency:** Hierarchy expansion adds measurable query time in the small benchmark. Profile and optimize only if a confirmed bottleneck justifies another production change.
- **Search behavior:** Model-generated restrictive queries can still return no results, and tool-call counts remain variable. Efficiency is diagnostic, not a hard grader threshold.
- **Ranking:** Heuristic relevance scores measure textual retrieval strength, not economic suitability; prevent false-positive parent expansion and preserve exact-ID, program, active-only, and limit behavior.
- **Comparability:** Preserve evaluation fingerprints, snapshot, model settings, and source revisions for any future controlled comparison. Do not interpret changes in pass rate from three repetitions as a causal estimate.

## 5. Disposition and evidence retention

**Decision:** Retain both BLS-002A production interventions; mark the identified retrieval-coverage defect substantially mitigated. Keep historical availability, efficiency, and latency as separate follow-up investigations rather than silently expanding this change.

Evidence: `BLS-002A-before.json`, `BLS-002A-after.json`, `BLS-002A-parent-after.json`; final and intermediate run `run.json`, `episodes.jsonl`, and `summary.md`. Store benchmark outputs under `eval/bls/results/benchmarks/`, scripts under `eval/bls/scripts/`, and patch downloads outside the repository. Do not commit generated results or credentials. The documentation update should be its own focused commit, separate from production MCP changes and evaluation-suite changes.
