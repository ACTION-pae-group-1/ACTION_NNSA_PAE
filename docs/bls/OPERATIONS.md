# BLS DuckDB operations: from downloaded files to an active snapshot

**Audience:** a human operator running a deliberate, local PC/CU refresh. This is
not an automated job or an MCP tool.
All examples below use **PowerShell from the repository root**. The repository's
[QUICKSTART](../../QUICKSTART.md) covers the CMD-based MCP setup and a small
sample snapshot; these commands are for full, offline DuckDB snapshots.

**Start here for an end-to-end rebuild.** More detailed references:

- [Monthly acquisition README](../../data/manual_monthly/README.md): actual BLS
  directory discovery, conservative serial downloads, cache reuse, manifests,
  and offline overlap audits. These scripts must be installed/merged first.
- [Snapshot lifecycle](snapshot-lifecycle.md): candidate validation,
  publication, activation and rollback guarantees.
- [Query services](query-services.md): `BLSStore` search, retrieval and
  normalization contracts.
- [PC](pc-ingestion.md) and [CU](cu-ingestion.md) ingestion specifications.

## 0. Identify the files you already have

Keep source files, manifests and published snapshots separate:

| Location | Contents | Policy |
| --- | --- | --- |
| `data/local/bls/YYYY-MM/pc/` | PC discovery, raw partitions, receipts, `pc-input*.json`, audit reports | Keep together for reproducible rebuilds. |
| `data/local/bls/YYYY-MM/cu/` | CU equivalents | Keep together for reproducible rebuilds. |
| `data/local/snapshots/` | Published `bls-*.duckdb`, validation reports and `active-snapshot.json` registry | **Do not delete** without a separate retention/migration plan. |
| `data/local/build-*.duckdb` and `data/local/*-smoke.duckdb` | Unpublished candidates / older smoke tests | Review individually after successful publication. |
| `data/local/pc/`, `data/local/cu/` | Earlier manually copied *sample* source sets, if present | Optional to archive after checking for dependent candidates. |
| `data/local/bls_specs.duckdb` (or `BLS_SPECS_DB_PATH`) | Saved index specifications | **Keep**; this is user state, not rebuildable from BLS files. |

`data/local/` is Git-ignored. Do not commit source archives, `.env`, DuckDB
files, validation reports, or the active-snapshot registry. **Manifest paths are
relative to the directory containing that manifest**, so moving raw files or a
manifest on its own breaks later audit/validation. Take a backup before cleaning.

## 1. Prerequisites and source acquisition (manual, at most monthly)

After checking out the ingestion/lifecycle code and the manual acquisition
scripts, synchronize dependencies once:

```powershell
uv sync --locked --group dev
```

Set `BLS_USER_AGENT` to an identifying contact value in the Git-ignored root
`.env`. Tell `uv` to load it when making BLS network requests. Check presence
without displaying your email:

```powershell
uv run --locked --env-file .env python -c "import os; print(bool(os.getenv('BLS_USER_AGENT')))"
$month = (Get-Date).ToUniversalTime().ToString('yyyy-MM')
```

If you **already downloaded** both programs this month, skip straight to
section 2. Otherwise run discovery **once per program per UTC calendar month**:

```powershell
uv run --locked --env-file .env python data/manual_monthly/manual_bls_monthly.py `
  --month $month discover --program pc
uv run --locked --env-file .env python data/manual_monthly/manual_bls_monthly.py `
  --month $month discover --program cu
```

Preview, then explicitly acquire historical partitions. Both programs use
sequential requests and conservative randomized pauses; the monthly lock
prevents simultaneous acquisition jobs. The plan makes no network requests:

```powershell
uv run --locked --env-file .env python data/manual_monthly/manual_bls_monthly.py `
  --month $month plan --program pc --selection historical --all-historical
