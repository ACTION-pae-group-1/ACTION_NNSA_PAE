"""Offline Employment Cost Index (CI) manifest, ingestion and lifecycle tests."""

import hashlib
import json
from pathlib import Path

import pytest

duckdb = pytest.importorskip("duckdb")

from bls_mcp.ingestion.ci import CIIngestError, ingest_ci  # noqa: E402
from bls_mcp.ingestion.ci_manifest import (  # noqa: E402
    CIInputError,
    load_ci_manifest,
    verify_ci_source,
)
from bls_mcp.ingestion.cli import main  # noqa: E402
from bls_mcp.ingestion.lifecycle import (  # noqa: E402
    build_candidate,
    validate_candidate,
)
from bls_mcp.ingestion.publish import (  # noqa: E402
    activate_snapshot,
    publish_candidate,
)
from bls_mcp.services.series_catalog import SeriesCatalogService  # noqa: E402
from bls_mcp.storage.connection import build_connection  # noqa: E402
from bls_mcp.storage.models import SnapshotInfo  # noqa: E402
from bls_mcp.storage.query_models import (  # noqa: E402
    CIClassification,
    SeriesSearchFilters,
)
from bls_mcp.storage.schema import initialize_schema  # noqa: E402
from bls_mcp.storage.snapshots import write_snapshot_info  # noqa: E402
from bls_mcp.storage.store import BLSStore  # noqa: E402

INDEX_SERIES = "CIU2012300000000I"
PERCENT_SERIES = "CIU2012300000000A"
DATA_HEADER = "series_id\tyear\tperiod\tvalue\tfootnote_codes\n"
SERIES_HEADER = (
    "series_id\tseasonal\towner_code\tindustry_code\toccupation_code\t"
    "subcell_code\tarea_code\tperiodicity_code\testimate_code\tseries_title\t"
    "footnote_codes\tbegin_year\tbegin_period\tend_year\tend_period\n"
)
SERIES_ROWS = (
    f"{INDEX_SERIES}\tU\t2\t230000\t000000\t00\t99999\tI\t01\t"
    "Total compensation, construction, current dollar index\t\t"
    "2001\tQ01\t2026\tQ02\n"
    f"{PERCENT_SERIES}\tU\t2\t230000\t000000\t00\t99999\tA\t01\t"
    "Total compensation, construction, 12-month percent change\t\t"
    "2001\tQ01\t2026\tQ02\n"
)
DATA_ROWS = (
    f"{INDEX_SERIES}\t2025\tQ04\t167.927\t\n"
    f"{INDEX_SERIES}\t2026\tQ01\t168.966\t\n"
    f"{INDEX_SERIES}\t2026\tQ02\t-\tA\n"
    f"{PERCENT_SERIES}\t2026\tQ01\t3.1\t\n"
)


def _mapping(code: str, text: str, rows: str) -> str:
    return f"{code}\t{text}\tdisplay_level\tselectable\tsort_sequence\n{rows}"


def ci_files(
    *, series: str = SERIES_ROWS, data: str = DATA_ROWS
) -> dict[str, tuple[str, str]]:
    return {
        "ci.owner": (
            "owner_mapping",
            _mapping(
                "owner_code", "owner_text", "2\tPrivate industry workers\t0\tT\t2\n"
            ),
        ),
        "ci.industry": (
            "industry_mapping",
            _mapping(
                "industry_code", "industry_text", "230000\tConstruction\t2\tT\t9\n"
            ),
        ),
        "ci.occupation": (
            "occupation_mapping",
            _mapping(
                "occupation_code",
                "occupation_text",
                "000000\tAll occupations\t0\tT\t1\n",
            ),
        ),
        "ci.subcell": (
            "subcell_mapping",
            _mapping("subcell_code", "subcell_text", "00\tAll workers\t0\tT\t1\n"),
        ),
        "ci.area": (
            "area_mapping",
            _mapping(
                "area_code", "area_text", "99999\tUnited States (National)\t0\tT\t1\n"
            ),
        ),
        "ci.estimate": (
            "estimate_mapping",
            _mapping(
                "estimate_code", "estimate_text", "01\tTotal compensation\t0\tT\t1\n"
            ),
        ),
        "ci.series": ("series_metadata", SERIES_HEADER + series),
        "ci.data.0.Current": ("current", DATA_HEADER + data),
    }


