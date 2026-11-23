# NNSA Cost Intelligence UI — SME review and decision record

**Status:** Proposed enhancement for subject-matter expert review; not yet an approved production calculation method.
**Prepared:** 2026-11-16
**Design reference:** `docs/ai_mcp_cost_intelligence_nnsa_spec_aligned.html`
**Implementation:** `src/cost_intel_app/`, `src/cost_intel_ui/`
**Scope:** Synthetic PPI escalation basket, custom allocations, result interpretation, UI, and release controls.

## 1. Purpose and requested SME decision

The current prototype presents an NNSA project scope, recommends a basket of illustrative Producer Price Index (PPI) components, and allows an analyst to adjust the components' allocation percentages. It currently displays **“Custom weights require live backend”** when a valid 100% basket differs from a predefined scenario, and disables the approval/results workflow. This is a prototype limitation, **not a mathematical necessity**: the codebase already contains a deterministic, local `Decimal`-based routine (`build_result_packet`) that calculates composite index results from a supplied set of weights and annual synthetic observations.

**Request:** Approve or revise the proposed methodology and workflow below so the demo can calculate and display a **clearly labeled synthetic result** for any valid custom allocation, without depending on a live BLS, PARS, or external service. Approval of this demo behavior **must not** be interpreted as validation of project cost estimates, production PPI mappings, or expenditure shares.

## 2. Current state versus proposed state

| Topic | Current implementation | Proposed implementation |
|---|---|---|
| Included cost components | Analyst can enable/disable candidate PPI series | Retain; disabled components contribute zero |
| Allocations | Analyst edits weights; Normalize rescales included weights | Retain; explicit 100% total required for approval |
| Presets | Named allocations are approvable, with calculated synthetic results | Preserve all existing preset behavior and numeric outputs |
| Custom allocation totaling 100% | Displays “Custom weights require live backend”; approval unavailable | Approval enabled once validation passes; local calculator computes the result |
| Invalid allocation | Approval blocked | Continue blocking; show actionable reason |
| Approved basket | Allocation locked; explorer chart, component detail, adjustment, table and comparison | Same behavior for approved custom baskets, with consistent source evidence |
| Evidence | `DEMO-` identifiers, synthetic observations, demo snapshot | Keep explicit synthetic labels and calculation/provenance metadata |
| Data movement | In-memory synthetic source | **No live network access or data egress** as part of this change |

**Scope boundary:** Do not change the authoritative source mappings, introduce a live backend, silently use the nearest preset, or represent the synthetic result as an official BLS-backed estimate. Do not rewrite the reference HTML's intended three-pane experience; the host owns its conversation pane, while the embedded UI owns the cost-analysis component.

## 3. Proposed calculation methodology for review

For each included component \(i\), the analyst enters an allocation \(w_i\) as a percentage. The app validates that included weights are finite, non-negative, at most 100%, and total 100% within its documented tolerance. A disabled component has **effective allocation zero** regardless of a previously entered field value; at least one component must be included.

Using synthetic annual source values \(P_{i,t}\) and the shared **2023 base year**, compute each normalized index factor

\[F_{i,t}=P_{i,t}/P_{i,2023}.\]

The proposed weighted composite factor is

\[C_t=\sum_i (w_i/100)\,F_{i,t},\quad \sum_i w_i=100.\]

Under this convention, \(C_{2023}=1\) (subject to controlled rounding), and the displayed change from the base is \((C_t-1)\times100\%\). The adjustment-to-base and waterfall displays must be derived from **the same result packet**, not recomputed independently in the UI. The existing code uses `Decimal` for its calculation and returns decimal strings under the `index_visualization_v1` result contract; preserve both practices.

**SME questions:**

1. Is a fixed-weight arithmetic composite of normalized component indices appropriate for this *illustrative escalation-index* use case? Should weights be defined as percentage shares of the project cost basis, and are there restrictions on zero-weight components?
2. Is the **2023 base year** appropriate for all demo scenarios? Should adjustment factors represent a source-year-to-base-year conversion using \(C_{base}/C_{source}\), with a clear distinction between factor and percent change?
3. Is annual 2021–2026 history adequate for the demo? Real PPI series may have different frequency, revision, reference-base, or availability characteristics; these are **not addressed by the synthetic fixture**.
4. What minimum evidence is required before production use: approved component selection, cost basis/WBS mapping, BLS series identifiers and vintages, observation date, missing-data/revision rules, and analyst sign-off?
5. Should custom baskets be marked **“Analyst-defined · synthetic calculation”** rather than “Approved fixture,” reserving production approval terminology for a later controlled workflow?

## 4. UI and analytical design review

The primary visual design reference is `docs/ai_mcp_cost_intelligence_nnsa_spec_aligned.html`, which uses a three-part experience: host/conversation context, a central analysis workspace, and project/evidence context. We should preserve that intent while respecting MCP host layout constraints instead of building a second chat interface inside Prefab.

Proposed incremental improvements:

- Constrain the center workspace width for legibility; improve title, summary-stat, table and action hierarchy without altering backend contracts.
- Keep an allocation ribbon that shows relative component weights **and** allows selection of a component; labels must not rely on color alone.
- Present the composite escalation chart with a visible 2023 base factor and unambiguous units; use a restrained grid, clear years, and informative series labels. Stacked contributions and the composite line should not be confused.
- Retain normalized/raw series switching, source-year adjustment, and sortable/filterable evidence table. State clearly when raw values are synthetic PPI index points versus normalized factors.
- Show result origin, synthetic-data warning, snapshot/version identifiers, and validation/approval status near the result rather than hiding these only in a footer.
- Display a useful error or blocked state if a calculation packet fails the existing schema and reconciliation checks; never substitute a preset silently.

