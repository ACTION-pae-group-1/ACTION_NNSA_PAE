# Employment Cost Index (CI) DuckDB ingestion

The `ci` loader adds **Employment Cost Index** series to an offline DuckDB
snapshot alongside PPI industry (`pc`) and CPI-U (`cu`). It follows the same
rules as the other loaders: every input is named in a checksum-pinned
manifest, nothing is downloaded, and the import is one transaction that
either fully succeeds or leaves no CI rows behind.

## What is loaded

Only **current-dollar index** series are loaded: `periodicity_code = I`,
reference base December 2005 = 100 (`ci.txt`, "Base periods").

Every other ECI family is left out and counted in the build report as
`excluded_series` and `excluded_rows`:

| `periodicity_code` | Meaning | Loaded |
| --- | --- | --- |
| `I` | Current dollar index number | Yes |
| `T` | Constant dollar index number | No |
| `A`, `Q` | 12-month / 3-month percent change, current dollars | No |
| `Z`, `X` | 12-month / 3-month percent change, constant dollars | No |
| `P`, `R`, `S` | Usable and response rates | No |

An escalation factor is a ratio of two index levels. Percent changes and
response rates are not index levels, and constant-dollar indexes have
inflation removed, so none of them is a valid input to that ratio. This
matches the earlier project decision recorded in
`src/bls_mcp/docs/bulk_files.md`.

For the files checked into `src/bls_mcp/docs/sample_data/`, that is 506
loaded series out of 2,470, and 20,968 observations out of 100,076 rows.

## Manifest

```json
{
  "schema_version": 1,
  "program": "ci",
  "files": [
    {"path": "ci.owner", "role": "owner_mapping", "sha256": "..."},
    {"path": "ci.data.0.Current", "role": "current", "sha256": "..."}
  ]
}
```

Paths are relative to the manifest file. `size_bytes`, `source_url`, `etag`
and `last_modified` are optional.

| Role | Required filename | Required |
| --- | --- | --- |
| `owner_mapping` | `ci.owner` | Yes |
| `industry_mapping` | `ci.industry` | Yes |
| `occupation_mapping` | `ci.occupation` | Yes |
| `subcell_mapping` | `ci.subcell` | Yes |
| `area_mapping` | `ci.area` | Yes |
| `estimate_mapping` | `ci.estimate` | Yes |
| `series_metadata` | `ci.series` | Yes |
| `current` | `ci.data.0.Current` | At least one data file |
| `all_data` | `ci.data.1.AllData` | At least one data file |

`ci.data.0.Current` is a subset of `ci.data.1.AllData`. Both may be selected:
identical overlapping observations are deduplicated and counted as
`identical_duplicates`; an overlap whose value or footnote differs fails the
build.

A ready-made manifest for the checked-in files is
`src/bls_mcp/docs/sample_data/ci-sample-input.json`. It selects
`ci.data.0.Current` only, which covers 2014 through 2026 Q2. Earlier history
needs `ci.data.1.AllData`, which is not in the repository.

## Commands

```
bls-data build --candidate <file> --snapshot-id <id> --ci-manifest <manifest>
bls-data validate --candidate <file> --ci-manifest <manifest>
```

Combine with `--pc-manifest` and `--cu-manifest` to build one snapshot for
several programs. Pass the same set of manifests to `validate`.

## Checks

The import fails, with nothing written, when:

- a file's bytes, size or header differ from the manifest;
- a series identifier disagrees with its own columns (length 17, `CI` prefix,
  seasonal, owner, estimate and periodicity positions);
- an index series uses a code missing from a mapping file;
- an observation has a period other than `Q01`-`Q04`, a non-numeric value, or
  a series ID absent from `ci.series`;
- the same series, year and period appears with different values;
- the data files hold no observation for any index series.

A value of `-` or blank is BLS's "not available" marker. Those rows are
skipped and counted as `missing_rows`; they are never stored as zero.

Snapshot validation additionally requires every CI catalog series to have a
`ci_series` row whose six codes all resolve in `ci_dimension`, and every CI
observation period to be quarterly.

## Queries

`BLSStore.search_series` returns a `CIClassification` (codes and names for
all six dimensions) for CI series, and series titles and dimension names are
searchable. The `industry_code`, `area_code` and `periodicity_code` filters
match CI series as well as PC and CU. Through the MCP tools, CI series report
`program: "ci"` and quarterly periods.

## Not included

- Downloading `ci` files. `data/manual_monthly/manual_bls_monthly.py` handles
  `pc` and `cu` only.
- Standard errors (`ci.aspect`).
- Constant-dollar index series.
