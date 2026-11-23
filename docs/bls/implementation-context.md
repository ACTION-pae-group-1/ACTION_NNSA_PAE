# BLS storage and ingestion rebuild: implementation context

> **Historical record.** This document was written while the DuckDB store was
> being built alongside the original SQLite catalog. That migration is
> complete: the SQLite catalog, its ingestion pipeline and the `bls_mcp.db`
> package have been removed, and the MCP server reads only the published
> DuckDB snapshot. Mentions of SQLite below describe the state at the time of
> writing, not the current code. See `src/bls_mcp/docs/DECISIONS.md`
> (2026-11-13) and [OPERATIONS.md](OPERATIONS.md) for the current design.

Status: Milestones 2-5 supplied in the uploaded 2026-11-05 branch; Milestone
6 lifecycle is implemented in this patch. Native publication tests are pending.
This is a navigation and design record. The repository,
its fixtures, and its tests take precedence when an assertion here becomes
stale. The controlling specification is "BLS_MCP: Storage and Ingestion System
Rebuild", version 1.0. Review this document before the next milestone, then
reopen only the specific source files needed.

## 1. Objective, scope, and non-goals

Build an MCP-independent, read-only analytical data foundation for BLS bulk
series, initially Producer Price Index industry (`pc`) and Consumer Price Index
(`cu`, especially CPI-U). Ingest locally archived original files or downloaded
BLS TSVs, validate them, build immutable DuckDB snapshots, search their series
catalogs, retrieve one to at least 1,000 series, and normalize each series to
an explicitly requested base observation. Every result must identify its
snapshot. The primary use case is reproducible cost escalation.

The new implementation lives alongside, rather than replacing, the existing
SQLite BLS catalog/cache. The current MCP tools, live BLS API client, escalation
calculations, and saved escalation specifications remain operational during this
phase. Do not migrate application/user state into DuckDB or introduce a new
service/database infrastructure dependency. MCP wiring, live snapshot hot-swap,
authentication changes, and redesigning the escalation application are not part
of this rebuild. Existing `pd`, `ci`, and `wp` parsing and service behavior must
not disappear merely because the first new adapters target `pc` and `cu`.

## 2. Settled architectural decisions

These decisions come from the specification; later milestones should not reopen
them without a demonstrated technical blocker.

| Area | Decision and implication |
| --- | --- |
| Analytics | DuckDB, not SQLite, for the new observation store; `DOUBLE` values. |
| Canonical data | One logical `observations` table; key `(series_id, year, period)` must be unique in a published snapshot. |
| Physical layout | Physically sort by `series_id, year, period`. Milestone 3 adds a post-load ART on `observations(series_id)` for selective lookups; benchmark the memory and latency tradeoff in Milestone 7 against an unindexed baseline and Parquet. |
| Catalog | Shared cross-program catalog plus separate source-program classification tables and mappings. |
| Normalization | Compute in SQL using each series' exact base observation; default target base 100, no interpolation or fallback. |
| Updates | Offline builds in a separate database; validate, checkpoint and close writers, then publish immutable versioned files. |
| Readers | Explicit read-only connections; bound concurrency/threads/memory, independent multi-process reads and proper cleanup. |
| Reproducibility | Original bytes, checksums, file selection, validation and snapshot identification are required. |
| Boundaries | Storage and ingestion must import neither FastMCP nor existing tool adapters. |

A DuckDB `PRIMARY KEY` can create index/constraint overhead; do not assume it
belongs on the initial benchmark baseline. Enforce logical key uniqueness and
referential integrity in build validation, and evaluate physical constraints
separately. Do not use a row-per-file or file-per-series storage design.

## 3. Repository inventory and dependency map

The 2026-11-04 repository archive has no `src/bls_mcp/storage/` or
`src/bls_mcp/ingestion/` package and does not declare `duckdb` in
`pyproject.toml`/`uv.lock`. The current project is Python >=3.11, uses uv/Poe,
Ruff, mypy, pytest, Pydantic v2, and FastMCP `>=3.2,<3.3` (3.2.4 locked).
Do not upgrade FastMCP to 4.x as collateral to the storage rebuild. The
repository's `CLAUDE.md` graphify rule is conditional; `graphify-out/` was not
present in this archive.

