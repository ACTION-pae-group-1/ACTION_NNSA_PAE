# BLS storage/ingestion rebuild: implementation progress

> **Historical record.** This document was written while the DuckDB store was
> being built alongside the original SQLite catalog. That migration is
> complete: the SQLite catalog, its ingestion pipeline and the `bls_mcp.db`
> package have been removed, and the MCP server reads only the published
> DuckDB snapshot. Mentions of SQLite below describe the state at the time of
> writing, not the current code. See `src/bls_mcp/docs/DECISIONS.md`
> (2026-11-13) and [OPERATIONS.md](OPERATIONS.md) for the current design.

Specification: "BLS_MCP: Storage and Ingestion System Rebuild", v1.0.
Started: 2026-11-05. This is a milestone log, not a deployment status page.
Update after each milestone; do not mark work complete without evidence.

## Current status

- **Milestone 1: complete for the provided 2026-11-04 repository archive.**
  Assessment and durable documents are prepared in this patch. No runtime
  storage migration has started.
- **Milestone 2: included in the uploaded 2026-11-05 merged `main` ZIP.**
  The native storage foundations are present. The original Milestone 2
  verification caveats remain recorded below; they are not repeated as
  assertions about the user's development machine.
- **Milestone 3: merged into uploaded `main` (2026-11-05).**
  PC source verification, bulk load, ART creation and offline tests are in
  the source baseline. Prior native verification notes are historical.
- **Milestone 4: included in the uploaded feature-branch baseline.**
  CU source selection and integrity, CPI-U metadata/catalog ingestion,
  monthly/semiannual observation import, shared ART indexing, transactions
  and cross-program tests are present. Schema v2 is historical; the subsequent
  real-file CU area-header correction advances the storage schema to v3.
  Local/native validation of this uploaded branch was not independently
  reproduced here.
- **Milestone 5: implemented in this patch; native DuckDB verification pending.**
  Read-only catalog search, multi-series retrieval, SQL normalization,
  deterministic pagination, typed per-series statuses and provenance; no
  schema, ART index, SQLite, or MCP changes.
- **Milestone 6: implemented in this patch; native verification pending.**
  Offline candidate build, validation/final sort, READY/PUBLISHED transition,
  checksum-gated immutable copies, atomic registry activation/rollback, CLI and
  failure reports. No MCP or legacy SQLite changes.
- **Milestones 7-8: not started.**
- No native context-compaction facility was available in this execution
  environment. `implementation-context.md` is the durable navigation record;
  no claim of successful compaction is made.

## Milestone log

| Milestone | Status | Evidence / next action |
| --- | --- | --- |
| 1. Repository assessment | Complete | Read spec and relevant BLS source/tests/docs; mapped SQLite, parsing, MCP and provenance dependencies; authored both documents under `docs/bls/`. |
| 2. Storage foundation | Merged into uploaded `main` | v1 DDL, connections, typed models and snapshot metadata; original native-verification caveat below. |
| 3. PC ingestion | Merged into uploaded `main` | PC manifest, classification and observation import, conflict rejection, ART index, tests. |
| 4. CU ingestion | Present in uploaded feature branch | CU manifest, area/item/series metadata, current/historical observation import, S-period support, reconciliation, PC/CU coexistence, ART tests; original BLS CU bytes not retrieved here. |
| 5. Query services | Implemented; native verification pending | `BLSStore` facade, bounded parameterized read-only queries, PC/CU classification filters, per-series status models and offline tests. |
| 6. Snapshot lifecycle | Implemented; native verification pending | `lifecycle.py`, `publish.py`, `cli.py`, Windows-friendly immutable versioned files, report SHA-256, registry lock/atomic pointer, rollback tests. |
| 7. Benchmarks | Not started | Compare sorted DuckDB, ART, Parquet, SQLite and normalization strategies. |
| 8. Final review | Not started | Full quality/test checks, migration documentation and MCP integration handoff. |

## Files added in Milestone 1

- `docs/bls/implementation-context.md`: scope, settled architecture, source
  inventory, contracts, verified parser behavior, proposed schema, package
  boundaries, test/benchmark plan, milestone gates, and risks.
- `docs/bls/implementation-progress.md`: this auditable milestone record.

Milestone 1 modified no existing source files, dependencies, MCP endpoints,
or schemas. Milestone 2 changes are recorded below.

## Verification record

