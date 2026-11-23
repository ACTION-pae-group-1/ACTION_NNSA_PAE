from __future__ import annotations

from fastmcp import FastMCP

ESCALATION_WORKFLOW_GUIDE = """\
# Escalation index workflow

Use only the tools listed here; nothing else is implied to exist.

## 1. Clarify scope
Ask only for what is missing: the project scope and components, the base and
target periods, each component's cost share and where that share comes from,
and any locality evidence. A city alone does not authorize a locality factor.

## 2. Find candidate series
- `search_series` finds candidates by substring; a title does not show what an
  index includes.
- `get_series_hierarchy` shows the narrower sub-items nested beneath a parent
  code. This is the primary way to verify what is included. Pick the level
  whose sub-items match the component, and tell the user what a chosen parent
  series includes. If its `status` is not `complete`, say which relationships
  could not be identified (`unverified`) and do not claim what is included
  beyond the sub-items listed.
- `describe_series` (or `bls://series/{series_id}`) gives program, unit,
  periodicity and date coverage. Missing metadata stays unknown.
- A series with no observations in the snapshot cannot be used. An explicit
  no-match is a valid outcome. The user approves any disclosed proxy.

## 3. Review checkpoint
Show a draft component table: series ID and title, what it includes, share,
weight source, exclusions and open questions. Separate user inputs from
illustrative assumptions. Wait for the user to confirm.

## 4. Build and validate
Call `create_index_spec`, then `validate_index_spec`. All components need one
periodicity. Do not save unless the user asks (`save_index_spec`; say so if
it replaces an existing ID).

## 5. Calculate
- Snapshot-backed: `calculate_index_from_bls` on a saved spec.
- Supplied-value what-if: `calculate_component_escalation` or
  `calculate_index_spec`, clearly labeled as supplied values.
- Locality, only when the user supplies wage evidence:
  `calculate_labor_locality_factor`. Read
  `methodology://locality-adjustment` and `methodology://composite-index`.

Report periods, weights, per-component factors and the composite. Never
invent observations or treat missing data as zero.
Live retrieval is optional; see `setup://bls-api` and
`get_bls_access_status`.
"""


def register(mcp: FastMCP) -> None:
    @mcp.resource("guide://escalation-workflow", mime_type="text/markdown")
    def escalation_workflow_resource() -> str:
        """Read the project-to-index workflow, checkpoints, and links."""
        return ESCALATION_WORKFLOW_GUIDE
