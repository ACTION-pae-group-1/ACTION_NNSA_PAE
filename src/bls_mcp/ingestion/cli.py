"""Offline administrative CLI for BLS DuckDB snapshot lifecycle operations."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

from bls_mcp.ingestion.lifecycle import build_candidate, validate_candidate
from bls_mcp.ingestion.publish import (
    activate_snapshot,
    current_snapshot_path,
    publish_candidate,
    read_registry,
    rollback_snapshot,
)


def _add_manifests(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--wp-manifest", type=Path, help="Pinned WP input manifest")
    parser.add_argument("--pc-manifest", type=Path, help="Pinned PC input manifest")
    parser.add_argument("--cu-manifest", type=Path, help="Pinned CU input manifest")
    parser.add_argument(
        "--ci-manifest", type=Path, help="Pinned CI (ECI) input manifest"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="bls-data", description="Offline DuckDB snapshots (no MCP or network)"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="Create a new BUILDING DuckDB candidate")
    build.add_argument("--candidate", type=Path, required=True)
    build.add_argument("--snapshot-id", required=True)
    build.add_argument("--build-commit")
    _add_manifests(build)

    validate = sub.add_parser("validate", help="Verify sources and finalize READY")
    validate.add_argument("--candidate", type=Path, required=True)
    _add_manifests(validate)

    publish = sub.add_parser("publish", help="Publish a READY immutable version")
    publish.add_argument("--candidate", type=Path, required=True)
    publish.add_argument("--registry-dir", type=Path, required=True)

    listing = sub.add_parser("list", help="List registered snapshots and active ID")
    listing.add_argument("--registry-dir", type=Path, required=True)

    current = sub.add_parser("current", help="Print the active DuckDB file path")
    current.add_argument("--registry-dir", type=Path, required=True)

    activate = sub.add_parser("activate", help="Atomically select a published version")
    activate.add_argument("--registry-dir", type=Path, required=True)
    activate.add_argument("--snapshot-id", required=True)

    rollback = sub.add_parser("rollback", help="Restore the prior active version")
    rollback.add_argument("--registry-dir", type=Path, required=True)

    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            build_report = build_candidate(
                args.candidate,
                args.snapshot_id,
                wp_manifest=args.wp_manifest,
                pc_manifest=args.pc_manifest,
                cu_manifest=args.cu_manifest,
                ci_manifest=args.ci_manifest,
                build_commit=args.build_commit,
            )
            print(json.dumps(asdict(build_report), indent=2))
        elif args.command == "validate":
            report = validate_candidate(
                args.candidate,
                wp_manifest=args.wp_manifest,
                pc_manifest=args.pc_manifest,
                cu_manifest=args.cu_manifest,
                ci_manifest=args.ci_manifest,
            )
            print(json.dumps(report.as_dict(), indent=2))
            return 0 if report.passed else 1
        elif args.command == "publish":
            published_snapshot = publish_candidate(args.candidate, args.registry_dir)
            print(json.dumps(asdict(published_snapshot), indent=2))
        elif args.command == "list":
            print(json.dumps(read_registry(args.registry_dir).as_dict(), indent=2))
        elif args.command == "current":
            print(current_snapshot_path(args.registry_dir))
        elif args.command == "activate":
            print(activate_snapshot(args.registry_dir, args.snapshot_id))
        elif args.command == "rollback":
            print(rollback_snapshot(args.registry_dir))
    except (OSError, ValueError) as exc:
        print(f"bls-data: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
