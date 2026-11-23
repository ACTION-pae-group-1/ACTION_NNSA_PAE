# PARS MCP wiring spec for the cost-intelligence UI

Scope: how the PARS MCP server (`pars_mcp`) plugs into the cost-intelligence UI on `feat/mcp-app`. This spec defines the contract only. The UI code belongs to the `feat/mcp-app` worktree (`C:/Users/maura.lapoff/Software/GitLocal/mcp_group_1-mcp-app`). Nothing in that worktree changes from this spec.

## What exists today (read-only review, 2026-11-15)

- **UI app:** a FastMCP app in `src/cost_intel_app/` (`server.py`, `basket_state.py`). Its tools are `update_basket`, `normalize_basket`, `approve_basket`, and `choose_preset`. The app is the PPI escalation basket.
- **Design file:** `docs/ai_mcp_cost_intelligence_nnsa_spec_aligned.html`, titled "PPI Results Explorer". It already plans for PARS in three places:
  - a source row, "CPDS / PARS: project descriptions and WBS context (mock)";
  - a tool log entry, `cpds_pars.read_project`, "Project and WBS context returned (demo fixture)";
  - a "PARS WBS write-back preview" modal. It shows a draft only and makes no update.
- **Project & evidence panel:** the right-hand panel (`aside#right`). Its "WBS context" is a single text field today.
- **Project keys differ:** UI projects are hypothetical NNSA projects (for example `y12`, id `DEMO-NNSA-Y12-001`). PARS projects are synthetic `parsid` values. The two sets do not match yet.

## Components to wire

| UI component | PARS tools | What the UI shows | Notes |
|---|---|---|---|
| Project & evidence header | `list_projects`, `get_project_info` | project name, id, WBS summary | replaces the mock "WBS context" text |
| WBS hierarchy view | `get_wbs_hierarchy`, `get_leaf_nodes`, `get_wbs_by_level` | tree of cost components for the selected project | level is the reported WBS level, not the WBS code |
| WBS search | `search_wbs` | matching elements with level and lineage | requires a non-blank project id |
| Element lineage | `get_wbs_lineage` | element first, then ancestors to the root | matches the tool description |
| Classification evidence | `validate_wbs_inputs`, `get_wbs_run_status` | data origin label, input check, run stages | shows "synthetic" when the origin is synthetic |
| Read-only data views | `get_wbs_project_descriptions`, `get_wbs_rows` | descriptions and sample rows | shown only when the source is synthetic; otherwise hidden |
| Agent chat | the 11 read-only tools (`READ_ONLY_TOOLS`) | the agent answers scope questions from PARS | the chat log logs each tool call |
| Write-back preview | none | draft preview only | `write_back_wbs` is on hold and is not called |

The UI calls only the 11 read-only tools. They are a subset of the `pars_mcp` allowlist in `src/mcp_servers.json`. The drift test checks the subset and the committed manifest.

## Connection

- The UI connects to PARS as an MCP client by running `uv run --no-sync python -m src.pars_local_mcp.server` from the repo root. The `--no-sync` flag means starting the server never syncs the checkout's `.venv`. The `pars_mcp` entry in `src/mcp_servers.json` uses the same flag.
- Tool names, arguments, and return keys are the ones defined in `src/pars_local_mcp/mcp/tools.py` and `wbs_tools.py`.
- Errors are returned as `{"error": "<fixed message>"}`. The UI shows the message and does not show exception text.

## Data rules

- All PARS data is synthetic. When PARS reports the origin as `synthetic_mock`, the header and evidence panels carry the label "synthetic" and the read-only views show. For any other origin, those panels show PARS's origin name and the read-only views stay hidden (see `docs/DATA_HANDLING.md`).
- The UI never calls `write_back_wbs`. The preview modal stays a draft.

## Acceptance criteria

1. Selecting a project shows its PARS header and hierarchy, with no mock text left in that panel.
2. Each PARS panel has three states: loaded, empty, and error (fixed message).
3. Read-only data views hide when the source is not synthetic.
4. The agent chat log shows each PARS tool call and its status.
5. Nothing in the UI calls a tool outside the allowlist.

## Open decisions

1. **Project keys (decided):** the PARS panels use the PARS project id (`parsid`, for example `100` or `1074`) as the project key. The UI reads the list at runtime from `list_projects`, so there is no mapping table and no separate picker. The `y12` keys stay only for the PPI basket until the `feat/mcp-app` branch decides whether to retire them.
2. **Pipeline from the UI:** should the UI start tune or predict runs, or only show runs that already exist? Recommendation: show existing runs only for the demo. Tuning depends on the dataset and can be slow.
3. **Owner of the PARS panels:** the `feat/mcp-app` branch implements them against this contract. Any change to tool names or return keys goes through the PARS closeout spec first.