- Examined `src/bls_mcp/data/`, `db/`, `repositories/`, `models/`,
  `services/`, `mcp/`, `lifespan.py`, `server.py`, `config.py`, existing BLS
  tests and fixtures, `tests/integration/test_flatfile_ingest.py`,
  `pyproject.toml`, `uv.lock`, and relevant documentation.
- Existing behavior baseline (offline subset, 2026-11-05): **54 passed** with
  `pytest -q src/bls_mcp/tests/test_flat_file.py
  src/bls_mcp/tests/test_cached_observations.py
  src/bls_mcp/tests/test_periods.py tests/integration/test_flatfile_ingest.py`.
- A wider selection including `src/bls_mcp/tests/test_manifest.py` could
  not collect because `fastmcp` was not installed here
  (`ModuleNotFoundError: No module named 'fastmcp'`). The full suite and MCP
  integration tests have **not** passed in this environment.
- Documentation-only change: no production behavior, live HTTP or DuckDB
  benchmark result is claimed. See the PR for patch application check.

## Milestone 2 implementation record (2026-11-05)

Changed: `.gitignore`, `pyproject.toml`, `requirements.txt`, `uv.lock`, and
`docs/bls/implementation-{context,progress}.md`. Added:
`docs/bls/schema.md`, `src/bls_mcp/storage/{__init__,connection,models,schema,snapshots}.py`,
and four offline test modules in `tests/bls/unit/`.

- DuckDB dependency range is `>=1.4,<2`, with 1.5.6 recorded in `uv.lock`.
  External dependency resolution was inaccessible from this container
  (DNS failure fetching PyPI). The lock entry was reconstructed from
  published PyPI SHA-256/BLAKE2b digests for the sdist and a subset of 3.11
  platform wheels. **It was not generated with online `uv lock`.** Before
  merging, run `uv lock` on a networked machine to regenerate complete
  platform wheel metadata, then `uv sync --locked --group dev`.
- Unignored the tracked `src/bls_mcp/storage/` source package while
  ignoring generated `.duckdb`/`.duckdb.wal` files.
- Added single-version v1 DDL, including canonical `DOUBLE` observations,
  lineage receipts, common metadata, PC classifications with composite
  product keys, and provisional CU classifications. No observations ART
  index, no arbitrary SQL API, and no migration of SQLite user state.
- Added separate new-file-only builder and read-only reader context managers;
  production readers require a matching schema version and PUBLISHED status.
  A separate explicit validation-mode option supports unpublished candidates.
- Added typed snapshot, source-receipt, series, observation and query-response
  records. Quarter codes such as `Q01` and annual averages `M13` remain intact.
  Dedicated ECI `ci_series` metadata is deferred; the canonical table already
  supports quarterly ECI readings.
- Physical observation sort, logical uniqueness, referential checks, full
  source verification, complete CU metadata and lifecycle transitions are
  intentionally deferred to ingestion/validation/publication milestones.

**Verification in this environment:**

- `python -m compileall -q src/bls_mcp/storage tests/bls/unit`: success.
- `uv lock --check --offline --python /usr/bin/python3.13 --no-progress`:
  success (116 packages resolved from the existing lock, including DuckDB).
- `uv export --locked --offline --python /usr/bin/python3.13 --no-dev
  --no-emit-project --no-hashes`: success; lists `duckdb==1.5.6`.
- `pytest -q tests/bls/unit src/bls_mcp/tests/test_flat_file.py
  src/bls_mcp/tests/test_cached_observations.py src/bls_mcp/tests/test_periods.py
  tests/integration/test_flatfile_ingest.py`: **59 passed, 3 skipped**.
  All three skipped modules are DuckDB integration tests; none have been
  exercised with a real DuckDB engine in this environment.
- Full suite, FastMCP integration tests, `ruff`, `mypy`, and real DuckDB
  persistence/constraint tests remain **unverified** here.

**Historical Milestone 2 gate:** regenerate the lock online and run native
DuckDB and full quality checks on the development machine. The uploaded
Milestone 3 baseline already contains the merged Milestone 2 files. The
current environment cannot independently reproduce native DuckDB results.

## Known gaps and decisions to resolve before later milestones

1. Need verified PC historical/current partition selection and overlap policy;
   do not concatenate everything or arbitrarily pick conflicting values.
2. CU header and identifier conventions were checked against published BLS
   documentation and external examples. Direct CU source retrieval remains
   blocked in this environment; verify a local original-byte replay before
   promoting a production snapshot.
