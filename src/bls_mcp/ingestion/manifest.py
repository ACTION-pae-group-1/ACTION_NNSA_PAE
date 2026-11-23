"""Explicit, checksum-pinned input selection for offline PC DuckDB ingestion.

Independent of the later snapshot publication registry. No network access
and no implicit filesystem globbing.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from bls_mcp.data.flat_file import PC_SERIES_COLUMNS

PCFileRole = Literal[
    "industry_mapping",
    "product_mapping",
    "series_metadata",
    "historical",
    "current",
    "all_data",
]
_REQUIRED: set[PCFileRole] = {"industry_mapping", "product_mapping", "series_metadata"}
_DATA = {"historical", "current", "all_data"}
_SHA256 = re.compile(r"[0-9a-fA-F]{64}\Z")
_DATA_COLUMNS = ("series_id", "year", "period", "value", "footnote_codes")
_HEADERS: dict[str, tuple[str, ...]] = {
    "industry_mapping": ("industry_code", "industry_name"),
    "product_mapping": ("industry_code", "product_code", "product_name"),
    "series_metadata": PC_SERIES_COLUMNS,
    "historical": _DATA_COLUMNS,
    "current": _DATA_COLUMNS,
    "all_data": _DATA_COLUMNS,
}
_ROLE_ORDER = {
    "industry_mapping": 0,
    "product_mapping": 1,
    "series_metadata": 2,
    "historical": 3,
    "current": 4,
    "all_data": 5,
}


class PCInputError(ValueError):
    """A source selection, file structure, or checksum is invalid."""


@dataclass(frozen=True, slots=True)
class PCSourceFile:
    """One selected source; path is relative to the manifest directory."""

    path: str
    role: PCFileRole
    sha256: str
    size_bytes: int | None = None
    source_url: str | None = None
    etag: str | None = None
    last_modified: str | None = None


@dataclass(frozen=True, slots=True)
class PCInputManifest:
    base_dir: Path
    files: tuple[PCSourceFile, ...]

    def selected(self) -> tuple[PCSourceFile, ...]:
        """Stable source-ID order: mappings, series, historical, current."""
        return tuple(sorted(self.files, key=lambda f: (_ROLE_ORDER[f.role], f.path)))

    def resolve(self, source: PCSourceFile) -> Path:
        root = self.base_dir.resolve()
        relative = Path(source.path)
        if relative.is_absolute() or not source.path or "\\" in source.path:
            raise PCInputError(f"Source path must be relative: {source.path!r}")
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise PCInputError(
                f"Source missing or outside manifest root: {source.path}"
            )
        return path


def load_pc_manifest(path: str | Path) -> PCInputManifest:
    """Load a versioned selection; never select files by guessing filename."""
    manifest_path = Path(path)
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PCInputError(f"Cannot load PC manifest: {manifest_path}") from exc
    if (
        not isinstance(data, dict)
        or data.get("schema_version") != 1
        or data.get("program") != "pc"
    ):
        raise PCInputError("PC manifest requires schema_version=1 and program='pc'")
    entries = data.get("files")
    if not isinstance(entries, list) or not entries:
        raise PCInputError("PC manifest requires an explicit nonempty files list")

    parsed: list[PCSourceFile] = []
    for index, item in enumerate(entries):
        if not isinstance(item, dict):
            raise PCInputError(f"files[{index}] must be an object")
        if set(item) - {
            "path",
            "role",
            "sha256",
            "size_bytes",
            "source_url",
            "etag",
            "last_modified",
        }:
            raise PCInputError(f"files[{index}] has unrecognized fields")
        try:
            entry = PCSourceFile(**item)
        except TypeError as exc:
            raise PCInputError(f"Malformed files[{index}]") from exc
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
            raise PCInputError(f"Invalid path, role, hash or size in files[{index}]")
        for field in ("source_url", "etag", "last_modified"):
            value = getattr(entry, field)
            if value is not None and not isinstance(value, str):
                raise PCInputError(f"files[{index}].{field} must be a string")

        if "\\" in entry.path:
            raise PCInputError("Source path must use relative POSIX separators")
        filename = Path(entry.path).name
        if entry.role == "series_metadata" and filename != "pc.series":
            raise PCInputError("Series metadata must be named pc.series")
        if entry.role == "industry_mapping" and filename not in (
            "pc.industry",
            "pc.industry.txt",
        ):
            raise PCInputError("Industry mapping must be pc.industry[.txt]")
        if entry.role == "product_mapping" and filename not in (
            "pc.product",
            "pc.product.txt",
        ):
            raise PCInputError("Product mapping must be pc.product[.txt]")
        if entry.role in _DATA and not filename.startswith("pc.data."):
            raise PCInputError("PC observations must be named pc.data.*")
        parsed.append(entry)

    paths = [entry.path for entry in parsed]
    if len(paths) != len(set(paths)):
        raise PCInputError("PC manifest selects the same path more than once")
    roles = [entry.role for entry in parsed]
    if any(roles.count(role) != 1 for role in _REQUIRED):
        raise PCInputError("Require one industry, product and series metadata file")
    if not _DATA.intersection(roles):
        raise PCInputError("At least one explicit PC data partition is required")
    if "all_data" in roles and (len(roles) != 4 or roles.count("all_data") != 1):
        raise PCInputError("AllData must be the only selected data partition")

    manifest = PCInputManifest(manifest_path.resolve().parent, tuple(parsed))
    for entry in manifest.files:
        manifest.resolve(entry)
    return manifest


def verify_pc_source(path: Path, source: PCSourceFile) -> int:
    """Check the exact header, optional size and SHA-256 before writing."""
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as stream:
            header = stream.readline().decode("utf-8-sig").rstrip("\r\n")
            actual = tuple(field.strip() for field in header.split("\t"))
            if actual != _HEADERS[source.role]:
                raise PCInputError(f"Unexpected {source.role} header: {source.path}")
            stream.seek(0)
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
                size += len(chunk)
    except (OSError, UnicodeDecodeError) as exc:
        raise PCInputError(f"Cannot read PC source {source.path}") from exc
    if digest.hexdigest() != source.sha256.lower():
        raise PCInputError(f"SHA-256 mismatch for {source.path}")
    if source.size_bytes is not None and size != source.size_bytes:
        raise PCInputError(f"Byte size mismatch for {source.path}")
    return size
