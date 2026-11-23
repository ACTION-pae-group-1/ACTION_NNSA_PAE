"""Offline PC/CU/CI snapshot building, validation, and READY finalization.

A candidate is never served by the production query API. Validation requires
its original checksum-pinned input manifests, verifies the bytes again, checks
cross-table integrity, and checkpoints the closed READY database before writing
an auditable report. Failures leave a nonpublishable FAILED candidate.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import duckdb

from bls_mcp.ingestion.ci import CIIngestReport, ingest_ci
from bls_mcp.ingestion.ci_manifest import load_ci_manifest, verify_ci_source
from bls_mcp.ingestion.cu import CUIngestReport, ingest_cu
from bls_mcp.ingestion.cu_manifest import load_cu_manifest, verify_cu_source
from bls_mcp.ingestion.manifest import load_pc_manifest, verify_pc_source
from bls_mcp.ingestion.pc import PCIngestReport, ingest_pc
from bls_mcp.ingestion.wp import WPIngestReport, ingest_wp
from bls_mcp.ingestion.wp_manifest import load_wp_manifest, verify_wp_source
from bls_mcp.storage.connection import build_connection, snapshot_reader
from bls_mcp.storage.models import SnapshotInfo, SnapshotState, ValidationStatus
from bls_mcp.storage.schema import SCHEMA_VERSION, initialize_schema
from bls_mcp.storage.snapshots import (
    read_snapshot_info,
    read_source_files,
    write_snapshot_info,
)

if TYPE_CHECKING:
    from duckdb import DuckDBPyConnection


class SnapshotLifecycleError(ValueError):
    """A candidate cannot advance through the snapshot lifecycle."""


@dataclass(frozen=True, slots=True)
class BuildReport:
    snapshot_id: str
    candidate_path: str
    programs: tuple[str, ...]
    program_reports: tuple[
        PCIngestReport | CUIngestReport | CIIngestReport | WPIngestReport, ...
    ]


@dataclass(frozen=True, slots=True)
class ValidationReport:
    snapshot_id: str
    schema_version: int
    validated_at: str
    passed: bool
    counts: dict[str, int]
    issues: tuple[str, ...]
    candidate_sha256: str | None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sync_directory(path: Path) -> None:
    """Best-effort directory durability; Windows disallows directory fsync."""
    if os.name != "posix":
        return
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    """Replace one JSON file atomically after durable flush, on the same volume."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".bls-json-", suffix=".tmp", dir=path.parent)
    tmp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, sort_keys=True, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        _sync_directory(path.parent)
    finally:
        tmp.unlink(missing_ok=True)


def validation_report_path(candidate_path: str | Path) -> Path:
    path = Path(candidate_path)
    return path.with_name(path.name + ".validation.json")


def build_candidate(
    candidate_path: str | Path,
    snapshot_id: str,
    *,
    wp_manifest: str | Path | None = None,
    pc_manifest: str | Path | None = None,
    cu_manifest: str | Path | None = None,
    ci_manifest: str | Path | None = None,
    build_commit: str | None = None,
) -> BuildReport:
    """Build a brand-new candidate; never overwrite a previous file.

    On an ingestion error the failed, unpublished candidate is retained for
    inspection. Rebuild under a new filename after fixing the inputs.
    """
    manifests = {
        "pc": pc_manifest,
        "cu": cu_manifest,
        "ci": ci_manifest,
        "wp": wp_manifest,
    }
    programs = tuple(code for code, path in manifests.items() if path is not None)
    if not programs:
        raise SnapshotLifecycleError(
            "At least one PC, CU, CI or WP input manifest is required"
        )
    path = Path(candidate_path).resolve()
    reports: list[
        PCIngestReport | CUIngestReport | CIIngestReport | WPIngestReport
    ] = []
    with build_connection(path) as conn:
        initialize_schema(conn)
        write_snapshot_info(
            conn,
            SnapshotInfo(
                snapshot_id=snapshot_id,
                built_at=datetime.now(UTC),
                programs=programs,
                build_commit=build_commit,
            ),
        )
        if pc_manifest is not None:
            reports.append(ingest_pc(conn, pc_manifest))
        if cu_manifest is not None:
            reports.append(ingest_cu(conn, cu_manifest))
        if ci_manifest is not None:
            reports.append(ingest_ci(conn, ci_manifest))
        if wp_manifest is not None:
            reports.append(ingest_wp(conn, wp_manifest))
        conn.execute("CHECKPOINT")
    return BuildReport(snapshot_id, str(path), programs, tuple(reports))