| Current location | Responsibility / significance |
| --- | --- |
| `src/bls_mcp/data/flat_file.py` | Verified PC/PD/CI/WP TSV parsing, period and missing-value handling; main behavioral reference. |
| `src/bls_mcp/data/ingest.py` | Offline, per-file orchestration; mapping -> series -> observations; skips unrecognized files and uses SQLite repos. |
| `src/bls_mcp/data/fetch.py` | Sequential, conditional-GET downloader with identifying User-Agent, temporary files, SHA-256 and length checks. |
| `src/bls_mcp/data/fetch_manifest.py` | Explicit manifest-based fetching, local receipts, SQLite importing and CSV export. |
| `src/bls_mcp/data/manifest.py`, `verify.py` | Deterministically serialized per-file provenance; file/hash/count and SQLite receipt verification. |
| `src/bls_mcp/db/connection.py`, `schema.py` | SQLite connection factory and schema initialization; also stores application state. |
| `src/bls_mcp/repositories/{series,observations,ingestion_log}.py` | SQLite metadata, observations, ingestion receipts. |
| `src/bls_mcp/repositories/specifications.py` | SQLite saved user escalation specifications; must stay separate from DuckDB. |
| `src/bls_mcp/models/{series,observations,periods,enums,provenance}.py` | Existing public serialization, period and program contracts. |
| `src/bls_mcp/services/{series_catalog,observations}.py` | Search, cached retrieval and live API retrieval. |
| `src/bls_mcp/clients/bls.py` | Independent BLS API v2 client; not the new bulk downloader. |
| `src/bls_mcp/lifespan.py`, `server.py`, `app.py`, `config.py` | Lifespan-owned services/HTTP client, FastMCP factory, transport and environment settings. |
| `src/bls_mcp/mcp/tools/`, `mcp/resources/` | Public tool/resource adapters; existing behavior is a migration boundary. |
| `src/bls_mcp/tests/`, `tests/integration/` | Unit, offline integration, MCP and regression contract tests. |
| `src/bls_mcp/docs/`, `data/manifest.json` | Historical format decisions, owner-saved samples, and tracked *legacy* source receipts. |
| `pyproject.toml`, `uv.lock`, `.github/workflows/ci.yml` | Locked workflow and checks; add new dependency/entry points in later PRs, not this one. |

Current runtime dependency flow:

```text
FastMCP tools/resources
  -> Context -> lifespan.Services
  -> SeriesCatalogService -> SeriesRepository -> SQLite series
  -> ObservationService -> ObservationRepository -> SQLite observations
                        \-> BLSClient -> optional live BLS API
  -> SpecificationService -> SpecificationRepository -> SQLite saved_index_specs

Offline CLI: manifest/fetch -> data.ingest.IngestionService
  -> flat_file parser -> SQLite repositories + ingestion_log
  -> data/manifest.json (tracked legacy receipt) -> optional CSV export
```

Proposed independent flow:

```text
archived TSVs / explicitly selected remote TSVs
  -> ingestion discovery/download -> staging + validation
  -> PC and CU adapters + lookup imports -> temporary DuckDB build
  -> sorted observations + series catalog + snapshot metadata
  -> validate/report -> finalize -> publish versioned snapshot
  -> read-only BLSStore Python API (MCP adapter deferred)
```

## 4. Existing interfaces and migration compatibility

`SeriesRepository.get(series_id)` returns `SeriesMetadata | None`;
`search(SeriesSearchRequest)` returns a list of `SeriesMetadata` matched by
title, description, or classification code. `SeriesCatalogService.search`
wraps matches as `SeriesSearchResult`. Request fields are `query`, `programs`,
`active_only`, `limit`; order is by title, without a pagination offset.
Keep existing `describe_series` and `search_series` behavior intact;
program-specific filters, deterministic tie breaks and pagination belong in
the **new** Python query API until MCP integration is reviewed.

`ObservationRepository.get_series_observations` returns `list[Observation]`;
`save_many` upserts SQLite records keyed by `(series_id, period)`.
`ObservationService.fetch_cached` defaults to the latest 24 rows (maximum
100) and allows year bounds; absence means an empty list. `get_series_data`
is a **separate** live API path, requiring a key, limited to 50 series and
20 years, with no caching. Do not reroute either existing tool in this phase.
`SpecificationRepository` stores user escalation specifications in SQLite
and must not be replaced by an analytical snapshot.

