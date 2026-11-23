"""Checksum-pinned CU (CPI-U) source selection for offline DuckDB builds.

The manifest is deliberately explicit: BLS CU data partitions overlap and
cannot safely be globbed together.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

CUFileRole = Literal[
    "area_mapping", "item_mapping", "series_metadata", "historical", "current"
]
_REQUIRED: set[CUFileRole] = {"area_mapping", "item_mapping", "series_metadata"}
_SHA256 = re.compile(r"[a-fA-F0-9]{64}\Z")
_HEADERS: dict[str, tuple[str, ...]] = {
    "area_mapping": (
        "area_code",
        "area_name",
        "display_level",
        "selectable",
        "sort_sequence",
    ),
    "item_mapping": (
        "item_code",
        "item_name",
        "display_level",
        "selectable",
        "sort_sequence",
    ),
    "series_metadata": (
        "series_id",
        "area_code",
        "item_code",
        "seasonal",
        "periodicity_code",
        "base_code",
        "base_period",
        "series_title",
        "footnote_codes",
        "begin_year",
        "begin_period",
        "end_year",
        "end_period",
    ),
    "historical": ("series_id", "year", "period", "value", "footnote_codes"),
    "current": ("series_id", "year", "period", "value", "footnote_codes"),
}
_ORDER = {
    "area_mapping": 0,
    "item_mapping": 1,
    "series_metadata": 2,
    "historical": 3,
    "current": 4,
}


class CUInputError(ValueError):
    """An explicit CU selection or its original bytes are invalid."""


@dataclass(frozen=True, slots=True)
class CUSourceFile:
    path: str
    role: CUFileRole
    sha256: str
    size_bytes: int | None = None
    source_url: str | None = None
    etag: str | None = None
    last_modified: str | None = None


@dataclass(frozen=True, slots=True)
class CUInputManifest:
    base_dir: Path
    files: tuple[CUSourceFile, ...]

    def selected(self) -> tuple[CUSourceFile, ...]:
        return tuple(sorted(self.files, key=lambda f: (_ORDER[f.role], f.path)))

    def resolve(self, source: CUSourceFile) -> Path:
        root = self.base_dir.resolve()
        relative = Path(source.path)
        if (
            relative.is_absolute()
            or not source.path
            or "\\" in source.path
            or ".." in relative.parts
        ):
            raise CUInputError(f"Source path must be relative: {source.path!r}")
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise CUInputError(
                f"Source missing or outside manifest root: {source.path}"
            )
        return path


def load_cu_manifest(path: str | Path) -> CUInputManifest:
    """Load a pinned selection, never infer CU partitions from a directory."""
    source_path = Path(path)
    try:
        document = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CUInputError(f"Cannot load CU manifest: {source_path}") from exc
    if (
        not isinstance(document, dict)
        or set(document) != {"schema_version", "program", "files"}
        or document.get("schema_version") != 1
        or document.get("program") != "cu"
    ):
        raise CUInputError("CU manifest requires version 1, program 'cu', and files")
    files = document["files"]
    if not isinstance(files, list) or not files:
        raise CUInputError("CU manifest requires explicit nonempty files")

    selected: list[CUSourceFile] = []
    for index, record in enumerate(files):
        if not isinstance(record, dict) or set(record) - {
            "path",
            "role",
            "sha256",
            "size_bytes",
            "source_url",
            "etag",
            "last_modified",
        }:
            raise CUInputError(f"Invalid fields in files[{index}]")
        try:
            entry = CUSourceFile(**record)
        except TypeError as exc:
            raise CUInputError(f"Malformed files[{index}]") from exc
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
            raise CUInputError(f"Invalid path, role, hash or size in files[{index}]")
        for key in ("source_url", "etag", "last_modified"):
            value = getattr(entry, key)
            if value is not None and not isinstance(value, str):
                raise CUInputError(f"files[{index}].{key} must be text")
        if "\\" in entry.path:
            raise CUInputError("CU paths must use relative POSIX separators")
        name = Path(entry.path).name
        required_names = {
            "area_mapping": "cu.area",
            "item_mapping": "cu.item",
            "series_metadata": "cu.series",
            "current": "cu.data.0.Current",
        }
        if entry.role in required_names and name != required_names[entry.role]:
            raise CUInputError(f"Unexpected filename for {entry.role}: {name}")
        if entry.role == "historical" and (
            not name.startswith("cu.data.") or name == "cu.data.0.Current"
        ):
            raise CUInputError("CU historical files must be cu.data.* partitions")
        selected.append(entry)

    paths = [entry.path.casefold() for entry in selected]
    if len(paths) != len(set(paths)):
        raise CUInputError("CU manifest selects the same path more than once")
    roles = [entry.role for entry in selected]
    if any(roles.count(role) != 1 for role in _REQUIRED):
        raise CUInputError("Require exactly one CU area, item and series file")
    if not any(role in ("historical", "current") for role in roles):
        raise CUInputError("At least one CU data partition is required")
    if roles.count("current") > 1:
        raise CUInputError("Only one CU current partition may be selected")
    manifest = CUInputManifest(source_path.resolve().parent, tuple(selected))
    for item in selected:
        manifest.resolve(item)
    return manifest


def cu_header(fields: list[str], role: CUFileRole) -> bool:
    """BLS sometimes appends blank tab fields, but never extra data fields."""
    expected = _HEADERS[role]
    while len(fields) > len(expected) and not fields[-1]:
        fields.pop()
    return tuple(fields) == expected


def verify_cu_source(path: Path, source: CUSourceFile) -> int:
    """Verify raw file bytes, length and BLS header before database mutation."""
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as stream:
            first = stream.readline().decode("utf-8-sig").rstrip("\r\n")
            header = [field.strip() for field in first.split("\t")]
            if not cu_header(header, source.role):
                raise CUInputError(f"Unexpected CU {source.role} header: {source.path}")
            stream.seek(0)
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
                size += len(chunk)
    except (OSError, UnicodeDecodeError) as exc:
        raise CUInputError(f"Cannot read CU source {source.path}") from exc
    if digest.hexdigest() != source.sha256.lower():
        raise CUInputError(f"SHA-256 mismatch for {source.path}")
    if source.size_bytes is not None and size != source.size_bytes:
        raise CUInputError(f"Byte size mismatch for {source.path}")
    return size
