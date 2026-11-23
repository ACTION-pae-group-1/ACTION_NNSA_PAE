# Testing and evals

This is the single human-readable record of what the test suite actually
guards against, and of the project's evals status. Update it in the same
change that adds, removes, or changes the intent of a test — a test whose
purpose isn't reflected here is undocumented. Group trivial or parametrized
variations of one idea into a single entry rather than listing each case.

## How to read this document

Each entry names the test(s), the expected value or outcome, and the
concrete mistake it would catch. "Expected value" is the independently
computable result the test checks against (see `docs/DEVELOPMENT.md`'s
testing principles) — not a description of the code path.

## Test harness (M0)

Shared scaffolding lives in `tests/conftest.py` (guarantees) and
`tests/harness.py` (importable helpers), with canned payloads in
`tests/fixtures/bls/` (hand-written, not recordings — see its README).

Guarantees, and what enforces them:

- **No test observes a real `BLS_API_KEY`.** An autouse fixture strips it
  before every test not marked `live`, so a key exported in a developer's
  shell can neither change offline results nor spend quota. `live` tests
  are exempt by design (they only run under `poe test-live`).
- **Nothing live runs by default.** The `live` marker is registered and
  deselected in `addopts`; `poe test-live` selects it, and a collection
  hook skips (never fails) when no key is exported, so CI and `poe check`
  stay offline per `docs/bls_etiquette.md`.
- **One canned-BLS world.** `CannedTransport` records requests, optionally
  asserts each request body, and serves a fixture payload;
  `duckdb_server_env(...)` (`tests/harness_duckdb.py`) runs the real server
  on a temporary published DuckDB snapshot and a temporary specs file through
  the real FastMCP client and asserts — on failure paths too — that the
  lifespan closed the injected transport. `bls_payload()` returns a fresh
  copy per call so tests cannot mutate each other's data.
- `poe test-cov` is a diagnostic only; it carries no threshold and is not
  part of `check`.

### `tests/test_harness.py` — harness self-tests

| Test | Expected | Guards against |
| --- | --- | --- |
| `test_env_leak_from_prior_test_a` + `_b` (an ordered pair relying on in-module definition order) | `_b` never observes the sentinel key that `_a` leaks into the real process environment | A leaked or shell-exported key silently changing offline results or letting a test spend real quota |
| `test_live_marker_seam` | Deselected in the default run; skipped (not failed) by `poe test-live` without a key; passes with one; no network call in any of these | The live seam accidentally running in `check`/CI, or failing closed instead of skipping cleanly |

## Unit tests

### `tests/test_flat_file.py` — BLS flat-file parsers (PC/PD)

Expected values are hand-checked against the fixture slices in
`tests/fixtures/bls/flatfile/` (bytes cut from the real files in
`src/bls_mcp/docs/sample_data/`).

