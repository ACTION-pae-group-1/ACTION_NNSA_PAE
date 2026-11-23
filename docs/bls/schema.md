# DuckDB analytical snapshot schema (v3)

Milestone 2 establishes the empty schema and its connection/metadata APIs.
Milestone 3 added offline PC bulk loading and an explicit post-load ART index.
Milestone 4 extends the provisional CU classifications, adds offline CPI-U
ingestion, and bumps the DuckDB schema from v1 to **v2**. Milestone 6
adds external lifecycle validation and immutable publication. Correcting the
published five-column `cu.area` layout advances the schema to **v3**, adding
`cu_area.selectable`. This database is **not** the saved-specifications
store and must never contain saved user escalation specifications.

## Canonical relations

| Relation | Key / key columns | Purpose |
| --- | --- | --- |
| `snapshot_info` | `singleton = 1` | Exactly one snapshot identity, schema version, build time, source programs, lifecycle and validation statuses. |
| `source_files` | `source_file_id` | Checksum, length, source URL, retrieval validators, and source-file selection role. |
| `series_catalog` | `series_id` | Common searchable source-program metadata (`pc`, `cu`, and later `ci` etc.). |
| `observations` | `(series_id, year, period)` **logical only** | Original BLS period, `DOUBLE` index value, optional raw footnote codes, source-file lineage. |

The `observations` table has **no PRIMARY KEY**. `initialize_schema()` leaves
it unindexed so that bulk import can run without index-maintenance overhead.
The PC and CU loaders insert each program's rows sorted by
`series_id, year, period`. A mixed-program candidate is not globally sorted
across independent ingestion calls; Milestone 6 globally sorts all program
observations and rebuilds ART at READY finalization. The first loader creates **`observations_series_id_art`**, an explicit non-unique DuckDB
**ART index** on `observations(series_id)`. Other program loaders must retain
that index for point/series retrieval. Test its persistence using
`duckdb_indexes()`. Milestone 7 will measure the memory and speed tradeoff.

The PC and CU loaders reject unknown series IDs, invalid periods and
non-finite values; conflicting logical keys abort the build. Identical current/history
overlaps are counted and collapsed with deterministic historical provenance,
not silently overwritten. Source-file receipts are checksum verified before
writes and before commit. Later snapshot validation and publication must
recheck global logical key uniqueness and source-file integrity. The database currently enforces
non-null core fields and finite values with a DuckDB `CHECK (isfinite(value))`.
Missing values are absent observations, not zeros. `M13` remains an annual
average and `Q01`-`Q04` can be represented without a different observations
table. DuckDB `DOUBLE` is approximate; downstream currency rounding belongs
outside storage.

The program-specific tables are:

- `pc_series`: industry/product/seasonal codes and source base date.
- `pc_industry`: industry names by industry code.
- `pc_product`: product names by **(industry_code, product_code)**.
- `cu_series`: area, item and seasonal codes, plus **periodicity**, **base
  code**, and **base period** for selecting comparable CPI-U indexes.
- `cu_area`: geographic name, display level, selectability and sort sequence.
- `cu_item`: item name, display level, selectability and sort sequence.

The CU structures correspond to the documented BLS files. Their headers and
trailing empty field behavior are enforced by `cu_manifest.py` and `cu.py`.
`M13` is an annual average and `S01`-`S03` are semiannual readings or
averages; neither is an ordinary monthly observation. The CU loader creates
the same non-unique `observations_series_id_art` index for a CU-only candidate,
or retains it for a mixed PC/CU candidate.

- `ci_dimension`: one row per Employment Cost Index code, keyed by
  `(dimension, code)`, where `dimension` is `owner`, `industry`, `occupation`,
  `subcell`, `area` or `estimate`. Holds the name, display level, selectable
  flag and sort sequence from the matching `ci.*` mapping file.
- `ci_series`: the six dimension codes plus seasonal code for each loaded ECI
  series. `periodicity_code` is constrained to `I` (current-dollar index).

