"""Offline, bounded-memory overlap audit of checksum-pinned PC/CU source files.

The audit is diagnostic, not a replacement for ingestion validation. It never
modifies source files, rewrites manifests, or contacts BLS. An external merge
sort avoids storing an entire historical archive in Python memory.
"""

from __future__ import annotations

import heapq
import itertools
import json
import math
import os
import re
import tempfile
from contextlib import ExitStack
from pathlib import Path
from typing import Iterator

Row = tuple[str, int, str, float, str, str]
_SORT_ROWS = 100_000
_OPEN_FILES = 32
_MONTHLY = re.compile(r"M(0[1-9]|1[0-3])\Z")
_CU_SEMIANNUAL = re.compile(r"S0[1-3]\Z")
_DATA_ROLES = {"historical", "current", "all_data"}


class OverlapAuditError(ValueError):
    """An offline overlap audit cannot be completed safely."""


def _key(row: Row) -> tuple[str, int, str]:
    return row[0], row[1], row[2]


def _verified_sources(manifest: Path) -> tuple[str, list[tuple[str, Path]]]:
    """Require the same file hashes and headers as the PC/CU ingestion layer."""
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        program = data["program"]
        result: list[tuple[str, Path]] = []
        if program == "pc":
            from bls_mcp.ingestion.manifest import (
                load_pc_manifest,
                verify_pc_source,
            )

            pc_selection = load_pc_manifest(manifest)
            for pc_source in pc_selection.selected():
                pc_path = pc_selection.resolve(pc_source)
                verify_pc_source(pc_path, pc_source)
                if pc_source.role in _DATA_ROLES:
                    result.append((pc_source.path, pc_path))
        elif program == "cu":
            from bls_mcp.ingestion.cu_manifest import (
                load_cu_manifest,
                verify_cu_source,
            )

            cu_selection = load_cu_manifest(manifest)
            for cu_source in cu_selection.selected():
                cu_path = cu_selection.resolve(cu_source)
                verify_cu_source(cu_path, cu_source)
                if cu_source.role in _DATA_ROLES:
                    result.append((cu_source.path, cu_path))
        else:
            raise OverlapAuditError("Audit requires a PC or CU input manifest")
        return program, result
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise OverlapAuditError(f"Cannot verify pinned audit inputs: {exc}") from exc


def _data_rows(
    program: str,
    sources: list[tuple[str, Path]],
    stats: dict[str, int],
) -> Iterator[Row]:
    for name, path in sources:
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as source:
                header = source.readline()
                if tuple(
                    part.strip() for part in header.rstrip("\r\n").split("\t")
                ) != ("series_id", "year", "period", "value", "footnote_codes"):
                    raise OverlapAuditError(f"Unexpected BLS data header: {name}")
                for line_number, line in enumerate(source, start=2):
                    if not line.strip():
                        continue
                    parts = [part.strip() for part in line.rstrip("\r\n").split("\t")]
                    while len(parts) > 5 and parts[-1] == "":
                        parts.pop()
                    if len(parts) != 5:
                        raise OverlapAuditError(
                            f"Malformed data columns: {name}:{line_number}"
                        )
                    series, year_text, period, value_text, footnotes = parts
                    stats["rows_read"] += 1
                    try:
                        year = int(year_text)
                    except ValueError as exc:
                        raise OverlapAuditError(
                            f"Invalid BLS observation year: {name}:{line_number}"
                        ) from exc
                    if (
                        not series
                        or not 1 <= year <= 32767
                        or not (
                            _MONTHLY.fullmatch(period)
                            or (program == "cu" and _CU_SEMIANNUAL.fullmatch(period))
                        )
                    ):
                        raise OverlapAuditError(
                            f"Invalid BLS observation: {name}:{line_number}"
                        )
                    if value_text in {"", "-"}:
                        stats["missing_rows"] += 1
                        continue
                    try:
                        value = float(value_text)
                    except ValueError as exc:
                        raise OverlapAuditError(
                            f"Invalid BLS observation value: {name}:{line_number}"
                        ) from exc
                    if not math.isfinite(value):
                        raise OverlapAuditError(
                            f"Invalid BLS observation value: {name}:{line_number}"
                        )
                    # DuckDB DOUBLE considers -0.0 equal to +0.0.
                    if value == 0.0:
                        value = 0.0
                    yield series, year, period, value, footnotes, name
        except (OSError, UnicodeError) as exc:
            raise OverlapAuditError(f"Cannot scan BLS data file: {path}") from exc


def _read_stream(stream: Iterator[str]) -> Iterator[Row]:
    for line in stream:
        row = json.loads(line)
        yield row[0], row[1], row[2], row[3], row[4], row[5]


def _merged_chunks(paths: list[Path]) -> Iterator[Row]:
    with ExitStack() as stack:
        # File handles remain open only for the duration of this merge.
        readers = []
        for path in paths:
            stream = stack.enter_context(path.open("r", encoding="utf-8"))
            readers.append(_read_stream(stream))
        yield from heapq.merge(*readers, key=_key)