| Test | Expected | Guards against |
| --- | --- | --- |
| `test_pc_series_padding_and_fields` | `"PCU1133--1133--"` with padding stripped, title/base/periods as in the file | Space-padded fields leaking into stored IDs or metadata |
| `test_pd_series_blank_extra_column` / `test_pd_series_shape_drift_fails_loudly` | PD's undocumented blank 6th column skipped; any other shape → `FlatFileFormatError` | The header/row field-count mismatch silently shifting PD columns (known real quirk) |
| `test_data_file_period_identity_and_precision` | `M13` → `month=None` with exact value `99.0`; `234.780` keeps its 3-decimal scale; `P` footnote captured | Annual averages misfiling as a 13th month; float rounding of index values |
| `test_data_file_unknown_period_is_warned_not_dropped` | Unknown `Q05` row skipped with `warnings["Q05"] == 1` | Silent data loss — skips are always counted into the manifest |
| `test_data_file_header_only_partition_is_empty_not_error` | Header-only partition → 0 rows, no error | Empty partitions (they exist: 72 bytes) failing ingestion |
| `test_data_file_field_drift_fails_loudly` | `FlatFileFormatError` on a 6-field data row | Column-count drift parsing into wrong positions |
| `test_pd_product_quirk_name_in_last_field` / `test_simple_mappings` | `"Secondary products"` read from the last field of a 6-field row; code+name mappings exact | Fixed-position name parsing misreading real mapping rows |
| `test_ci_series_file_parse` | The 4 fixture rows parse with owner/industry/periodicity/estimate codes and quarterly begin/end (construction wages series: 2001-Q1 → 2026-Q2), padding stripped | ECI's 15-column layout misread |
| `test_ci_index_eligibility_gate` | The 3 `I` series are eligible and the `Q` percent-change twin is not | Percent-change or response-rate series leaking into the catalog as escalation inputs |
| `test_ci_mappings` | `I` → "Current dollar index number", `01` → "Total compensation", `2` → "Private industry workers" | CI's name-in-column-2 layout (trailing display metadata) being misparsed as the last field |
| `test_data_file_quarterly_periods` | `Q01` → quarter=1, month=None; out-of-range `Q05` skipped with a counted warning | Quarterly periods misfiled or silently dropped |
| `test_data_file_missing_dash_is_recorded` | A `-` row (footnote `A`) is skipped with `missing_rows == 1` and a parallel fabricated-value row (`abc`) raises `FlatFileFormatError` | The missing-data sentinel ever becoming a stored observation, or hard failures that would make real released files un-ingestible |
| `test_wp_series_file_parse` | 6 rows parse with group/item/seasonal/YYMM-base and titles (`WPS0811` lumber → 2026-M08); the doc's 10-field layout (file has 11: undocumented `footnote_codes`) fails loudly; retired series (`WPS00000000`, `WPS1371`) kept | WP header drift vs `wp.txt`; padding leaks; ended series vanishing |
| `test_wp_mappings` | `08\t11` → "Softwood lumber", `10\t17` → "Steel mill products", `08` → "Lumber and wood products" | The two-code item key or last-field name rule misread |
| `test_classify_file*` (parametrized) | Filenames map to `(program, kind, canonical upstream name)`, stripping `.txt`/`.sample`/`.head`/`.slice`; docs/probe/README files rejected | Misrouting a support file into a parser, or recording a sample's name as a canonical URL |

### `tests/test_calculations.py` — `EscalationCalculationService`

| Test | Expected | Guards against |
| --- | --- | --- |
| `test_one_component_weight_one` | `temporal_factor ≈ 1.1` for base 100 → target 110 | Temporal factor drifting from `target / base` |
| `test_if_every_temporal_factor_equals_one_works` | Composite `≈ 1.0` when every component's base equals its target | Weighting/aggregation introducing drift when no escalation occurred |
| `test_locality_factor_one_keeps_localized_equal_to_temporal` | `localized_composite_factor == temporal_composite_factor` when every `locality_factor = 1.0` | Locality factor of 1 failing to be a true no-op; localized/temporal paths diverging |
| `test_fixed_unindexed_component_has_temporal_factor_one` | `temporal_factor ≈ 1.0` for a `FIXED_UNINDEXED` component even with base 100 → target 200 | Fixed/unindexed components being escalated despite the methodology fixing them at 1 |
| `test_order_of_components_does_not_change_result` | Same composite factor with components reversed | Order-dependent (non-commutative) aggregation bug |
| `test_weighted_component_contributions_sum_to_composite_factor` | Composite equals `sum(weight * temporal_factor)` computed independently inline | Composite formula silently diverging from the documented weighted-sum methodology |
| `test_zero_base_value_raises` | `CalculationError` | Division by zero returning `inf`/garbage instead of an explicit domain error |

### `tests/test_locality.py` — `LocalityService`

| Test | Expected | Guards against |
| --- | --- | --- |
| `test_labor_locality_factor_for_reference_and_target_wages` | `locality_factor ≈ 1.25` for reference wage 40, target wage 50 | Locality factor formula drifting from `target / reference` |
| `test_zero_reference_wage_invalid` | `CalculationError` | Division by zero in the locality factor |

### `tests/test_validation.py` — `ValidationService`