Existing `Observation.value` is `Decimal`, JSON-serialized as a **string**;
the SQLite value is exact decimal text. New DuckDB `DOUBLE` output needs
separate typed results and floating-point tolerances. Later MCP integration
must explicitly test and document this serialization change rather than
silently changing the old tool schema.

`EconomicPeriod` serializes monthly (`YYYY-MNN`), quarterly (`YYYY-Qn`),
annual (`YYYY`), and annual-average (`YYYY-M13`) identities. The new schema
stores `year` and the original BLS `period` separately. `M13` is never a
calendar month. Current `EconomicPeriod.sort_key` places M13 before monthly
periods in a year; define and test a deliberate SQL sort order.

`BLSProgram` presently exposes `PPI`, `ECI`, `OEWS`, not CPI; source programs
`pc`, `pd`, `wp` all map to the wider PPI enum. Keep exact source codes in
new catalog data and defer any enum/API alteration to an integration PR.
`create_server()` and `create_lifespan()` own the FastMCP services; tools
access `ctx.lifespan_context["services"]`. SQLite connections are per
operation, and a shared `httpx.AsyncClient` serves live calls. The planned
`bls://snapshot` resource is an **unregistered stub**, not a working API.

## 5. Verified reusable parsing and validation behavior

`src/bls_mcp/data/flat_file.py` plus `test_flat_file.py` are the verified
behavioral baseline. Reuse rules, not Python row-by-row insertion at scale:
the new pipeline should bulk-read into DuckDB staging and validate with SQL.

- **PC:** header-driven `pc.series` has 11 columns, including undocumented
  `footnote_codes`; titles, industry/product/seasonal codes, `YYYYMM`
  `base_date`, and begin/end periods. Padded TSV fields are stripped; data
  rows use `series_id, year, period, value, footnote_codes`. Historical
  values mix one and three decimal places; `P` marks preliminary data.
  `pc.product` joins on the **industry/product pair**.
- **PD (legacy):** discontinued SIC series lack a title, synthesized from
  industry/product lookup data. The 9-field series header describes 10-field
  rows with one blank inserted column; this quirk is explicitly tested.
- **CI (legacy):** a 15-column ECI series file; valid data periods are
  `Q01`-`Q04`. Only `periodicity_code == "I"` represents eligible index
  levels. Other families are skipped with counts, not passed into escalation
  math. Mapping files use the second column for names.
- **WP (legacy):** 11-column series file with undocumented footnote field;
  group/item pairs and ended/inactive series must be retained.
- **Common:** parse `M01`-`M12`, `M13` (annual average), `Q01`-`Q04`;
  preserve footnotes, spaces, and file header formats. Unknown periods are
  warned and counted, but malformed/NaN/infinite values and structural
  drift raise `FlatFileFormatError`. Dash/blank values are recorded as
  missing, never zero. Header-only data partitions are valid. Mapping rows
  tolerate known extra columns.

The new specification adds strict publication gates: classify documented
nonfatal anomalies explicitly; unknown coverage changes, unresolved
conflicting/duplicate keys, missing required inputs and invalid numeric
values must not reach a published snapshot. Never fabricate observations.

## 6. BLS source-file requirements and acquisition policy

Start with `https://download.bls.gov/pub/time.series/pc/` and
`https://download.bls.gov/pub/time.series/cu/`. Bulk data conventionally
include `xx.series`, `xx.data.*`, and program-specific lookup files, with
headers and padded TSV fields. PC/PD/CI/WP are verified from samples;
**CU has no parser, local fixture, or verified header/schema in this repo**.
Before Milestone 4, archive and verify CU series fields, area/item/seasonal
lookups, CPI-U identifiers, period codes, and missing-value rules. Never
assume PC's column layout applies to CU.

Preserve original raw bytes outside Git; log filename, source URL, SHA-256,
size, UTC retrieval time, HTTP validators (if present), and parser/selection
results. Support manifest-driven, fully offline builds without relying on
remote directory listings. Verify existing copies; download into temporary
files, check completion, and use conditional requests when appropriate.
Existing `data/fetch.py` requires an identifying contact User-Agent, sequential
pacing, and stops on HTTP errors (see `docs/bls_etiquette.md`). Resolve the
spec's bounded-transient-retry requirement without bypassing 403/429 access
restrictions. Only fetch explicitly approved BLS paths.