def write_manifest(root: Path, files: dict[str, tuple[str, str]]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    entries = []
    for name, (role, body) in files.items():
        raw = body.encode("utf-8")
        (root / name).write_bytes(raw)
        entries.append(
            {
                "path": name,
                "role": role,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size_bytes": len(raw),
            }
        )
    path = root / "ci.json"
    path.write_text(
        json.dumps({"schema_version": 1, "program": "ci", "files": entries})
    )
    return path


def pc_manifest(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    files = {
        "pc.industry.txt": (
            "industry_mapping",
            "industry_code\tindustry_name\n334---\tMachinery\n",
        ),
        "pc.product": (
            "product_mapping",
            "industry_code\tproduct_code\tproduct_name\n334---\t334---\tOutput\n",
        ),
        "pc.series": (
            "series_metadata",
            "series_id\tindustry_code\tproduct_code\tseasonal\tbase_date\t"
            "series_title\tfootnote_codes\tbegin_year\tbegin_period\t"
            "end_year\tend_period\n"
            "PCU334---334---\t334---\t334---\tU\t200012\tMachinery PPI\t\t"
            "2000\tM01\t2026\tM12\n",
        ),
        "pc.data.0.Current": (
            "current",
            DATA_HEADER + "PCU334---334---\t2025\tM12\t110.0\t\n",
        ),
    }
    entries = []
    for name, (role, body) in files.items():
        raw = body.encode("utf-8")
        (root / name).write_bytes(raw)
        entries.append(
            {"path": name, "role": role, "sha256": hashlib.sha256(raw).hexdigest()}
        )
    path = root / "pc.json"
    path.write_text(
        json.dumps({"schema_version": 1, "program": "pc", "files": entries})
    )
    return path


@pytest.fixture
def writer(tmp_path: Path):
    from datetime import UTC, datetime

    with build_connection(tmp_path / "candidate.duckdb") as conn:
        initialize_schema(conn)
        write_snapshot_info(conn, SnapshotInfo("ci_test", datetime.now(UTC), ("ci",)))
        yield conn


# --------------------------------------------------------------------------
# Manifest
# --------------------------------------------------------------------------


def test_manifest_orders_roles_and_verifies_bytes(tmp_path: Path):
    manifest = load_ci_manifest(write_manifest(tmp_path, ci_files()))
    assert [f.role for f in manifest.selected()] == [
        "owner_mapping",
        "industry_mapping",
        "occupation_mapping",
        "subcell_mapping",
        "area_mapping",
        "estimate_mapping",
        "series_metadata",
        "current",
    ]
    assert all(verify_ci_source(manifest.resolve(f), f) > 0 for f in manifest.files)


@pytest.mark.parametrize("missing", ["ci.owner", "ci.series", "ci.data.0.Current"])
def test_manifest_requires_every_mapping_series_and_data(tmp_path: Path, missing):
    files = ci_files()
    del files[missing]
    with pytest.raises(CIInputError):
        load_ci_manifest(write_manifest(tmp_path, files))


def test_manifest_rejects_wrong_filename_and_program(tmp_path: Path):
    files = ci_files()
    files["ci.areas"] = files.pop("ci.area")
    with pytest.raises(CIInputError, match="Unexpected filename"):
        load_ci_manifest(write_manifest(tmp_path / "a", files))
    path = write_manifest(tmp_path / "b", ci_files())
    document = json.loads(path.read_text())
    document["program"] = "cu"
    path.write_text(json.dumps(document))
    with pytest.raises(CIInputError, match="program 'ci'"):
        load_ci_manifest(path)


def test_tampered_bytes_fail_verification(tmp_path: Path):
    path = write_manifest(tmp_path, ci_files())
    (tmp_path / "ci.series").write_bytes(b"changed\n")
    manifest = load_ci_manifest(path)
    series = next(f for f in manifest.files if f.role == "series_metadata")
    with pytest.raises(CIInputError):
        verify_ci_source(manifest.resolve(series), series)


# --------------------------------------------------------------------------
# Ingestion
# --------------------------------------------------------------------------


def test_only_index_series_and_their_observations_are_loaded(writer, tmp_path):
    report = ingest_ci(writer, write_manifest(tmp_path / "raw", ci_files()))
    assert (report.series, report.excluded_series) == (1, 1)
    assert report.rows_read == 4
    assert report.excluded_rows == 1  # the percent-change row
    assert report.missing_rows == 1  # the "-" value
    assert report.observations == 2
    assert report.dimension_codes == 6
    catalog = writer.execute(
        "SELECT series_id, program_code, units, original_reference_base, "
        "seasonal_adjustment, first_period, last_period, active FROM series_catalog"
    ).fetchall()
    assert catalog == [
        (INDEX_SERIES, "ci", "index", "December 2005=100", False, "Q01", "Q02", True)
    ]
    rows = writer.execute(
        "SELECT year, period, value FROM observations ORDER BY year, period"
    ).fetchall()
    assert rows == [(2025, "Q04", 167.927), (2026, "Q01", 168.966)]
    assert writer.execute("SELECT periodicity_code FROM ci_series").fetchall() == [
        ("I",)
    ]


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        (f"{INDEX_SERIES}\t2026\tM01\t1.0\t\n", "Malformed CI observation"),
        (f"{INDEX_SERIES}\t2026\tQ05\t1.0\t\n", "Malformed CI observation"),
        (f"{INDEX_SERIES}\t2026\tQ01\tabc\t\n", "Malformed CI observation"),
        ("CIU9999999999999I\t2026\tQ01\t1.0\t\n", "unknown CI series"),
        (
            f"{INDEX_SERIES}\t2026\tQ01\t1.0\t\n{INDEX_SERIES}\t2026\tQ01\t2.0\t\n",
            "Conflicting CI observations",
        ),
        (f"{PERCENT_SERIES}\t2026\tQ01\t3.1\t\n", "no index observations"),
    ],
)
def test_bad_data_rolls_back_entire_ci_import(writer, tmp_path, data, expected):
    with pytest.raises(CIIngestError, match=expected):
        ingest_ci(writer, write_manifest(tmp_path / "raw", ci_files(data=data)))
    for table in ("series_catalog", "ci_series", "ci_dimension", "observations"):
        assert writer.execute(f"SELECT COUNT(*) FROM {table}").fetchone() == (0,)
    assert writer.execute("SELECT COUNT(*) FROM source_files").fetchone() == (0,)


