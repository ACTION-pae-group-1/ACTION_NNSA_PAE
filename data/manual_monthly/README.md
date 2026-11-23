# Manual monthly BLS source acquisition

**Manual only; discover once per calendar month for each BLS program.**
Staged downloads within a month reuse the same cached discovery, never re-fetch
verified files, and do not schedule additional work. These are repository support
scripts, not background jobs, MCP tools, or a
replacement for the production ingestion code. They do not touch a DuckDB
database. All downloads are opt-in and sequential.

There are two complementary scripts:

- `manual_bls_monthly.py` **actually requests BLS's PC/CU directory listings**,
  discovers the currently published filenames, downloads an explicitly selected
  subset, and generates a checksum-pinned DuckDB input manifest.
- `generate_bls_input_manifest.py` operates **only on files you already have**.
  It does not contact BLS. Use it for files you downloaded manually in a browser
  or obtained through another permitted channel.

## Official sources and retrieval etiquette

- PC: <https://download.bls.gov/pub/time.series/pc/>
- CU: <https://download.bls.gov/pub/time.series/cu/>
- BLS automated-retrieval policy: <https://www.bls.gov/bls/blsterms.htm>

Use a descriptive User-Agent with contact information. BLS may return HTTP 403
for automated requests, and corporate networks may require their root CA for
HTTPS. **Do not disable TLS validation or try to bypass BLS access controls.**
Downloads are **serial**, across PC and CU processes as well as within one
process. A filesystem lock prevents overlapping manual runs. Each request
is preceded by a randomly selected pause in the **30–90 second range by
default**, configurable only to slower ranges via `--min-delay` and
`--max-delay` (minimum 30 seconds). The pauses spread demand; they are not a
method of concealing automation or a guarantee BLS will allow access.

The script never overwrites completed downloads and refuses to repeat discovery
in the same program/month. The requested `--month` must be the current UTC
calendar month. A failed or interrupted download can resume its uncompleted
files without re-fetching already verified files. The same monthly discovery
can be reused to **expand a selection** (for example, current first, then
historical), but requests for previously downloaded files are never repeated.
Each distinct selection gets its own immutable manifest; previously created
`pc-input.json` / `cu-input.json` files are not modified. It does not schedule itself,
retry HTTP errors automatically, or turn off TLS verification. A 403/429
response writes `data/local/bls/.bls-access-paused.json` and **stops further
network attempts** until you have manually reviewed the BLS access policy and
resolved the issue. Do not delete that marker merely to retry a block.

Each attempted discovery/download is recorded in a local `requests.jsonl`
(timestamp, URL, outcome, HTTP status when available, and bytes received).
A stale `.monthly-acquisition.lock` after a crash must be removed manually
**only after confirming no acquisition process remains active**.

## Step 1: discover filenames (one directory request per program)

From the repository root, in PowerShell:

```powershell
# BLS_USER_AGENT is in the ignored .env; use uv --env-file below.
$month = (Get-Date).ToUniversalTime().ToString('yyyy-MM')

uv run --locked --env-file .env python data/manual_monthly/manual_bls_monthly.py `
  --month $month discover --program pc
uv run --locked --env-file .env python data/manual_monthly/manual_bls_monthly.py `
  --month $month discover --program cu
```

Review `data/local/bls/<YYYY-MM>/pc/discovery.json` and the corresponding CU
file. The inventory is based on actual BLS HTML links, not guessed partition
names. A listing that BLS blocks or changes unexpectedly is an error, not an
empty data set. Discovery is cached for the month and cannot be repeated by
simply rerunning the command.

## Step 2: review the selection without downloading

The `plan` command uses the saved directory listing and makes **no network
requests**. It verifies cached downloads by SHA-256, labels each selected file
as **REUSE** or **DOWNLOAD**, warns about potential observation overlaps, and
estimates the waiting time for **new requests only**:

