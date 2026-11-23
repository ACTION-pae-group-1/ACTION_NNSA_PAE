# Evaluation document — outline

The hackathon deliverable next to the repo and the slide deck. This is its
planned skeleton: section by section, what it will claim and where each
claim's evidence lives. Status markers: **[have]** material already in the
repo (self-test, committed runs), **[pending]** needs a real-model run with
`LLM_*` credentials, **[write]** prose to draft.

Suggested file name for the finished document: `EVALUATION.md` at the repo
root, linked from QUICKSTART and the slide deck's evidence slide.

1. **What we evaluated and why** — [write]
   The question the document answers: can a model with no other context
   drive the BLS server's tools to a defensible escalation answer — and can
   we *prove* it fails loudly on bad data instead of inventing numbers?
   One paragraph; the roadmap milestone this closes is M4' (eval evidence
   pack).

2. **System under test** — [have]
   - Server: in-process, through a real MCP client (`eval/bls/world.py`).
   - Environment: a deterministic synthetic snapshot
     (`snapshot_id=eval_synthetic_world`) built from committed manifests —
     same ingestion pipeline as a real snapshot, so findings generalize to
     published data.
   - Models: [have, first pass] three local open-weight models via ollama
     (gpt-oss 20b, qwen3 14b, gemma4 12b), 3 repetitions × 3 cases each,
     all at commit `34eb702` with identical fingerprints (eval
     `f492beb25f0f`, tools `c4e045d4a227`, prompt `7f948ad17ecb`). A
     frontier-model run is still [pending]. Record temperature once the
     runner records it (it does not yet).

3. **Method: conversation evals, graded by contract, not vibes** — [have]
   - Three cases: known basket; mixed materials+labor basket exercising
     quarterly-to-annual alignment; open-ended negotiated basket.
   - A simulated user drives each episode; every episode runs the real
     server with tools — no mocks in the loop.
   - Gradables are programmatic checks over the transcript and the server's
     own outputs, grouped in four dimensions: process, accuracy, answer
     format, guardrails.
   - Grader validation: reference "oracle" agents must pass every check,
     and deliberately flawed agents (alignment hiding, misattributed
     quarters, …) must fail exactly the checks they are designed to defeat
     (`EXPECTED_FAILURES` self-test). This is what makes the rubric
     trustworthy; present it as the method's core claim.

4. **Results** — tables generated from recorded runs — [have for self-test /
   scripted agents], [have, first pass, for model episodes; see section 5
   before quoting any score]
   - Self-test summary (committed: `eval/bls/results/SELFTEST.md`): graders
     work, flawed agents fail as designed.
   - Scripted-agent baselines by case and check.
   - Real-model episodes: pass rate per dimension, per case, per repetition;
     the specific checks the model struggles with (expected: alignment
     disclosure phrasing, refusing to recompute decimals).
   - Comparison table across runs (`poe eval-report --compare`), including
     any prompt/tool-doc fixes prompted by an early run — that iteration
     loop is itself evidence of evaluation value.

