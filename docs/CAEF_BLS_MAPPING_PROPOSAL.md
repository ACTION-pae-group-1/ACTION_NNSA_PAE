# CAEF-to-BLS Mapping Proposal

**Status: PROPOSED — NOT APPROVED — NOT DEPLOYED**

This is a research proposal for analyst and owner review. It does not change any application code, calculation, basket, or data file. No mapping here is validated economically. Every row requires analyst or subject-matter review before any use.

## 1. Scope and sources

| Input | Location | Notes |
|---|---|---|
| CAEF category vocabulary and hierarchy | `src/pars_local_mcp/data/CAEF 2.0 Standard WBS.xlsx`, sheet `WBS` (837 rows) | Reference hierarchy. `level` column maps to `level_n`. |
| CAEF training labels | `src/pars_local_mcp/data/mock_pars_full.duckdb`, table `gold_corrections` (50,000 rows) | **Synthetic.** Marker table `_mock_marker`: "SYNTHETIC MOCK DATA - NOT REAL. Generated from table structure only." |
| BLS catalog | `data/local/snapshots/bls-sample_pc_ci.duckdb` (read-only), tables `series_catalog`, `observations`, `ci_series`, `pc_series`, `source_files`, `snapshot_info` | Approved local snapshot. SHA-256 `fb61d88f90c0e414847f6dc03f5b5b2bb245fc550c675091471897f311e933ec`, verified before and after this work. |
| Snapshot provenance | `data/local/snapshots/active-snapshot.json`, `data/local/snapshots/bls-sample_pc_ci.duckdb.validation.json` | Validation `passed: true`, schema 4, `issues: []`. |

Scratch outputs are in `C:/tmp/caef_mapping/`: `wbs_hierarchy.tsv`, `caef_categories.tsv` (325 rows with parent paths), `caef_match_by_category.tsv` (325 rows with match type), `verified_series.json` (read-only verification of every cited series ID).

Network access: none. No tests were run, no models were retrained, and no dependencies were installed.

## 2. CAEF vocabulary reviewed

Distinct non-blank category names per level, derived from `gold_corrections` and confirmed against the WBS sheet (every label occurs at the same WBS level, and every WBS title at that level occurs in the labels):

| Level | Categories reviewed |
|---|---|
| L2 | 6 |
| L3 | 24 |
| L4 | 36 |
| L5 | 68 |
| L6 | 75 |
| L7 | 70 |
| L8 | 46 |
| **Total** | **325** |

Blank strings also occur in the labels at each level (for example, 180 blank rows at L2). They are excluded from the counts above.

Parent-child structure: parent links in the training labels agree with the WBS parent titles (0 mismatches). However, 59 category names appear under more than one parent in the WBS (for example, "Electrical", "HVAC", and "Security" recur under different D&D and Standard Equipment branches). The mapping below is keyed by level and name, and a path-keyed version would be needed for any production use.

## 3. BLS catalog reviewed

Snapshot `sample_pc_ci` (`snapshot_info`: built 2026-11-18, lifecycle PUBLISHED, validation PASSED).

| Program | Series in catalog | Series with observations | Observation rows | Observation years | Notes |
|---|---|---|---|---|---|
| `pc` (PPI commodity/industry) | 4,510 | **2** | 34 | 2003–2026 (see below) | Only two PC series have any observations. Source file: `pc.data.20.ComputerProduct.sample`. |
| `ci` (see note) | 506 | 423 | 20,968 | 2014–2026 | Employment Cost Index (ECI) compensation series. Source file: `ci.data.0.Current`. |
| `cu` | 0 | 0 | 0 | — | No CPI series in snapshot. |

Total: 5,016 series and 21,002 observations.

**Program note.** The brief described CI as capital investment or construction input. The snapshot's CI program is the BLS Employment Cost Index, with titles such as "Total compensation for all civilian workers, current dollar index" (base December 2005 = 100). This is confirmed by `src/bls_mcp/docs/bulk_files.md` (around lines 200–206) and `src/bls_mcp/docs/ROADMAP.md` line 466 ("ECI (`ci`) is the MVP's baseline labor source").

