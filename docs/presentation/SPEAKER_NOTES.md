# Speaker notes: mcp_group_1 — Source-backed cost escalation, built for agents

## 1. Source-backed cost escalation, built for agents

Open with the one-line claim: an agent can bring an old cost estimate forward, and every number in its answer can be traced to a published BLS series, a weight the analyst chose, a period, and an immutable snapshot. Fill in the team and presenter placeholders before presenting. Scope of this deck: the BLS escalation server (src/bls_mcp) is the main subject. PARS (src/pars_local_mcp), the MCP App (src/cost_intel_app), the Streamlit UI and the portable client (src/portable_llm_mcp) are supporting pieces. Everything quoted in this deck was checked against the main branch at commit 32f896f, and against a clean-clone run on 2026-11-17.

## 2. An escalation factor is only as good as its paper trail

The pitch in one sentence: escalation is judgment plus arithmetic, and the arithmetic has to be auditable. The middle card is not a hypothetical. The BLS eval includes deliberately flawed agents that do exactly these things (recalls-series-ids, hides-alignment, bare-number-answer), and the graders catch each one. See eval/bls/results/SELFTEST.md. Mission context: this supports cost estimating and independent review, where a factor has to survive questions about where it came from.

## 3. One estimate, end to end

The running example. Every slide in the story reuses it. It is eval case 2, “mixed-materials-and-labor”, from eval/bls/cases.py. The values come from the synthetic eval world (eval/bls/world.py), not BLS data, so every expected answer can be worked out by hand. The user leaves out the target year on purpose. A correct agent has to ask for it (the user then says 2026) rather than assume it. The labor series publishes quarterly only, like the real Employment Cost Index, so this case also exercises the server’s quarterly-to-annual alignment. Correction to docs/DIAGRAM_PROMPTS.md prompt 9: it used an illustrative 50/50 split. This version uses the 60/40 basket the eval reproduces exactly.

## 4. Two questions, two evidence paths

Two questions sit inside “what will this cost?”: what is the work, and how have its prices moved. Left path: the PARS server (src/pars_local_mcp) answers scope questions over synthetic WBS data: projects, hierarchy, lineage, leaf nodes. Right path: the BLS server (src/bls_mcp) answers price questions: catalog search, hierarchy checks, specification, validation, calculation. The dashed line is the analyst’s handoff. Scope informs which series and weights to choose, but no tool turns PARS scope into a BLS basket automatically today. That handoff is a future-work item (slide 20). No corrections were needed to prompt 6.

## 5. Where the factor came from

This is the heart of the design. The model never supplies an index value. calculate_index_from_bls loads the saved specification, reads both index levels for each component from the snapshot, and returns the result together with a ledger: observations used, provenance and warnings. The arithmetic: relative = level at target ÷ level at base; composite = sum of weight × relative. 0.60 × 310/200 + 0.40 × 224/140 = 0.93 + 0.64 = 1.5700. The labor series has no annual average, so the server takes its Q04 value for each year and says so in the component result, the ledger warnings and the provenance. It never averages quarters BLS didn’t publish. The two green chips are real grader checks: “weights sum to 1” and “composite matches an independent recomputation”. The oracle agent passes both in poe eval-selftest. Correction to prompt 7: the prompt’s illustrative 1.032 and a “CUSR…” series (a CPI prefix, not ECI) were replaced with this reproducible basket.

## 6. What we can demonstrate today

Say plainly what is demonstrable and what is not. Judges reward honest labeling. Card 1 works offline: once the sample snapshot is built, poe verify passes (15 tools, 4 resources, no network). Card 2 is the MCP App in src/cost_intel_app. Per the README’s “Boundaries” section, its basket math runs on synthetic data and is not a source-backed BLS result. Card 3 figures come from the seven recorded runs in eval/bls/results/runs/ (6 with scored episodes). They are observations from local open-weight models, not verified scores at scale. Correction to prompt 8: the prompt described card 1 as a source-backed explorer over the basket demo; the source-backed path is the BLS server’s own.

