"""CU selection/integrity tests; require neither internet nor DuckDB."""

import hashlib
import json
from pathlib import Path

import pytest

from bls_mcp.ingestion.cu_manifest import (
    CUInputError,
    load_cu_manifest,
    verify_cu_source,
)


@pytest.fixture
def selection(tmp_path: Path) -> tuple[Path, list[dict[str, object]]]:
    entries: list[dict[str, object]] = []
    for name, role, header in (
        (
            "cu.area",
            "area_mapping",
            "area_code\tarea_name\tdisplay_level\tselectable\tsort_sequence",
        ),
        (
            "cu.item",
            "item_mapping",
            "item_code\titem_name\tdisplay_level\tselectable\tsort_sequence",
        ),
        (
            "cu.series",
            "series_metadata",
            "series_id\tarea_code\titem_code\tseasonal\tperiodicity_code\t"
            "base_code\tbase_period\tseries_title\tfootnote_codes\t"
            "begin_year\tbegin_period\tend_year\tend_period",
        ),
        (
            "cu.data.0.Current",
            "current",
            "series_id\tyear\tperiod\tvalue\tfootnote_codes",
        ),
    ):
        raw = (header + "\r\n").encode()
        (tmp_path / name).write_bytes(raw)
        entries.append(
            {
                "path": name,
                "role": role,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size_bytes": len(raw),
            }
        )
    manifest = tmp_path / "cu.json"
    _rewrite(manifest, entries)
    return manifest, entries


def _rewrite(path: Path, entries: list[dict[str, object]]) -> None:
    path.write_text(
        json.dumps({"schema_version": 1, "program": "cu", "files": entries}),
        encoding="utf-8",
    )


def test_selection_is_deterministic_and_verified(selection):
    path, _ = selection
    record = load_cu_manifest(path)
    assert [x.role for x in record.selected()] == [
        "area_mapping",
        "item_mapping",
        "series_metadata",
        "current",
    ]
    assert all(verify_cu_source(record.resolve(x), x) > 0 for x in record.files)


def test_cu_area_published_header_requires_selectable(selection):
    manifest_path, entries = selection
    area = manifest_path.parent / "cu.area"
    raw = area.read_bytes().replace(
        b"display_level\tselectable\tsort_sequence",
        b"display_level\tsort_sequence",
    )
    area.write_bytes(raw)
    for item in entries:
        if item["path"] == "cu.area":
            item["sha256"] = hashlib.sha256(raw).hexdigest()
            item["size_bytes"] = len(raw)
    _rewrite(manifest_path, entries)
    record = load_cu_manifest(manifest_path)
    with pytest.raises(CUInputError, match="area_mapping header"):
        verify_cu_source(record.resolve(record.files[0]), record.files[0])


def test_current_and_multiple_explicit_historical_sources(selection):
    path, entries = selection
    for filename in ("cu.data.10.OtherWest", "cu.data.1.AllItems"):
        raw = ("series_id\tyear\tperiod\tvalue\tfootnote_codes\n").encode()
        (path.parent / filename).write_bytes(raw)
        entries.append(
            {
                "path": filename,
                "role": "historical",
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size_bytes": len(raw),
            }
        )
    _rewrite(path, list(reversed(entries)))
    assert [x.path for x in load_cu_manifest(path).selected()][3:] == [
        "cu.data.1.AllItems",
        "cu.data.10.OtherWest",
        "cu.data.0.Current",
    ]


def test_bad_hash_and_size_are_not_ignored(selection):
    path, entries = selection
    source = path.parent / "cu.item"
    source.write_bytes(source.read_bytes() + b"SA0\tAll items\t0\tT\t1\n")
    with pytest.raises(CUInputError, match="SHA-256"):
        manifest = load_cu_manifest(path)
        verify_cu_source(manifest.resolve(manifest.files[1]), manifest.files[1])
    entries[1]["sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    _rewrite(path, entries)
    with pytest.raises(CUInputError, match="Byte size"):
        manifest = load_cu_manifest(path)
        verify_cu_source(manifest.resolve(manifest.files[1]), manifest.files[1])


def test_wrong_header_rejected_even_with_correct_checksum(selection):
    path, entries = selection
    raw = b"series_id\tvalue\n"
    (path.parent / "cu.data.0.Current").write_bytes(raw)
    entries[3]["sha256"] = hashlib.sha256(raw).hexdigest()
    entries[3]["size_bytes"] = len(raw)
    _rewrite(path, entries)
    manifest = load_cu_manifest(path)
    with pytest.raises(CUInputError, match="header"):
        verify_cu_source(manifest.resolve(manifest.files[3]), manifest.files[3])


def test_empty_trailing_header_tabs_are_tolerated(selection):
    path, entries = selection
    source = path.parent / "cu.item"
    source.write_bytes(source.read_bytes().rstrip(b"\r\n") + b"\t\t\r\n")
    raw = source.read_bytes()
    entries[1]["sha256"] = hashlib.sha256(raw).hexdigest()
    entries[1]["size_bytes"] = len(raw)
    _rewrite(path, entries)
    record = load_cu_manifest(path)
    assert verify_cu_source(record.resolve(record.files[1]), record.files[1]) == len(
        raw
    )


@pytest.mark.parametrize(
    "role", ["area_mapping", "item_mapping", "series_metadata", "current"]
)
def test_required_sources_are_explicit(selection, role):
    path, entries = selection
    _rewrite(path, [item for item in entries if item["role"] != role])
    with pytest.raises(CUInputError, match="Require exactly one|At least one"):
        load_cu_manifest(path)


def test_duplicate_selection_is_rejected(selection):
    path, entries = selection
    _rewrite(path, [*entries, dict(entries[3])])
    with pytest.raises(CUInputError, match="same path"):
        load_cu_manifest(path)


@pytest.mark.parametrize(
    "bad", ["../outside/cu.area", "nested\\cu.area", "/abs/cu.area"]
)
def test_bad_paths_are_rejected(selection, bad):
    path, entries = selection
    entries[0]["path"] = bad
    _rewrite(path, entries)
    with pytest.raises(CUInputError, match="outside manifest root|relative"):
        load_cu_manifest(path)


def test_unexpected_manifest_fields_and_roles_are_rejected(selection):
    path, entries = selection
    entries[0]["skip_hash"] = True
    _rewrite(path, entries)
    with pytest.raises(CUInputError, match="Invalid fields"):
        load_cu_manifest(path)
    del entries[0]["skip_hash"]
    entries[0]["role"] = "all_data"
    _rewrite(path, entries)
    with pytest.raises(CUInputError, match="Invalid path"):
        load_cu_manifest(path)


def test_data_partition_roles_are_not_interchangeable(selection):
    path, entries = selection
    entries[3]["role"] = "historical"
    _rewrite(path, entries)
    with pytest.raises(CUInputError, match="historical"):
        load_cu_manifest(path)
    entries[3]["role"] = "current"
    entries[3]["path"] = "cu.data.1.AllItems"
    _rewrite(path, entries)
    with pytest.raises(CUInputError, match="filename"):
        load_cu_manifest(path)
