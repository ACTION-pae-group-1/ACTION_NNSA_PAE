# PARS MCP close-out (feat/pars_mcp)

## Goal

Close out feat/pars_mcp. Success means all three of these hold:

1. **Registered:** the PARS server registers exactly the tools in `src/mcp_servers.json` (`servers.pars_mcp.allowed_tools`, 15 names). The read-only UI does not invoke `write_back_wbs`; the registry currently does allowlist it for the general MCP client. Review this separately before granting client access.
2. **Works when running:** each of the 15 allowlisted tools returns a correct result when the server runs the way the config starts it (stdio). This is checked end to end by a separate interrogation, not only by in-process tests.
3. **Merged:** the work is committed on feat/pars_mcp, pushed to origin/feat/pars_mcp, and merged into local `main`, then `main` is pulled from origin.

## Decisions already made

- Historical decision (superseded): keep `write_back_wbs` out of the allowlist. The supplied registry currently includes it. The UI separately blocks it through `READ_ONLY_TOOLS`.
- `get_wbs_lineage` returns element first, then ancestors to the root. The tool description says so.
- `get_wbs_project_descriptions` and `get_wbs_rows` return data only when the source is synthetic.
- Ancestor titles come from the reported `wbs_level`, not from WBS codes or parent links. Each project's rows are in tree order.
- `concatenate_data` sorts rows by `parsid` with a stable sort. This only groups projects together and keeps each project's order.

## Out of scope

- Direct UI invocation of `write_back_wbs` (on hold); the tool remains registered and the general MCP registry currently permits it.
- Unrelated work on fix/pars-mcp-fixes and integrate/pars-mcp-into-main (parked, not merged into this branch).
- The Phoenix tracing stash (`stash@{0}`, eval harness, not the PARS server).
- Cost-intelligence and DuckDB ECI work.

## To-do

- [x] **T1 Pipeline and server fixes** (agent a481767b803e183e9). `run_id` full match; `get_wbs_rows` honors the legacy suffix; `run_wbs_pipeline` validates before writing; `n_jobs` and seeds rejected at the tool boundary; server instructions match the real tools; synthetic-data gate on `get_wbs_project_descriptions` and `get_wbs_rows`. Tests first.
- [x] **T2 Running-server entry point.** Decision: `mcp_servers.json` now starts `src.pars_local_mcp.server`, which calls `initialize_database` at startup and creates synthetic data at `data/wbs.duckdb` (gitignored). The previous entry, `src.pars_local_mcp.mcp.server`, created no database, so every tool would have failed against an empty path.
- [x] **T3 Interrogator.** Start the server as `mcp_servers.json` says. For each of the 15 tools, call it with valid inputs and check the result, and call it with one bad input and check the refusal. Report pass or fail per tool with evidence. Any failure goes back to T1 or T2.
- [x] **T4 Full tests.** Run the default pytest suite and the full `src/pars_local_mcp` package. Both must pass. The previous full run had one failure, which is fixed (stale storage message).
- [x] **T5 Code graph.** Run `graphify update .` after the code changes (CLAUDE.md).
- [ ] **T6 Commit.** Commit only PARS server files, the allowlist, tests, and this doc. Leave out `.github/workflows/ci.yml` (kept deleted), `claude-code-templates`, untracked reports, and unrelated docs.
- [ ] **T7 Push.** Push feat/pars_mcp to origin (approved in the close-out plan).
- [ ] **T8 Merge.** Merge feat/pars_mcp into local `main`. Pull `main` from origin. Resolve conflicts if any. Pushing `main` needs a separate confirmation.
- [ ] **T9 Report.** Final status against the three success criteria, with evidence.

## Working loop (until closed)

Repeat until every to-do item above is checked and the server is green, interrogated, validated, and verified:

1. **TDD:** write a failing test for each gap, make it pass, and keep existing assertions unless they are wrong.
2. **Interrogate:** run the interrogator against the server as the config starts it (`uv run python -m src.pars_local_mcp.server`). Every allowlisted tool must pass; write_back_wbs stays on hold.
3. **Commit:** commit each green slice. Commit only PARS server files, the allowlist, tests, and this spec.

## Status log