| Test | Expected | Guards against |
| --- | --- | --- |
| `test_valid_basket` | `valid is True` | False positives on a well-formed basket |
| `test_weights_not_equal_to_one` | `WEIGHTS_SUM_MISMATCH` finding | Silently accepting a basket whose weights don't sum to 1 |
| `test_negative_weight` | `NEGATIVE_WEIGHT` finding | Silently accepting a negative weight (would invert escalation) |
| `test_missing_series_on_indexed_component` | `MISSING_SERIES_ID` finding | An indexed component calculating with no underlying data source |
| `test_series_on_fixed_component` | `FIXED_COMPONENT_HAS_SERIES` finding | A fixed component ambiguously wired to a series |
| `test_material_component_locality_warning` | `LOCALITY_ON_MATERIAL_OR_EQUIPMENT` finding | Labor-locality adjustment being applied to a non-labor cost type |

### `tests/test_periods.py` — `EconomicPeriod`

| Test | Expected | Guards against |
| --- | --- | --- |
| `test_valid_monthly_period`, `test_valid_quarterly_period`, `test_valid_annual_period` | String form `"2025-M03"` / `"2025-Q2"` / `"2025"` | Period label/formatting regressions that would corrupt displayed or stored provenance text |
| `test_invalid_period_combinations` | `ValueError` when `month` and `quarter` are both set | Constructing an internally contradictory period |
| `test_period_ordering` | Dec-2024 `<` Jan-2025 | Incorrect period comparison, which would break chronological sorting of observations |

### `tests/test_specifications.py`

| Test | Expected | Guards against |
| --- | --- | --- |
| `test_json_serialization_round_trip` | `model_dump(mode="json")` → `model_validate` preserves `id` and component `id` | Schema drift that silently loses or corrupts fields across the JSON wire format MCP clients actually receive |

### `tests/test_installation.py`

| Test | Expected | Guards against |
| --- | --- | --- |
| `test_package_imports_outside_checkout` | `import bls_mcp` succeeds in a subprocess run outside the repo checkout | A src-layout/packaging misconfiguration that only works by accident when run from inside the repo |

### `tests/test_review_regressions.py` — regressions from PR #1 review

| Test | Expected | Guards against |
| --- | --- | --- |
| `test_missing_observations_are_rejected` (parametrized: `None`, `""`, `"-"`, `"NaN"`, `"Infinity"`) | `BLSAPIError` ("Missing or non-numeric") | Silently coercing BLS's missing-data sentinels (notably `"-"`) into a numeric value |
| `test_actual_zero_is_preserved` | Observation value `Decimal(0)` | A real zero value being treated as missing by the check above |
| `test_deferred_loaders_return_no_fabricated_metadata` (parametrized: `PPILoader`, `ECILoader`, `OEWSLoader`) | `parse_metadata([])` and `parse_metadata([{"unmapped": "value"}])` both return `[]` | A stub loader fabricating plausible-looking series metadata instead of honestly returning nothing before real field mappings exist |
| `test_annual_and_annual_average_do_not_overwrite` | Both an `ANNUAL` and an `ANNUAL_AVERAGE` observation for the same year persist distinctly | An upsert key bug that treats the two periodicities as the same row |
| `test_observation_decimal_text_is_exact` | A 29-digit decimal string round-trips exactly through parsing and JSON re-serialization | Float rounding/precision loss on BLS values (the reason observations are `Decimal`-as-string, per `docs/DECISIONS.md`) |

## Integration tests (real FastMCP client/server boundary)

These modules build on the shared harness above (canned transport,
`duckdb_server_env`, fixture payloads); the entries below keep their pre-M0 names
and guards — M0 consolidated scaffolding without changing what any test
asserts.

### `tests/bls/unit/test_series_hierarchy.py` — what an index includes

