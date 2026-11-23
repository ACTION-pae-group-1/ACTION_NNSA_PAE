# Milestone 3: Offline PC ingestion into DuckDB

The `bls_mcp.ingestion.pc.ingest_pc` API loads **Producer Price Index (PC)**
raw bulk files into a newly initialized, **unpublished** DuckDB snapshot. It
is independent of FastMCP and the BLS network downloader.
Milestone 6 will add the snapshot build/publish administrative CLI and
lifecycle. This milestone does **not** make a candidate safe for production.

## Explicit file selection and provenance

The loader reads one JSON manifest with `schema_version: 1`, `program: "pc"`,
and a `files` array. Each entry requires a `path` relative to the manifest
folder, a `role`, and the raw source's SHA-256 `sha256`; `size_bytes`,
`source_url`, `etag`, and `last_modified` are optional. The three required
metadata roles occur **exactly once**: `industry_mapping`, `product_mapping`,
and `series_metadata`. At least one PC observation partition must be chosen:
`historical`, `current`, or `all_data`. `all_data` must be the **only** selected
observation partition; it cannot be combined with `historical` or `current`.
Historical and current partitions may overlap, but inconsistent values or
footnotes for a logical key abort the entire transaction.

Example (replace the checksums with hashes of the exact original files):

```json
{
  "schema_version": 1,
  "program": "pc",
  "files": [
    {"path": "pc.industry", "role": "industry_mapping", "sha256": "<64 hex>"},
    {"path": "pc.product", "role": "product_mapping", "sha256": "<64 hex>"},
    {"path": "pc.series", "role": "series_metadata", "sha256": "<64 hex>"},
    {"path": "pc.data.1.Historical", "role": "historical", "sha256": "<64 hex>"},
    {"path": "pc.data.0.Current", "role": "current", "sha256": "<64 hex>"}
  ]
}
```

Input is deliberately not selected by a wildcard or an HTTP directory
listing. All files are verified for header shape, SHA-256, and (when
specified) byte length **before** database writes; checksums are checked
again before commit. The loader rejects absolute paths, traversal/symlinks
escaping the manifest directory, missing files, duplicate selected paths,
and unknown manifest fields. File receipts are saved in `source_files` with
stable IDs determined by role and relative pathname.

**PC filename conventions:** `pc.industry` (or `.txt`), `pc.product` (or
`.txt`), `pc.series`, and explicitly selected `pc.data.*` partitions. The
source URL is recorded only when supplied by the caller.

## Ingestion and validation

1. Open a **new** DuckDB file with `build_connection`, call
   `initialize_schema`, and write a `SnapshotInfo` in `BUILDING` state that
   includes program `pc`.
2. Verify the selected input files, parse PC industry/product/series metadata,
   require unique classification keys, and check each series' industry/product
   references. PC product names use the **(industry_code, product_code)** key.
3. Stage large data partitions directly into a temporary DuckDB table using
   `read_csv` with fixed five-column tab-delimited text definitions. Strip BLS
   padding and validate series membership, years, `M01`-`M13` periods, and
   finite numeric values. The dash/blank missing-value sentinel is counted but
   not stored as an observation.
4. Detect duplicates grouped by `(series_id, year, period)`. Equal values and
   footnote codes are counted and collapsed; conflicts abort ingestion. If an
   identical key appears in historical and current files, the historical
   record supplies the canonical `source_file_id`. `AllData` is exclusive.
5. Insert distinct observations **ordered by `series_id, year, period`**.
   Create an explicit **DuckDB ART index** on `observations(series_id)` only
   **after** insertion:

   ```sql
   CREATE INDEX observations_series_id_art ON observations (series_id);
   ```

6. Verify the index's presence using `duckdb_indexes()`, reconcile loaded,
   missing, and duplicate counts, recheck file hashes, and commit atomically.
   The typed `PCIngestReport` contains snapshot ID, file/classification/series
   counts, raw rows, missing rows, collapsed duplicates, observation count,
   and ART index name. The snapshot remains `BUILDING` for later validation
   and publication; the report is **not** a publication certificate.

DuckDB's explicit `CREATE INDEX` creates an Adaptive Radix Tree (ART). A
single-column index may speed highly selective `series_id` lookups. It
increases snapshot size and needs memory during construction, so it belongs
in **Milestone 7's comparative benchmarks** against a sorted-only DuckDB
snapshot. Do not claim measured query improvements yet. The ART index is
non-unique; logical key uniqueness is enforced by the import validation,
not by an observation table `PRIMARY KEY`.

## Offline example using the checked-in PC sample files

The following script assembles a *temporary copy* of the known PC samples,
creates a local manifest and builds a candidate. Run with `uv run --locked
python your_script.py` from the repository root. The database pathname must
not already exist:

```python
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

from bls_mcp.ingestion.pc import ingest_pc
from bls_mcp.storage.connection import build_connection
from bls_mcp.storage.models import SnapshotInfo
from bls_mcp.storage.schema import initialize_schema
from bls_mcp.storage.snapshots import write_snapshot_info

source = Path("src/bls_mcp/docs/sample_data")
target = Path("tmp/pc-m3-example")
target.mkdir(parents=True, exist_ok=True)
selected = [
    ("pc.industry.txt", "industry_mapping"),
    ("pc.product", "product_mapping"),
    ("pc.series", "series_metadata"),
    ("pc.data.20.ComputerProduct.sample", "historical"),
]
files = []
for name, role in selected:
    shutil.copyfile(source / name, target / name)
    raw = (target / name).read_bytes()
    files.append({
        "path": name, "role": role, "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
    })
manifest = target / "selection.json"
manifest.write_text(json.dumps({
    "schema_version": 1, "program": "pc", "files": files,
}))

with build_connection(target / "candidate.duckdb") as conn:
    initialize_schema(conn)
    write_snapshot_info(
        conn, SnapshotInfo("pc_example", datetime.now(UTC), ("pc",))
    )
    print(ingest_pc(conn, manifest))
    print(conn.execute(
        "SELECT index_name, sql FROM duckdb_indexes() "
        "WHERE table_name = 'observations'"
    ).fetchall())
```

The checked-in 2026 sample slice has 4,510 PC series, 998 industry names,
4,510 industry/product descriptions, and **34 observations**, including one
annual-average `M13`. These are sample counts, **not** a whole-BLS-population
claim. No BLS HTTP request is made by the example.

## Verification and remaining work

```powershell
uv run --locked pytest tests/bls/unit/test_pc_manifest.py -v -ra
uv run --locked pytest tests/bls/unit/test_pc_ingestion.py -v -ra
uv run --locked pytest tests/bls/unit -v -ra
uv run --locked poe lint
uv run --locked poe format-check
uv run --locked poe typecheck
uv run --locked poe test
```

The DuckDB tests must **not skip** on a development machine with DuckDB
installed. Test both `historical + current` overlaps and `AllData` exclusivity,
metadata joins, bad hashes, missing/invalid data, conflict rollback,
nonpublication, and ART index persistence after reopening the database.
Later milestones cover CU ingestion, read APIs, full snapshot lifecycle,
benchmarks and administrative CLI. Saved escalation specifications remain
untouched.
