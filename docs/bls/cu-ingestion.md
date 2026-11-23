# Milestone 4: CPI-U (CU) DuckDB ingestion

Milestone 4 adds an **offline, checksum-pinned CU loader**. The CU program is
Consumer Price Index for All Urban Consumers (CPI-U), not CPI-W (`cw`) or
Chained CPI (`su`). The loader stages canonical BLS *index levels*, not monthly
percentage changes, and never downloads files, publishes a
snapshot, or changes MCP tools/resources.

## Source layout and evidence

The BLS bulk download directory is
<https://download.bls.gov/pub/time.series/cu/>. Its current directory listing
shows `cu.area`, `cu.item`, `cu.series`, `cu.data.0.Current`, and multiple
`cu.data.N.*` partitions. The [BLS CU series-identifier guide]
(https://www.bls.gov/cpi/factsheets/cpi-series-ids.htm) distinguishes CPI-U
(`CU`), seasonal (`S`/`U`), and regular (`R`) versus semiannual (`S`)
publication. The [BLS CPI field definitions]
(https://www.bls.gov/help/def/cu.htm) describe base, item, area and frequency;
[BLS's CPI Handbook](https://www.bls.gov/opub/hom/cpi/calculation.htm)
distinguishes annual and semiannual *averages* from actual month readings.

The implemented TSV layout follows those published field definitions and
independently documented BLS file columns:

| File | Expected columns |
| --- | --- |
| `cu.area` | `area_code`, `area_name`, `display_level`, `selectable`, `sort_sequence` |
| `cu.item` | `item_code`, `item_name`, `display_level`, `selectable`, `sort_sequence` |
| `cu.series` | `series_id`, `area_code`, `item_code`, `seasonal`, `periodicity_code`, `base_code`, `base_period`, `series_title`, `footnote_codes`, `begin_year`, `begin_period`, `end_year`, `end_period` |
| `cu.data.*` | `series_id`, `year`, `period`, `value`, `footnote_codes` |

For the published five-column `cu.area`, `selectable` is validated as `T`/`F`
and retained as `BOOLEAN` in `cu_area`. The original four-column assumption
was incorrect. Existing v2 DuckDB snapshots must be rebuilt under **schema v3**
from pinned sources; input-manifest schema version 1 does not change.

Headers must match; metadata rows may have **empty trailing tab fields**,
which BLS files sometimes contain. Extra *nonempty* fields are rejected.
The loader strips BLS field padding, checks referenced codes, unique keys,
seasonal and frequency flags, years, and series ID structure. The item code
**includes** the base-code character at position nine: `CUUR0000SA0` has
base `S`, area `0000`, item `SA0`. Do not infer that the item code is `A0`.

**Verification limit:** Direct retrieval of the original CU files was blocked
in the patch-building environment. File schemas and representative identifier
semantics were checked against published documentation and external examples,
but no real whole-file BLS CU replay was performed. The new integration tests
use independently constructed, format-faithful offline fixtures. Before a
production snapshot, preserve original BLS bytes and run a pinned manifest
against real files, investigating any observed format drift instead of
relaxing validation.

CU periods accepted as published codes: `M01`-`M12` (monthly), `M13`
(annual average), `S01`/`S02` (first/second half), and `S03` (semiannual
annual average). A regular (`R`) series must use `M*` periods; a semiannual
(`S`) series must use `S*`. Do not interpret any of these averages as
monthly observations. An empty or dash (`-`) value is counted as missing and
omitted, not silently converted to zero.

## Pinned input manifest

Each manifest has `schema_version: 1` (the **manifest format**, independent
of the DuckDB schema version), `program: "cu"`, and an explicit `files` array.
Each item has a relative path, role, SHA-256 of the **original bytes**, and
optionally a byte count, source URL, ETag, and Last-Modified.

```json
{
  "schema_version": 1,
  "program": "cu",
  "files": [
    {"path": "cu.area", "role": "area_mapping", "sha256": "<64 hex>"},
    {"path": "cu.item", "role": "item_mapping", "sha256": "<64 hex>"},
    {"path": "cu.series", "role": "series_metadata", "sha256": "<64 hex>"},
    {"path": "cu.data.1.AllItems", "role": "historical", "sha256": "<64 hex>"},
    {"path": "cu.data.0.Current", "role": "current", "sha256": "<64 hex>"}
  ]
}
```

The placeholders above are explanatory: replace them with the exact hashes of
the retrieved raw files. Create the manifest **in the directory containing
those sources** or use relative subpaths. Do not load an unverified directory
by wildcard. Select additional `cu.data.N.*` partitions explicitly, with
one role `historical` per selected partition and at most one `current`.
There is no implied CU `AllData` file. Current and historical files can
contain overlapping logical keys, so the loader compares them instead of
assuming nonoverlap or a release-vintage precedence. Selecting only a subset
of partitions yields a **partial** candidate dataset. Full program coverage
must be separately validated in Milestone 6.

The loader rejects duplicate paths, absolute and traversal paths, symlink
escapes, incorrect headers, altered SHA-256 checksums, size mismatches and
unrecognized fields. Files are rechecked before committing. Source-file IDs
are stable within the chosen import order: area, item, series, historical
(sorted by filename), current. Matching duplicate observations select the
first of those sources for provenance. Conflicting values or footnotes fail
the entire import. The data table has no unique key, so this validation must
remain active; later snapshot validation rechecks global key uniqueness.

## Build an unpublished candidate

Use Python 3.11+ with DuckDB and the project dependencies installed.

```python
from datetime import UTC, datetime
from pathlib import Path

from bls_mcp.ingestion.cu import ingest_cu
from bls_mcp.storage.connection import build_connection
from bls_mcp.storage.models import SnapshotInfo
from bls_mcp.storage.schema import initialize_schema
from bls_mcp.storage.snapshots import write_snapshot_info

# The manifest references actual local cu.* files with their real checksums.
manifest = Path("tmp/bls-cu/cu-input.json")
with build_connection(Path("tmp/cu-candidate.duckdb")) as writer:
    initialize_schema(writer)
    write_snapshot_info(
        writer, SnapshotInfo("cu_candidate", datetime.now(UTC), ("cu",))
    )
    report = ingest_cu(writer, manifest)
    print(report)
```

Run the example through `uv run --locked python script_name.py`; the candidate
DB path must not already exist. Builders can use `programs=("pc", "cu")` and
load either program first. Each loader allocates source-file IDs beyond those
already present and operates only on its own classifications. The canonical
`observations` relation is shared. The **ART index**
`observations_series_id_art` is created after a CU-only bulk load, or retained
when PC created it first. Both loaders keep the candidate in `BUILDING`; the
existence of a valid index does **not** authorize production reads.

## Schema version and compatibility

Milestone 4 originally advanced the storage schema from v1 to v2. Correcting
the `cu.area` layout adds a `cu_area.selectable` column and advances
`SnapshotInfo.schema_version` to **3**. The shared observations and PC tables
are unchanged. There is **no in-place migration**: v1 and v2 DuckDB candidates
must be rebuilt, and the read-only reader rejects versions other than 3.
The separate JSON input-manifest schema stays at version 1. Saved user
specifications live in their own file and remain untouched.

## Offline verification

```powershell
uv run --locked pytest tests/bls/unit/test_cu_manifest.py -v -ra
uv run --locked pytest tests/bls/unit/test_cu_ingestion.py -v -ra
uv run --locked pytest tests/bls/unit -v -ra
uv run --locked poe lint
uv run --locked poe format-check
uv run --locked poe typecheck
uv run --locked poe test
```

All native DuckDB test modules, including the PC regression and CU cross-
program tests, must **pass with zero skips** before merging. In particular,
verify rollback on data errors, metadata relationships, classification/base
retention, overlapping current/historical rows, `M13` and `S01`-`S03`,
and the ART index after closing and reopening the database.
Production acquisition, snapshot publication, MCP integration, and ECI
labor-escalation ingestion remain separate milestones.
