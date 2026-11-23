# High-level diagram prompts (SVG for PowerPoint)

Prompts for an SVG-generating model to produce the five high-level diagrams the
story needs — one per slide, 16:9, 1920×1080. Each section gives the outline
(what the diagram claims), the elements, and a ready-to-paste prompt.

**How to use:** paste the Shared render spec once at the top of your session,
then paste the diagram prompt. Or paste the shared spec + prompt together as a
single message per diagram. Generate each diagram as its own standalone SVG —
they are designed to be independent slides. **Fact-checked deck-flow option
(see below) recommends proposal A with the two-column diagram (prompt 6) as
slide 2; the standing five-diagram set then serves as the backup/appendix
slides.**

---

## Shared render spec (paste before any diagram prompt)

```text
You will draw a single standalone SVG diagram for use as a Microsoft PowerPoint slide graphic.

Hard constraints:
- Exactly one SVG root element; viewBox="0 0 1920 1080", width="1920" height="1080" (16:9).
- Inline CSS only in one <style> block; no JavaScript, no external images, fonts, or references of any kind.
- All text as real <text> elements (never outlined paths or embedded images) so it stays crisp and selectable in PowerPoint.
- Fonts: "Segoe UI", Arial, sans-serif. Title 64px, box labels 30–34px, edge labels 26px. Nothing below 24px anywhere.
- Palette: background #F7F8FA; card fill #FFFFFF with 1.5px stroke #1A1D21 (rx=12); ink #1A1D21; secondary text #4B5563; single accent #2563EB for emphasis and arrowheads; semantic accents — green #0F766E (something that held/passed), amber #B45309 (attention), red #B91C1C (failure/blocked). All text meets WCAG AA contrast on its background.
- Flat design only: no gradients, no drop shadows heavier than a subtle 0/2/8 rgba(0,0,0,.08) filter, no textures, no 3D perspective.
- Arrowheads via a single reusable <marker>; lines ≥2.5px; generous minimum spacing so no element overlaps.
- Include a brief <title> child on the root describing the diagram.
- Left-to-right (or top-to-bottom) reading order; keep total node count ≤ 24; prefer one clean layer over nested clusters.
- Output exactly one fenced ```svg code block and nothing else. No prose before or after the block.

Acknowledge the spec with the word READY, then wait for the diagram prompt.
```

---

## 1. System architecture — "the repo at a glance"

**Slide claim:** one picture of the working system: an agent connects to MCP
servers over stdio, one of which escalates construction cost from BLS data, and
everything runs through one small portable client library.

**Outline:**
- Center: **portable_llm_mcp** (the MCP client/agent library) — emphasized node.
- Left: host LLM endpoints it talks to (**Ask Sage -gov** or **local Ollama**; label "approved endpoints only").
- Right: three MCP servers as peer cards: **bls_mcp** (tool server: search/describe/hierarchy/data + index-spec tools), **pars_local_mcp** (read-only PARS WBS tools over DuckDB), **cost_intel_app** (FastMCP UI app for the custom PPI escalation workspace).
- Top-left outside: **BLS public API** as an external cloud, arrow into bls_mcp only (fixed origin, env-only API key).
- Bottom: **cost_intel_ui** (Streamlit) as the human-facing frontend, arrow to the agent; note "conversation owned by the host".
- Data store note on bls_mcp/pars cards: "DuckDB / immutable snapshot registry".
- Callout chip: "stdio transports · allowlisted tools · sanitized errors".

```text
Draw a horizontal system-architecture diagram for an MCP (Model Context Protocol) codebase.

Layout, left to right:
1) A cloud-shaped card "LLM endpoints" containing two small chips: "Ask Sage (-gov models)" and "Local Ollama"; caption under it: "approved endpoints only — publicly configurable hosts are refused".
2) The emphasized central node: card labeled "portable_llm_mcp" with subtitle "MCP client + agent library (the harness and the product share it)". Accent-colored 3px border to mark it as the hub.
3) Three peer server cards on the right, stacked vertically, each a white card with title, one-line subtitle, and 2–3 bullet chips:
   - "bls_mcp" — subtitle "BLS cost-escalation MCP server" — chips: "15 tools", "BLS API (fixed origin, key from env)", "DuckDB snapshot registry".
   - "pars_local_mcp" — subtitle "PARS WBS classification & hierarchy (read-only)" — chips: "16 tools", "DuckDB".
   - "cost_intel_app" — subtitle "FastMCP UI app for custom PPI baskets" — chips: "prefab-ui renderer".
   Draw one arrow from the hub to each server, labeled "stdio".