@pytest.mark.parametrize(
    ("series", "expected"),
    [
        (SERIES_ROWS.replace("\t230000\t", "\t999999\t"), "Unknown CI industry"),
        (SERIES_ROWS.replace("\tU\t2\t", "\tU\t3\t"), "contradicts metadata"),
        (SERIES_ROWS.replace("2001\tQ01", "2001\tM01"), "Invalid CI series date"),
        (SERIES_ROWS.splitlines(keepends=True)[1], "no current-dollar index"),
    ],
)
def test_bad_series_metadata_is_rejected(writer, tmp_path, series, expected):
    with pytest.raises(CIIngestError, match=expected):
        ingest_ci(writer, write_manifest(tmp_path / "raw", ci_files(series=series)))


def test_identical_overlap_between_current_and_all_data_is_deduplicated(
    writer, tmp_path
):
    files = ci_files()
    files["ci.data.1.AllData"] = (
        "all_data",
        DATA_HEADER + DATA_ROWS + f"{INDEX_SERIES}\t2001\tQ01\t85.0\t\n",
    )
    report = ingest_ci(writer, write_manifest(tmp_path / "raw", files))
    assert report.identical_duplicates == 2
    assert report.observations == 3


def test_reingestion_is_refused(writer, tmp_path):
    manifest = write_manifest(tmp_path / "raw", ci_files())
    ingest_ci(writer, manifest)
    with pytest.raises(CIIngestError, match="already contains CI"):
        ingest_ci(writer, manifest)