```powershell
uv run --locked --env-file .env python data/manual_monthly/manual_bls_monthly.py `
  --month $month plan --program pc
uv run --locked --env-file .env python data/manual_monthly/manual_bls_monthly.py `
  --month $month plan --program cu
```

For longer historical selections, use `plan --selection historical --partition
NAME` with exact filenames from `discovery.json`. The displayed estimate is
pause time only, not a promise about file transfer or total execution time.

## Step 3: download a small test selection

Default `current` fetches the three required metadata mappings plus the
published `*.data.0.Current` file, with byte-level SHA-256 checksums:

```powershell
uv run --locked --env-file .env python data/manual_monthly/manual_bls_monthly.py `
  --month $month download --program pc
uv run --locked --env-file .env python data/manual_monthly/manual_bls_monthly.py `
  --month $month download --program cu
```

Outputs:

```text
data/local/bls/<YYYY-MM>/pc/pc-input.json
data/local/bls/<YYYY-MM>/cu/cu-input.json
```

The raw files, discovery receipts, request logs, and manifests are stored under
the Git-ignored `data/local/` directory. `*.data.0.Current` is not a complete
historical archive. The above selection is for initial testing.

The default interval can be adjusted **upward**, for example:

```powershell
uv run --locked --env-file .env python data/manual_monthly/manual_bls_monthly.py `
  --month $month download --program pc --min-delay 60 --max-delay 120
```

With 60 files and the 30–90 second default, the intentional pauses alone total
30–90 minutes, plus actual transfer time. This is a conservative operational
choice, **not an official BLS rate limit**. A high-volume acquisition may take
hours, and BLS can still block it. Stop if BLS refuses a request.

To request only particular historical partitions, use exact
name from `discovery.json`:

```powershell
uv run --locked --env-file .env python data/manual_monthly/manual_bls_monthly.py `
  --month $month download --program pc --selection historical `
  --partition pc.data.20.ComputerProduct

uv run --locked --env-file .env python data/manual_monthly/manual_bls_monthly.py `
  --month $month download --program cu --selection historical `
  --partition cu.data.1.AllItems
```

`--selection both --partition NAME` selects current and the named historical
partition. `--selection historical --all-historical` downloads **all**
historical partitions shown by the BLS listing, which can be large. A combined
current/historical ingestion may encounter genuine overlapping/conflicting
observations and fail validation; the PC/CU loaders deliberately do not hide
those conflicts. Never silently change the ingestion rules to force a build.

## Historical acquisitions, cache reuse, and overlap reporting

With `discovery.json` already saved for both programs, first preview all
historical sources **without another network request**:

```powershell
uv run --locked --env-file .env python data/manual_monthly/manual_bls_monthly.py `
  --month $month plan --program pc --selection historical --all-historical
uv run --locked --env-file .env python data/manual_monthly/manual_bls_monthly.py `
  --month $month plan --program cu --selection historical --all-historical
```

Then download the historical selection. Previously verified mapping files will
be reused, even if an earlier `*-input.json` was already completed. Request
pacing and the 403/429 access-stop marker remain unchanged.

```powershell
uv run --locked --env-file .env python data/manual_monthly/manual_bls_monthly.py `
  --month $month download --program pc --selection historical --all-historical `
  --min-delay 60 --max-delay 120
uv run --locked --env-file .env python data/manual_monthly/manual_bls_monthly.py `
  --month $month download --program cu --selection historical --all-historical `
  --min-delay 60 --max-delay 120