## 7. From a clean checkout to a cited factor

Before presenting, apply future-work fix 1 (slide 18). On a fresh clone of main today, step 1 stops with “SHA-256 mismatch for pc.industry.txt”, because the manifest hashes were computed on Windows CRLF copies of files committed with LF endings. Values checked on 2026-11-17 on a clean Linux clone, with the manifest hashes regenerated in a scratch copy: • Step 2 printed “PASS discovery: 15 tools, 4 resources, 1 resource templates … PASS smoke check complete; no BLS requests or specification writes”. • Step 3, run through an in-process MCP client: CIU1010000000000I, annual spec 2015 → 2025, resolved from 2015-Q04 = 125.1 and 2025-Q04 = 173.642, composite 1.388025…, with two ledger warnings disclosing the Q04 alignment. • Step 4 printed “SELFTEST PASSED: oracles pass; every flawed agent is caught”. Step 5 needs LLM_* settings in src/portable_llm_mcp/.env. Run one case first: python -m eval.bls.runner --agent model --case mixed-materials-and-labor. Step 6, in full: fastmcp dev apps src/cost_intel_app/server.py:mcp. It needs the apps dependency group (prefab-ui).

## 8. Where the evidence is

Use this as the map for Q&A: each row points to the slide with the evidence. The criteria are quoted from the hackathon brief: technical quality (readability, performance and reliability, MCP design principles), innovation, mission alignment and presentation.

## 9. Each concern has one home

Point at the tree: a reader can find any tool, model or query without searching. Evidence: • src/bls_mcp/mcp/tools/__init__.py registers each of 15 tools explicitly, one module per tool. • src/bls_mcp/lifespan.py: “Dependencies owned by one running server, never a module singleton.” • src/bls_mcp/mcp/adapters.py: domain_errors() turns domain exceptions into ToolError; unexpected errors stay masked (mask_error_details=True in server.py). • src/bls_mcp/services/source_calculation.py opens with the formula and the quarterly-to-annual rule. • uv run mypy src/bls_mcp src/portable_llm_mcp: “Success: no issues found in 118 source files” (clean clone, 2026-11-17). • src/templates/example_server/ is the copyable template for the next server. Known gaps, covered in future work: ruff reports 27 lint errors and 5 unformatted files (mostly eval/asksage); PARS has two server.py entry points.

## 10. Reliability is designed in, then tested

Reliability here means a number can’t drift under you: the data is pinned and the failure modes are explicit. Evidence: • Pipeline: bls-data build → validate → publish → activate, plus rollback (src/bls_mcp/ingestion/cli.py). See Appendix A2. • Tests: uv run python -m pytest on a clean Linux clone, 2026-11-17: 1,191 passed, 4 failed, 6 errors, 6 skipped, 1 xfailed (about 14 minutes). The failures come from (a) the CRLF/LF manifest-hash mismatch and (b) three tests that still expect unknown program codes to return empty results after the codes became strict, plus a test-order import clash on the module name “data”. • HTTP security tests: tests/integration/test_http_security.py (fixed origin, rejected paths, sanitized upstream errors). • Limits are stated in the server instructions: at most 50 series and 20 inclusive years per live call. Performance: tools read a local DuckDB file; the PARS readiness summary reports under a second per query on synthetic data. Neither server has a formal latency benchmark yet (future work).

## 11. We tested the graders before we tested the models

This is the method’s core claim: the rubric is validated adversarially, not by eye. Each flawed agent makes one known mistake. The self-test exits non-zero unless the oracles pass everything and each flawed agent fails exactly the checks listed for it in EXPECTED_FAILURES (eval/bls/runner.py). Six of the eleven are shown; the others are misattributes-quarters, changes-basket-after-confirmation, validates-after-calculating, ignores-stated-share and guesses-everything. Three cases: a known basket missing its target year; materials plus labor with quarterly-to-annual alignment; and a vague project where the basket has to be negotiated. Results are reported in four separate dimensions so a regression in one isn’t hidden by the others. The “format” dimension is the citation contract. Run it: uv run --locked poe eval-selftest. Diagram: Appendix A3.