4) An external cloud top-left labeled "BLS public API" with a thin dashed arrow down into the bls_mcp card, labeled "HTTPS · fixed origin".
5) A bottom-center card "cost_intel_ui" styled distinctly (light gray fill) — subtitle "Streamlit operations UI" — with an arrow up to the hub labeled "drives the agent".
6) A small caption bar along the bottom: "stdio transports · tool allowlists · sanitized error messages · no live BLS calls in evals".

Semantic accents: use green only on the caption bar's "sanitized error messages" chip; do not use red anywhere (nothing is failing in this picture).
Title (top-left, 64px): "One client, three servers".
```

---

## 2. Data pipeline — "snapshots are the unit of truth"

**Slide claim:** data enters exactly one way, is validated before it becomes
speakable, and the published snapshot is immutable — which is what makes eval
fingerprints meaningful.

**Outline:**
- Four pipeline stages in a left→right flow, matching the `bls-data` CLI verbs: **build → validate → publish → activate**.
- Source node at far left: "BLS public files (pc / ci / cu series)".
- Between validate and publish: a "gate" diamond labeled "fails closed".
- End of the chain: a stacked-sheets icon labeled "Snapshot registry (DuckDB) — versioned, read-only once published" with a small lock glyph.
- Bottom annotation strip: "same pipeline for eval's synthetic world — `eval_synthetic_world` — so eval findings generalize to published data"; "hashes recorded in manifests".

```text
Draw a left-to-right pipeline diagram, four equal stages.

Stages as white cards in a row, each with a verb as title and one-line subtitle:
1) "build" — "download + normalize BLS series (pc, ci, cu)"
2) "validate" — "schema, ranges, hash checks"
3) "publish" — "write versioned DuckDB snapshot"
4) "activate" — "point the server at the published snapshot"

Connect stages with arrows. Between stage 2 and 3, insert a small diamond gate labeled "fails closed" (amber accent).

At the far left, a lighter input card "BLS public data files" with an arrow into stage 1.
At the far right, an output cluster: three stacked rectangles with a small padlock glyph, labeled "Snapshot registry (DuckDB)" and caption "versioned · immutable once published · hashes in the manifest".

Bottom annotation strip (gray card, full width, 26px text): "The eval harness builds its synthetic world from the same pipeline (snapshot_id=eval_synthetic_world) — eval results inherit the same guarantees."

Use amber only on the gate diamond and its arrows; no red. Title (top-left): "Snapshots are the unit of truth".
```

---

## 3. Eval harness A — "conversation evals, graded by contract, not vibes"

**Slide claim:** agent behavior is checked like code: a scripted user drives
the real server, and programmatic graders — themselves adversarially
validated — score every episode on four dimensions and record everything.

**Outline:**
- Loop of three actors: **simulated user** (scripted) ⇄ **agent under test** (portable MCP client + LLM) ⇄ **real BLS server** (in-process, deterministic `eval_synthetic_world` snapshot; chip: "no mocks in the loop").
- Agent→server side labeled "stdio · allowlisted read tools".
- Below the server: **programmatic graders** box listing the four dimensions as chips: process · accuracy · answer format · guardrails (guardrails chip green).
- Right side: **oracle + flawed-agent self-test** box: "oracle agents must pass every check; deliberately flawed agents must fail exactly their target check" — the rubric-validation claim, accent-bordered.
- Far right outputs (three small file chips): `run.json` (metadata + per-check results), `summary.md` (human tables), `episodes.jsonl` (full transcripts) — with a fourth chip, `errors.jsonl`, styled gray with "infrastructure failures excluded from scores" (amber).

```text
Draw an evaluation-pipeline loop diagram.

Top row, three cards connected by paired arrows (request forward, response back):
1) "Simulated user" — subtitle "scripted, deterministic".
2) "Agent under test" — subtitle "portable MCP client + LLM (Ask Sage -gov or Ollama)".
3) "Real BLS server" — subtitle "in-process over stdio, allowlisted tools" — small chip inside: "deterministic snapshot eval_synthetic_world — no mocks in the loop".

From the server card, one arrow down (labeled "transcripts + tool outputs") to a wide card "Programmatic graders" containing four chips in a row: "process", "accuracy", "answer format", "guardrails" — color the guardrails chip green and the rest neutral.
An arrow from graders right, labeled "per-check pass/fail".

Below the graders card, a bordered callout (accent border, no fill): "Rubric self-test: oracle agents must pass every check; deliberately flawed agents must fail exactly the check they were designed to defeat."

