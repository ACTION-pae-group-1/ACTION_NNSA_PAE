# The evaluation story so far

**Date:** 2026-11-16 · **Branch:** `main` · **Status:** two harnesses live, evidence pack planned

This page is the narrative version of the repo's evaluation work: what is
documented today, how it came to be, what the numbers say (and don't say),
what was learned, and what was changed because of it. Evidence pointers are
everywhere on purpose — this document should never be quoted without them.

---

## 1. What is documented today

| Harness / doc | What it is | Where |
| --- | --- | --- |
| **BLS conversation evals** | Scripted-user episodes driving the real BLS escalation server; graded programmatically on **process, accuracy, answer format, guardrails** | [`eval/bls/`](../eval/bls/README.md), runner `python -m eval.bls.runner`, poe tasks `eval-selftest` / `eval` / `eval-report` |
| **Grader self-test** | Oracle agents must pass every check; deliberately flawed agents must fail exactly the check they are designed to defeat | `eval/bls/results/SELFTEST.md` |
| **Recorded model runs** | 7 run directories from 3 local open-weight models (gpt-oss 20b, qwen3 14b, gemma4 12b), each with `run.json` + `summary.md` + `episodes.jsonl` (+ `errors.jsonl` for infrastructure failures) | `eval/bls/results/runs/` |
| **PARS LLM-as-judge harness** | `PARSAgent` + Phoenix judges (`match_expected_response`, `check_answer_scope`), datasets `pars-eval-0` (25 queries, frozen) and `pars-eval-1` (60), prompts v1/v2, loopback-only tracing with JSONL fallback | [`eval/phoenix/`](../eval/phoenix/README.md) |
| **PARS deployment-readiness summary** | Unsupported claim, not a result: the page's "100% on 50/50 examples" has no recorded run output and is flagged for correction. The Phoenix read-only allowlist exposed 7 of the 16 registered PARS tools; those 7 were exercised on the synthetic seed. The other 9 were not evaluated. | [`eval/DEPLOYMENT_READINESS_SUMMARY.md`](../eval/DEPLOYMENT_READINESS_SUMMARY.md) |
| **Ask Sage smoke/eval scripts** | Direct OpenAI-compatible checks of the approved endpoint and model list; tool traces (which may contain internal catalog metadata) stay out of Git, per-model CSV summaries are observational metrics and commit-worthy | [`eval/asksage/`](../eval/asksage/README.md) |
| **Evidence-pack outline** | Planned 8-section `EVALUATION.md` with `[have]`/`[pending]`/`[write]` markers, including the first-pass results table and the lessons below | [`eval/EVALUATION_DOC_OUTLINE.md`](../eval/EVALUATION_DOC_OUTLINE.md) |

---

## 2. The story, in order

**Phase 1 — prove the graders before spending on models.** The BLS harness
was built so that `poe eval-selftest` needs no model, key, or network and
exits non-zero unless the oracle agents pass everything *and* each flawed
agent fails exactly the checks it should. That self-test is the method's core
claim: the rubric is validated by adversarial cases, not by vibes.

**Phase 2 — baseline with local models.** Three open-weight models via a
loopback Ollama endpoint were run across 3 cases × 3 repetitions at commit
`34eb702`, with fingerprints recorded for the eval, tools, and system prompt
so runs can be compared (`poe eval-report --compare`).

**Phase 3 — the iteration loop paid for itself immediately.** The first
recorded runs exposed (a) a recorder bug — its own output folder made every
later run read as "uncommitted changes" — and (b) the harness-limit findings
in §4. Both changed the repo before any model was judged again.

**Phase 4 — an LLM-as-judge harness for the second server.** The PARS tool
server got the Phoenix harness from the `mcp-eval` skill, deliberately
adapted: the agent is the repo's portable `MCPAgent`/`MCPHub` (no LangChain —
`eval/phoenix/tests/test_approved_imports.py` fails if that ever changes),
traces go only to a loopback Phoenix with a JSONL fallback, and both agent
and judge calls go through the approved client (Ask Sage `-gov` models or
local Ollama; public endpoints are refused at config load).

