"""Checksum-pinned CI (Employment Cost Index) source selection for DuckDB builds.

Mirrors the PC and CU manifests: every input is named explicitly and pinned by
SHA-256, and nothing is inferred from a directory listing. ``ci.data.0.Current``
is a subset of ``ci.data.1.AllData``; either or both may be selected, and the
loader reconciles identical overlaps and rejects conflicting ones.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

CIFileRole = Literal[
    "owner_mapping",
    "industry_mapping",
    "occupation_mapping",
    "subcell_mapping",
    "area_mapping",
    "estimate_mapping",
    "series_metadata",
    "current",
    "all_data",
]

#: Mapping role -> (dimension name, code column, text column, required filename).
CI_DIMENSIONS: dict[str, tuple[str, str, str, str]] = {
    "owner_mapping": ("owner", "owner_code", "owner_text", "ci.owner"),
    "industry_mapping": ("industry", "industry_code", "industry_text", "ci.industry"),
    "occupation_mapping": (
        "occupation",
        "occupation_code",
        "occupation_text",
        "ci.occupation",
    ),
    "subcell_mapping": ("subcell", "subcell_code", "subcell_text", "ci.subcell"),
    "area_mapping": ("area", "area_code", "area_text", "ci.area"),
    "estimate_mapping": ("estimate", "estimate_code", "estimate_text", "ci.estimate"),
}
CI_SERIES_HEADER = (
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
CI_DATA_ROLES = ("current", "all_data")
_DATA_HEADER = ("series_id", "year", "period", "value", "footnote_codes")
_DATA_NAMES = {"current": "ci.data.0.Current", "all_data": "ci.data.1.AllData"}
_REQUIRED: tuple[str, ...] = (*CI_DIMENSIONS, "series_metadata")
_SHA256 = re.compile(r"[a-fA-F0-9]{64}\Z")
_HEADERS: dict[str, tuple[str, ...]] = {
    **{
        role: (code, text, "display_level", "selectable", "sort_sequence")
        for role, (_, code, text, _name) in CI_DIMENSIONS.items()
    },
    "series_metadata": CI_SERIES_HEADER,
    "current": _DATA_HEADER,
    "all_data": _DATA_HEADER,
}
_ORDER = {role: index for index, role in enumerate(_HEADERS)}
_FIELDS = {
    "path",
    "role",
    "sha256",
    "size_bytes",
    "source_url",
    "etag",
    "last_modified",
}


class CIInputError(ValueError):
    """An explicit CI selection or its original bytes are invalid."""


@dataclass(frozen=True, slots=True)
class CISourceFile:
    """One selected source; path is relative to the manifest directory."""

    path: str
    role: CIFileRole
    sha256: str
    size_bytes: int | None = None
    source_url: str | None = None
    etag: str | None = None
    last_modified: str | None = None


@dataclass(frozen=True, slots=True)
class CIInputManifest:
    base_dir: Path
    files: tuple[CISourceFile, ...]

    def selected(self) -> tuple[CISourceFile, ...]:
        """Stable source-ID order: mappings, series, current, all data."""
        return tuple(sorted(self.files, key=lambda f: (_ORDER[f.role], f.path)))

    def resolve(self, source: CISourceFile) -> Path:
        root = self.base_dir.resolve()
        relative = Path(source.path)
        if (
            relative.is_absolute()
            or not source.path
            or "\\" in source.path
            or ".." in relative.parts
        ):
            raise CIInputError(f"Source path must be relative: {source.path!r}")
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise CIInputError(
                f"Source missing or outside manifest root: {source.path}"
            )
        return path


def _expected_name(role: str) -> str:
    if role in CI_DIMENSIONS:
        return CI_DIMENSIONS[role][3]
    if role == "series_metadata":
        return "ci.series"
    return _DATA_NAMES[role]


def load_ci_manifest(path: str | Path) -> CIInputManifest:
    """Load a pinned selection; never infer CI files from a directory."""
    source_path = Path(path)
    try:
        document = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CIInputError(f"Cannot load CI manifest: {source_path}") from exc
    if (
        not isinstance(document, dict)
        or set(document) != {"schema_version", "program", "files"}
        or document.get("schema_version") != 1
        or document.get("program") != "ci"
    ):
        raise CIInputError("CI manifest requires version 1, program 'ci', and files")
    files = document["files"]
    if not isinstance(files, list) or not files:
        raise CIInputError("CI manifest requires explicit nonempty files")

    selected: list[CISourceFile] = []
    for index, record in enumerate(files):
        if not isinstance(record, dict) or set(record) - _FIELDS:
            raise CIInputError(f"Invalid fields in files[{index}]")
        try:
            entry = CISourceFile(**record)
        except TypeError as exc:
            raise CIInputError(f"Malformed files[{index}]") from exc
        if (
            not isinstance(entry.path, str)
            or not entry.path
            or not isinstance(entry.role, str)
            or entry.role not in _HEADERS
            or not isinstance(entry.sha256, str)
            or not _SHA256.fullmatch(entry.sha256)
            or (
                entry.size_bytes is not None
                and (type(entry.size_bytes) is not int or entry.size_bytes < 0)
            )
        ):
            raise CIInputError(f"Invalid path, role, hash or size in files[{index}]")
        for key in ("source_url", "etag", "last_modified"):
            value = getattr(entry, key)
            if value is not None and not isinstance(value, str):
                raise CIInputError(f"files[{index}].{key} must be text")
        if "\\" in entry.path:
            raise CIInputError("CI paths must use relative POSIX separators")
        name = Path(entry.path).name
        if name != _expected_name(entry.role):
            raise CIInputError(f"Unexpected filename for {entry.role}: {name}")
        selected.append(entry)

    paths = [entry.path.casefold() for entry in selected]
    if len(paths) != len(set(paths)):
        raise CIInputError("CI manifest selects the same path more than once")
    roles: list[str] = [entry.role for entry in selected]
    if any(roles.count(role) != 1 for role in _REQUIRED):
        raise CIInputError(
            "Require exactly one CI owner, industry, occupation, subcell, area, "
            "estimate and series file"
        )
    if not any(role in CI_DATA_ROLES for role in roles):
        raise CIInputError("At least one CI data file is required")
    if any(roles.count(role) > 1 for role in CI_DATA_ROLES):
        raise CIInputError("Select each CI data file at most once")
    manifest = CIInputManifest(source_path.resolve().parent, tuple(selected))
    for item in selected:
        manifest.resolve(item)
    return manifest


def ci_header(fields: list[str], role: str) -> bool:
    """BLS sometimes appends blank tab fields, but never extra data fields."""
    expected = _HEADERS[role]
    while len(fields) > len(expected) and not fields[-1]:
        fields.pop()
    return tuple(fields) == expected


def verify_ci_source(path: Path, source: CISourceFile) -> int:
    """Verify raw file bytes, length and BLS header before database mutation."""
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as stream:
            first = stream.readline().decode("utf-8-sig").rstrip("\r\n")
            header = [field.strip() for field in first.split("\t")]
            if not ci_header(header, source.role):
                raise CIInputError(f"Unexpected CI {source.role} header: {source.path}")
            stream.seek(0)
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
                size += len(chunk)
    except (OSError, UnicodeDecodeError) as exc:
        raise CIInputError(f"Cannot read CI source {source.path}") from exc
    if digest.hexdigest() != source.sha256.lower():
        raise CIInputError(f"SHA-256 mismatch for {source.path}")
    if source.size_bytes is not None and size != source.size_bytes:
        raise CIInputError(f"Byte size mismatch for {source.path}")
    return size
