"""The deterministic world every eval episode runs in.

A published DuckDB snapshot is built from the real PPI industry (``pc``)
catalog files checked into ``src/bls_mcp/docs/sample_data`` plus **synthetic**
observations for a handful of construction-material series (annual averages)
and one ECI-like labor series (quarterly rows only, mirroring how ECI
publishes). The labor series arrives through the real CI ingestion pipeline
from a minimal synthetic input set (six dimension mappings, one ci.series
row, one ci.data file), so it is discoverable through ``search_series`` in
the CI program alongside the real 4,510-series pc catalog. Real series IDs
and titles keep series discovery realistic; synthetic values make every
expected answer exactly computable. The values are not BLS data.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from bls_mcp.ingestion.ci_manifest import CI_DIMENSIONS
from bls_mcp.ingestion.lifecycle import build_candidate, validate_candidate
from bls_mcp.ingestion.publish import activate_snapshot, publish_candidate

#: ci input filename -> manifest role, from the ingestion contract itself.
_CI_ROLES: dict[str, str] = {
    definition[3]: role for role, definition in CI_DIMENSIONS.items()
}

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DATA = REPO_ROOT / "src" / "bls_mcp" / "docs" / "sample_data"
SNAPSHOT_ID = "eval_synthetic_world"
BASE_YEAR = 2014
TARGET_YEAR = 2026
ANNUAL_AVERAGE = "M13"

READY_MIX = "PCU327320327320"
STEEL_MILLS = "PCU331110331110"
SAWMILLS = "PCU321113321113"
STRUCTURAL_METAL = "PCU332312332312"
FLAT_GLASS = "PCU327211327211"
GYPSUM = "PCU327420327420"
CEMENT = "PCU327310327310"
#: Synthetic ECI-like labor series in the CI program. ECI publishes quarterly
#: observations only, so the server aligns it to the spec's annual periods
#: (see bls_mcp.services.source_calculation.QUARTERLY_ANNUAL_ANCHOR). The ID
#: encodes CI + seasonal U + owner 1 + estimate 01 + final periodicity I.
LABOR_COST = "CIU1010000000000I"

#: series_id -> (2014 annual average, 2026 annual average). Synthetic.
ENDPOINTS: dict[str, tuple[float, float]] = {
    READY_MIX: (200.0, 310.0),
    STEEL_MILLS: (180.0, 252.0),
    SAWMILLS: (150.0, 195.0),
    STRUCTURAL_METAL: (160.0, 248.0),
    FLAT_GLASS: (120.0, 150.0),
    GYPSUM: (220.0, 363.0),
    CEMENT: (190.0, 285.0),
}

#: Quarterly-only series: (value at 2014-Q04, value at 2026-Q04). Synthetic.
QUARTERLY_ENDPOINTS: dict[str, tuple[float, float]] = {
    LABOR_COST: (140.0, 224.0),
}

#: Series that count as "steel" when a case asks for a steel component.
STEEL_FAMILY = frozenset({STEEL_MILLS, STRUCTURAL_METAL})

#: Minimal, self-consistent synthetic ECI (CI) input set. Codes are unique to
#: this world; only the one labor series is ingested, so case 3 exercises the
#: real quarterly-to-annual alignment through the real ingestion pipeline.
_CI_DIMENSION_FILES: dict[str, tuple[str, str, list[tuple[str, str]]]] = {
    "ci.owner": ("owner_code", "owner_text", [("1", "All workers (synthetic)")]),
    "ci.industry": (
        "industry_code",
        "industry_text",
        [("100000", "Construction of buildings (synthetic)")],
    ),
    "ci.occupation": (
        "occupation_code",
        "occupation_text",
        [("0000", "All occupations (synthetic)")],
    ),
    "ci.subcell": (
        "subcell_code",
        "subcell_text",
        [("00", "All subcells (synthetic)")],
    ),
    "ci.area": ("area_code", "area_text", [("00000", "United States (synthetic)")]),
    "ci.estimate": (
        "estimate_code",
        "estimate_text",
        [("01", "Employment Cost Index (synthetic)")],
    ),
}

_CI_SERIES_COLUMNS = (
    "series_id",
    "seasonal",
    "owner_code",
    "industry_code",
    "occupation_code",
    "subcell_code",
    "area_code",
    "periodicity_code",
    "estimate_code",
    "series_title",
    "footnote_codes",
    "begin_year",
    "begin_period",
    "end_year",
    "end_period",
)

_CI_SERIES_ROW = "\t".join(
    (
        LABOR_COST,
        "U",
        "1",
        "100000",
        "0000",
        "00",
        "00000",
        "I",
        "01",
        "Synthetic employment cost index for construction labor (ECI-like)",
        "",
        "2014",
        "Q01",
        "2026",
        "Q04",
    )
)


def value(series_id: str, year: int) -> float:
    """Synthetic annual average: linear between the two endpoints."""
    start, end = ENDPOINTS[series_id]
    step = (end - start) / (TARGET_YEAR - BASE_YEAR)
    return round(start + step * (year - BASE_YEAR), 1)


def quarter_value(series_id: str, year: int, quarter: int) -> float:
    """Synthetic quarterly observation for a quarterly-only series.

    Linear across the whole publish span, with the 2014-Q04 and 2026-Q04
    endpoints from :data:`QUARTERLY_ENDPOINTS` landing exactly on them.
    """
    start, end = QUARTERLY_ENDPOINTS[series_id]
    step = (end - start) / ((TARGET_YEAR - BASE_YEAR) * 4)
    index = (year - BASE_YEAR) * 4 + (quarter - 4)
    return round(start + step * index, 1)


def relative(series_id: str, base_year: int, target_year: int) -> float:
    """Price relative I(target) / I(base), mirroring server resolution.

    Annual series resolve from their annual averages; quarterly-only series
    resolve from their Q04 rows, the same rule the server applies
    (``QUARTERLY_ANNUAL_ANCHOR``).
    """
    if series_id in QUARTERLY_ENDPOINTS:
        return quarter_value(series_id, target_year, 4) / quarter_value(
            series_id, base_year, 4
        )
    return value(series_id, target_year) / value(series_id, base_year)


def composite(weights: dict[str, float], base_year: int, target_year: int) -> float:
    """Fixed-weight composite: sum of weight * price relative."""
    return sum(
        weight * relative(series_id, base_year, target_year)
        for series_id, weight in weights.items()
    )


def _observations_file() -> str:
    lines = ["series_id\tyear\tperiod\tvalue\tfootnote_codes"]
    for series_id in sorted(ENDPOINTS):
        for year in range(BASE_YEAR, TARGET_YEAR + 1):
            lines.append(
                f"{series_id}\t{year}\t{ANNUAL_AVERAGE}\t{value(series_id, year)}\t"
            )
    return "\n".join(lines) + "\n"


def _ci_observations_file() -> str:
    lines = ["series_id\tyear\tperiod\tvalue\tfootnote_codes"]
    for series_id in sorted(QUARTERLY_ENDPOINTS):
        for year in range(BASE_YEAR, TARGET_YEAR + 1):
            for quarter in range(1, 5):
                lines.append(
                    f"{series_id}\t{year}\tQ0{quarter}"
                    f"\t{quarter_value(series_id, year, quarter)}\t"
                )
    return "\n".join(lines) + "\n"


def _write_ci_metadata(raw: Path) -> None:
    """Write the six CI dimension mappings and the one-series ci.series file."""
    for name, (code_column, text_column, rows) in _CI_DIMENSION_FILES.items():
        lines = [
            "\t".join(
                (
                    code_column,
                    text_column,
                    "display_level",
                    "selectable",
                    "sort_sequence",
                )
            )
        ]
        lines += [f"{code}\t{text}\t1\tT\t1" for code, text in rows]
        (raw / name).write_text("\n".join(lines) + "\n", encoding="utf-8")
    (raw / "ci.series").write_text(
        "\t".join(_CI_SERIES_COLUMNS) + "\n" + _CI_SERIES_ROW + "\n", encoding="utf-8"
    )


def _manifest_for(raw: Path, program: str, entries: list[tuple[str, str]]) -> Path:
    """Write a checksum-pinned manifest for *program* over raw/* files."""
    files = []
    for name, role in entries:
        data = (raw / name).read_bytes()
        files.append(
            {
                "path": name,
                "role": role,
                "sha256": hashlib.sha256(data).hexdigest(),
                "size_bytes": len(data),
            }
        )
    manifest = raw / f"{program}.manifest.json"
    manifest.write_text(
        json.dumps({"schema_version": 1, "program": program, "files": files})
    )
    return manifest


def build_world(root: Path) -> Path:
    """Build, validate, publish and activate the eval snapshot under *root*.

    Returns the registry directory to pass as ``BLS_SNAPSHOT_REGISTRY_DIR``.
    """
    raw = root / "raw"
    raw.mkdir(parents=True)
    entries = []
    for name, role in (
        ("pc.industry.txt", "industry_mapping"),
        ("pc.product", "product_mapping"),
        ("pc.series", "series_metadata"),
    ):
        shutil.copyfile(SAMPLE_DATA / name, raw / name)
        entries.append((name, role))
    (raw / "pc.data.0.Current").write_text(_observations_file(), encoding="utf-8")
    entries.append(("pc.data.0.Current", "current"))
    pc_manifest = _manifest_for(raw, "pc", entries)

    _write_ci_metadata(raw)
    (raw / "ci.data.0.Current").write_text(_ci_observations_file(), encoding="utf-8")
    ci_manifest = _manifest_for(
        raw,
        "ci",
        [
            *[(filename, role) for filename, role in _CI_ROLES.items()],
            ("ci.series", "series_metadata"),
            ("ci.data.0.Current", "current"),
        ],
    )

    candidate = root / f"{SNAPSHOT_ID}.duckdb"
    build_candidate(
        candidate, SNAPSHOT_ID, pc_manifest=pc_manifest, ci_manifest=ci_manifest
    )
    report = validate_candidate(
        candidate, pc_manifest=pc_manifest, ci_manifest=ci_manifest
    )
    if not report.passed:
        raise RuntimeError(f"Eval world failed validation: {report.issues}")
    registry = root / "registry"
    publish_candidate(candidate, registry)
    activate_snapshot(registry, SNAPSHOT_ID)
    return registry
