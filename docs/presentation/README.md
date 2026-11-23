# Judges' deck and diagrams

A 27-slide deck for the hackathon judges, and the nine diagrams requested in
[`docs/DIAGRAM_PROMPTS.md`](../DIAGRAM_PROMPTS.md). The deck tells the story of
one escalation estimate, maps the repository's evidence to each judging
criterion, and ends with future work and an appendix of architecture and
evaluation diagrams.

## Files

| Path | What it is |
| --- | --- |
| `mcp_group_1_judges_deck.pdf` | The deck, one 1920×1080 slide per page, speaker notes hidden |
| `SPEAKER_NOTES.md` | The speaker notes for every slide, with the evidence each slide cites |
| `diagrams/svg/` | The nine diagrams as editable SVG (1920×1080 canvas) |
| `diagrams/png/` | The same diagrams rendered to 1920×1080 PNG |
| `source/` | The deck's source files (`deck.json`, `deck.css`, one HTML file per slide) |

## Status of the deck and PDF (competition closeout)

**The PDF is outdated and was not regenerated.** `mcp_group_1_judges_deck.pdf` is dated 2026-11-17. It describes the BLS escalation work and predates the competition closeout. Do not present it as the current state of the NNSA Cost Intelligence competition demonstration.

- **Why it was not regenerated:** the repository has no build script for the PDF. `source/deck.json` names an external builder, and the slide HTML refers to `/_blob/` image assets that are not in the repository. No PDF toolchain was verified locally, and nothing was installed.
- **Historical figures, not closeout results:** the commit `32f896f` reference and the test figure of 1,191 passed, 4 failed, 6 errors, 6 skipped, 1 xfailed (a 2026-11-17 clean-clone full run) are historical. The closeout did **not** run the full repository suite. The closeout's isolated suite result is 662 passed, 4 skipped, 1 xfailed, 0 failed.
- **Not current evidence, excluded from competition evidence:** the deck is outdated and was not regenerated (no verified build tooling in the repository). Do not cite its figures as closeout results.
- **Not claimed in the deck:** the in-app CSV button is blocked on hosts without the open-link handler. The three competition distinctions are: (1) PARS MCP retrieves and displays synthetic PARS WBS data; (2) CAEF 2.0 inference runs on the compatible synthetic dataset, project 100 (backend-verified per the integration owner); (3) PARS-to-CAEF inference for proj_001 and proj_002 is BLOCKED by missing source fields and preprocessing reference data. The model does not generate labels for proj_001 or proj_002. The analyst-authored WBS-to-BLS mapping is not machine-learning-powered. The standalone PARS Phoenix result (reported 2026-11-11, 100 percent, 50 of 50) is historical and reported only; it does not establish end-to-end CAEF integration. Current status is in `docs/COMPETITION_DEMO_QUICKSTART.md`.

## Before presenting

The deck's facts were checked against `main` at commit `32f896f` and a
clean-clone run on 2026-11-17. Since then, all six fixes on slide 18
("Six fixes that protect the score"): the sample-data hashes, the strict
program-code tests and the `data` import clash, the two allowlist entries, the
PARS readiness summary, ruff, and `deploy/README.md`. Before presenting:

- Move slide 18's items from future work to done, and refresh the slides that
  quote the old state: the fresh-clone "SHA-256 mismatch" on slide 7, the
  1,191-test count on slides 8 and 10, and the ruff count on slide 9.
- Fill in the `[Team name]` and `[Presenter names]` placeholders on slide 1.

## Diagrams

Each diagram follows its prompt in `docs/DIAGRAM_PROMPTS.md`, with corrections
where the prompt disagreed with the code. Slide 27 (Appendix A6) lists every
correction and the reason for it.

| # | Prompt | Files (`diagrams/svg`, `diagrams/png`) | Slide |
| --- | --- | --- | --- |
| 1 | System architecture | `1_system_architecture` | 22 (Appendix A1) |
| 2 | Data pipeline | `2_data_pipeline` | 23 (Appendix A2) |
| 3 | Eval harness A, BLS | `3_eval_harness_bls` | 24 (Appendix A3) |
| 4 | Eval harness B, PARS | `4_eval_harness_pars` | 25 (Appendix A4) |
| 5 | Evaluation timeline | `5_evaluation_timeline` | 26 (Appendix A5) |
| 6 | Two questions, two evidence paths | `6_two_evidence_paths` | 4 |
| 7 | Where the factor came from | `7_where_factor_came_from` | 5 |
| 8 | What we can demonstrate today | `8_demonstrate_today` | 6 |
| 9 | The running example | `9_running_example` | 3 |

The SVGs import into PowerPoint (Insert, Pictures) and stay editable there.