def _write_chunk(path: Path, rows: Iterator[Row]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as out:
        for row in rows:
            out.write(json.dumps(row, ensure_ascii=True, separators=(",", ":")))
            out.write("\n")


def _sort_to_chunks(rows: Iterator[Row], scratch: Path, chunk_size: int) -> list[Path]:
    paths: list[Path] = []
    chunk: list[Row] = []
    for row in rows:
        chunk.append(row)
        if len(chunk) == chunk_size:
            chunk.sort(key=_key)
            path = scratch / f"chunk-{len(paths):06d}.jsonl"
            _write_chunk(path, iter(chunk))
            paths.append(path)
            chunk.clear()
    if chunk:
        chunk.sort(key=_key)
        path = scratch / f"chunk-{len(paths):06d}.jsonl"
        _write_chunk(path, iter(chunk))
        paths.append(path)
    return paths


def _sorted_rows(paths: list[Path], scratch: Path, max_open: int) -> Iterator[Row]:
    generation = 0
    while len(paths) > max_open:
        generation += 1
        new_paths: list[Path] = []
        for offset in range(0, len(paths), max_open):
            batch = paths[offset : offset + max_open]
            merged = scratch / f"merged-{generation}-{offset:06d}.jsonl"
            _write_chunk(merged, _merged_chunks(batch))
            new_paths.append(merged)
            for path in batch:
                path.unlink()
        paths = new_paths
    yield from _merged_chunks(paths)


def _summarize(sorted_rows: Iterator[Row], stats: dict[str, int]) -> dict[str, object]:
    duplicate_samples: list[dict[str, object]] = []
    conflict_samples: list[dict[str, object]] = []
    overlap_count = 0
    identical_count = 0
    conflict_count = 0
    unique_count = 0
    for (series, year, period), group in itertools.groupby(sorted_rows, _key):
        first = next(group)
        count = 1
        mismatches = 0
        sources = {first[5]}
        conflicting_row = None
        for row in group:
            count += 1
            sources.add(row[5])
            if (row[3], row[4]) != (first[3], first[4]):
                mismatches += 1
                if conflicting_row is None:
                    conflicting_row = row
            else:
                identical_count += 1
        unique_count += 1
        if count <= 1:
            continue
        overlap_count += 1
        example: dict[str, object] = {
            "series_id": series,
            "year": year,
            "period": period,
            "sources": sorted(sources),
            "copies": count,
            "conflict": mismatches > 0,
        }
        if mismatches:
            conflict_count += 1
            if len(conflict_samples) < 5:
                assert conflicting_row is not None
                example["first"] = {
                    "source": first[5],
                    "value": first[3],
                    "footnotes": first[4],
                }
                example["other"] = {
                    "source": conflicting_row[5],
                    "value": conflicting_row[3],
                    "footnotes": conflicting_row[4],
                }
                conflict_samples.append(example)
        elif len(duplicate_samples) < 5:
            duplicate_samples.append(example)
    stats["valid_rows"] = stats["rows_read"] - stats["missing_rows"]
    return {
        **stats,
        "unique_keys": unique_count,
        "overlapping_keys": overlap_count,
        "identical_duplicate_rows": identical_count,
        "conflicting_keys": conflict_count,
        "result": (
            "EMPTY_DATA"
            if stats["rows_read"] == 0
            else "FAIL_CONFLICTS"
            if conflict_count
            else "PASS_IDENTICAL_OVERLAP"
            if overlap_count
            else "PASS_NO_OVERLAP"
        ),
        "examples": [*conflict_samples, *duplicate_samples],
    }


def _write_report(path: Path, report: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".bls-audit-", dir=path.parent)
    temp = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as out:
            json.dump(report, out, indent=2, sort_keys=True)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def audit_manifest(
    manifest_path: str | Path,
    *,
    scratch_dir: Path | None = None,
    chunk_size: int = _SORT_ROWS,
    max_open: int = _OPEN_FILES,
) -> tuple[Path, dict[str, object]]:
    """Verify and audit pinned files; persist success or failure diagnostics.

    The in-memory bound is `chunk_size` rows; intermediate sort files can be
    substantial for full archives. The report is NOT a waiver for ingestion.
    """
    if chunk_size <= 0 or max_open < 2:
        raise OverlapAuditError("Invalid audit sort limits")
    manifest = Path(manifest_path)
    report_path = manifest.parent / "reports" / f"{manifest.name}.overlaps.json"
    stats = {"rows_read": 0, "missing_rows": 0}
    phase = "verify_sources"
    program: str | None = None
    sources: list[tuple[str, Path]] = []
    try:
        program, sources = _verified_sources(manifest)
        phase = "scan_observations"
        with tempfile.TemporaryDirectory(
            prefix="bls-overlap-", dir=scratch_dir
        ) as workspace:
            scratch = Path(workspace)
            chunks = _sort_to_chunks(
                _data_rows(program, sources, stats), scratch, chunk_size
            )
            report = _summarize(_sorted_rows(chunks, scratch, max_open), stats)
        phase = "reverify_sources"
        # Verify that original pinned bytes did not change while scanning.
        _verified_sources(manifest)
    except Exception as exc:
        # Do not lose the diagnostic report when a source fails verification
        # before scanning starts. Never replace a checksum failure with PASS.
        failure: dict[str, object] = {
            "result": "FAIL_AUDIT_ERROR",
            "phase": phase,
            "error": str(exc),
            "program": program,
            "manifest": str(manifest.resolve()),
            "source_files": [name for name, _ in sources],
            **stats,
        }
        try:
            _write_report(report_path, failure)
        except OSError as report_exc:
            raise OverlapAuditError(
                f"Overlap audit failed during {phase}: {exc}; "
                f"also cannot write diagnostic report: {report_path}"
            ) from report_exc
        if isinstance(exc, OverlapAuditError):
            raise
        raise OverlapAuditError(f"Overlap audit failed during {phase}: {exc}") from exc

    report.update(
        {
            "program": program,
            "manifest": str(manifest.resolve()),
            "source_files": [name for name, _ in sources],
        }
    )
    try:
        _write_report(report_path, report)
    except OSError as exc:
        raise OverlapAuditError(f"Cannot write audit report: {report_path}") from exc
    return report_path, report