uv run --locked --env-file .env python data/manual_monthly/manual_bls_monthly.py `
  --month $month plan --program cu --selection historical --all-historical

uv run --locked --env-file .env python data/manual_monthly/manual_bls_monthly.py `
  --month $month download --program pc --selection historical --all-historical `
  --min-delay 60 --max-delay 120
uv run --locked --env-file .env python data/manual_monthly/manual_bls_monthly.py `
  --month $month download --program cu --selection historical --all-historical `
  --min-delay 60 --max-delay 120
```

Review the discovered partitions and `plan` output before requesting *all*
history. Reusing cached files does not redownload them. You may opt to select
`current` or `both` instead, but mixing current and historical partitions can
introduce overlapping or revised values. Do not assume those will reconcile.
If BLS returns 403/429, stop and review the saved request log and access pause
marker. Do not disable TLS validation or work around BLS access restrictions.

## 2. Choose the exact pinned manifests

The downloader prints each manifest's actual path. A second selection can
create `pc-input-<id>.json` or `cu-input-<id>.json` **without replacing** an
earlier `*-input.json`. Use the paths for the intended historical selection,
not simply the first matching filename:

```powershell
Get-ChildItem "data/local/bls/$month/pc" -Filter 'pc-input*.json'
Get-ChildItem "data/local/bls/$month/cu" -Filter 'cu-input*.json'

# Replace these two values with the actual paths printed by your downloader.
$pcManifest = "data/local/bls/$month/pc/pc-input.json"
$cuManifest = "data/local/bls/$month/cu/cu-input.json"

(Get-Content $pcManifest -Raw | ConvertFrom-Json).files |
  Group-Object role | Select-Object Name, Count
(Get-Content $cuManifest -Raw | ConvertFrom-Json).files |
  Group-Object role | Select-Object Name, Count
```

Each manifest needs the three program-specific metadata files plus at least
one data partition. For a historical-only PC selection, expect one each of
`industry_mapping`, `product_mapping`, and `series_metadata`, plus one or more
`historical` files. For CU, expect `area_mapping`, `item_mapping`,
`series_metadata`, and `historical` files. The inventory proves what was
selected; it does **not** by itself prove the data are complete or consistent.

## 3. Audit each program for overlapping observations

Use the same manifests for the audit and the later DuckDB build:

```powershell
uv run --locked python data/manual_monthly/manual_bls_monthly.py `
  audit --manifest $pcManifest
if ($LASTEXITCODE -ne 0) { throw 'PC overlap audit failed; review the report.' }

uv run --locked python data/manual_monthly/manual_bls_monthly.py `
  audit --manifest $cuManifest
if ($LASTEXITCODE -ne 0) { throw 'CU overlap audit failed; review the report.' }
```

The audit is **offline** and uses temporary disk space to sort large archives.
It writes a JSON report under the corresponding program's `reports/` directory:

| Result | Decision |
| --- | --- |
| `PASS_NO_OVERLAP` | Proceed. |
| `PASS_IDENTICAL_OVERLAP` | Proceed; repeated values/footnotes are identical and can be deduplicated by ingestion. |
| `FAIL_CONFLICTS` | **Stop.** Review conflicting series, years, periods and source partitions. |
| `FAIL_AUDIT_ERROR` | **Stop.** Check the report's `phase` and `error` for bad headers, hashes, or scan/storage failures. |

A failed audit exits nonzero. It **does not** modify source files. Review the
report and revise the explicit selection if appropriate (for example, an
`--exclude-partition` with `--all-historical`), then re-run the audit with the
**new** manifest. Excluding a file also excludes its non-overlapping history,
so document the coverage trade-off; do not silently drop conflicting data.
The DuckDB loaders independently recheck integrity and may reject other errors.

## 4. Build a new DuckDB candidate

Use a **unique filename and snapshot ID** for each attempt. The builder
intentionally refuses to overwrite an existing database. Build and validate
are separate operations. Keep the original source manifests and raw files
available through validation:

```powershell
$runId = Get-Date -Format 'yyyyMMdd_HHmmss'
$snapshotId = "bls_$runId"
$candidate = "data/local/build-$runId.duckdb"
$registry = 'data/local/snapshots'

uv run --locked bls-data build `
  --candidate $candidate `
  --snapshot-id $snapshotId `
  --pc-manifest $pcManifest `
  --cu-manifest $cuManifest
if ($LASTEXITCODE -ne 0) { throw 'Build failed; inspect the output and use a new candidate path.' }
```

This builds the shared PC/CU catalog and observations, checks source bytes,
reconciles identical duplicates, rejects conflicts, and constructs the
`observations_series_id_art` index. Building does **not** make the snapshot
ready for production queries or change the currently active snapshot. A real
historical archive may require significant time, free disk space and memory.

For a PC-only or CU-only trial, omit the other program's manifest option from
**both** build and validate. Avoid accidentally reusing a candidate's existing
filename after an error: the builder will not overwrite it.

**Employment Cost Index (ECI).** Add `--ci-manifest <path>` to **both** the
build and validate commands to include current-dollar ECI index series in the
same snapshot. The monthly downloader in section 1 does not fetch `ci` files;
a pinned manifest for the ECI files checked into the repository is at
`src/bls_mcp/docs/sample_data/ci-sample-input.json`. See
[ci-ingestion.md](ci-ingestion.md) for the manifest roles and what is loaded.

## 5. Validate the closed candidate before publication

```powershell
uv run --locked bls-data validate `
  --candidate $candidate `
  --pc-manifest $pcManifest `
  --cu-manifest $cuManifest
if ($LASTEXITCODE -ne 0) { throw 'Validation failed; do not publish this candidate.' }

$report = Get-Content "${candidate}.validation.json" -Raw | ConvertFrom-Json
if (-not $report.passed) { throw 'Validation report did not pass.' }
$report | Select-Object snapshot_id, passed, schema_version, counts, issues
```

Validation rechecks manifests/receipts, observation uniqueness, classifications,
index presence, and global ordering. On success the candidate becomes
`READY/PASSED` with a validation report and file checksum. On failure it
becomes nonpublishable; inspect the report and rebuild under a **new** name.
Do not edit a READY database or its report after validation.

## 6. Publish, inspect, activate

```powershell
uv run --locked bls-data publish `
  --candidate $candidate `
  --registry-dir $registry
if ($LASTEXITCODE -ne 0) { throw 'Publication failed; active snapshot is unchanged.' }

uv run --locked bls-data list --registry-dir $registry
uv run --locked bls-data activate `
  --registry-dir $registry `
  --snapshot-id $snapshotId
if ($LASTEXITCODE -ne 0) { throw 'Activation failed.' }
uv run --locked bls-data current --registry-dir $registry
```

Publication creates an immutable versioned copy and registry entry; it does
**not** activate the new snapshot automatically. Activation changes the active
registry pointer. Earlier published versions are retained. If a newer version
later turns out to be unsuitable, run `uv run --locked bls-data rollback
--registry-dir $registry` to select the previous active version. **Rollback
requires a prior activation history**; it is not needed for the first snapshot.
Existing readers keep their original file until the client is restarted.

## 7. Smoke-test the published data, read-only

The database does not automatically become the backing store for existing MCP
tools; this is a direct Python test of the new DuckDB query service:

```powershell
@'
from bls_mcp.ingestion.publish import current_snapshot_path
from bls_mcp.storage.query_models import SeriesSearchFilters
from bls_mcp.storage.store import BLSStore

path = current_snapshot_path('data/local/snapshots')
store = BLSStore(path)
print('active file:', path)

for program in ('pc', 'cu'):
    page = store.search_series(SeriesSearchFilters(programs=(program,), limit=3))
    print(program, 'series count:', page.total_matches)
    if not page.matches:
        continue
    series_id = page.matches[0].series.series_id
    rows = store.get_observations([series_id], start_year=2020, end_year=2026)
    print('example:', series_id, 'observations:', len(rows.observations))

