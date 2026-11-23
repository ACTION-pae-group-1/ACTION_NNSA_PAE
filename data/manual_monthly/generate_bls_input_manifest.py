#!/usr/bin/env python3
"""MANUAL, LOCAL-ONLY: hash selected PC/CU files into a DuckDB input manifest.

Unlike manual_bls_monthly.py, this script does not access the BLS website,
list remote filenames, or download any files. Use it for browser downloads or
existing samples, always with explicit ROLE=PATH selections.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path, PurePosixPath

PC_ROLES = {
    "industry_mapping",
    "product_mapping",
    "series_metadata",
    "historical",
    "current",
    "all_data",
}
CU_ROLES = {"area_mapping", "item_mapping", "series_metadata", "historical", "current"}
REQUIRED = {
    "pc": {"industry_mapping", "product_mapping", "series_metadata"},
    "cu": {"area_mapping", "item_mapping", "series_metadata"},
}
ORDER = {
    "pc": [
        "industry_mapping",
        "product_mapping",
        "series_metadata",
        "historical",
        "current",
        "all_data",
    ],
    "cu": ["area_mapping", "item_mapping", "series_metadata", "historical", "current"],
}


def source_entry(
    root: Path, role: str, filename: str, program: str
) -> dict[str, object]:
    relative = PurePosixPath(filename)
    if (
        not filename
        or filename.startswith("/")
        or "\\" in filename
        or relative.is_absolute()
        or any(part in {"..", "."} for part in filename.split("/"))
        or ":" in filename
    ):
        raise ValueError(
            f"Source path must be relative with forward slashes: {filename!r}"
        )
    name = relative.name
    if program == "pc":
        allowed = {
            "industry_mapping": {"pc.industry", "pc.industry.txt"},
            "product_mapping": {"pc.product", "pc.product.txt"},
            "series_metadata": {"pc.series"},
        }
        if role in allowed and name not in allowed[role]:
            raise ValueError(f"Unexpected PC filename for {role}: {name}")
        if role in {"historical", "current", "all_data"} and not name.startswith(
            "pc.data."
        ):
            raise ValueError(f"PC observations must be named pc.data.*: {name}")
    else:
        allowed = {
            "area_mapping": "cu.area",
            "item_mapping": "cu.item",
            "series_metadata": "cu.series",
            "current": "cu.data.0.Current",
        }
        if role in allowed and name != allowed[role]:
            raise ValueError(f"Unexpected CU filename for {role}: {name}")
        if role == "historical" and (
            not name.startswith("cu.data.") or name == "cu.data.0.Current"
        ):
            raise ValueError(
                f"CU historical files must be cu.data.* except Current: {name}"
            )
    path = (root / filename).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError(f"Source not found or outside source directory: {filename}")
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return {
        "path": filename,
        "role": role,
        "sha256": digest.hexdigest(),
        "size_bytes": size,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--program", choices=["pc", "cu"], required=True)
    parser.add_argument(
        "--source-dir",
        type=Path,
        required=True,
        help="Directory containing the original raw BLS files",
    )
    parser.add_argument(
        "--file",
        action="append",
        required=True,
        metavar="ROLE=PATH",
        help="Explicitly select one input; repeat for every file",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing manifest (invalidates old build provenance)",
    )
    args = parser.parse_args()
    root = args.source_dir.resolve()
    if not root.is_dir():
        parser.error(f"Source directory does not exist: {root}")

    allowed = PC_ROLES if args.program == "pc" else CU_ROLES
    selected: list[tuple[str, str]] = []
    for spec in args.file:
        if "=" not in spec:
            parser.error(f"Use ROLE=PATH, got {spec!r}")
        role, filename = spec.split("=", 1)
        if role not in allowed:
            parser.error(f"Invalid role for {args.program}: {role!r}")
        selected.append((role, filename))
    counts = Counter(role for role, _ in selected)
    for role in REQUIRED[args.program]:
        if counts[role] != 1:
            parser.error(f"Exactly one {role} entry is required")
    data_roles = (
        {"historical", "current", "all_data"}
        if args.program == "pc"
        else {"historical", "current"}
    )
    if not any(counts[role] for role in data_roles):
        parser.error("Select at least one observation file")
    if (
        args.program == "pc"
        and counts["all_data"]
        and (counts["all_data"] != 1 or counts["current"] or counts["historical"])
    ):
        parser.error("PC all_data must be the only observation partition")
    if counts["current"] > 1:
        parser.error("At most one current partition may be selected")
    paths = [filename.casefold() for _, filename in selected]
    if len(paths) != len(set(paths)):
        parser.error("A raw file may be selected only once")

    ordered = sorted(
        selected,
        key=lambda item: (ORDER[args.program].index(item[0]), item[1]),
    )
    entries = [
        source_entry(root, role, filename, args.program) for role, filename in ordered
    ]
    destination = root / f"{args.program}-input.json"
    if destination.exists() and not args.force:
        parser.error(f"Manifest exists: {destination} (use --force to replace)")
    payload = {"schema_version": 1, "program": args.program, "files": entries}
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Created {destination} with {len(entries)} checksum-pinned sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