3. Need new snapshot provenance separate from legacy `data/manifest.json` and
   its SQLite ingestion-log receipt, plus a clearly defined registry format.
4. Need an explicit `DOUBLE` versus legacy `Decimal` API compatibility plan.
5. Need review of BLS HTTP etiquette versus bounded transient retry policy.
6. Need read-only connection and publication tests across processes/OSes.
7. Need a deterministic SQL sort/filter policy for annual-average `M13`.
8. Milestone 3 now intentionally adds an ART index after PC bulk loading;
   benchmark its memory and lookup tradeoff versus sorted-only and Parquet in
   Milestone 7, without an unmeasured performance claim.

## Milestone 3 implementation record (2026-11-05)

Added `src/bls_mcp/ingestion/{__init__,manifest,pc}.py`,
`tests/bls/unit/{test_pc_manifest,test_pc_ingestion}.py` and
`docs/bls/pc-ingestion.md`. Updated schema/context/progress documentation.
No changes to SQL schema version, dependencies, existing SQLite pipelines,
MCP registrations, or FastMCP code.

- A pinned PC manifest explicitly chooses industry/product/series metadata
  and historical/current **or exclusive AllData** partitions; it verifies
  raw headers, bytes, size and SHA-256 with no network traffic. Deterministic
  `source_files` receipts document all inputs.
- PC metadata validates industry/product references and preserves the
  `(industry_code, product_code)` product key. The canonical shared catalog
  stores original series base and active interval metadata.
- DuckDB bulk-stages observation rows using fixed-schema tab-separated
  `read_csv`. Invalid years/periods, nonfinite numbers, unknown series and
  conflicting current/history index levels or footnotes block ingestion.
  Missing values are counted and omitted, identical duplicates collapse with
  deterministic historical provenance. Insert order is series/year/period.
- Requested ART index `observations_series_id_art` on `series_id` is created
  **after** bulk loading. An ingestion report reconciles raw, missing,
  duplicate and inserted counts. This is a candidate build, not publication.

**Verification in this container:** `pytest -q tests/bls/unit/test_pc_manifest.py
 tests/bls/unit/test_pc_ingestion.py` passed **11 tests, 1 module skipped**;
 the skipped module requires native DuckDB. `python -m compileall` passed for
 new modules. Full native DuckDB tests, Ruff and mypy remain to be run on the
 developer workstation. No ART speedup or published-snapshot claims are made.

## Milestone 4 implementation record (2026-11-05)

Added `src/bls_mcp/ingestion/{cu_manifest,cu}.py`,
`tests/bls/unit/{test_cu_manifest,test_cu_ingestion}.py` and
`docs/bls/cu-ingestion.md`. Updated the CU classification tables in the
DuckDB schema and advanced the schema version to **2** (including the
`SnapshotInfo` model default and schema-version test); the shared PC and
observation tables are unchanged. No new dependencies, HTTP access, SQLite
writes or MCP registrations.

- CU manifests pin `cu.area`, `cu.item`, `cu.series`, and at least one
  explicit `cu.data.*` partition. BLS filenames, source headers, optional
  size and exact SHA-256 are checked before writes and again before commit.
- CU metadata preserves area/item display order and selectability, and series
  area/item codes, seasonal adjustment, periodicity and reference bases.
  Semantic checks also decode the CU series identifier.
- DuckDB stages large observation files in bulk, allows `M01`-`M13` for
  regular series and `S01`-`S03` for semiannual series, counts missing rows,
  rejects malformed/nonfinite/unknown observations, deduplicates identical
  overlaps and rejects conflicting values/footnotes atomically.
- CU-only loads build the requested `observations_series_id_art` after bulk
  insertion; mixed PC/CU builds retain the same index and use distinct
  `source_file_id` ranges. Candidate snapshots remain BUILDING.
- No native DuckDB engine or genuine CU source bytes are available here;
  **real CU ingestion and schema/index persistence must be tested locally**.
  The manifest tests and existing offline subset can run without DuckDB.

## Real-file CU header and offline audit correction (2026-11-10)

The BLS-published `cu.area` layout contains five fields, including
`selectable`; the original CU parser incorrectly expected four. Updated the
checksum-pinned header validator and loader to validate and retain the flag,
advanced the DuckDB snapshot schema to v3, and expanded offline tests for
published headers, saved selectability, and audit error diagnostics.