**PC series with observations (both verified read-only):**

| Series ID | Title | Observations | Observation years |
|---|---|---|---|
| `PCU334---334---` | PPI industry sub-sector data for Computer & electronic product mfg, not seasonally adjusted | 14 (`pc_series` / `observations`) | 2003–2004 only |
| `PCU334519334519S` | PPI industry data for Other measuring and controlling device mfg-Secondary products, not seasonally adjusted | 20 | 2018–2026 (gaps) |

All other PC series (4,508) are catalog entries with **no observations**. They cannot support an index calculation until observation data is ingested.

## 4. Proposed mapping table

Match types: **DIRECT** (series title names the same commodity or service), **RELATED** (plausible but indirect; the indirect link is stated), **INSUFFICIENT** (no defensible series). AMBIGUOUS means several candidate series exist; the analyst chooses. Series are not ranked.

Every series ID and title below was verified by a read-only query on `series_catalog` and `observations` (`C:/tmp/caef_mapping/verified_series.json`).

| CAEF level | CAEF category (parent path, from WBS) | BLS series ID | BLS official title (snapshot) | Series or index type | Rationale | Match type | Evidence |
|---|---|---|---|---|---|---|---|
| L5, L6, L7 (HVAC) | HVAC; e.g. `Total Estimated Cost > Standard Equipment & Utilities > Commissioning > ...`, `... > Deactivation` (3 WBS placements at L5, 1 at L6, 4 at L7 under D&D branches; see `caef_categories.tsv`) | PCU33341-33341- | PPI industry data for HVAC and commercial refrigeration equipment, not seasonally adjusted | PPI industry index (`units`=index, base per series) | Title names the same equipment class. Match is on commodity, not on CAEF cost scope. | **DIRECT**, AMBIGUOUS | `series_catalog` row for PCU33341-33341-; **0 observations** (catalog only); years 2003–2026. WBS rows e.g. 1.1.5.1.1, 1.1.5.4.1.1, 1.1.5.4.2.1.1 in `wbs_hierarchy.tsv`. |
| L5, L6, L7 (HVAC) | (same as above) | PCU3334--3334-- | PPI industry group data for HVAC and commercial refrigeration equipment, not seasonally adjusted | PPI industry-group index | Group-level alternative to the industry series above. | **DIRECT**, AMBIGUOUS (candidate) | `series_catalog` row; **0 observations**; years 2003–2026. |
| L4, L5, L6, L7 (Electrical) | Electrical; e.g. `Site O&S > Utilities`, `Total Estimated Cost > Standard Equipment & Utilities > ...` | PCU335313335313 | PPI industry data for Switchgear and switchboard apparatus mfg, not seasonally adjusted | PPI industry index | Switchgear is one electrical equipment class. The CAEF category covers broader electrical scope (wiring, distribution, and more). | RELATED | `series_catalog` row; **0 observations**; years 1985–2026. |
| L4, L5, L6, L7 (Security) | Security; e.g. `Site O&S > Indirect Labor > ...`, `Total Estimated Cost > Management and Support > SE&TM`, `... > Deactivation` | PCU561612561612 | PPI industry data for Security guards and patrol services, not seasonally adjusted | PPI industry index (service price) | Security services price. CAEF Security is a WBS scope that may include equipment and systems, so the link is indirect. | RELATED | `series_catalog` row; **0 observations**; years 2004–2026. |
| L6, L7, L8 (Foundation and Substructure) | Foundation and Substructure; e.g. `Total Estimated Cost > Vertical Construction > Primary Mission Facilities > New Construction` (4 placements at L6, 2 at L7, 8 at L8) | PCU236400236400224 | PPI industry data for New nonresidential building construction by contractor type/region-Poured concrete foundation and structure contractors, not seasonally adjusted | PPI industry index (contractor service price) | Poured concrete foundation contractors relate to foundation and substructure work. The series covers only the poured-concrete contractor segment of new nonresidential construction. | RELATED | `series_catalog` row; **0 observations**; years 2014–2026. |
| L7, L8 (Supercomputers) | Supercomputers; e.g. `Total Estimated Cost > Process Equipment & Instrumentation > Commissioning > NSE-Specific Equipment & Instrumentation > Stockpile Research...` (3 placements at L7, 1 at L8) | PCU334---334--- | PPI industry sub-sector data for Computer & electronic product mfg, not seasonally adjusted | PPI sub-sector index | Supercomputers are a subset of computer and electronic product manufacturing. The sub-sector is much broader than the CAEF item. | RELATED | `series_catalog` row; **14 observations** (`observations`), years **2003–2004 only**, so the series is stale for current use. |
| L3 (Direct Labor; parent Mission O&S), L3 (Indirect Labor; parent Site O&S), L4 (Craft; parent `Mission O&S > Direct Labor`), L4 (Managers), L4 (Scientists and Engineers), L5 (Project Managers) | Labor categories (project-role labels) | CIS2012300000000I | Total compensation for private industry workers in the construction industry, current dollar index | ECI compensation index (current-dollar, base Dec 2005 = 100) | Labor-cost proxy for construction-industry workers. It is a compensation index, not a labor rate or labor-hour cost, and it is not role-specific. | RELATED, AMBIGUOUS | **50 observations**, years 2014–2026 (`observations`, `ci_series`). |
| (same as above) | (same as above) | CIS2022300000000I | Wages and salaries for private industry workers in the construction industry, current dollar index | ECI wages-and-salaries index | Wages-only alternative to total compensation. | RELATED, AMBIGUOUS (candidate) | **50 observations**, years 2014–2026. |
| (same as above) | (same as above) | CIU1010000405000I | Total compensation for civilian workers in construction, extraction, farming, fishing, and forestry occupations, current dollar index | ECI occupation index, civilian | Occupation-based alternative. Craft trades are closer to construction occupations than to the industry series. | RELATED, AMBIGUOUS (candidate) | **50 observations**, years 2014–2026. |
| (same as above) | (same as above) | CIS2010000405000I | Total compensation for private industry workers in construction, extraction, farming, fishing, and forestry occupations, current dollar index | ECI occupation index, private industry | Private-industry variant of the occupation series above. | RELATED, AMBIGUOUS (candidate) | **50 observations**, years 2014–2026. |