# --------------------------------------------------------------------------
# Lifecycle, CLI and queries
# --------------------------------------------------------------------------


def test_ci_only_snapshot_validates_publishes_and_is_queryable(tmp_path: Path):
    manifest = write_manifest(tmp_path / "raw", ci_files())
    candidate = tmp_path / "c.duckdb"
    build_candidate(candidate, "ci_only", ci_manifest=manifest)
    report = validate_candidate(candidate, ci_manifest=manifest)
    assert report.passed, report.issues
    assert report.counts["ci_series"] == 1
    assert report.counts["ci_observations"] == 2
    registry = tmp_path / "registry"
    publish_candidate(candidate, registry)
    store = BLSStore(activate_snapshot(registry, "ci_only"))

    page = store.search_series(SeriesSearchFilters(query="construction"))
    assert [hit.series.series_id for hit in page.matches] == [INDEX_SERIES]
    classification = page.matches[0].classification
    assert isinstance(classification, CIClassification)
    assert classification.industry_name == "Construction"
    assert classification.estimate_name == "Total compensation"
    assert classification.area_name == "United States (National)"
    for filters in (
        SeriesSearchFilters(industry_code="230000"),
        SeriesSearchFilters(area_code="99999"),
        SeriesSearchFilters(periodicity_code="I"),
        SeriesSearchFilters(programs=("ci",)),
    ):
        assert store.search_series(filters).total_matches == 1
    assert store.search_series(SeriesSearchFilters(programs=("pc",))).total_matches == 0

    observations = store.get_observations([INDEX_SERIES]).observations
    assert [(o.year, o.period, o.value) for o in observations] == [
        (2025, "Q04", 167.927),
        (2026, "Q01", 168.966),
    ]
    metadata = SeriesCatalogService(store).get(INDEX_SERIES)
    assert metadata is not None
    assert (metadata.program, metadata.industry_code) == ("ci", "230000")
    assert metadata.occupation_code == "000000"
    assert metadata.latest_period is not None
    assert metadata.latest_period.quarter == 2


def test_mixed_pc_ci_snapshot_and_missing_ci_manifest_fails_validation(tmp_path):
    ci = write_manifest(tmp_path / "ci", ci_files())
    pc = pc_manifest(tmp_path / "pc")
    candidate = tmp_path / "mixed.duckdb"
    build = build_candidate(candidate, "mixed", pc_manifest=pc, ci_manifest=ci)
    assert build.programs == ("pc", "ci")
    report = validate_candidate(candidate, pc_manifest=pc, ci_manifest=ci)
    assert report.passed, report.issues
    assert report.counts["pc_observations"] == 1
    assert report.counts["ci_observations"] == 2

    other = tmp_path / "other.duckdb"
    build_candidate(other, "other", pc_manifest=pc, ci_manifest=ci)
    failed = validate_candidate(other, pc_manifest=pc)
    assert not failed.passed
    assert "every declared program" in failed.issues[0]


def test_cli_accepts_ci_manifest(tmp_path: Path, capsys):
    manifest = write_manifest(tmp_path / "raw", ci_files())
    candidate = tmp_path / "cli.duckdb"
    assert (
        main(
            [
                "build",
                "--candidate",
                str(candidate),
                "--snapshot-id",
                "cli_ci",
                "--ci-manifest",
                str(manifest),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["programs"] == ["ci"]
    assert (
        main(
            ["validate", "--candidate", str(candidate), "--ci-manifest", str(manifest)]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["passed"] is True


def test_checked_in_sample_manifest_builds_real_eci_files(tmp_path: Path):
    sample = Path(__file__).resolve().parents[4] / "src/bls_mcp/docs/sample_data"
    manifest = sample / "ci-sample-input.json"
    candidate = tmp_path / "sample.duckdb"
    build = build_candidate(candidate, "sample_ci", ci_manifest=manifest)
    eci = build.program_reports[0]
    assert eci.series == 506
    assert eci.series + eci.excluded_series == 2470
    assert eci.rows_read == eci.excluded_rows + eci.missing_rows + eci.observations
    assert eci.observations > 20_000
    assert validate_candidate(candidate, ci_manifest=manifest).passed