The monthly overlap audit now writes `FAIL_AUDIT_ERROR` reports for source
verification or scan errors instead of failing without a report. No source
files, checksums, or source-manifest format were changed. Existing DuckDB v2
candidates and published snapshots require rebuilding or explicit versioned
reader compatibility before this v3 code can read them. Run the full native
DuckDB and real-file CU checks on the developer workstation.

## Historical next action (Milestone 5, after M4 review)

Run all native DuckDB unit tests with **no skipped modules** on the developer
workstation, the repository-wide quality checks, and a replay of archived BLS
CU files with pinned original hashes. Review the schema-version bump and
build fresh v2 candidate files. Once M4 is merged, proceed to the query
services milestone (catalog search, multi-series retrieval, SQL
normalization and per-series statuses). Snapshot publication remains M6.

## Milestone 5 implementation record (2026-11-05)

Added `src/bls_mcp/storage/{query_models,store}.py`,
`tests/bls/unit/{test_query_models,test_store_queries}.py`, and
`docs/bls/query-services.md`. Existing `series_catalog`, `observations`,
`pc_*`, `cu_*` and ART-index definitions are unchanged; schema version remains
**2**. There are no dependency, SQLite, MCP registration, or FastMCP changes.

- `BLSStore(snapshot_path=...)` opens an independent, scoped read-only DuckDB
  connection for each operation, requires v2 schema, `PUBLISHED` lifecycle
  and `PASSED` validation, and returns its fixed `snapshot_id` with results.
- `search_series()` provides literal case-insensitive text search, PC and CU
  classification filters, stable title/series pagination and total counts.
  `get_observations()` retrieves original DOUBLE readings, periods, source IDs
  and footnotes with a strict 1,000-series/row-budget contract.
- `normalize_series()` uses a SQL base join. Exact base values are fetched
  independently of the output window; no missing/zero-base fallback is made.
  Unknown series, missing bases, zero bases, empty windows and success are
  distinguished for each input series in its requested order.
- Python unit tests cover request validation. Native tests exercise 1,000 IDs,
  mixed PC/CU lookup, M13 and semiannual ordering, all normalization statuses,
  SQL injection resistance, ART persistence, and concurrent independent reads.

**Verification here:** Pure-Python query-model and existing PC/CU manifest
checks passed (29 tests). The environment has no DuckDB wheel and cannot
resolve PyPI DNS, so **native SQL queries, Ruff, and mypy are not verified**.
Run the prescribed local tests before merging. Milestone 6 will establish the
actual validation, checkpoint, publication and activation workflow.

## Milestone 6 implementation record (2026-11-05)

Added `src/bls_mcp/ingestion/{lifecycle,publish,cli,__main__}.py`,
`tests/bls/unit/test_snapshot_lifecycle.py` and
`docs/bls/snapshot-lifecycle.md`. Added the `bls-data` console entry in
`pyproject.toml` (no new dependencies or DuckDB schema migration). Updated
implementation context and progress. The uploaded Milestone 5 feature-branch
ZIP is the patch baseline; use a merged `main` containing Milestone 5.

- Offline build consumes explicit checksum-pinned PC/CU manifests into a fresh
  candidate file. Validation independently hashes original source bytes,
  reconciles receipts, catalog/classification relationships, canonical keys,
  nonfinite/period checks and the required ART index. It globally sorts PC/CU
  rows, recreates the ART, and preserves the canonical finite-value constraint.
- Valid candidates transition BUILDING -> VALIDATING -> READY/PASSED, are
  checkpointed, closed and verified through a read-only reopen. Failed
  validation records VALIDATING/FAILED and a durable JSON failure report.
- Publication verifies the READY report and closed file SHA, copies onto the
  destination filesystem, updates only the copy to PUBLISHED, checkpoints,
  reopens read-only, then renames it to a unique immutable version. A versioned
  report and digest are registered separately from activation.
- A cross-process exclusive lock serializes administration. Atomic registry
  replacement changes the active pointer; activation/rollback verify version
  checksums and preserve earlier files and already-open readers. A restart is
  sufficient to select the new active snapshot; MCP wiring is still deferred.
- Real DuckDB execution, Windows file-lock behavior, full Ruff/mypy suite and
  production-sized PC/CU replay remain local gates. No runtime benchmark or
  successful native DB test is claimed in this environment.

**Next:** After native Milestone 6 checks pass and the PR is merged, run
Milestone 7 performance comparisons (sorted DuckDB with/without ART, Parquet,
SQLite and normalization strategies).