Right column, four small file chips stacked vertically under a header "Recorded per run": "run.json — metadata + every check", "summary.md — readable tables", "episodes.jsonl — full transcripts", and a fourth chip "errors.jsonl — infrastructure failures, excluded from scores" with gray fill and amber text.

Title (top-left): "Graded by contract, not vibes".
```

---

## 4. Eval harness B — "an LLM judges the PARS agent"

**Slide claim:** a second harness answers a different question — can a model
with no other context use only the PARS tools to answer real WBS questions —
scored by an LLM judge, traced locally, and frozen in datasets.

**Outline:**
- Left column: **Question datasets** (two file chips: "pars-eval-0 — 25 frozen questions", "pars-eval-1 — 60 questions"; each derived from `evaluation.xml`).
- Center: **PARSAgent** card (portable MCP agent; prompts v1 basic / v2 scoped as small chips) → stdio arrow to **PARS MCP server** (Phoenix read-only allowlist: 7 of 16 registered tools; the other 9 not evaluated).
- Right of that: **LLM judges** card with two chips: `match_expected_response` (correct/incorrect) and `check_answer_scope` (within/out of scope); note chip "temperature 0 · judge model may differ from agent".
- Bottom center: **Tracing** strip: arrow labeled "OTLP" to a small card "Phoenix (loopback only)" and a parallel arrow to "JSONL fallback traces"; both styled as one lane labeled "every call traced — nothing leaves the loopback".
- Top edge: the same "approved endpoints" constraint chip as diagram 1, shared visual family.
- Verdict chip bottom-right (amber, not green): "Reported 2026-11-11: 100% correctness & scope, 50/50 (v1 and v2) — withdrawn, unverified".

```text
Draw a left-to-right evaluation flow diagram.

1) Far-left column "Question datasets": two file-icon cards — "pars-eval-0 · 25 questions (frozen)" and "pars-eval-1 · 60 questions" — caption: "eval questions travel with the CSV they generate". Arrow into the center.
2) Center card "PARSAgent" — subtitle "portable MCPAgent / MCPHub — no LangChain" — with two small chips: "prompt v1: basic analyst", "prompt v2: scoped". Arrow right, labeled "stdio · 7 of 16 tools allowlisted", into a card "PARS MCP server" with chip "WBS classification & hierarchy (DuckDB)".
3) An arrow down-right from the agent into a card "LLM judges" containing two chips: "match_expected_response → correct / incorrect" and "check_answer_scope → within / out of scope", with caption "temperature 0 · judge model may differ from the agent's".
4) Bottom full-width lane "Tracing": one arrow to a chip "Phoenix UI — loopback only" and a parallel arrow to a chip "JSONL fallback", lane caption "every agent and judge call traced; nothing leaves the loopback".
5) Top-right shared constraint chip (same style as the system-architecture slide): "approved endpoints only (Ask Sage -gov / local Ollama)".
6) Bottom-right verdict chip, amber fill at 10% opacity with amber border and amber text: "Reported 100% correctness & scope, 50/50 examples — withdrawn, unverified (no run output)".

Title (top-left): "An LLM judges the PARS agent".
```

---

## 5. Story timeline — "the evaluation journey"

**Slide claim:** we proved the graders before spending on models, baseline ran
on local models, the iteration loop caught its own bugs, a second harness was
built, and the docs caught up — five phases, each leaving an artifact behind.

**Outline:**
- Horizontal timeline, five milestones, left→right, matching `docs/EVALUATION_JOURNEY.md` §2:
  1. **Prove the graders** — oracle + flawed-agent self-test (no model needed). Artifact chip: `SELFTEST.md`.
  2. **Baseline** — 3 local models × 3 cases × 3 reps, fingerprints recorded. Artifact chip: `results/runs/`.
  3. **Iteration loop bites** — recorder bug caught via fingerprints (green "fixed"), simulated-user limit identified (amber "the honest finding").
  4. **Second harness** — PARS judged with frozen datasets; amber chip "reported 100% / 50 of 50, unverified".
  5. **Docs catch up** — skills/docs synced with reality; artifact chip `EVALUATION_JOURNEY.md`.
- A thin baseline axis with small artifact chips hanging below each milestone ("what is left behind").
- One-line footer: "Next: frontier-model run through the approved client · simulated-user broadening · CI decision".

```text
Draw a horizontal five-milestone timeline diagram.

A 6px baseline axis across the lower third, five evenly spaced milestone cards above it, each connected to the axis by a short stem. Number each milestone with a 40px-circle badge.