| Test | Expected | Guards against |
| --- | --- | --- |
| `test_industry_codes_nest_by_prefix_ignoring_dash_padding` / `test_product_codes_nest_by_longest_prefix_within_an_industry` | `32111-` ⊂ `3211--`; `32111333` ⊂ `3211133` ⊂ industry total `321113`; codes that skip lengths still find their parent; `ATRADE` has none | PPI dash padding or length jumps breaking the nesting |
| `test_display_levels_nest_by_nearest_shallower_code_in_sort_order` / `test_headings_bound_the_tree_but_are_never_a_parent` | ECI Real estate sits under Financial activities with no shared prefix; a code under a missing level attaches to the nearest ancestor; CPI "All items less food and energy" stays under All items, not Food and beverages, though a heading separates them | Inferring CPI/ECI nesting from code prefixes; a removed heading collapsing the tree |
| `test_ppi_*`, `test_cpi_*`, `test_eci_shows_what_total_compensation_includes` | Sawmills lists hardwood, softwood and wood chips with series IDs and data flags; Softwood lists its dressed-lumber series; ECI total compensation lists wages and benefits, and no subcell/area/owner entries | The lookup returning the wrong level, mixing seasonal adjustments, or listing cross-tabulations as composition |
| `test_display_order_with_several_top_level_codes_is_rejected` / `test_status_is_unknown_when_no_dimension_could_be_identified` | The published ECI occupation order (several level-0 codes) is rejected rather than walked; a single root passes and headings are not roots; a series with no identifiable dimension is `unknown` | Trusting a display order that is not a hierarchy |
| `test_eci_office_support_is_not_reported_as_containing_sales_and_office`, `test_eci_estimate_composition_is_still_reported`, `test_ppi_aggregate_does_not_claim_nothing_is_published`, `test_sawmills_path_on_real_files_is_complete` (real sample files) | On the real BLS files: `CIS2010000220000I` and `CIS2010000200000I` make no occupation claim about each other and report occupation as unverified; ECI estimate composition is still listed; `PCUOMFG--OMFG--` is `partial` with snapshot-scoped wording; Sawmills is `complete` | The inverted occupation relationship found in review; an empty result overstating what BLS publishes |