**Phase 5 — documentation caught up.** The read-me layer had drifted from
what the harnesses are (see §5); it was synchronized in the working tree on
2026-11-16: `eval/README.md` no longer claims the Phoenix harness "has not
built", the readiness summary no longer points at three documents that never
existed, and the mcp-eval skill now describes the harness it actually ships.

---

## 3. The numbers, read honestly

**BLS (harness test, not a model verdict).** First-pass episodes, all checks
passed per model: **gpt-oss 20b 0/7, qwen3 14b 0/9, gemma4 12b 0/9** — but
23 of 25 scored episodes ended because the simulated user never answered a
legitimate request (§4, lesson 1). The stable headline across every run:

- **guardrails held in every recorded run, measured:** 100% in six of the
  seven runs; the worst run (qwen3, `20261116T021942Z`) scored **26/27 (96.3%)**
  — every episode catalog-searched before using a series and none calculated
  from agent-typed index values, but one qwen3 episode attempted a live BLS
  call. The grader records that as a failed "no live BLS API call" check
  (8/9 for that check); the server's behavior in that attempt — refusing
  safely because no key is configured, so no unauthenticated request left
  and no number was invented — is a property of the server, reported
  separately from the grader rate. Failure modes were loud and safe,
  never invented numbers.
- gemma4's better showing (one successful `calculate_index_from_bls` through
  the mixed quarterly-to-annual case, ~38% process checks in the later run)
  versus the other models points at what tool ergonomics can and can't
  absorb.

**PARS (what is recorded).** The recorded `pars-eval-0` v1 runs show
correctness between **24% and 84%**. The 84% figure is **not validated**: the
calibration sheet has no human verdicts. **No v2 run is recorded**, so v2 is
**not evaluated** and no prompt version is recommended on this evidence.
`pars-eval-1` (60 queries) has **no recorded execution**.

What the record does support: the Phoenix read-only allowlist exposed **7 of the
16 registered PARS tools**, and those 7 were exercised on the synthetic seed
(proj_001 Alpha, 34 elements; proj_002 Beta, 25 elements). The other 9 were
**not evaluated**: validate_wbs_inputs, clean_wbs_data, tune_and_train_wbs,
predict_wbs, write_back_wbs, run_wbs_pipeline, get_wbs_run_status,
get_wbs_project_descriptions, get_wbs_rows. Their read-only status is
unverified and is not claimed here. Correctness and scope are **unvalidated**
until human verdicts exist.

**CAEF classification and inference were not part of any PARS Phoenix
evaluation.** The PARS harness does not establish end-to-end CAEF integration.