`data/manifest.json` contains **30 legacy file receipts for PC/PD/CI/WP,
none for CU**; it is not a new snapshot registry. `fetch_manifest.py` writes
a separate local receipt under `data/download/`. Keep these existing
provenance and offline fixture flows undisturbed by the DuckDB builder.

Historical PC partitions, `*.data.0.Current`, and potential `AllData`
files may **overlap**. Investigate actual file coverage and record a
per-program file-selection/precedence policy before ingestion. Milestone 3
implements an explicit checksum-pinned PC input manifest, with exclusive
`AllData` selection or historical/current overlap checks. Stage with a
`source_file_id`; count identical duplicates (historical receipt wins) but
block unexplained conflicting keys/values/footnotes. Missing required files also block
publication. Revised preliminary PPI values change only in a newly
validated snapshot, never the currently published one.

## 7. Proposed DuckDB logical schema (design, not DDL migration)

The following is the Milestone 1 design model. Milestone 2 established the
original v1 DuckDB DDL in `src/bls_mcp/storage/schema.py`; Milestone 4 bumps
that DDL to **v2**, adding CU display and periodicity/reference-base columns.
The actual schema is documented in `docs/bls/schema.md`. Real original-byte
CU replay is still required before production promotion. Do not assume PK/FK constraints or indexes are
present just because the logical relationships below are required.

```sql
-- Exactly one row identifies the immutable database itself.
CREATE TABLE snapshot_info (
    snapshot_id VARCHAR NOT NULL,
    schema_version INTEGER NOT NULL,
    built_at TIMESTAMPTZ NOT NULL,
    build_commit VARCHAR,
    programs VARCHAR NOT NULL,
    validation_status VARCHAR NOT NULL
);

-- Each selected raw file has a durable, independently verifiable receipt.
CREATE TABLE source_files (
    source_file_id BIGINT NOT NULL,
    program_code VARCHAR NOT NULL,
    filename VARCHAR NOT NULL,
    source_url VARCHAR,
    sha256 VARCHAR NOT NULL,
    size_bytes BIGINT NOT NULL,
    retrieved_at TIMESTAMPTZ,
    etag VARCHAR,
    last_modified VARCHAR,
    selection_role VARCHAR NOT NULL
);

CREATE TABLE series_catalog (
    series_id VARCHAR NOT NULL,
    program_code VARCHAR NOT NULL, -- source survey: pc or cu; not enum PPI
    title VARCHAR NOT NULL,
    description VARCHAR,
    seasonal_adjustment BOOLEAN,
    first_year SMALLINT,
    first_period VARCHAR,
    last_year SMALLINT,
    last_period VARCHAR,
    units VARCHAR,
    original_reference_base VARCHAR,
    active BOOLEAN
);

CREATE TABLE observations (
    series_id VARCHAR NOT NULL,
    year SMALLINT NOT NULL,
    period VARCHAR NOT NULL,
    value DOUBLE NOT NULL,
    footnote_codes VARCHAR,
    source_file_id BIGINT NOT NULL
);
```

Build the canonical `observations` table in the specified physical sort order.
Each `(series_id, year, period)` must occur once; each `series_id` must be in
`series_catalog`, and each `source_file_id` must resolve to `source_files`.
`year` should be verified to fit `SMALLINT`. `value` must be finite; distinguish
missing source observations from actual zero and enforce positive/recognized
source period codes, including program-specific allowances. `M13` is an
annual-average code, not a month. An explicit `source_file_id` supports
observation-level lineage without conflating ingestion vintage with the
snapshot ID; measure its storage cost before optimizing it away.

Add source-program structures, not a generic plugin metadata blob:

| Relations | Key and relationship |
| --- | --- |
| `pc_series` | `series_id` -> catalog; `industry_code`, `product_code`, `seasonal_code`, `base_date` as **source strings**. |
| `pc_industry` | `industry_code` -> BLS industry description. |
| `pc_product` | `(industry_code, product_code)` -> BLS product description; never join on product alone. |
| `cu_series` | `series_id` -> catalog; area/item/seasonal and other verified CU source fields (exact list pending samples). |
| `cu_area`, `cu_item`, CU lookups | Preserve documented classification codes, descriptions, and relevant joins after verifying actual CU files. |
| Validation report | Human and JSON reports beside the snapshot, with counts, anomalies and selection policy; embed a concise status/summary in snapshot metadata. |