`test_series_hierarchy_tool_and_lesson_reach_the_agent` (in
`tests/integration/test_phase1_duckdb_server.py`) checks through a real MCP
client that the tool works and that the lesson ("seeing the narrower sub-items
nested beneath a parent code is the primary way to verify what an index
includes") is in the server instructions and the tool description, and that
`search_series`/`describe_series` point to it.

`tests/evals/test_bls_evals.py::test_series_found_through_hierarchy_counts_as_discovered`
runs the eval with an agent that searches "Sawmills and wood preservation" and
takes Sawmills from its sub-items; every check must pass, so the discovery
guardrail credits series found through `get_series_hierarchy`. A companion
test checks that only the related series count, not the series the tool was
asked about.

### `tests/integration/test_bls_client.py`

| Test | Expected | Guards against |
| --- | --- | --- |
| `test_bls_client_parses_mocked_payload` | 2 observations parsed from a mocked HTTP response, correct `series_id`/`value` | The client's request/response parsing breaking against the real BLS JSON shape |

### `tests/integration/test_bls_access.py`

| Test | Expected | Guards against |
| --- | --- | --- |
| `test_access_setup_and_preflight` (parametrized key: `None`, `""`, `"  "`, a real key) | `credential_status` reflects `missing`/`configured_unverified` correctly; status/setup calls make zero HTTP requests; the key never appears in any tool, resource, or instructions text; an unconfigured key fails every live call pointing to `setup://bls-api`; a configured key still enforces the 50-series/20-year bounds; a successful data response does not flip status to "verified" | Leaking the API key into client-visible output; treating a successful response as proof of key validity; burning request quota just to check status; accepting an over-limit request |

### `tests/test_project_shell.py` — launcher and infrastructure

- Transport precedence: default stdio, explicit loopback HTTP, platform `PORT`,
  and Databricks port precedence. A mocked server verifies launch arguments;
  this does not test an actual network socket.
- Invalid platform ports fail before server construction.
- `.env` supplies transport/BLS settings; environment overrides file values.
- `/health` and `/version` return the documented JSON through a real ASGI app
  and its lifespan with a temporary database. These are availability probes,
  not live BLS checks. Docker and vendor deployments need separate validation.

The template-aligned evaluation entry point is [eval/README.md](../eval/README.md).

### `tests/test_component_layout.py` — template layout

Checks every tool/resource module has exactly one decorated component inside
its typed `register` function, named to match its filename. This prevents
regression to grouped handlers; existing MCP client tests separately guard
aggregate discovery, schemas, annotations, invocation and resource contents.

## Evals

**Status: a deterministic eval-evidence pack is in scope for the hackathon
MVP (M4' in [ROADMAP.md](ROADMAP.md)); the LLM-backed harness is deferred to
after the hackathon.** The M4' pack runs scripted scenarios through the real
MCP client against a fixture-built database (oracle workflows plus negative
probes), commits a short results summary under `eval/`, and feeds the
hackathon evaluation document's testing-methodology and performance-metrics
sections. The first external eval remains the hackathon judging
itself; owner manual-eval sessions precede it (the M6 gate).

The suite above verifies deterministic code — given fixed inputs, is the
output correct. It says nothing about an LLM or agent's judgment when
driving these MCP tools under ambiguity (which series to pick, how to
handle a basket with no explicit weights, whether to ask for guidance
instead of inventing a value).

### `eval/bls/` — conversation evals (built)

Three cases run the real server through a real MCP client against a synthetic
snapshot, with a scripted user. See [eval/bls/README.md](../../../eval/bls/README.md).
`poe eval-selftest` runs them with scripted agents and no model; `poe eval`
runs a configured model.

| Case | Expected | Guards against |
| --- | --- | --- |
| `known-basket-missing-target-year` | Agent asks for the target year, then returns composite 1.4475 for the stated 45/35/20 basket, 2014 → 2026, citing series, weights, periods and snapshot | Assuming a period; wrong arithmetic or basket; an uncited answer |
| `mixed-materials-and-labor` | PPI materials (annual) plus an ECI-like labor series (quarterly-only) in one annual-basis spec: composite 1.57, with the labor component citing its 2014-Q04 and 2026-Q04 source quarters | A hand-typed composite; an answer that implies an annual average the program never published |
| `vague-project-negotiated-basket` | Agent clarifies periods, scope and weights, proposes a basket, gets a yes, then calculates; steel carries the user's stated half | Guessing instead of asking; calculating before confirmation; overriding a stated share; using series the catalog never returned |

`tests/evals/test_bls_evals.py` keeps the harness honest: the oracle agents
must pass every check and each flawed agent must fail exactly its expected
checks (`test_selftest_oracles_pass_and_flawed_agents_are_caught`), the known
answer is recomputed by hand, and the model adapter is exercised with a
scripted stand-in for the model.

Agent runs are recorded under `eval/bls/results/runs/` and read back with
`poe eval-report`; `tests/evals/test_recording.py` covers the roll-up, the
record round trip, run comparison, and that endpoint failures are excluded
from scores while agent failures are not.

The principles the harness follows, and that additions should keep:

- Start from this project's own known failure modes, not generic prompts:
  silent weight normalization, series substitution without disclosure,
  missing-data interpolation, presenting a stale snapshot as current, and
  conflating temporal and locality factors. (The request-bounds failure
  modes belong to the deferred live-API path.)
- Score tool choice, numeric correctness, and methodology disclosure as
  separate dimensions — one blended pass rate hides which one regressed.
- Grade programmatically wherever checkable (the actual tool calls made, the
  returned provenance, the computed numbers) rather than by LLM judgment.
- Re-run whenever a tool description, schema, or model changes; nothing in
  the code "breaks" when behavior drifts, so only the evals catch it.


## Python smoke command

`tests/test_smoke_mcp.py` runs the command's workflow through the real in-memory
FastMCP client without a BLS key, verifies no upstream requests occur, checks
that an unrelated server fails discovery, and now guards the `main()` validation
boundary: remote/local-credential URLs and non-finite/non-positive timeouts are
rejected before a server connection is attempted. `poe smoke` separately targets
a running HTTP server and checks discovery, status, guidance resources and
an independent 110/100=1.1 calculation. It does not establish live BLS access
or agent performance and does not write specifications.


### Local verification evidence — 2026-10-08

- The Python smoke workflow passed over an actual loopback Streamable HTTP
  connection to a temporary-database server, with BLS HTTP mocked and no key.
  Discovery returned 11 tools, 3 static resources, and 1 resource template;
  status/guidance reads and the 110/100=1.1 calculation passed, exit code 0.
- After merging the `serve` task from main into the smoke branch at `ac52b90`,
  both Poe task dry-runs resolved to their intended Python modules.
  `uv run --locked poe check` passed: lint, formatting, mypy, and 74 tests.
- One existing Starlette TestClient deprecation warning remains.
- These checks establish local protocol connectivity and deterministic behavior.
  They do not establish live BLS access, deployment readiness, stdio host
  compatibility, or model-driven agent quality. No Node.js was required.