5. **Early results and lessons learned** — [have]; source for the slide
   deck's lessons-learned section

   **First-pass results** (`eval/bls/results/runs/`, committed in PR #19):

   | Model | Scored episodes | All checks | process | accuracy | format | guardrails |
   | --- | --- | --- | --- | --- | --- | --- |
   | gpt-oss 20b | 7 (+2 endpoint errors) | 0/7 | 26% | 0% | 0% | 100% |
   | qwen3 14b | 9 | 0/9 | 26% | 0% | 0% | 96% |
   | gemma4 12b | 9 | 0/9 | 38% | 11% | 12% | 100% |

   **Read these as a test of the harness, not of the models.** Classifying
   how each of the 25 scored episodes ended: 23 stopped because the
   simulated user did not answer a legitimate request from the agent, one
   ended without a calculation, and one reached a successful
   `calculate_index_from_bls` call (gemma4, mixed basket). The scores
   above mostly measure that harness limit.

   Lessons, each with its evidence and what we changed or will change:

   1. **The simulated user was too literal, and it shaped every score.** It
      replies only to sentences ending in `?` that contain one of its
      keywords. "Please confirm if you would like to proceed." got no reply
      (12 episodes), and so did "Could you provide these details?" when the
      keywords were in the list above it (11 episodes). Lesson: validate
      the simulated user against real model phrasing, not only against
      scripted agents, before reading any score. *To do:* broaden its
      matching (imperative requests, the whole message when it asks
      something) and add flawed-phrasing cases to the self-test.
   2. **Tools that silently accept bad input send models in circles.**
      gpt-oss called `search_series` with invented fields (`keywords`,
      `class`, `year`). The request model ignored them, ran an empty
      query, and returned the same unrelated first page (abrasives) up to
      ten times in a row. A strict schema that rejects unknown fields would
      have produced an error the model could correct. *To do:*
      `extra="forbid"` on tool request models.
   3. **Error messages must say how to recover.** 20 of 29 tool errors were
      `search_series` program filters: models passed `PPI`/`ECI` (or `{}`)
      where the codes `pc`/`ci` are required. The message says only "must
      be exactly two lowercase letters". *To do:* list the valid codes in the
      error and the tool description, or accept the program names as
      aliases.
   4. **The workflow order is not obvious from the tools.** Three
      `calculate_index_from_bls` calls failed with "Specification not
      found" because the model calculated before `save_index_spec`. No model
      called `validate_index_spec` in any episode, although the system prompt
      asks for it. *To do:* say "save first" in the not-found error and the
      tool description. Separately, decide whether the rubric should require
      a step that `calculate_index_from_bls` already performs internally.
   5. **The guardrails held under a weak agent.** Every episode searched the
      catalog before using a series, none calculated from index values the
      model typed in, and the one live-BLS attempt (qwen3,
      `get_series_data`) was refused safely because no key is configured.
      This is the strongest finding to present: failure modes were loud and
      safe, never invented numbers.
   6. **Infrastructure failures must stay out of the scores.** The local
      endpoint returned HTTP errors 13 times across the trial runs (all 9
      episodes of one qwen3 run). The runner recorded them in `errors.jsonl`
      and excluded them, as designed, so an outage did not read as bad
      behaviour.
   7. **Record enough to compare runs, and check the record itself.** The
      first runs exposed a recorder bug: its own output folder marked every
      later run "uncommitted changes" (fixed in PR #19). Fingerprints showed
      the code under test was unchanged, which is why they are recorded.
   8. **Local model speed varies widely.** Episodes took about 10 s on
      gemma4 and up to 5 min on qwen3, which limits how many repetitions are
      practical on a laptop.

   *Next run, so the deck can show the iteration loop:* fix lesson 1, rerun
   the same three models with unchanged tools, then fix lessons 2–4 and
   rerun again. Show both comparisons with `poe eval-report --compare`.

6. **Correctness and disclosure analysis** — [have], [write]
   - The alignment story: quarterly-only ECI series resolved via Q04 with
     disclosure in component periods, ledger warnings, provenance notes —
     evals assert the model passes the disclosure through to the user.
   - Missing data: incomplete years are omitted with warnings, never
     zero-filled or interpolated; the eval asserts the model reports them.
   - Numeric contract: decimal strings from the server, quoted not
     recomputed; the UI's `validatePayload` re-checks every artifact before
     display.

7. **Threats to validity** — [write]
   - Synthetic data may not stress real-file edge cases (footnotes,
     revised releases).
   - Scripted users cannot produce the full diversity of a human
     interlocutor.
   - Single-snapshot world; no live BLS claims are made.
   - Model-agent scaffold is the bundled `portable_llm_mcp` loop, not a
     bespoke harness.
   - The simulated user's keyword matching ended most first-pass episodes
     early (section 5, lesson 1); any score quoted must say which
     simulated-user version produced it.
   - First-pass models are small local models; results do not predict
     frontier-model behaviour.

8. **Reproducing** — [have]
   - `poe eval-selftest` (no model or network; exit nonzero on any grader
     regression), then `poe eval` / `runner --agent model --repetitions N`,
     and reading back results with `poe eval-report`.
   - Point judges at `eval/bls/README.md` and one recorded `run.json`.

9. **Appendices** — [have / write]
   - A. Check catalog: every grader, its dimension, and its failure text
     (generated).
   - B. Run catalog: run IDs, dates, agents, case×check pass matrix.
   - C. Decisions the methodology depends on (Q04 anchor policy, weights
     rescaling tolerance) cross-referenced to `DECISIONS.md`.

## Drafting order

1. Sections 2–3 and 8 can be written today from committed material.
2. Done for local models: first-pass runs recorded; lessons in section 5.
3. Fix the simulated user (lesson 1), rerun, and update sections 4–5 with
   the comparison; then a frontier-model run; then revise section 1's
   headline sentence.
4. Sections 6, 7, 9 last; generate appendices from `eval-report` output
   rather than writing them by hand.