One series may carry original BLS reference base information, but query-time
normalization must use the *requested* observed base value, never infer an
implicit common base from that label. Preserve source metadata sufficient to
reconstruct search results (title, classifications, area, seasonal adjustment,
first/last periods and coverage) and compare snapshot vintages.

## 8. Package boundaries and read-only query contract

Recommended code boundaries for subsequent PRs:

- `src/bls_mcp/storage/`: DuckDB `schema.py`, `connection.py`,
  `snapshots.py`; later `observations.py`, `catalog.py`, `normalization.py`.
  All public reads must use read-only connections; readers never open a build
  database. Connection scopes must be safe across threads and processes,
  expose thread/memory settings, and close deterministically. No SQL from
  arbitrary MCP clients.
- `src/bls_mcp/ingestion/`: `discovery`, `download`, `staging`, `validation`,
  `manifest`, `pipeline`, `publish`, and simple `programs/pc.py` and `cu.py`.
  Builders are offline, single-writer processes. Source adapters only define
  program schemas/rules. Staging keeps origin of every row; bulk SQL creates
  the sorted, validated final data. Publish only READY databases.
- `src/bls_mcp/models/`: new query request/result and per-series status
  models. Keep existing `Observation` and `SeriesMetadata` public contracts
  untouched until an explicit MCP migration PR.
- `src/bls_mcp/data/`, `db/`, `repositories/`, `services/`, `mcp/`:
  legacy functionality remains available throughout development; build no
  circular dependency from the independent storage package back into MCP.
- A later `bls-data` administrative CLI will separate download, offline build,
  validate, publish, list, and benchmark, with nonzero failure exit codes.

Plan a `BLSStore(snapshot_path=...)` Python facade exposing `search_series`,
`get_observations`, and `normalize_series` with typed filters/results and the
immutable `snapshot_id`. Accept 1, 10, 100, 500, and 1,000 series IDs with
bounded inputs/rows, parameterized SQL or safely bound relations, stable order,
and optional Arrow/DataFrame export. Report **unknown series**, **missing base
period**, **zero base denominator**, **no rows in selected output window** and
**success** per requested series. Base values must be read even when outside
the output range. Compare a window-function approach with a separate base
lookup/join and publish benchmark evidence before choosing a default.

Milestone 6 implements `BUILDING -> VALIDATING -> READY -> PUBLISHED` using
`ingestion/{lifecycle,publish,cli}.py`; failures record VALIDATING/FAILED.
Validation rechecks input hashes and foreign-key-style joins, globally sorts
observations and rebuilds ART, checkpoints, then reopens read-only. Publication
copies the closed candidate, checkpoints a PUBLISHED copy and registers its
immutable version. Activation/rollback atomically change only the registry. A
graceful server restart selects the newly active path. See
`docs/bls/snapshot-lifecycle.md` for operational caveats. The registry is *not* the SQLite application-state DB.

## 9. Testing, verification, and benchmark requirements

Existing behavioral baselines are `src/bls_mcp/tests/test_flat_file.py`
(headers, padding, numeric/missing/period handling, M13, CI eligibility and
mappings), `test_fetch.py`, `test_fetch_manifest.py`, `test_manifest.py`,
`test_ingest_cli.py`, `test_cached_observations.py`, `test_review_regressions.py`,
and `tests/integration/test_flatfile_ingest.py` (replay of checked-in source
files and manifest receipts). `tests/integration/test_mcp_server.py` and
`test_server.py` protect MCP schemas/registration. Existing tests establish
legacy compatibility, **not** correctness of an unbuilt DuckDB pipeline.

Add offline `tests/bls/{unit,integration,concurrency,performance}/` coverage:
verified PC/CU parsing, mapping joins, missing/invalid data, M13, duplicates
(identical vs conflicting), overlapping files, bad hashes, incomplete inputs,
source/provenance counts, unknown series, missing/zero normalization bases,
base outside output window, deterministic results, 1,000-series retrieval,
SQL injection resistance, read-only access from threads/processes, and
publication failure/rollback. Include small synthetic failure fixtures and
replay of verified real samples. Live downloads remain optional. Assert
fixture expectations and manifest reconciliation rather than hard-coded
whole-population totals.

