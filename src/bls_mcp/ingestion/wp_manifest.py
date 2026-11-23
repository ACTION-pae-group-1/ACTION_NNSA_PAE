"""Pinned, offline WP commodity PPI source selection."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

HEADERS = {
    "group_mapping": ("group_code", "group_name"),
    "item_mapping": ("group_code", "item_code", "item_name"),
    "series_metadata": (
        "series_id",
        "group_code",
        "item_code",
        "seasonal",
        "base_date",
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
REQUIRED = {"group_mapping", "item_mapping", "series_metadata"}


@dataclass(frozen=True)
class WPSource:
    path: str
    role: str
    sha256: str
    size_bytes: int
    source_url: str | None = None


@dataclass(frozen=True)
class WPManifest:
    root: Path
    files: tuple[WPSource, ...]

    def selected(self):
        order = {
            "group_mapping": 0,
            "item_mapping": 1,
            "series_metadata": 2,
            "historical": 3,
            "current": 4,
        }
        return sorted(self.files, key=lambda x: (order[x.role], x.path))

    def resolve(self, source):
        relative = Path(source.path)
        if relative.is_absolute() or "\\" in source.path or not source.path:
            raise ValueError("WP paths must be relative POSIX paths")
        root = self.root.resolve()
        target = (root / relative).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            raise ValueError("WP source missing or outside manifest root")
        return target


def load_wp_manifest(path):
    manifest_path = Path(path).resolve()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("program") != "wp":
        raise ValueError("Expected WP schema_version=1 manifest")
    entries = data.get("files")
    if not isinstance(entries, list):
        raise ValueError("WP files must be a list")
    files = []
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) - {
            "path",
            "role",
            "sha256",
            "size_bytes",
            "source_url",
        }:
            raise ValueError("Invalid WP source entry")
        source = WPSource(**entry)
        if (
            source.role not in HEADERS
            or len(source.sha256) != 64
            or any(c not in "0123456789abcdefABCDEF" for c in source.sha256)
            or type(source.size_bytes) is not int
            or source.size_bytes < 0
        ):
            raise ValueError("Invalid WP source role/hash/size")
        if source.source_url is not None and not isinstance(source.source_url, str):
            raise ValueError("Invalid WP source URL")
        files.append(source)
    roles = [f.role for f in files]
    if any(roles.count(role) != 1 for role in REQUIRED) or not any(
        role in ("historical", "current") for role in roles
    ):
        raise ValueError("WP requires group, item, series and observation files")
    if len({f.path for f in files}) != len(files):
        raise ValueError("Duplicate WP source path")
    manifest = WPManifest(manifest_path.parent, tuple(files))
    for source in files:
        manifest.resolve(source)
    return manifest


def verify_wp_source(path, source):
    with path.open("rb") as stream:
        header = stream.readline().decode("utf-8-sig").rstrip("\r\n")
        actual = tuple(field.strip() for field in header.split("\t"))
        if actual != HEADERS[source.role]:
            raise ValueError(f"WP header mismatch: {source.path}: {actual}")
        stream.seek(0)
        digest = hashlib.sha256()
        size = 0
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    if digest.hexdigest() != source.sha256.lower() or size != source.size_bytes:
        raise ValueError(f"WP checksum/size mismatch: {source.path}")
    return size