## 12. Guardrails held; the workflow did not, yet

Read these as a harness test, not a model verdict. No episode passed every check (0 of 32 scored episodes across all seven runs), and that is expected for small local models on a strict contract. Table rows are the latest full run per model: gpt-oss 20261116T020812Z (7 scored, 2 infrastructure errors excluded), qwen3 20261116T021942Z, gemma4 20261116T031759Z. Source: uv run poe eval-report. The strongest finding: guardrails held under weak agents. 100% in 5 of 6 scored runs; the worst was 26/27. The miss was one qwen3 attempt to call the live BLS API, which the server refused safely because no key was configured. No number was invented. gemma4 completed one full calculate_index_from_bls through the mixed quarterly-to-annual case. Caveat to say out loud: the scripted user was widened after these runs, so the current eval fingerprint (ccdfccfcc1bc) differs from the recorded runs (f492beb25f0f), and the scores need a re-run. 13 episodes lost to endpoint errors were excluded by design (errors.jsonl).

## 13. Built for an agent, not a browser

Examples worth quoting if asked: • SeriesSearchRequest (src/bls_mcp/models/series.py): programs is a list of Literal["pc","ci","pd","wp"], with a description that says to use lowercase codes; limit is bounded 1–100. • calculate_index_from_bls returns SourceBackedCalculationResponse(result, ledger). • get_series_hierarchy’s docstring tells the model to check status (complete, partial or unknown) and not to claim what a series includes when relationships could not be identified. • save_index_spec carries readOnlyHint false and destructiveHint true, because it replaces a spec with the same ID. • Resources: methodology://composite-index, methodology://locality-adjustment, setup://bls-api, guide://escalation-workflow and the bls://series/{series_id} template. Prompt: design_escalation_basket. Gaps, in future work: request models don’t yet set extra="forbid", so invented fields are silently accepted; PARS tools take bare arguments and return {"error": …} dicts instead of raising ToolError.

## 14. Tools follow the analyst’s workflow, not the API

The judges asked whether each tool is a real agent-facing action rather than a thin wrapper around one REST call. Here, 14 of the 15 tools never touch the BLS API at all. calculate_index_from_bls is the clearest goal-level tool: one call loads the saved spec, resolves base and target observations for every component from the snapshot, applies the quarterly-to-annual rule where needed, computes the composite, and returns a ledger. get_series_hierarchy exists because a series title doesn’t show what an index includes. For example, PPI “Sawmills” includes hardwood lumber, softwood lumber and wood chips, so a framing-lumber component is better matched by “Softwood lumber”. Honest gap: the specify step takes four calls (create, validate, save, calculate), and in the recorded runs models calculated before saving and never validated unprompted. A single goal tool that validates and calculates an inline spec is in future work (slide 20).

## 15. What to look at first