Notes on the table:
- Labor rows are AMBIGUOUS because four observation-backed series fit with different scope (industry or occupation, compensation or wages, civilian or private). The analyst must choose.
- The labor and HVAC candidates are the only rows with observation support. The electrical, security, foundation, and HVAC rows are catalog-only and therefore not usable for any calculation until data is ingested.
- Management and engineering role categories (Managers, Scientists and Engineers, Project Managers) were matched only to the construction-industry labor series. Occupation series for management or engineering roles were not searched in this pass, so those rows are not exhaustive.

**Categories reviewed and not mapped (INSUFFICIENT):**
- All six L2 categories (Total Estimated Cost, Mission O&S, Site O&S, Other Project Costs, Other Direct Costs, Contractor Fee). These are aggregates, operating services, or fees with no matching series in the snapshot.
- Instrumentation categories (for example "Process Equipment & Instrumentation" and its variants at L3–L8). The only observation-backed candidate, PCU334519334519S (20 observations, 2018–2026 with gaps), covers one device class, not the CAEF equipment scope. PCU33451-33451- ("Nav/measuring/medical/control instruments mfg") is catalog only. Neither is proposed.
- Waste Management (L3, `CIS2015600000000I` is a labor-compensation index for waste-services industry, not a service price). Not proposed.
- All other categories (about 300 rows): no series with a supported title match was identified in this pass. This is not an exhaustive search of the 4,510 PC catalog titles.

## 5. Coverage report

Counts are from `C:/tmp/caef_mapping/caef_match_by_category.tsv` (325 rows, counted by level and name).