**Unsupported claims, not results.** The 2026-11-11 readiness figures ("100%
correctness and scope, 50 of 50", "v2 recommended for deployment") have no
recorded artifact behind them. They are unsupported and must not be cited as
evaluation results. The readiness summary is flagged to the user for
correction.

Caveat the doc itself carries: synthetic data; scale tests with real project
data are still TBD.

---

## 4. Lessons learned (each with its evidence)

1. **Validate the simulated user against real model phrasing, not only
   scripted agents.** It replies only to sentences ending in `?` containing a
   keyword; "Please confirm if you would like to proceed." went unanswered in
   12 episodes. Every first-pass BLS score is partly a measurement of this.
2. **Tools that silently accept bad input send models in circles.** gpt-oss
   invented tool fields (`keywords`, `class`, `year`), got an empty query,
   and returned the same unrelated first page up to ten times. Strict schemas
   (`extra="forbid"`) produce errors a model can actually correct.
3. **Error messages must say how to recover.** 20 of 29 tool errors were
   `search_series` program filters — models passed `PPI`/`ECI` where `pc`/`ci`
   are required, and the message didn't say so.
4. **Workflow order must be visible from the tools.** Models calculated
   before `save_index_spec` ("Specification not found") and never called
   `validate_index_spec` unprompted.
5. **The guardrails held under a weak agent — measured, not assumed.**
   26/27 guardrail checks in the worst run (96.3%), 100% in all others; the
   single miss (a qwen3 live-BLS attempt) was refused safely by the server,
   which the grader records separately from the pass rate (§3). The
   strongest finding to present.
6. **Infrastructure failures stay out of the scores.** Nine episodes of one
   qwen3 run died on HTTP errors; `errors.jsonl` recorded them and the
   scoring excluded them, as designed.
7. **Record fingerprints and check the record itself.** The recorder bug
   (§2) would have been invisible without fingerprints showing the code under
   test was unchanged across runs.
8. **Local model speed varies widely** (~10 s/episode on gemma4, up to
   5 min on qwen3) — repetitions on a laptop are bounded, favor `--repetitions`
   planning by model.
9. **Skills, readmes, and reality can drift apart silently.** A skill audit
   found the mcp-eval skill prescribing env vars and dependencies the harness
   no longer uses (a LangChain stack that a test actively bans), plus three
   stale docs. Lesson: audit the guidance the agents follow as part of doc
   hygiene.
10. **No CI means no second opinion.** The evaluation harnesses are the only
    automated evidence layer while the CI workflow remains disabled
    ("enterprise GitHub cannot create a runner") — which raises, not lowers,
    the bar on recorded-run discipline.

---

## 5. Changes and fixes made

| Fix | Why | Where |
| --- | --- | --- |
| Recorder bug: output folder polluted git-state metadata, marking later runs "uncommitted changes" | First-pass runs exposed it; fingerprints proved code was unchanged | fixed in **PR #19** |
| Root-cause hardening of series validation (`pc`/`ci` stronger validation; sample-data hash updates) | Lesson 3 | commit `188b298` |
| Timeout and system-path fixes for local/eval runs | Lessons 6 & 8 friction | commit `dab4a4e` |
| Doc/skill synchronization (this cycle, 2026-11-16) | Lesson 9: `eval/README.md`, `eval/DEPLOYMENT_READINESS_SUMMARY.md`, `CONTRIBUTING.md` drift; the mcp-eval skill's env-var/dependency/launch sections corrected in both copies | working tree of `main` |
| LangChain-family dependencies removed from the `dev` group; `uv.lock` re-locked | The rewritten harness enforces no-LangChain; dependencies described a harness that no longer exists | `pyproject.toml`, verified with `eval/phoenix/tests/test_approved_imports.py` (24 passed) |
| CONTRIBUTING.md made to match the real hook set (`ruff-fix-and-stage`, `pytest-full` on `manual`, `tdd-companion-gate`); phantom `enforce-tdd` scripts and the "508 tests" counts removed | Same audit as above; the doc named checks that never run | `CONTRIBUTING.md` |

---

## 6. What's next

- [ ] Broaden the simulated user's matching (imperatives, whole-message
      questions) and add flawed-phrasing cases to the self-test; note the
      simulated-user version with every quoted score (lesson 1).
- [ ] `extra="forbid"` on tool request models; then rerun the same three
      models with unchanged tools to show the comparison loop
      (`poe eval-report --compare`).
- [ ] Error text that names the valid `pc`/`ci` codes; "save first" in the
      "Specification not found" path (lessons 2–4).
- [ ] Frontier-model run through the approved client (the evidence pack's
      main `[pending]` item; see the outline's markers).
- [ ] Turn on a working CI pipeline or formally document its replacement —
      the readiness verdict currently rests on local hooks and recorded runs
      (lesson 10).
- [ ] Build the slide-deck diagrams from [`docs/DIAGRAM_PROMPTS.md`](DIAGRAM_PROMPTS.md)
      (system architecture, data pipeline, both eval harnesses, story timeline).
- [ ] Write `EVALUATION.md` from the outline, linking SELFTEST.md, one
      `run.json`, and this page.

## Reproducing

```bash
uv run --locked poe eval-selftest   # grader self-test; no model or network
uv run --locked poe eval            # a recorded model run (requires LLM_* env)
uv run --locked poe eval-report     # read results back; --compare across runs
# PARS harness: see eval/phoenix/README.md (create_dataset / run_experiment)
```
