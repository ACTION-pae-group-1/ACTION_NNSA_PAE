# Milestone 6: Immutable DuckDB snapshot lifecycle

Milestone 6 adds an **offline-only** administrative interface, independent of
FastMCP. A snapshot advances through:

```
BUILDING / NOT_RUN
   -> VALIDATING / NOT_RUN
   -> READY / PASSED             (validated, checkpointed and closed candidate)
   -> PUBLISHED / PASSED         (versioned, immutable publication copy)
```

Any validation error becomes `VALIDATING / FAILED`. FAILED candidates are
terminal: fix the input or implementation and build another candidate. A
validation report includes reconciliation counts, failures, a timestamp and,
on success, the SHA-256 of the finalized **closed** candidate file.

## Command-line workflow

All commands are **local and offline**. No live BLS downloads, MCP
registration, or server restarts occur automatically. The `bls-data` entry
point is available after `uv sync --locked --group dev`, or use
`uv run --locked python -m bls_mcp.ingestion ...`.

In PowerShell, with original BLS bytes and checksum-pinned PC/CU input manifests:

```powershell
# One candidate can include PC, CU, or both. Choose a unique ID and path.
uv run --locked bls-data build `
  --candidate data/local/build-20261105.duckdb `
  --snapshot-id bls_20261105_01 `
  --pc-manifest data/local/pc-input.json `
  --cu-manifest data/local/cu-input.json

# This INDEPENDENT step rechecks every selected raw file and its DB receipt.
# Global observation keys, classifications and ART are checked. The final
# observation table is globally sorted, ART is rebuilt, and the DB is closed.
uv run --locked bls-data validate `
  --candidate data/local/build-20261105.duckdb `
  --pc-manifest data/local/pc-input.json `
  --cu-manifest data/local/cu-input.json

# Publication adds a new version without changing the active snapshot.
uv run --locked bls-data publish `
  --candidate data/local/build-20261105.duckdb `
  --registry-dir data/local/snapshots

uv run --locked bls-data list --registry-dir data/local/snapshots
uv run --locked bls-data activate `
  --registry-dir data/local/snapshots --snapshot-id bls_20261105_01
uv run --locked bls-data current --registry-dir data/local/snapshots

# After publishing/activating another version:
uv run --locked bls-data rollback --registry-dir data/local/snapshots
```

For a PC-only candidate, omit both CU flags; for CU-only omit both PC flags.
Every declared program requires its corresponding original-source manifest at
validation time. Missing raw bytes, hash mismatches, duplicate logical keys,
bad metadata joins, incomplete series, or a missing ART index block READY.
`validate` writes `<candidate>.validation.json` even when validation fails,
and returns a nonzero exit status for failures. `publish` requires a PASSED
report whose candidate SHA-256 matches the database bytes.

All commands return nonzero on errors; build and publication errors never
silently update the active pointer. Do not regenerate or edit a READY
candidate after validation. Do not put DuckDB files or downloaded raw BLS
data under version control. The `.gitignore` already excludes local snapshots.

## Publication and activation guarantees

- The builder refuses to overwrite an existing candidate. It uses the PC/CU
  loaders' verified manifests and transactions; failed builds leave an
  unpublished file for inspection, not an active partial dataset.
- Validation checks a fresh source-file hash for **every** selected input,
  reconciles receipts, series, classifications, index and observation count,
  rejects missing/duplicate keys, checks source lineage and period grammar,
  and rejects cross-program inconsistencies. It globally sorts observations
  and recreates the non-unique `observations_series_id_art` after sorting,
  preserving the `isfinite(value)` column constraint.
- The validator writes READY/PASSED only after all checks and sorting succeed,
  executes `CHECKPOINT`, closes the writer, and reopens read-only. On failure,
  it records VALIDATING/FAILED, checkpoints, and writes the failure report.
- Publication first verifies the READY report, candidate hash, catalog,
  integrity counts and existing ART. It copies the candidate onto the same
  filesystem as the version directory, rechecks the copied bytes, transitions
  **only that copy** to PUBLISHED, checkpoints, closes, reopens read-only and
  verifies it. Only then is the closed copy renamed to `bls-<id>.duckdb`.
- Registry schema 1 (`active-snapshot.json`) is separate from DuckDB schema 3
  and the BLS **input manifest schema 1**. Every registry record contains the
  published filename, SHA-256, timestamp, and validation-report filename.
  An exclusive `.publication.lock` serializes cooperating administrative
  commands. Registry writes use a temporary file, fsync and `os.replace`.
- `publish` registers a version but **does not activate** it. `activate` and
  `rollback` verify the destination checksum and published metadata, then
  atomically replace the active registry pointer and append an audit event.
  Older immutable versions remain available and are never auto-deleted.
- A query process can call `current_snapshot_path(registry_dir)` at startup
  and construct `BLSStore(path)` once. The returned path is a fixed version,
  not a mutable `latest.duckdb` alias. Existing readers continue using their
  original file even after activation or rollback. **A graceful restart is
  required** for an existing server process to use the new active snapshot.

No new MCP tools/resources are registered. Source data and snapshot filenames
must reside on a reliable local filesystem; a shared network filesystem may
not honor DuckDB advisory locking or atomic rename assumptions. Registry
readers do **not** hash the entire published DB on every query: full hashes
are checked at activation and rollback, and a caller may independently
verify the published registry SHA-256 during an audit.

## Failure recovery and operating cautions

A crash after a versioned file is created but before registry replacement can
leave an **orphan published file or report**. The active pointer still refers
to the previous version, and no file is automatically overwritten/deleted.
Inspect the registry and file locks before removing orphan files manually.
A stale `.publication.lock` also requires inspection of the owning process;
the code does not silently steal locks. If Windows reports a sharing
violation, close the writer/reader and retry after ensuring the original
operation has stopped. Do **not** delete an open version or an active lock.

The final copy and registry updates are two separate filesystem operations;
there is no cross-file atomic transaction. The **activation pointer update**
is atomic, and no reader follows a partially written version. Keep enough free
storage for the source candidate plus an additional published copy, staging
and sort workspace. Windows/macOS/Linux native DuckDB checks and concurrent
multi-process readers are required before production use.

The registry and files are locally managed, **not cryptographically signed**.
Access controls should prevent untrusted users from modifying snapshots or
registry JSON. A large production replay using original BLS CU bytes is still
required before activating a production CPI-U snapshot. Milestone 7 will
measure the cost and benefit of the ART and final global sort; no speedup is
claimed here.

## Python integration (not MCP wiring)

```python
from bls_mcp.ingestion.publish import current_snapshot_path
from bls_mcp.storage.store import BLSStore

fixed_path = current_snapshot_path("data/local/snapshots")
store = BLSStore(fixed_path, threads=2, memory_limit="512MB")
```

Do not periodically re-resolve the active pointer inside each query. A
well-defined restart boundary keeps one request's data and snapshot ID
consistent and allows rollback without closing existing read-only readers.

## Merge validation

Run all of these with native DuckDB installed and no skipped storage tests:

```powershell
uv run --locked pytest tests/bls/unit/test_snapshot_lifecycle.py -v -ra
uv run --locked pytest tests/bls/unit -v -ra
uv run --locked poe lint
uv run --locked poe format-check
uv run --locked poe typecheck
uv run --locked poe test
```

Manual follow-up: exercise `bls-data` on Windows with real PC/CU archives,
verify a second process can read the previous published file during activation,
and simulate interruption around publication/registry replacement.