Benchmark 1/10/100/500/1,000 series across full-history/five-year reads,
normalization and catalog search. Compare sorted DuckDB, sorted DuckDB + ART,
Parquet via DuckDB, and indexed SQLite where practical; also compare window
vs base-join normalization. Record median/p95 latency, throughput, file size,
peak memory if measurable, build time, dataset/hardware/DuckDB version, and
repeat methodology. Do not claim performance gains without measurements.

On 2026-11-05, the offline subset `pytest -q
src/bls_mcp/tests/test_flat_file.py
src/bls_mcp/tests/test_cached_observations.py
src/bls_mcp/tests/test_periods.py tests/integration/test_flatfile_ingest.py`
passed (**54 tests**). An expanded run including `test_manifest.py` failed
at collection because `fastmcp` was not installed here. No full-suite,
DuckDB, or MCP integration pass is claimed by this documentation-only patch.

## 10. Milestones, PR sequence, and acceptance gates

1. **Assessment (this PR):** Repository map, design/risks, and both
   `docs/bls/implementation-*.md` files. Documentation-only, no runtime edits.
2. **Storage foundation:** Lock DuckDB dependency; schema, read-only/builder
   connections, snapshot metadata, typed models, and offline storage tests.
3. **PC ingestion:** Explicit checksum-pinned file selection, PC
   classification import, native DuckDB bulk staging, strict validation,
   identical-duplicate reconciliation, typed report, and an ART index built
   after loading. See `docs/bls/pc-ingestion.md`.
4. **CU ingestion:** Add pinned CU source selection and classification
   imports, bulk monthly/semiannual ingestion, shared ART maintenance, and
   cross-program tests. See `docs/bls/cu-ingestion.md`. An original-byte BLS
   file replay remains a prepublication gate.
5. **Query services:** Filtered search/pagination, deterministic multi-series
   reads, SQL normalization, per-series statuses and snapshot provenance.
   Implemented in `storage/{query_models,store}.py` with the test and usage
   contract in `docs/bls/query-services.md`; native DuckDB verification
   remains a local pre-merge gate.
6. **Snapshot lifecycle:** Independent offline build, source/data validation,
   global sort and ART, READY finalization, immutable publish, atomic registry
   activation/rollback, failure reports and `bls-data` CLI. Added in this patch;
   native verification pending. See `docs/bls/snapshot-lifecycle.md`.
7. **Benchmarks:** Compare prescribed storage/normalization strategies,
   document reproducible results and choose measured defaults.
8. **Final review:** Unit/integration/concurrency tests, lint/format/mypy,
   safe SQL/resource review, migration documentation and MCP handoff.

Keep each PR single-subject, working against the preceding milestone. The
storage builder must be independently usable before any MCP wiring. Append
files, test commands/results, remaining issues, and next actions to
`implementation-progress.md` after each milestone. Native context compaction
was unavailable in this environment; this document is the durable substitute,
not a claim that compaction ran.

## 11. Open questions and technical risks

- **PC source selection:** Actual `0.Current`, historical partitions, and
  `AllData` overlap/precedence are unverified. Inspect coverage before
  deciding which files enter the canonical table; conflicts block publishing.
- **CU formats:** No CU samples or parser exist here. Verify CPI-U IDs,
  `.series` fields, area/item classifications, source periods and missing
  sentinels before writing transformations.
- **Compatibility:** `BLSProgram` lacks CPI; PPI encompasses PC/PD/WP; exact
  `Decimal` JSON differs from DuckDB `DOUBLE`. Add adapters only through a
  separately tested migration, preserving saved specifications and legacy
  PC/PD/CI/WP parsing.
- **Periods:** `EconomicPeriod.sort_key` does not order `M13` after the
  monthly periods; define explicit SQL ordering and test all period kinds.
- **Downloader:** Bounded transient retry requirements must honor the
  existing BLS 403/rate-limit etiquette, not evade access restrictions.
- **Safe publication:** Validate completed/closed DuckDB files, atomic
  registry writes, Windows file locks, concurrent readers and rollback.
- **Integrity and speed:** Reconcile counts/checksums/provenance, reject
  non-finite and conflicting values, and benchmark the requested Milestone 3
  ART index against a sorted-only baseline and Parquet before asserting a
  speed benefit. Legacy per-file ingestion is not atomic.