def _transition(
    conn: DuckDBPyConnection, state: SnapshotState, status: ValidationStatus
) -> None:
    conn.execute("BEGIN TRANSACTION")
    try:
        conn.execute(
            "UPDATE snapshot_info SET lifecycle_state=?, validation_status=? "
            "WHERE singleton=1",
            [state.value, status.value],
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def _scalar(conn: DuckDBPyConnection, statement: str) -> int:
    row = conn.execute(statement).fetchone()
    if row is None:
        raise SnapshotLifecycleError("Integrity query returned no count")
    return int(row[0])


def _integrity(conn: DuckDBPyConnection, programs: tuple[str, ...]) -> dict[str, int]:
    """Fail closed on unresolved keys, classification gaps and missing ART."""
    counts = {
        "source_files": _scalar(conn, "SELECT COUNT(*) FROM source_files"),
        "series": _scalar(conn, "SELECT COUNT(*) FROM series_catalog"),
        "observations": _scalar(conn, "SELECT COUNT(*) FROM observations"),
        "pc_series": _scalar(conn, "SELECT COUNT(*) FROM pc_series"),
        "cu_series": _scalar(conn, "SELECT COUNT(*) FROM cu_series"),
        "ci_series": _scalar(conn, "SELECT COUNT(*) FROM ci_series"),
        "wp_series": _scalar(conn, "SELECT COUNT(*) FROM wp_series"),
    }
    if not counts["source_files"] or not counts["series"] or not counts["observations"]:
        raise SnapshotLifecycleError(
            "Snapshot is missing source receipts, series, or observations"
        )

    problems = {
        "duplicate observation keys": """SELECT COUNT(*) FROM (
            SELECT 1 FROM observations GROUP BY series_id, year, period
            HAVING COUNT(*) > 1)""",
        "orphan observations or source receipts": """SELECT COUNT(*) FROM observations o
            LEFT JOIN series_catalog c ON c.series_id=o.series_id
            LEFT JOIN source_files f ON f.source_file_id=o.source_file_id
            WHERE c.series_id IS NULL OR f.source_file_id IS NULL
               OR c.program_code <> f.program_code
               OR f.selection_role NOT IN ('historical','current','all_data')""",
        "invalid values or years": """SELECT COUNT(*) FROM observations
            WHERE NOT isfinite(value) OR year < 1 OR year IS NULL""",
        "observations outside catalog coverage": """SELECT COUNT(*)
            FROM observations o JOIN series_catalog c USING (series_id)
            WHERE (c.first_year IS NOT NULL AND o.year < c.first_year)
               OR (c.last_year IS NOT NULL AND o.year > c.last_year)""",
        "unmapped PC products": """SELECT COUNT(*) FROM pc_product p
            LEFT JOIN pc_industry i ON i.industry_code=p.industry_code
            WHERE i.industry_code IS NULL""",
        "unknown source program": """SELECT COUNT(*) FROM source_files
            WHERE program_code NOT IN ('pc','cu','ci','wp')""",
        "unknown catalog program": """SELECT COUNT(*) FROM series_catalog
            WHERE program_code NOT IN ('pc','cu','ci','wp')""",
        "unclassified PC series": """SELECT COUNT(*) FROM series_catalog c
            LEFT JOIN pc_series p ON c.series_id=p.series_id
            LEFT JOIN pc_industry i ON p.industry_code=i.industry_code
            LEFT JOIN pc_product prod ON prod.industry_code=p.industry_code
                 AND prod.product_code=p.product_code
            WHERE c.program_code='pc' AND (p.series_id IS NULL
                 OR i.industry_code IS NULL
                 OR (p.product_code IS NOT NULL AND prod.product_code IS NULL))""",
        "unclassified CU series": """SELECT COUNT(*) FROM series_catalog c
            LEFT JOIN cu_series u ON c.series_id=u.series_id
            LEFT JOIN cu_area a ON u.area_code=a.area_code
            LEFT JOIN cu_item i ON u.item_code=i.item_code
            WHERE c.program_code='cu' AND (u.series_id IS NULL
                 OR a.area_code IS NULL OR i.item_code IS NULL)""",
        "unclassified CI series": """SELECT COUNT(*) FROM series_catalog c
            LEFT JOIN ci_series e ON c.series_id=e.series_id
            LEFT JOIN ci_dimension ow ON ow.dimension='owner'
                 AND ow.code=e.owner_code
            LEFT JOIN ci_dimension ind ON ind.dimension='industry'
                 AND ind.code=e.industry_code
            LEFT JOIN ci_dimension occ ON occ.dimension='occupation'
                 AND occ.code=e.occupation_code
            LEFT JOIN ci_dimension sub ON sub.dimension='subcell'
                 AND sub.code=e.subcell_code
            LEFT JOIN ci_dimension ar ON ar.dimension='area'
                 AND ar.code=e.area_code
            LEFT JOIN ci_dimension est ON est.dimension='estimate'
                 AND est.code=e.estimate_code
            WHERE c.program_code='ci' AND (e.series_id IS NULL
                 OR ow.code IS NULL OR ind.code IS NULL OR occ.code IS NULL
                 OR sub.code IS NULL OR ar.code IS NULL OR est.code IS NULL)""",
        "dangling PC classification": """SELECT COUNT(*) FROM pc_series p
            LEFT JOIN series_catalog c ON c.series_id=p.series_id
            WHERE c.series_id IS NULL OR c.program_code<>'pc'""",
        "dangling CU classification": """SELECT COUNT(*) FROM cu_series u
            LEFT JOIN series_catalog c ON c.series_id=u.series_id
            WHERE c.series_id IS NULL OR c.program_code<>'cu'""",
        "unclassified WP series": """SELECT COUNT(*) FROM series_catalog c
            LEFT JOIN wp_series w ON w.series_id=c.series_id
            LEFT JOIN wp_group g ON g.group_code=w.group_code
            LEFT JOIN wp_item i ON i.group_code=w.group_code AND i.item_code=w.item_code
            WHERE c.program_code='wp' AND 
            (w.series_id IS NULL OR g.group_code IS NULL OR i.item_code IS NULL)""",
        "dangling WP classification": """SELECT COUNT(*) FROM wp_series w
            LEFT JOIN series_catalog c ON c.series_id=w.series_id
            WHERE c.series_id IS NULL OR c.program_code<>'wp'""",
        "wrong WP observation period": """SELECT COUNT(*) FROM observations o
            JOIN series_catalog c ON c.series_id=o.series_id WHERE c.program_code='wp'
            AND NOT regexp_full_match(o.period,'M(0[1-9]|1[0-3])')""",
        "dangling CI classification": """SELECT COUNT(*) FROM ci_series e
            LEFT JOIN series_catalog c ON c.series_id=e.series_id
            WHERE c.series_id IS NULL OR c.program_code<>'ci'""",
        "wrong CI observation period": """SELECT COUNT(*) FROM observations o
            JOIN series_catalog c ON c.series_id=o.series_id
            WHERE c.program_code='ci'
              AND NOT regexp_full_match(o.period, 'Q0[1-4]')""",
        "wrong PC observation period": """SELECT COUNT(*) FROM observations o
            JOIN series_catalog c ON c.series_id=o.series_id
            WHERE c.program_code='pc'
              AND NOT regexp_full_match(o.period, 'M(0[1-9]|1[0-3])')""",
        "wrong CU observation period": """SELECT COUNT(*) FROM observations o
            JOIN series_catalog c ON c.series_id=o.series_id
            JOIN cu_series u ON u.series_id=o.series_id
            WHERE c.program_code='cu'
              AND (
                   (u.periodicity_code='R'
                    AND NOT regexp_full_match(o.period, 'M(0[1-9]|1[0-3])'))
                OR (u.periodicity_code='S'
                    AND NOT regexp_full_match(o.period, 'S0[1-3]'))
                OR u.periodicity_code NOT IN ('R','S'))""",
    }
    for description, statement in problems.items():
        count = _scalar(conn, statement)
        if count:
            raise SnapshotLifecycleError(f"{description}: {count}")

    rows = conn.execute(
        "SELECT program_code, COUNT(*) FROM series_catalog GROUP BY program_code"
    ).fetchall()
    catalog_programs = {str(code): int(count) for code, count in rows}
    rows = conn.execute(
        "SELECT c.program_code, COUNT(*) FROM observations o "
        "JOIN series_catalog c ON o.series_id=c.series_id GROUP BY c.program_code"
    ).fetchall()
    observation_programs = {str(code): int(count) for code, count in rows}
    receipt_programs = {
        str(code): int(count)
        for code, count in conn.execute(
            "SELECT program_code, COUNT(*) FROM source_files GROUP BY program_code"
        ).fetchall()
    }
    if (
        set(catalog_programs) != set(programs)
        or set(observation_programs) != set(programs)
        or set(receipt_programs) != set(programs)
    ):
        raise SnapshotLifecycleError(
            "Declared programs differ from loaded data and receipts"
        )
    for code in programs:
        classification = counts[f"{code}_series"]
        if classification != catalog_programs[code]:
            raise SnapshotLifecycleError(f"Incomplete {code} series classifications")
        counts[f"{code}_observations"] = observation_programs[code]
        counts[f"{code}_source_files"] = receipt_programs[code]

    indexes = conn.execute(
        "SELECT sql, is_unique FROM duckdb_indexes() "
        "WHERE table_name='observations' AND index_name='observations_series_id_art'"
    ).fetchall()
    if (
        len(indexes) != 1
        or indexes[0][1]
        or "series_id" not in str(indexes[0][0]).lower()
    ):
        raise SnapshotLifecycleError(
            "Required observations(series_id) ART index missing"
        )
    return counts


def _sort_and_reindex(conn: DuckDBPyConnection) -> None:
    """Finalize global cross-program row order and rebuild the ART once, atomically.

    Separate per-program loaders append sorted runs; a mixed candidate needs
    one final global sort before publication. Recreate the finite-value CHECK
    rather than using CTAS, which would silently discard column constraints.
    """
    conn.execute("BEGIN TRANSACTION")
    try:
        conn.execute(
            """CREATE TABLE _final_observations (
                series_id VARCHAR NOT NULL,
                year SMALLINT NOT NULL,
                period VARCHAR NOT NULL,
                value DOUBLE NOT NULL CHECK (isfinite(value)),
                footnote_codes VARCHAR,
                source_file_id BIGINT NOT NULL
            )"""
        )
        conn.execute(
            """INSERT INTO _final_observations
            SELECT series_id, year, period, value, footnote_codes, source_file_id
            FROM observations ORDER BY series_id, year, period"""
        )
        # DuckDB disallows some ALTER operations while an ART depends on a table.
        conn.execute("DROP INDEX observations_series_id_art")
        conn.execute("DROP TABLE observations")
        conn.execute("ALTER TABLE _final_observations RENAME TO observations")
        conn.execute(
            "CREATE INDEX observations_series_id_art ON observations (series_id)"
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def _verify_manifests(
    conn: DuckDBPyConnection,
    programs: tuple[str, ...],
    pc_manifest: str | Path | None,
    cu_manifest: str | Path | None,
    ci_manifest: str | Path | None,
    wp_manifest: str | Path | None,
) -> None:
    supplied = {
        code
        for code, path in (
            ("pc", pc_manifest),
            ("cu", cu_manifest),
            ("ci", ci_manifest),
            ("wp", wp_manifest),
        )
        if path is not None
    }
    if supplied != set(programs):
        raise SnapshotLifecycleError(
            "Provide one source manifest for every declared program"
        )
    expected: set[tuple[str, str, str, str, int]] = set()
    if pc_manifest is not None:
        pc = load_pc_manifest(pc_manifest)
        for pc_source in pc.selected():
            size = verify_pc_source(pc.resolve(pc_source), pc_source)
            expected.add(
                ("pc", pc_source.path, pc_source.role, pc_source.sha256.lower(), size)
            )
    if cu_manifest is not None:
        cu = load_cu_manifest(cu_manifest)
        for cu_source in cu.selected():
            size = verify_cu_source(cu.resolve(cu_source), cu_source)
            expected.add(
                ("cu", cu_source.path, cu_source.role, cu_source.sha256.lower(), size)
            )
    if ci_manifest is not None:
        ci = load_ci_manifest(ci_manifest)
        for ci_source in ci.selected():
            size = verify_ci_source(ci.resolve(ci_source), ci_source)
            expected.add(
                ("ci", ci_source.path, ci_source.role, ci_source.sha256.lower(), size)
            )
    if wp_manifest is not None:
        wp = load_wp_manifest(wp_manifest)
        for source in wp.selected():
            size = verify_wp_source(wp.resolve(source), source)
            expected.add(("wp", source.path, source.role, source.sha256.lower(), size))
    receipts = read_source_files(conn)
    actual = {
        (r.program_code, r.filename, r.selection_role, r.sha256.lower(), r.size_bytes)
        for r in receipts
    }
    if len(actual) != len(receipts) or actual != expected:
        raise SnapshotLifecycleError(
            "Source receipts differ from pinned, verified manifests"
        )


def validate_candidate(
    candidate_path: str | Path,
    *,
    wp_manifest: str | Path | None = None,
    pc_manifest: str | Path | None = None,
    cu_manifest: str | Path | None = None,
    ci_manifest: str | Path | None = None,
) -> ValidationReport:
    """Validate and finalize BUILDING -> VALIDATING -> READY or FAILED.

    A FAILED candidate is terminal: repair the inputs and build a new one.
    The JSON report is adjacent to the candidate and includes the hash of the
    checkpointed, closed READY database. Publication requires this report.
    """
    path = Path(candidate_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    counts: dict[str, int] = {}
    issues: tuple[str, ...] = ()
    with closing(duckdb.connect(str(path), read_only=False)) as conn:
        info = read_snapshot_info(conn)
        if (
            info.lifecycle_state is not SnapshotState.BUILDING
            or info.validation_status is not ValidationStatus.NOT_RUN
        ):
            raise SnapshotLifecycleError(
                "Only an unvalidated BUILDING candidate can be validated"
            )
        _transition(conn, SnapshotState.VALIDATING, ValidationStatus.NOT_RUN)
        try:
            _verify_manifests(
                conn, info.programs, pc_manifest, cu_manifest, ci_manifest, wp_manifest
            )
            counts = _integrity(conn, info.programs)
            _sort_and_reindex(conn)
            if _integrity(conn, info.programs) != counts:
                raise SnapshotLifecycleError("Final sort changed validated row counts")
            _transition(conn, SnapshotState.READY, ValidationStatus.PASSED)
            conn.execute("CHECKPOINT")
        except Exception as exc:
            issues = (f"{type(exc).__name__}: {exc}",)
            _transition(conn, SnapshotState.VALIDATING, ValidationStatus.FAILED)
            conn.execute("CHECKPOINT")
    if not issues:
        try:
            with snapshot_reader(path, require_published=False) as conn:
                reopened = read_snapshot_info(conn)
                if (
                    reopened.lifecycle_state is not SnapshotState.READY
                    or reopened.validation_status is not ValidationStatus.PASSED
                    or reopened.snapshot_id != info.snapshot_id
                ):
                    raise SnapshotLifecycleError(
                        "READY candidate failed read-only reopen"
                    )
                if _integrity(conn, reopened.programs) != counts:
                    raise SnapshotLifecycleError(
                        "Candidate counts changed after reopening"
                    )
        except Exception as exc:
            issues = (f"{type(exc).__name__}: {exc}",)
            with closing(duckdb.connect(str(path), read_only=False)) as conn:
                _transition(conn, SnapshotState.VALIDATING, ValidationStatus.FAILED)
                conn.execute("CHECKPOINT")
    digest = sha256_file(path) if not issues else None
    report = ValidationReport(
        snapshot_id=info.snapshot_id,
        schema_version=SCHEMA_VERSION,
        validated_at=datetime.now(UTC).isoformat(),
        passed=not issues,
        counts=counts,
        issues=issues,
        candidate_sha256=digest,
    )
    write_json_atomic(validation_report_path(path), report.as_dict())
    return report