- **T1:** done. The fix agent (a481767b803e183e9) was stopped after about 380k tokens; its edits are in the working tree and covered by the tests below. Changes: `run_id` full match; `get_wbs_rows` honors the legacy suffix; `run_wbs_pipeline` validates before writing (a refused call creates no run dir); `n_jobs` and seeds rejected at the tool boundary; server instructions match the tools; synthetic-data gate on `get_wbs_project_descriptions` and `get_wbs_rows`; blank `project_id` refused on every project-scoped tool with the fixed message (last gap closed: `get_wbs_hierarchy`, `get_wbs_lineage`, `get_project_info`).
- **Test validation (fail-first or mutant checks):** parent-link test was red before the fix. Blank-project cases for the three tools above were red before the fix (9 failures) and are green now. The labeled-origin gate test passes on real code and fails when the gate admits `unknown`. The new `concatenate_data` ordering test passes on real code and fails with the parsid sort removed; without the sort, a child takes an ancestor title from another project (`P1 root | P2 child a`).
- **T2:** done. Config points at `src.pars_local_mcp.server`.
- **T3:** done on final code, over stdio as `mcp_servers.json` starts the server.
  - Positive (`interrogate/v3.out`, exit 0): all 14 non-pipeline allowlisted tools returned correct content. list_projects: 2 projects. search_wbs: 34 elements. get_wbs_hierarchy: 1 child. get_wbs_lineage: 7 elements, element first. get_project_info, get_leaf_nodes: 11, get_wbs_by_level: 3, get_wbs_project_descriptions: 5 rows, get_wbs_rows: 5 rows, validate_wbs_inputs: ok, clean_wbs_data, tune_and_train_wbs (tuned test F1 0.8486, equal to the untuned value; the unseeded search chose the untuned configuration), predict_wbs: 16,720 rows, get_wbs_run_status: clean, predict and tune_train stages.
  - run_wbs_pipeline, separately (`interrogate/pipeline_stdio.out`): 71.4 s on an idle machine with n_iter 2, cv_folds 3, n_jobs 1. Stages clean, tune_train, predict, write_back. Write-back matched 16,720 rows. The same run took 1404 s in the earlier loaded in-process run. The default parameters (n_iter 10, cv_folds 3, n_jobs -1) were not timed.
  - Refusals (`interrogate/negatives2.out`): one bad input per tool that takes input. 12 of 13 return a fixed tool_error with no data. run_wbs_pipeline refuses with the error plus the attempted run_id, and creates no run dir. No refused call created a run dir.
  - `write_back_wbs` is registered; current registry includes it, but the UI does not. It was not called in the historical interrogation.
- **Config command (decided):** `servers.pars_mcp` now runs `uv run --no-sync python -m src.pars_local_mcp.server` from the repo root, so it uses the repo venv. The bls entry has the same bare-`python` problem; it is outside this closeout and not changed here.
- **Decided: keep pars-hardening.** The worktree at `.claude/worktrees/pars-hardening` and branch `feat/pars-hardening` stay, with their 12 modified tracked files and 57 untracked files untouched. A copy of the tracked edits is at `c:/tmp/keep/backup/pars-hardening-uncommitted.patch` (753 lines).
- **Branch cleanup:** `feat/pars-hardening-port` deleted (fully merged, worktree removed, was clean). Other unmerged branches kept.
- **Handoff:** no handoff file for `feat/pars_mcp` exists in the repo. This spec is the handoff.
- **Known flaky test (accepted):** `tests/test_settings_operations.py::TestSnapshotRegistry::test_register_multiple_workflows` failed once in a full default run because of a write race on the settings file. It passes when run alone. It is outside PARS. The race fix is commit `8a10089` on `fix/runner-and-settings-race`, which stays parked.
- **T4 (final code):** default suite `uv run pytest`: 759 passed, 2 skipped, 1 deselected, 1 xfailed, exit 0 (`testrun/final_default3.log`). The flaky test passed this run. Rest of the full package (`wbs`, `wbs_port`, `data`, root `test_config.py` and `test_server.py`): 165 passed, 1 xfailed, exit 0 (`testrun/final_pars_complement.log`). The default testpaths cover `mcp`, `storage` and `tests`, so the two runs together cover all of `src/pars_local_mcp`.
- **T5:** `graphify update .` run after the final code edits. `graphify-out/` is gitignored.
- **T6 to T8:** pending at the time of writing. The commit, push and merge are recorded in the git history rather than in this doc.