**SME questions:** Which metrics are essential for a reviewer to make a decision? Is a stacked contribution chart sufficiently interpretable, or should the composite line be primary? Which terms require preferred NNSA wording? Which audit fields should be shown to analysts versus reviewers?

## 5. Proposed technical implementation (subject to SME approval)

The existing calculation routine is `src/cost_intel_ui/fake_data.py::build_result_packet`. Presets are obtained through `InMemoryDataSource.get_result(project, scenario)`. Custom support needs a deliberate way to pass the **validated, locked allocation** through session approval, result retrieval, explorer updates, and audit views. A scenario label alone is insufficient: it must not be possible to request `scenario="custom"` with different weights and receive an unrelated cached result.

Suggested minimal design:

1. In the data-source layer, expose a local, deterministic custom-result calculation entry point that accepts project identity plus the exact validated component weights; keep existing preset `get_result()` behavior unchanged.
2. In the approval/session layer, permit a valid custom basket, distinguish its scenario from presets, and bind the approved immutable weights to its calculation result. Continue applying `validate_packet` and existing refusal rules.
3. In the stateless MCP tool layer, round-trip the approved custom weights through all view-refresh/explore actions and **refuse mutations** that would alter the locked basket. Never trust a client-supplied scenario label as proof of prior approval.
4. Ensure comparison cards continue showing named preset alternatives, with the active custom basket distinguished accurately. Ensure result tabs, audit views, and source context use the same custom result.
5. Replace “Custom weights require live backend” and preset-only notices with precise text: **“Custom allocation is valid. Approve to calculate a synthetic result using the local demo data.”** Use “Calculated synthetic result” after approval.

This specification is **not a claim that these changes have been implemented or tested**. Implementation should be reviewed as a separate code diff.

## 6. Acceptance criteria and verification evidence

| ID | Acceptance criterion | Verification |
|---|---|---|
| CW-01 | A valid, non-preset 100% allocation can be approved and produces a result | New backend and MCP integration tests |
| CW-02 | A custom result uses the supplied weights, not a preset or default | Assert exact component weights and independently check composite formula |
| CW-03 | Preset results remain numerically unchanged | Regression/golden results across projects and scenarios |
| CW-04 | Missing, invalid, nonfinite, negative, >100%, or non-100% allocations are refused | Boundary-value tests |
| CW-05 | Disabling a component produces zero effective contribution and preserves validation rules | Component inclusion tests |
| CW-06 | Approved custom weights are immutable across update, explorer, normalize and tool calls | Locked-state and tamper/refusal tests |
| CW-07 | Composite line, component rows, waterfall and table reconcile to a single result | Contract and tab integration tests |
| CW-08 | A synthetic label, methodology/version, snapshot and source IDs are visible in result context | View-state and manual browser review |
| CW-09 | Weight inputs and preset buttons still work independently in the browser | Manual host/iframe interaction checks |
| UI-01 | Visual hierarchy aligns with the authoritative HTML reference where host allows | Side-by-side screenshots and SME sign-off |
| REL-01 | Existing UI baseline remains clean: **456 passed, 4 skipped** (2026-11-16) | Re-run UI suite, Ruff lint/format, Git diff check |
| REL-02 | Integration retains updates to `origin/main` and does not overwrite other contributors' docs | Git incoming/outgoing and file-diff review |

**Current verification status:** 456 UI tests passed and 4 were skipped before this proposed custom-allocation change; Ruff checks were clean. These tests do **not** establish that custom-result calculation is already supported or that manual host interactions are complete.

## 7. Branch integration and cleanup controls

The UI work is currently uncommitted on `feat/mcp-app` (snapshot provided 2026-11-16). `origin/main` was observed at `a725fa5`; re-fetch before integration because these facts can change. One upstream cost-intelligence test-file change (`test_pars_read_tools.py`) was identified, with no file-level overlap against the currently modified UI files. Preserve newer root `README.md` and `QUICKSTART.md`, BLS/PARS work, and other contributors' worktrees.

For closure: review and commit only validated UI work; fetch and compare with `origin/main`; integrate without force pushing; rerun tests and review the outgoing diff; then delete **only** owned local branches that are fully merged and not checked out in any worktree, using `git branch -d`. Do **not** remove branches merely because their names look old. The inventory shows `feat/fastmcp-app-closeout`, `feat/mcp-app`, `feat/pars-hardening`, and `main` are worktree-attached and therefore protected. Local fixes and `main-pre-closeout` require separate ancestry and ownership checks. The diverged `integrate/pars-mcp-into-main` branch (`ahead 6, behind 77` as inventoried) is **not** a routine pruning candidate. Do not prune remote branches automatically.

## 8. SME sign-off record

| Decision | SME response |
|---|---|
| Arithmetic fixed-weight composite acceptable for synthetic demo? | Pending |
| 2023 normalization and adjustment convention acceptable? | Pending |
| Custom weight approval/immutability behavior acceptable? | Pending |
| Preferred wording for synthetic vs approved results? | Pending |
| Required source/provenance and analyst review fields? | Pending |
| Chart/ribbon layout and metric hierarchy acceptable? | Pending |
| Any conditions before pilot or production data integration? | Pending |

**Reviewer / role:** ____________________
**Review date:** ____________________
**Decision:** Approve for synthetic demo / Approve with conditions / Revise and resubmit
**Comments and required changes:** _______________________________________

---

**Data and security note:** This proposal uses only synthetic in-memory fixture data. The proposed Python calculation has no required outbound network calls. Any later integration with BLS/PARS or real project data requires a separate source, privacy, security, and data-quality review. This document does not confer authorization to use or disclose real government data.
