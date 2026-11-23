# MVP FastMCP component list

**MVP scope:** a local BLS flat-file snapshot, no user API key, deterministic
and offline checks. A judge defines a weighted cost basket and gets an
escalation index in which every number traces to a snapshot observation.

Currently registered: 15 tools, 3 static resources, 1 resource template, and
0 prompts.

## Tools

Tools validate, calculate, and explicitly persist state. Each lives in its own
file under `src/bls_mcp/mcp/tools/`.

| Tool | Description |
| --- | --- |
| `search_series` | Search the local series catalog by text and program filters.
| `describe_series` | Return metadata for a known series ID, or null if it is not in the catalog.
| `get_series_hierarchy` | The parent and the sub-items nested directly beneath a series' code, each with its series ID in this snapshot (if any) and whether it has observations. Seeing the sub-items nested beneath a parent code is the primary way to verify what an index includes, so the server instructions and the `search_series`/`describe_series` descriptions point here before a series is chosen. PPI nests by industry and product code prefix; CPI items and ECI industry and estimate by published display level and sort order, skipping non-selectable headings. Display order is used only when it forms a single hierarchy; ECI occupation does not (eight top-level codes, and it would invert Sales and office with Office and administrative support), so occupation relationships are not reported. `status` is `complete`, `partial` or `unknown`, and `unverified` names each dimension that could not be identified and why, including PPI aggregates such as `OMFG--` whose members are not encoded in the code. An empty list is never presented as "nothing is published". |
| `create_index_spec` | Build a typed basket (periods, components, series, weights). Does not save or normalize weights. |
| `validate_index_spec` | Return structured findings for a basket. M3 adds periodicity-mismatch and source-backed input checks. |
| `save_index_spec` | Persist a specification by ID. Replaces an existing ID and updates its timestamp. |
| `get_index_spec` | Retrieve a saved specification, or null for an unknown ID. |
| `calculate_index_from_bls(spec_id)` | Read the saved spec, validate it, resolve exact base/target observations from the local snapshot, calculate, and return the composite with a ledger of sources, snapshot identity, and warnings. Missing data is an error, never zero. |
| `get_index_visualization(spec_id, start_year?, end_year?, source_year?)` | Annual history of a saved spec for charting, in the index visualization contract (`docs/UI Handoff schema/`, schema_version 1.0): components, normalized and weighted points, composite factors, a year-to-base adjustment and warnings. Incomplete years are left out and reported; ECI series use Q04. The same result, plus chart/table rows, is served to the web UI at `/api/index-visualization`. |
| `calculate_component_escalation` | Component factor from supplied base/target values and an explicit locality factor. |
| `calculate_index_spec` | Weighted composite from supplied component calculations, using the specification weights. |
| `calculate_labor_locality_factor` | Target/reference wage ratio from supplied wages. OEWS lookup is deferred. |
| `get_bls_access_status` | Report live-API configuration and limits without HTTP or secrets. |
| `get_series_data` | Retrieve live-API observations for known series IDs (key required; 50 series and 20 years per call). |

Flat-file download and ingestion is deliberately **not** an MCP tool: judges
must not be able to trigger BLS traffic. It is operator CLI work (`bls-data`;
see [OPERATIONS.md](../../../docs/bls/OPERATIONS.md)) under
[bls_etiquette.md](bls_etiquette.md).

## Resources

Resources are read-only, local, and bounded reference material. One per file
under `src/bls_mcp/mcp/resources/`.

| URI | Description |
| --- | --- |
| `guide://escalation-workflow` | Canonical project-to-index workflow: stages, questions to ask, which tool to call, missing-input handling, and links to the other resources. |
| `bls://snapshot` | Snapshot identity, per-file retrieval dates and hashes, per-program catalog versus observation coverage, and verification scope. Shares one snapshot-identity service with the M3 ledger. |
| `basket://archetypes/{archetype_id}` | Reviewed decomposition (materials, labor, fixed share), candidate search terms, and worked examples. Starts with `vertical-construction`. Examples never supply authoritative weights. |
| `bls://series/{series_id}` | JSON metadata for a known local series. Unknown IDs return a resource error. |
| `methodology://composite-index` | Temporal factors, weighted composite, and percent change. M3 extends it with weight tolerance, exact periods, single periodicity, precision, and snapshot disclosure. |
| `methodology://locality_adjustment` | The separate, explicitly applied wage ratio. Extended with wage-evidence requirements; states that OEWS mapping is deferred. |
| `setup://bls-api` | Optional live-API registration, key configuration, and limits. Reworded to separate it from the no-key snapshot flow. |

## Prompts

Prompts organize the host LLM's workflow. Retrieving one returns text only: it
runs no tools, saves nothing, downloads nothing, and calls no LLM. Hosts may
not expose prompts, so nothing may live only in a prompt; the workflow guide is
the single source. One per file under `src/bls_mcp/mcp/prompts/`.

| Prompt | Description |
| --- | --- |
| `design_escalation_basket` | Required `project_description`; optional `base_period`, `target_period`, `locality`, `archetype_id`. Guides scope clarification, candidate-series review, and a draft component table with exclusions and weight sources. |
| `calculate_and_explain_index` | Required `spec_id`. Guides a source-backed calculation and explains periods, contributions, provenance, and limits. Designed with M3 and not advertised until `calculate_index_from_bls` exists. |

## Context

FastMCP `Context` is a runtime object, not a registered component type. The
MVP uses it, and related shared context, as follows.

| Context item | Description |
| --- | --- |
| `ctx: Context` in handlers | Injected into every handler and hidden from client schemas. Handlers call `get_services(ctx)` (`mcp/adapters.py`), which reads `ctx.lifespan_context["services"]`. | Implemented |
| Lifespan-owned `Services` | Built once per server run in `lifespan.py`: access, catalog, observations, specifications, calculations, locality, validation. Never module singletons; DuckDB connections stay scoped to individual store and repository operations. |
| Snapshot-identity and observation-resolution services | Added to the lifespan for `bls://snapshot` and `calculate_index_from_bls`. |
| Server `instructions` | Entry-point guidance in `server.py`. Currently covers only the live-API flow; must point to `guide://escalation-workflow` and the no-key snapshot flow. |
| `Settings` | Typed operator configuration (database path, weight tolerance) from `.env`. Credentials and settings never appear in client-visible arguments. |
| Archetype and example content | Reviewed, versioned local content shared by the archetype resource, the prompt, and eval fixtures. |

Not used in the MVP: sampling, elicitation, subscriptions, progress reporting,
and MCP-level authentication.
