# Results explorer UI

`ai_mcp_cost_intelligence_nnsa_spec_aligned 1.html` is the front-end
proposal: a self-contained, offline page built around precomputed fixtures.
It stays here unchanged as the design reference.

The served version is `src/bls_mcp/web/index.html`, generated from the
proposal with a live mode added. When the server runs over HTTP it is at
`/ui`:

- `GET /api/specs` lists saved specifications with their components.
- `GET|POST /api/index-visualization` takes `spec_id` and, optionally,
  `start_year`, `end_year`, `source_year` and (POST only) `weights` as
  `{component_id: fraction}`, a what-if that does not change the saved spec.
  It returns `{"result": IndexVisualizationData, "presentation": {...}}`:
  the same shape as the proposal's fixtures. `result` follows
  `docs/UI Handoff schema/index_visualization_v1.schema.json`, and
  `presentation` holds `adjustments_by_year`, `table_rows`, `stack_layers`
  and `latest_change_percent`.

The page runs its existing `validatePayload` contract check on every server
response before drawing it. `tests/integration/test_index_visualization.py`
runs that same function in Node against a real server response, and
`tests/bls/unit/test_index_visualization.py` pins the Pydantic model to the
published JSON Schema, so the backend and page cannot drift apart silently.

Opened as a local file, the served page behaves like the proposal: fully
offline, with example projects only.