1) "Prove the graders" — subtitle "oracle + flawed-agent self-test, no model needed" (accent border).
2) "Baseline" — subtitle "3 local models × 3 cases × 3 reps at commit 34eb702, fingerprints recorded".
3) "Iteration loop bites" — subtitle "recorder bug caught via fingerprints; simulated user ended 23/25 episodes early" (amber accent on this card only).
4) "Second harness" — subtitle "PARS agent judged by LLM judge on frozen datasets" with a small amber status chip "reported 100% · 50/50, unverified".
5) "Docs catch up" — subtitle "skills and readmes synced to the harness that actually ships".

Below the axis, under each milestone, one small artifact chip (gray, file-icon style): "SELFTEST.md", "results/runs/", "PR #19 fix", "deployment readiness summary", "EVALUATION_JOURNEY.md".

Footer strip centered at the bottom: "Next: frontier-model run via approved client · broaden the simulated user · CI or its documented replacement".

Accents: green only on milestone 4's status chip; amber only on milestone 3. No red anywhere.
Title (top-left): "The evaluation journey".
```

---

## Deck flow — proposal A with B as slide 2 (fact-checked)

Recommendation adopted: **A (follow one estimate), with B's two-column
diagram as slide 2.** Fact-check of every load-bearing claim against the
repo (`main`, 2026-11-16):

| Claim in the proposal | Verdict | Evidence |
| --- | --- | --- |
| Project scope + analyst's labor/material split (A1) | ✅ real | negotiated-basket eval case (analyst clarifies scope, states shares — steel at 0.5; `eval/bls/cases.py:138,158`), `mixed-materials-and-labor` case; labor side may use quarterly ECI (ci) or wage ratios (`calculate_labor_locality_factor`) — say "periods may differ per component" rather than assuming annual |
| PARS scope evidence ∥ BLS series selection, analyst owns weights & periods (A2) | ✅ real | Phoenix read-only allowlist: 7 of 16 registered PARS tools (the other 9 not evaluated); `create_index_spec`/`save_index_spec` carry weights + periods; the eval checks "clarified periods and weights before calculating" |
| Component price changes + source record → one factor (A3) | ✅ real | `models/provenance.py`, `visualization.py`, `index_visualization_v1.schema.json`; graders check weights sum to 1, composite matches an independent recomputation, decimals quoted not recomputed |
| Source-backed explorer / synthetic basket demo / optional agent (A4) | ✅ exists, label honestly | `cost_intel_app` `ExplorerView` + full provenance JSON (`audit_view.py`); demo snapshot `DEMO-ANNUAL-2021-2026-v1` + synthetic PARS projects (QUICKSTART); agent = portable client, **demo-grade: observational results, frontier-model run still pending** |
| Two-column with dashed project→basket handoff (B) | ✅ consistent with spec | `docs/custom_ppi_escalation_app_spec.md` (scope informs index choice; analyst judgment explicit) |
| Who decides / computes / checks (C) | ✅ accurate | analyst (with optional model-assisted discovery) selects series & weights; validation is server-side and mandatory inside `calculate_index_from_bls` (`validate_index_spec` also callable); the immutable registry pins the snapshot; review/reproduce currently rests on local hooks + recorded runs (CI disabled) |

**Honesty notes to keep on the slides themselves** (from
`docs/EVALUATION_JOURNEY.md`): label the basket demo as *synthetic data*;
label the agent as *observational, not verified scores*; BLS numbers never
interpolate missing data and quarterly ECI is disclosed per component; the
frontier-model run is pending and CI is disabled.

Prompts 6–9 below generate the four slides this flow needs.

### Prompt 6 — two questions, two evidence paths (slide 2)

```text
Draw one landscape decision diagram, top-down then two columns.

Top center card: "The analyst's question — what will this project cost next year?" (accent border).
Two columns beneath it, each headed by a column title.

LEFT column "Understand the work":
  three small step chips stacked top→bottom, connected by thin arrows: "find the project (PARS)", "classify scope (WBS)", "trace lineage to the work packages"; ending chip: "output: defined scope + evidence links".

RIGHT column "Measure price change":
  three step chips: "select BLS series (materials: pc, labor: ci)", "analyst sets weights and periods per component", "validate before speaking"; ending chip: "output: a calculated, source-backed factor".

Both ending chips send arrows down into a single shared bottom card: "The analyst brings them together — owns the judgment; the server computes the math".
A short dashed connector labeled "proposed basket" runs from the LEFT column's ending area diagonally toward the RIGHT column's second step, meaning: scope informs the index choice, and the analyst owns that handoff.

Keep the columns visually balanced (equal width, mirrored step counts). The dashed connector is the only dashed line in the diagram. Green accent only on the two "output" chips; no red. Title (top-left): "Two questions, two evidence paths".
```

### Prompt 7 — where did the factor come from? (slide 3)

```text
Draw a composition diagram, left to right.