Lead with the top two: they are what makes the evaluation trustworthy. • Citation contract: the “format” dimension in eval/bls/graders.py. A numerically right answer fails if it doesn’t say where the numbers came from. • Adversarial grader validation: eval/bls/agents.py (scripted oracle and flawed agents) and EXPECTED_FAILURES in eval/bls/runner.py. • Quarterly-to-annual alignment: QUARTERLY_ANNUAL_ANCHOR = "Q04" in src/bls_mcp/services/source_calculation.py. • Fingerprints: eval/bls/recording.py hashes the eval sources, every tool’s name, description and input schema, and the system prompt. They exposed a recorder bug (fixed in PR #19). • MCP App: src/cost_intel_app/server.py uses FastMCPApp and prefab-ui; the model sees one entry tool, ppi_basket, and the UI calls UI-only backend tools. • Endpoint enforcement: src/portable_llm_mcp/config.py (APPROVED_HOSTS; Ask Sage model names must end in -gov). Also worth a mention if time allows: the repo’s own agentic development setup (.claude/agents and hooks such as the TDD companion gate and the git-safety preflight) that the team used to build and review the servers.

## 16. Factors an estimator can defend in review

Tie it to service delivery and oversight: escalation is a recurring step in cost estimating, and reviewers need to see where each factor came from. This server makes that trail automatic instead of something rebuilt by hand. Evidence: • Ledger and provenance: src/bls_mcp/models/provenance.py; calculate_index_from_bls returns both. • Immutability: published snapshots in the registry are selected by ID (activate, rollback); a published version is never edited. • Data handling: docs/DATA_HANDLING.md: synthetic data only, handled as CUI until marking review; no PII or real project data may be loaded. • Read-only boundaries: the PARS panels in the MCP App only accept a GuardedClient limited to read-only tools. Keep the claim modest: today the demo runs on sample and synthetic data. Live BLS refresh and real project data are future work.

## 17. What the first runs taught us

All six come from docs/EVALUATION_JOURNEY.md, section 4, each with its evidence there. The point for judges: the evaluation changed the code. Series validation was hardened (commit 188b298), the recorder was fixed (PR #19), and the scripted user was widened, all before any model was judged again. Lessons 2 to 4 are still open as tool changes (extra="forbid", recovery hints in error text, a single goal-level calculate tool), and they appear in future work. The timeline of these phases is in Appendix A5.

## 18. Six fixes that protect the score

These are the gaps a judge will hit by cloning the repo and following the README. Effort is my estimate. 1. src/bls_mcp/docs/sample_data/pc-sample-input.json and ci-sample-input.json record SHA-256 hashes and sizes of CRLF copies (for example pc.industry.txt: manifest 716bce1a…, committed file bfc35bf4…; the manifest hash equals the file with CRLF endings). .gitattributes marks the folder -text, so the files stay LF everywhere. Regenerating both fields from the committed bytes let the full sample pipeline and poe verify pass in a scratch copy. Add a test that rebuilds from the manifest. 2. tests/bls/unit/test_catalog_service_duckdb.py (2 tests) and tests/integration/test_phase1_duckdb_server.py expect unknown program codes to return empty results, but SeriesSearchRequest now rejects them. test_manual_bls_*.py pass alone but fail in the full run because another module named “data” is imported first. 3. src/mcp_servers.json allows 10 BLS tools; the eval harness uses all 15. 4. eval/DEPLOYMENT_READINESS_SUMMARY.md says "production-ready" and "DEPLOY" with 7 tools; no Phoenix run output is committed, and the PARS allowlist now includes the training, prediction and write_back_wbs tools. 5. uv run ruff check . and uv run ruff format --check . 6. deploy/README.md describes src/example_server and deploy/databricks/, which isn’t in the repo.

## 19. Raise the evidence: evaluation and reliability

Mapped to criterion 2, “submitters must include their own evaluation setup and results.” The harnesses are strong; the results need refreshing and broadening. • The recorded BLS runs measure an earlier eval version (fingerprint f492beb25f0f); the current one is ccdfccfcc1bc. Re-running the same three models gives a clean before/after with poe eval-report --compare. • A frontier-model run is the evidence pack’s main pending item (eval/EVALUATION_DOC_OUTLINE.md). • The PARS harness exists and is tested offline, but its 100% result can’t be reproduced from the repo until a run’s output is committed. • CI is commented out in .github/workflows/ci.yml because the enterprise GitHub instance has no runner. A self-hosted runner, or a documented local gate, would give judges a second opinion. • Three cases is a smoke signal, as eval/bls/README.md says; more cases make model comparisons meaningful.

## 20. Sharpen the design: MCP principles and code

Mapped to criteria 1, 3 and innovation. MCP design: • extra="forbid": today only the visualization model forbids extra fields; lesson 2 shows why it matters. • Error text: lesson 3. The search_series description already says to use lowercase codes; the error should say it too. • A goal-level tool: lesson 4. Models struggled with create → validate → save → calculate. A tool such as escalate_basket(spec) that validates and calculates in one call, returning the same ledger, removes the ordering trap. • PARS tools return dict[str, Any] with {"error": …} on failure, so MCP clients see a success result; raising ToolError sets isError. • write_back_wbs is on the general PARS allowlist; the UI already blocks it. MCP elicitation can ask the user before any write. Code: • src/pars_local_mcp/server.py and src/pars_local_mcp/mcp/server.py both assemble the server, with different instructions text. • The root pyproject installs scikit-learn, hiclass and other PARS model dependencies for the BLS server too. • src/bls_mcp/mcp/resources/snapshot_resource.py and archetype_resource.py are unregistered stubs. Innovation: the dashed “proposed basket” handoff on slide 4 is manual today; a tool could turn WBS scope into a draft basket for the analyst to confirm.

## 21. Three things to remember

Close on the three takeaways, then open questions. The appendix holds the five architecture and evaluation diagrams (system, pipeline, both harnesses, timeline) and a list of what was corrected against docs/DIAGRAM_PROMPTS.md.

## 22. Appendix A1. Three MCP servers, one portable client

Appendix A1, prompt 1. The system at a glance. Corrections to the prompt: PARS is not read-only (its 9 pipeline tools, including write_back_wbs, are on the client allowlist); cost_intel_app is launched by an MCP host rather than by portable_llm_mcp, and calls PARS through a read-only GuardedClient; the Streamlit UI is not wired to the agent. Evidence: src/mcp_servers.json, src/cost_intel_app/pars_panels.py (READ_ONLY_TOOLS), README “Architecture” and “Boundaries”.

## 23. Appendix A2. Snapshots are the unit of truth

Appendix A2, prompt 2. Corrections: build reads files already pinned in the manifest (it does not download; acquisition is a separate step in docs/bls/OPERATIONS.md), and the CLI’s rollback verb was added. The fail-closed gate is real and observable: on a fresh clone today, bls-data build stops with “SHA-256 mismatch for pc.industry.txt” (future-work fix 1), and publish refuses a candidate with “Missing or invalid READY validation report”. Evidence: src/bls_mcp/ingestion/cli.py, lifecycle.py, publish.py; eval/bls/world.py uses build_candidate, validate_candidate, publish_candidate and activate_snapshot.

## 24. Appendix A3. Graded by contract, not vibes

Appendix A3, prompt 3. Corrections: the server runs through an in-process FastMCP client (Client(create_server(...)) in eval/bls/runner.py), not stdio; the agent sees all 15 tools from list_tools, not an allowlist. episodes.jsonl and errors.jsonl are git-ignored; run.json and summary.md are committed for all seven recorded runs.

## 25. Appendix A4. An LLM judges the PARS agent

Appendix A4, prompt 4. Corrections: the 100% verdict is shown in amber as reported, not verified, because no Phoenix run output is committed; the PARS server now registers 16 tools, of which the eval exposes 7 (READ_ONLY_TOOLS in eval/phoenix/agent.py). The harness itself is real and tested offline: eval/phoenix/tests and eval/phoenix/judges/tests, including test_approved_imports.py, which fails if LangChain is ever imported.

## 26. Appendix A5. The evaluation journey, five milestones

Appendix A5, prompt 5. Corrections: milestone 4 is amber instead of green, since no PARS run output is committed; the footnote records that the BLS runs used eval fingerprint f492beb25f0f while the current eval (with the widened scripted user) is ccdfccfcc1bc. Source: docs/EVALUATION_JOURNEY.md, sections 2 and 5.

## 27. What the diagrams correct in their prompts

Each diagram also carries its correction as a footnote, so the standalone SVGs stay honest when copied into another deck. The nine SVGs are 1920×1080, inline CSS, real text, and follow the shared render spec in docs/DIAGRAM_PROMPTS.md (palette, 24px minimum, one arrow marker). Every text element also carries its font as an attribute, so the text renders correctly where a style block is stripped.
