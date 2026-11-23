# Milestone 5: Read-only DuckDB query services

The `bls_mcp.storage.store.BLSStore` facade queries an **existing, validated,
PUBLISHED DuckDB snapshot**. It is a pure Python library; it registers no MCP
tools and does not download or ingest BLS data. Milestone 6 provides offline publication and an active-snapshot registry.
The query layer still accepts an **explicit fixed file path**, not a mutable
"latest" alias; resolve the active path at startup using
`ingestion.publish.current_snapshot_path()` and restart to adopt an update.

The DuckDB schema is **v3** after retaining `cu_area.selectable`. The
post-load `observations_series_id_art` index created by the PC/CU ingest
loaders remains in place and is available to
highly selective series reads. Milestone 7 will measure its actual performance;
this change makes no speedup claim.

## Python API

```python
from bls_mcp.storage.query_models import SeriesSearchFilters
from bls_mcp.storage.store import BLSStore

store = BLSStore("data/snapshots/bls-2026-11-05.duckdb", threads=2,
                 memory_limit="512MB")

# Case-insensitive literal substring search over IDs, titles, descriptions,
# and available classification codes and labels.
page = store.search_series(
    SeriesSearchFilters(
        query="machinery", programs=("pc",), active_only=True,
        industry_code="334---", limit=25, offset=0,
    )
)
print(page.snapshot_id, page.total_matches)
for hit in page.matches:
    print(hit.series.series_id, hit.series.title, hit.classification)

# One request supports 1-1,000 distinct source series IDs.
series_ids = [hit.series.series_id for hit in page.matches]
if series_ids:
    original = store.get_observations(series_ids, start_year=2020, end_year=2025)
    rebased = store.normalize_series(
        series_ids, base_year=2020, base_period="M12",
        start_year=2023, end_year=2025, target_base=100.0,
    )
    for status in rebased.statuses:
        print(status.series_id, status.status, status.base_value)
```

The file above is an example path, **not a published snapshot supplied by this
PR**. Milestone 6 will establish a supported publication workflow. Tests only
simulate publication of synthetic offline files to exercise the query API.

## Search and retrieval contract

- `search_series(SeriesSearchFilters(...))` returns a `SeriesSearchPage` with
  source `snapshot_id`, `total_matches`, `limit`, `offset`, ordered matches,
  and typed `PCClassification` or `CUClassification` detail where available.
  Search filters include source programs (`pc`/`cu`), active status, seasonal
  adjustment, PC industry/product, CU area/item/periodicity, and title/label
  text. Query characters such as `%` and `_` are **literal**, not SQL wildcards.
  Search results sort by case-folded title and then exact series ID; pagination
  is deterministic for a fixed immutable snapshot.
- `get_observations(series_ids, start_year=..., end_year=...)` returns
  `ObservationsPage` with original `DOUBLE` values, footnotes, source-file ID,
  snapshot ID and one `SeriesOutcome` per requested series. Rows sort by
  `series_id`, `year`, and the original zero-padded BLS `period` code.
  `M13` is the annual average and sorts after `M12`. `S01`-`S03` represent
  semiannual periods; `Q01`-`Q04` are recognized base period identifiers.
  There is no date imputation or conversion of M13 into a calendar month.
- `normalize_series(series_ids, base_year=..., base_period=...)` looks up the
  **exact base observation for each series** in SQL **independently of the
  requested output years**. The default target base is 100. The SQL operation
  is `(value / exact_base_value) * target_base` and returns both original and
  normalized values, original footnotes and source IDs, and the exact base
  reading. There is no fallback, interpolation, or borrowing another series'
  denominator. Rebased PPI and CPI index series are not automatically made
  equivalent in economic meaning or composition.

Both multi-series operations preserve the **input ID order in statuses** and
produce one of five explicit per-series outcomes:

| Status | Meaning |
| --- | --- |
| `success` | One or more returned observations; for normalization, a valid nonzero base exists. |
| `unknown_series` | No corresponding `series_catalog` entry. |
| `missing_base` | Known series, but the exact requested base observation is absent. |
| `zero_base` | Known series, but its exact base observation is zero; no division is attempted. |
| `no_rows_in_window` | Known series with a valid base if required, but nothing to return within the requested year bounds. |

Errors for individual series do **not** make the entire mixed request fail.
Invalid request shapes, unsupported snapshot versions, unpublished/failed
snapshots, duplicate base observations, or result budgets being exceeded do
raise exceptions. Errors never result in fabricated readings or silent partial
results. `SeriesOutcome.observation_count` counts output rows, not base rows.

## Bounded, read-only, parameterized execution

- Inputs: 1-1,000 distinct series IDs; search page size 1-1,000; bounded
  query/identifier lengths, offsets and year range. Empty or malformed
  requests fail fast. A maximum of 1,000,000 output rows is permitted, with a
  default budget of 100,000. `max_rows+1` detects overflow and raises
  `QueryResultLimitError` instead of silently truncating results.
- All user values, including a full list of series IDs, are supplied as
  DuckDB **bound parameters**. The query text uses only internal fixed
  clauses and column names. The 1,000-series request is a single vectorized
  query using `unnest(?::VARCHAR[])`, not 1,000 Python SQL calls.
- Every operation creates a new, closed `read_only=True` connection through
  `snapshot_reader()`. The facade additionally requires validation status
  `PASSED`, a v3 schema, and lifecycle `PUBLISHED`. It never accepts a
  pre-publication reader override. No shared connection is handed between
  threads. Source-file provenance is retained on each result.
- No Arrow/pandas dependency or export method is introduced here. The
  benchmark/export choice remains open for Milestone 7, when actual result
  volumes and hardware measurements are available.

## Validation

Run with native DuckDB installed, with **no skips**:

```powershell
uv run --locked pytest tests/bls/unit/test_query_models.py -v -ra
uv run --locked pytest tests/bls/unit/test_store_queries.py -v -ra
uv run --locked pytest tests/bls/unit -v -ra
uv run --locked poe lint
uv run --locked poe format-check
uv run --locked poe typecheck
uv run --locked poe test
```

The native test fixtures exercise both PC and CU, `M13` and `S` periods,
search/pagination/classification, 1,000-series batches, provenance,
normalization with base outside the output window, all per-series statuses,
row limits, SQL injection attempts, read-only isolation across threads, and
persistence of the ART index. They do **not** publish real data or establish
production latency numbers.