**Schema version 4** adds the two `ci_*` tables. Readers require an exact
version match, so v3 snapshots must be rebuilt.

**Schema version 3** is a breaking change for v1/v2 DuckDB snapshots.
The `SnapshotInfo` default and reader version check now require v3. There is
no in-place migration; rebuild older candidates from their pinned source
files before publication. Existing published v2 snapshots cannot be opened
by this version's reader. The separate CU input-manifest format remains v1.
See `docs/bls/cu-ingestion.md` for source selection and verification limits.

Do not join PC products by product code alone. Program codes are BLS bulk
survey codes, not the legacy `BLSProgram` enum. The existing ECI/`ci` loader
is unchanged. A later ECI migration can reuse the canonical quarterly
observations and add appropriate `ci_series` classification metadata without
changing the canonical table.

## Snapshot metadata and reader safety

`SnapshotInfo` is stored once per database and contains a safe snapshot ID,
schema version, timezone-aware build timestamp, optional commit, JSON-encoded
source program list, lifecycle state, and validation status. The `source_files`
receipts are individually stored with SHA-256, size, optional URL and retrieval
metadata. The original file bytes and external validation report are preserved
outside DuckDB by later ingestion steps; no assumption is made that receipt
persistence alone verifies a downloaded file.

`build_connection(path)` creates a **new** scratch database and refuses to
open any existing file for writing. It does not publish or initialize the
schema implicitly. Builders call `initialize_schema(conn)` and
`write_snapshot_info(conn, ...)`, and later stages ingest and validate data.
The builder's writable connection is closed before read-only verification.

`snapshot_reader(path)` opens only an existing DuckDB file with
`read_only=True`, checks the supported schema version and requires lifecycle
state `PUBLISHED` by default. The validation pipeline may explicitly pass
`require_published=False` to inspect an unpublished candidate. No caller
should expose that exception to production MCP reads. Configurable `threads`
and `memory_limit` are passed to `duckdb.connect` as database options. Reader
connections are per-scope and always closed; do not share one live connection
across independent threads or processes.

Milestone 6 implements publication in `ingestion/{lifecycle,publish}.py`;
see `docs/bls/snapshot-lifecycle.md`. Publication must enforce
`BUILDING -> VALIDATING -> READY -> PUBLISHED`, close/checkpoint writers,
validate source/observation integrity, use immutable versioned files, and
atomically update an active registry with rollback. No current scratch
snapshot should be represented as a validated production dataset.

## Example for offline development

```python
from datetime import datetime, timezone
from pathlib import Path

from bls_mcp.storage.connection import build_connection, snapshot_reader
from bls_mcp.storage.models import SnapshotInfo
from bls_mcp.storage.schema import initialize_schema
from bls_mcp.storage.snapshots import read_snapshot_info, write_snapshot_info

path = Path("tmp/bls-candidate.duckdb")  # must not already exist
with build_connection(path, threads=2, memory_limit="512MB") as writer:
    initialize_schema(writer)
    write_snapshot_info(
        writer,
        SnapshotInfo(
            snapshot_id="candidate_20261105",
            built_at=datetime.now(timezone.utc),
            programs=("pc", "cu"),
        ),
    )

# An unpublished candidate is ONLY readable via the explicit validation mode.
with snapshot_reader(path, require_published=False) as reader:
    print(read_snapshot_info(reader).snapshot_id)
```

## Milestone 5 read-only query facade

`BLSStore` now exposes search, observation retrieval, and SQL normalization
on an explicitly selected **PUBLISHED/PASSED v3** snapshot. It opens a
read-only connection per operation and never creates a database. PC/CU
classification tables back program-specific filters and labels;
all observations remain in the canonical table and retain the post-load
`observations_series_id_art` index. This PR makes **no schema change**.

Normalization uses a bound base-period join and does not restrict base rows
to the output year window. Missing/zero bases and empty windows are separate
per-series statuses. See `docs/bls/query-services.md` for the typed API,
limits, result ordering, and local test requirements. Snapshot publication
and its integrity checks remain Milestone 6.
