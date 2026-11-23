"""No network or DuckDB required for selection and source integrity tests."""

import hashlib
import json
from pathlib import Path

import pytest

from bls_mcp.ingestion.manifest import PCInputError, load_pc_manifest, verify_pc_source


@pytest.fixture
def selection(tmp_path: Path) -> tuple[Path, list[dict[str, object]]]:
    entries: list[dict[str, object]] = []
    for name, role, header in (
        ("pc.industry.txt", "industry_mapping", "industry_code\tindustry_name"),
        (
            "pc.product",
            "product_mapping",
            "industry_code\tproduct_code\tproduct_name",
        ),
        (
            "pc.series",
            "series_metadata",
            "series_id\tindustry_code\tproduct_code\tseasonal\tbase_date\t"
            "series_title\tfootnote_codes\tbegin_year\tbegin_period\t"
            "end_year\tend_period",
        ),
        (
            "pc.data.0.Current",
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
    path = tmp_path / "pc-selection.json"
    path.write_text(
        json.dumps({"schema_version": 1, "program": "pc", "files": entries})
    )
    return path, entries


def _rewrite(path: Path, entries: list[dict[str, object]]) -> None:
    path.write_text(
        json.dumps({"schema_version": 1, "program": "pc", "files": entries})
    )


def test_manifest_selects_and_verifies_pinned_files(selection):
    path, _ = selection
    manifest = load_pc_manifest(path)
    assert [f.role for f in manifest.selected()] == [
        "industry_mapping",
        "product_mapping",
        "series_metadata",
        "current",
    ]
    assert all(
        verify_pc_source(manifest.resolve(entry), entry) > 0 for entry in manifest.files
    )


def test_checksum_and_length_mismatch_are_fatal(selection):
    path, entries = selection
    manifest = load_pc_manifest(path)
    source = manifest.selected()[0]
    source_path = manifest.resolve(source)
    source_path.write_text("industry_code\tindustry_name\nCHANGED\tName\n")
    with pytest.raises(PCInputError, match="SHA-256"):
        verify_pc_source(source_path, source)
    entries[0]["sha256"] = hashlib.sha256(source_path.read_bytes()).hexdigest()
    _rewrite(path, entries)
    with pytest.raises(PCInputError, match="Byte size"):
        verify_pc_source(source_path, load_pc_manifest(path).selected()[0])


def test_header_mismatch_is_fatal_even_with_matching_checksum(selection):
    path, entries = selection
    source_path = path.parent / "pc.data.0.Current"
    raw = b"wrong\theader\n"
    source_path.write_bytes(raw)
    entries[3]["sha256"] = hashlib.sha256(raw).hexdigest()
    entries[3]["size_bytes"] = len(raw)
    _rewrite(path, entries)
    with pytest.raises(PCInputError, match="header"):
        verify_pc_source(source_path, load_pc_manifest(path).selected()[3])


@pytest.mark.parametrize(
    "removed", ["industry_mapping", "product_mapping", "series_metadata", "current"]
)
def test_required_files_are_explicit(selection, removed):
    path, entries = selection
    _rewrite(path, [row for row in entries if row["role"] != removed])
    with pytest.raises(PCInputError, match="Require one|At least one"):
        load_pc_manifest(path)


def test_all_data_must_be_exclusive(selection):
    path, entries = selection
    copy = dict(entries[3])
    copy["path"] = "pc.data.AllData"
    copy["role"] = "all_data"
    (path.parent / str(copy["path"])).write_bytes(
        (path.parent / "pc.data.0.Current").read_bytes()
    )
    _rewrite(path, [*entries, copy])
    with pytest.raises(PCInputError, match="AllData"):
        load_pc_manifest(path)


def test_duplicate_paths_are_rejected(selection):
    path, entries = selection
    _rewrite(path, [*entries, dict(entries[3])])
    with pytest.raises(PCInputError, match="same path"):
        load_pc_manifest(path)


def test_path_traversal_and_windows_separator_are_rejected(selection):
    path, entries = selection
    entries[3]["path"] = "../elsewhere/pc.data.0.Current"
    _rewrite(path, entries)
    with pytest.raises(PCInputError, match="outside manifest root"):
        load_pc_manifest(path)
    # Windows and POSIX path separators must not be interpreted differently.
    entries[3]["path"] = "subdir\\pc.data.0.Current"
    _rewrite(path, entries)
    with pytest.raises(PCInputError, match="relative"):
        load_pc_manifest(path)


def test_unknown_manifest_fields_are_rejected(selection):
    path, entries = selection
    entries[3]["ignore_hash"] = True
    _rewrite(path, entries)
    with pytest.raises(PCInputError, match="unrecognized"):
        load_pc_manifest(path)
