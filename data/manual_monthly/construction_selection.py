#!/usr/bin/env python3
"""OFFLINE candidate partition selection from saved monthly BLS discovery.

Outputs reviewable exact filenames; does not download or authorize ingestion.
"""

import argparse
import json
from pathlib import Path

TERMS = {
    "pc": (
        "construction",
        "metal",
        "machinery",
        "computer",
        "electrical",
        "chemical",
        "plastic",
        "rubber",
        "mineral",
        "wood",
        "petroleum",
        "transportation",
        "professional",
        "technical",
        "rental",
        "leasing",
        "waste",
        "remediation",
        "utilities",
        "warehouse",
        "storage",
    ),
    "wp": (
        "construction",
        "constructn",
        "steel",
        "metal",
        "machinery",
        "mineral",
        "lumber",
        "fuel",
        "chemical",
        "rubber",
        "service",
        "transport",
        "aggregate",
        "specialindex",
        "fd-id",
    ),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("discovery", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    doc = json.loads(args.discovery.read_text(encoding="utf-8"))
    program = doc.get("program")
    if program not in TERMS:
        parser.error(
            "Only PC/WP have multiple topical historical partitions;"
            " CI uses AllData, CU needs item/area review"
        )
    files = doc.get("files", [])
    candidates = sorted(
        f["path"]
        for f in files
        if f.get("role") == "historical"
        and any(term in f["path"].lower() for term in TERMS[program])
    )
    if not candidates:
        parser.error("No candidate partitions found in saved discovery")
    if args.output.exists():
        parser.error(
            "Output already exists; review existing selection rather than overwrite"
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"program": program, "partitions": candidates}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {len(candidates)} candidates to {args.output}; REVIEW BEFORE DOWNLOAD"
    )


if __name__ == "__main__":
    main()