```

A second selection creates an immutable `pc-input-<id>.json` or
`cu-input-<id>.json`; it does **not** overwrite the first `pc-input.json` or
`cu-input.json`. The script prints the actual manifest path after each run.
Use that path for the next step, rather than assuming the unqualified filename
points to the most recently selected dataset.

**Important:** Selecting multiple source files is not the same as proving
non-overlap of *observation keys*. BLS current and historical partitions can
repeat `(series_id, year, period)`. Identical index values and footnotes can be
deduplicated by DuckDB; conflicting values or footnotes must be reported, not
silently resolved. The new offline `audit` command reads the pinned manifest,
checks source hashes and headers, uses a bounded-memory external sort, and
writes a JSON report in `reports/` beside the manifest:

```powershell
$pcManifest = 'data/local/bls/' + $month + '/pc/pc-input-<id>.json'
$cuManifest = 'data/local/bls/' + $month + '/cu/cu-input-<id>.json'
# Replace <id> with the actual paths printed by the download commands.

uv run --locked python data/manual_monthly/manual_bls_monthly.py `
  audit --manifest $pcManifest
uv run --locked python data/manual_monthly/manual_bls_monthly.py `
  audit --manifest $cuManifest
```

The audit distinguishes `PASS_NO_OVERLAP`, `PASS_IDENTICAL_OVERLAP`, and
`FAIL_CONFLICTS`. For conflicts it prints a bounded set of examples including
both source filenames and values/footnotes, writes a durable report, and exits
nonzero. Nothing is deleted or modified to make the overlap disappear. The
audit is diagnostic; ingestion still performs all of its own checks.

If you need to exclude a problematic historical partition **after reviewing
its conflicts**, you can specify repeatable `--exclude-partition NAME` flags
alongside `--all-historical`. The plan shows what was excluded and how many
files will be reused. A new input manifest is created for the smaller selection;
the excluded files and earlier manifests remain on disk. You can also choose
`--selection historical` to avoid mixing the current partition with historical
files. PC `AllData` partitions, when discovered, are excluded from regular
historical selections and must be chosen alone with `--selection all-data`.

A long audit requires temporary disk space proportional to the source rows.
Use `audit --scratch-dir PATH` if the system temporary directory is too small.
The sort files are removed on completion or failure, including on Windows.


## Step 4: build and validate with Milestone 6

```powershell
uv run --locked bls-data build `
  --candidate data/local/bls/test-pc-cu.duckdb `
  --snapshot-id test_pc_cu_01 `
  --pc-manifest "data/local/bls/$month/pc/pc-input.json" `
  --cu-manifest "data/local/bls/$month/cu/cu-input.json"

uv run --locked bls-data validate `
  --candidate data/local/bls/test-pc-cu.duckdb `
  --pc-manifest "data/local/bls/$month/pc/pc-input.json" `
  --cu-manifest "data/local/bls/$month/cu/cu-input.json"
```

Build uses a new candidate filename each time; it will not overwrite an
existing DuckDB database. If validation passes, use the `bls-data publish`
command documented in `docs/bls/snapshot-lifecycle.md`.

## Audit failure diagnostics

The audit writes `reports/<input-manifest-filename>.overlaps.json` for both
successful scans and failures that occur during file verification, parsing,
or temporary sorting. `FAIL_AUDIT_ERROR` reports include `phase`, `error`,
`rows_read`, and `missing_rows` to distinguish invalid pinned source headers
or checksums from malformed observations. A failure still exits nonzero;
**do not build** from a failed selection. Inspect the report and correct the
input selection or code, without editing original downloaded bytes.

The CU `cu.area` mapping has **five** published columns:
`area_code`, `area_name`, `display_level`, `selectable`, `sort_sequence`.
The corrected DuckDB loader retains `selectable`, requiring schema **v3**.
The `*-input.json` format stays at version 1 and existing downloaded files
and their checksums remain unchanged. Previous v2 DuckDB candidates must be
rebuilt, not migrated in place.

## Locally acquired files (no scraping)

If a corporate proxy blocks automated directory retrieval, use the separate
local-only generator instead. It requires **explicit** filenames and creates
hashes from actual bytes:

```powershell
uv run --locked python data/manual_monthly/generate_bls_input_manifest.py `
  --program pc --source-dir data/local/pc `
  --file industry_mapping=pc.industry `
  --file product_mapping=pc.product `
  --file series_metadata=pc.series `
  --file current=pc.data.0.Current