LEFT: three small component cards stacked vertically, each with a monospace series row and two caption lines:
  - "PCU3253A-… (PPI, materials · weight 0.50)" — caption "quarter: 2024→2025 · Δ +3.2% (illustrative)".
  - "CUSR0000SA… analog (ECI, labor · weight 0.50)" — caption "quarterly, disclosed as Q04 → annual alignment".
  Any third card as "…", grayed out. Caption under the stack: "weights are the analyst's call — the server never invents them".
MIDDLE: a centered plus "+" glyph and one wide chevron arrow labeled "deterministic combine (server-side, decimal strings)".
RIGHT: one emphasized output card: "Composite escalation factor — 1.032 (server-quoted, not recomputed)" with two chips: "weights sum to 1 · verified", "matches independent recomputation · verified".
Below the output card, attached by a thin bracket: a "source record" card (monospace-flavored) with three lines: "snapshot_id = DEMO-ANNUAL-2021-2026-v1", "series IDs + periods, disclosed per component", "ledger warnings preserved (no zero-fill, no interpolation)".

Label both the illustrative numbers as "(illustrative)" — the slide cites a recorded run for real numbers. Green on the two verified chips only. Title (top-left): "Where the factor came from".
```

### Prompt 8 — what can we demonstrate today? (slide 4)

```text
Draw a capabilities map: three equal cards in a row, each with a name, a one-line "works today" description, and a status chip; then one full-width honesty strip below.

Card 1: "Source-backed explorer" — description "browse the published snapshot; every displayed number carries a provenance chain (snapshot id, series, periods)" — status chip, green: "works today".
Card 2: "Synthetic basket demo" — description "full pipeline from stated basket → validated spec → server-calculated factor on demo snapshot DEMO-ANNUAL-2021-2026-v1; PARS demo projects are synthetic" — status chip, amber: "demo data only".
Card 3: "Optional agent" — description "portable client drives the same read-only tools in conversation; guardrails held (no invented numbers), conversation results observed, not yet verified at scale" — status chip, amber: "demo-grade · frontier-model run pending".

Honesty strip (full width, gray card, amber left border), one line: "Not yet claimed: live BLS numbers in a demo · frontier-model results · automated CI verification (local hooks + recorded runs today)".

No red anywhere. Title (top-left): "What we can demonstrate today".
```

### Prompt 9 — the running example (slide 1)

```text
Draw a light example-setter diagram, two cards side by side.

LEFT card "The project" (capital-acquisition flavor): three short lines as plain text, e.g. "Capital acquisition — specialty construction" / "Scope classified against PARS WBS (demo project)" / "Target year: next budget year".
RIGHT card "The analyst's split" (stated, not computed): two chips — "Materials ≈ 50% (steel family → PPI, pc annual)" and "Labor ≈ 50% (ECI, ci — quarterly, aligned to annual)" with a caption "the analyst states the shares and periods; the server asserts they are honored".

An arrow from LEFT to RIGHT labeled "what does this cost next year?".
Footnote line (26px, secondary color): "Running example: synthetic, matches shipped demo data; every slide after this one reuses it."
Keep it airy — one-third text density of the other slides. Title (top-left): "One estimate, end to end".
```


## Production notes

- **Order on the deck:** default flow = proposal A (fact-checked section above): prompt 9 → prompt 6 → prompt 7 → prompt 8; the standing five diagrams (1 system, 2 pipeline, 3 harness-A, 4 harness-B, 5 timeline) serve as the appendix/deep-dive set. Diagrams 1–2 set up the system, 3–4 are the evidence, 5 is the close.
- **Verify after generation:** open each SVG in a browser at 25% zoom — if any label blurs or overlaps, regenerate; slide-scale readability is the pass criterion, not code elegance.
- **PowerPoint import:** Insert → Pictures → This Device (SVG keeps vector quality); right-click → Convert to Shape only if you need to re-brand colors in-deck.
- **Keep diagrams and numbers in sync:** the verdict chips (green/amber) quote `eval/bls/results/runs/*/summary.md` and `eval/DEPLOYMENT_READINESS_SUMMARY.md` — regenerate the SVG if those artifacts change, and note the simulated-user caveat when presenting diagram 3 (see `EVALUATION_JOURNEY.md` §3).
- **Do not add data charts to these slides** (pass-rate bars etc.): scores live in the recorded summaries; copying figures by hand into a picture invites silent drift. Screenshots of `summary.md` tables or a live report render are safer evidence.