| CAEF level | Categories reviewed | DIRECT rows | RELATED rows | AMBIGUOUS rows | INSUFFICIENT rows |
|---|---|---|---|---|---|
| L2 | 6 | 0 | 0 | 0 | 6 |
| L3 | 24 | 0 | 2 | 2 | 22 |
| L4 | 36 | 0 | 5 | 3 | 31 |
| L5 | 68 | 1 | 3 | 2 | 64 |
| L6 | 75 | 1 | 3 | 1 | 71 |
| L7 | 70 | 1 | 4 | 1 | 65 |
| L8 | 46 | 0 | 2 | 0 | 44 |
| **Total** | **325** | **3** (1 name: HVAC) | **19** (10 names) | **9** | **303** |

- Categories with a DIRECT candidate: 1 name (HVAC), 3 placements. All DIRECT candidates are catalog-only (0 observations).
- Categories with RELATED candidates only: 10 names (19 placements).
- Categories with any supported candidate: 11 names (22 placements).
- Categories with no supported match: 303 placements (INSUFFICIENT).
- Categories with an observation-backed candidate: labor (6 names, 4 series, 50 observations each) and Supercomputers (2 placements, 14 observations, 2003–2004 only).

## 6. Limitations

1. **CAEF training labels are synthetic.** `gold_corrections` in `mock_pars_full.duckdb` is marked "SYNTHETIC MOCK DATA - NOT REAL". The category names are the real CAEF vocabulary, but the row distribution and identifiers (for example `mock_lowest_level_0`) are generated. The packaged demo run is also `data_origin: synthetic_mock` (`src/cost_intel_app/demo_assets/caef/demo_run.json`). Label counts and frequencies must not be read as real cost evidence.
2. **Level counts differ from the brief only in blank handling.** The brief's counts (6, 24, 36, 68, 75, 70, 46) are reproduced when blank strings are excluded. Including blanks, `count(distinct)` returns 7, 25, 37, 69, 76, 71, 47.
3. **Name-keyed mapping.** 59 category names occur under multiple WBS parents. The table above is keyed by level and name only.
4. **BLS snapshot is a sample.** It holds 5,016 series with 21,002 observations. Only 2 of 4,510 PC series have observations. The 4,508 other PC series are catalog metadata only. No CU series. No series in the snapshot has observations before 2003 (PC) or 2014 (CI).
5. **CI is compensation, not capital investment.** The CI program is the ECI, so no capital-investment or construction-input price index is present in the snapshot.
6. **Existing app basket is synthetic.** `src/cost_intel_app/wbs_bls_mapping.py` requires `origin == "synthetic_mock"` evidence and uses `DEMO-WPU1017`, which is not in the snapshot. Existing tests (`src/cost_intel_app/tests/test_wbs_bls_mapping.py`, `test_pars_view.py`) assert on that demo ID.
7. **No economic validation.** No cost shares, basket weights, escalation rates, or base-period choices are proposed. Each row needs analyst or subject-matter review.
8. **Search breadth.** Keyword search over PC titles was not exhaustive. Management and engineering occupation series in CI were not searched. Any row marked INSUFFICIENT means "not identified in this pass".

## 7. Recommended minimum application-side changes (described, not applied)

1. Keep the synthetic-origin gate in `wbs_bls_mapping.py`. Do not enable real-data mapping until the owner approves this proposal.
2. Store approved mappings as versioned data, keyed by CAEF level, category, and parent path (not name alone). Each row needs `status`, `approved_by`, and `approved_at`. Unapproved rows must not drive any calculation.
3. Validate every series ID against `series_catalog` in the active snapshot, and reject catalog-only series (zero observations) for any calculation.
4. Correct program labels in the UI and docs: the CI program is the Employment Cost Index (compensation), not capital investment.
5. Require an explicit analyst choice wherever a row is AMBIGUOUS. Do not rank candidates automatically.
6. Add a snapshot-version check so a mapping approved against `sample_pc_ci` is re-reviewed when the snapshot changes.

## 8. Approval

This proposal requires explicit review and approval of the proposed rows by the coordinator and the analyst before any deployment. No row is approved, deployed, or wired into the application.