```

If your organization intercepts HTTPS, configure its trusted CA certificate
through the normal Python/system trust-store mechanism (`SSL_CERT_FILE` may be
useful in some environments). Never use `verify=False` or an unverified HTTP
fallback.

## Validate the scripts offline

```powershell
uv run --locked pytest tests/bls/unit/test_manual_bls_monthly.py -v -ra
uv run --locked pytest tests/bls/unit/test_manual_bls_overlaps.py -v -ra
uv run --locked poe lint
uv run --locked poe format-check
```

These tests simulate BLS's directory listing, streaming responses, HTTP 429,
monthly caching, safe filename selection, random pause bounds, concurrency
lock, receipt validation, selection expansion, and overlap auditing. **They do
not make live BLS requests.** A live discovery/download is an explicitly initiated
operational check, never part of the test suite or CI.

If you already manually downloaded `cu.area`, `cu.item`, `cu.series`, and a CU
data file, use the local-only generator instead. There is no reason to fetch
those files again just to test the manifest workflow.

## Engineering safeguards

- Only PC/CU filenames linked directly in the appropriate BLS directory are
  accepted; redirects to other hosts are rejected.
- Downloads stream into temporary files, reject empty/HTML/oversized replies,
  and are moved into place only after successful completion.
- The receipt is persisted after each completed file. A resumed run verifies
  cached checksums rather than re-downloading the same file.
- A complete `*-input.json` is written only when every selected file exists
  and matches its recorded SHA-256 hash and byte length.
- Discovery, raw files, request logs, and receipts are month-specific. The
  generated input manifests are immutable, with new filenames for expanded
  selections.
- HTTP 403/429 stops acquisition, leaves a persistent pause marker, and never
  triggers an automatic retry or alternate host.
- Source manifest schema version is 1; this is separate from DuckDB schema
  version 3.

## Construction-focused four-program selection (manual, offline review)

The coordinator now supports PC, WP, CU and CI. Existing monthly discovery,
30-90-second serial pacing, access-denial marker, receipt verification and
immutable manifest behavior are unchanged. It does **not** download anything
without an explicit `download` command.

After `discover --program pc` and `discover --program wp`, create *candidate*
partition lists entirely offline (PowerShell examples):

```powershell
$month = (Get-Date).ToUniversalTime().ToString('yyyy-MM')
uv run --locked python data/manual_monthly/construction_selection.py data/local/bls/$month/pc/discovery.json --output data/local/bls/$month/pc/construction-partitions.json
uv run --locked python data/manual_monthly/construction_selection.py data/local/bls/$month/wp/discovery.json --output data/local/bls/$month/wp/construction-partitions.json
```

Review/edit the resulting JSON files. Keyword matching is intentionally broad,
not an authoritative classification: false positives and omissions are possible.
Then preview, without network calls:

```powershell
uv run --locked python data/manual_monthly/manual_bls_monthly.py --month $month plan --program pc --selection historical --partition-file data/local/bls/$month/pc/construction-partitions.json
uv run --locked python data/manual_monthly/manual_bls_monthly.py --month $month plan --program wp --selection historical --partition-file data/local/bls/$month/wp/construction-partitions.json
uv run --locked python data/manual_monthly/manual_bls_monthly.py --month $month plan --program ci --selection all-data
```

To acquire the reviewed sources, replace `plan` with `download` in the commands.
For CI, `--selection all-data` acquires the full historical observation file and
required metadata. For CU, use reviewed exact `--partition` arguments; do not
assume all consumer geography/category partitions are relevant. PC/WP partition
names are a coarse filter; a later offline series-level review is necessary.

WP input manifests intentionally omit HTTP ETag/Last-Modified because the WP
manifest reader does not accept those optional fields. Other existing source
receipt behavior is preserved. Do not schedule these commands or repeatedly
probe BLS when access is denied.