import duckdb
with duckdb.connect(str(path), read_only=True) as conn:
    indexes = conn.execute(
        "SELECT index_name FROM duckdb_indexes() WHERE table_name='observations'"
    ).fetchall()
    print('ART index names:', indexes)
    assert ('observations_series_id_art',) in indexes
'@ | uv run --locked python -
```

For an example of normalization using an actual available base observation,
see [query-services.md](query-services.md). Avoid assuming every series has a
particular year/period. The MCP server reads the active snapshot and picks up
a newly activated one at its next start.

## 8. Monthly refresh, rollback and conservative cleanup

For the next UTC month, create a new `YYYY-MM` source directory, reuse the
same discover/plan/download/audit process, build a **new** DuckDB candidate,
and validate/publish/activate its own version. Do not replace files in an old
pinned source directory or edit earlier manifests; historical reproducibility
is the point. Keep enough space for a candidate, published copy and sorting
scratch files. A successful activation is reversible through the registry.

Before cleaning, confirm the current active path and list published versions:

```powershell
uv run --locked bls-data current --registry-dir data/local/snapshots
uv run --locked bls-data list --registry-dir data/local/snapshots
```

If `data/local/pc/` and `data/local/cu/` contain earlier **manually copied
sample** data and you no longer need to revalidate any candidate built from
them, archive those **two directories only** outside the repository before
removing them. Do not move the monthly source folders, their manifests, the
snapshot registry, or your saved-specifications file. Never delete a published
snapshot referenced by the registry. Review orphan/unpublished
`build-*.duckdb` and `*-smoke.duckdb` separately; keep their validation reports
with the corresponding candidate when investigating failures.

For example, **only after** confirming no candidate still needs these sample
sources, move the two obsolete sample directories outside the repository for
safe keeping. This is an archive operation, not a deletion:

```powershell
$archive = Join-Path (Split-Path (Get-Location).Path -Parent) `
  ('bls-old-samples-' + (Get-Date -Format 'yyyyMMdd'))
New-Item -ItemType Directory -Force $archive | Out-Null

foreach ($program in @('pc', 'cu')) {
  $source = "data/local/$program"
  $destination = Join-Path $archive $program
  if ((Test-Path $source) -and -not (Test-Path $destination)) {
    Move-Item -LiteralPath $source -Destination $destination
  }
}
Get-ChildItem $archive
```

If an older candidate then needs its original manifest/source paths, move
these directories **back** to their original locations before revalidating.
Do not archive anything under `data/local/bls/YYYY-MM/` just to shorten the
file tree; it is your pinned, reproducible source archive.

## Common problems

| Symptom | Response |
| --- | --- |
| `ModuleNotFoundError` when running the offline audit | Install the acquisition import fix or run `python -m data.manual_monthly.manual_bls_monthly audit --manifest ...` from the repository root. |
| 403/429 during download | Inspect the request log/access-pause marker; follow BLS rules. Do not retry a block automatically. |
| TLS certificate error | Configure the approved local certificate authority; never use `verify=False`. |
| `FAIL_CONFLICTS` | Investigate the reported source partitions and revise the selection deliberately. |
| `candidate already exists` | Use a new candidate path and snapshot ID; do not overwrite immutable build attempts. |
| `VALIDATING/FAILED` | Read `<candidate>.validation.json`, preserve inputs, correct the cause and build a new candidate. |
| Publication/activation file lock on Windows | Close processes using the file; do not remove active registry locks. |
| MCP tools still return the previous snapshot's data | Restart the server; the active snapshot is resolved at startup. |

For testing code changes, run `uv run --locked poe lint`, `poe format-check`,
`poe typecheck`, and `poe test` with the configured project environment.
