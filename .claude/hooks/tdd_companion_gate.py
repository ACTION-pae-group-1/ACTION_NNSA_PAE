#!/usr/bin/env python3
# ruff: noqa: E501
"""Require a Git-indexed companion test for staged production source changes.

This hook examines the staged Git index, not untracked or unstaged working-tree
files. It does not require companion tests for test code or package markers.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_SUFFIXES = frozenset({".py", ".ts", ".tsx", ".js", ".jsx"})
NONPRODUCTION_DIRS = frozenset(
    {
        "tests",
        "test",
        "__tests__",
        "scripts",
        "__pycache__",
        "node_modules",
        ".git",
        ".venv",
        "venv",
        "dist",
        "build",
        ".storybook",
    }
)

# Verified generator-owned artifact patterns
# These files are produced by automated code generators and do not require companion tests.
# Exemption is verified by (1) exact directory/filename match AND (2) generator header verification.
# Policy: GENERATOR_EXEMPTIONS.md governs criteria for adding new patterns.
# Last verified: 2026-11-05 | Generator: @hey-api/openapi-ts | Update when: generator version changes
GENERATED_FILE_PATTERNS = frozenset(
    {
        # @hey-api/openapi-ts generated files (re-export aggregator and type definitions)
        ("frontend/src/client/@tanstack", "react-query.gen.ts"),
        ("frontend/src/client", "sdk.gen.ts"),
        ("frontend/src/client", "types.gen.ts"),
        (
            "frontend/src/client",
            "index.ts",
        ),  # Re-export aggregator, verified auto-generated
    }
)


class GitIndexError(RuntimeError):
    """Raised when the staged Git index cannot be inspected safely."""


def _git_paths(repo_root: Path, *args: str) -> set[Path]:
    """Read NUL-delimited repository-relative file paths from Git."""
    try:
        result = subprocess.run(
            ["git", *args, "-z"],
            cwd=repo_root,
            capture_output=True,
            check=True,
            timeout=15,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise GitIndexError(
            f"Cannot inspect Git index ({' '.join(args)}): {exc}"
        ) from exc
    return {Path(os.fsdecode(value)) for value in result.stdout.split(b"\0") if value}


def get_staged_files(repo_root: Path = REPO_ROOT) -> set[Path]:
    """Return paths staged as added, copied, modified, renamed, or type-changed."""
    return _git_paths(
        repo_root,
        "diff",
        "--cached",
        "--name-only",
        "--diff-filter=ACMRT",
    )


def get_indexed_files(repo_root: Path = REPO_ROOT) -> set[Path]:
    """Return paths already tracked in HEAD or staged in the current index."""
    return _git_paths(repo_root, "ls-files", "--cached", "--full-name")


def _git_blob_map(repo_root: Path, args: list[str], *, staged: bool) -> dict[Path, str]:
    """Map repository paths to blob ids from `git ls-tree` or `git ls-files -s`."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            capture_output=True,
            check=True,
            timeout=15,
        )
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise GitIndexError(f"Cannot read Git blobs ({' '.join(args)}): {exc}") from exc
    blobs: dict[Path, str] = {}
    for record in result.stdout.split(b"\0"):
        if not record:
            continue
        meta, _, name = record.partition(b"\t")
        fields = meta.split()
        if staged:
            # ls-files -s: <mode> <sha> <stage>\t<path>; only stage 0 is a resolved entry.
            if fields[2] != b"0":
                continue
            blob = fields[1]
        else:
            # ls-tree: <mode> <type> <sha>\t<path>; submodules are not blobs.
            if fields[1] != b"blob":
                continue
            blob = fields[2]
        blobs[Path(os.fsdecode(name))] = blob.decode("ascii")
    return blobs


def trunk_identical_paths(repo_root: Path) -> set[Path]:
    """Staged paths whose content equals the trunk side of a merge in progress.

    A file that arrives from trunk unchanged was gated when it landed on trunk, so
    the branch's merge does not gate it again. Files the branch added, or resolved
    to something other than trunk, are not in this set and stay gated. Returns an
    empty set when no merge is in progress.
    """
    try:
        probe = subprocess.run(
            ["git", "rev-parse", "-q", "--verify", "MERGE_HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GitIndexError(f"Cannot inspect merge state: {exc}") from exc
    if probe.returncode != 0:
        return set()
    trunk = _git_blob_map(
        repo_root, ["ls-tree", "-r", "-z", probe.stdout.strip()], staged=False
    )
    staged = _git_blob_map(repo_root, ["ls-files", "-s", "-z"], staged=True)
    return {path for path, blob in staged.items() if trunk.get(path) == blob}


def _has_generator_header(file_path: Path) -> bool:
    """Verify file contains @hey-api/openapi-ts generation marker in first line."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            return "@hey-api/openapi-ts" in first_line or (
                "This file is auto-generated" in first_line
                and "openapi-ts" in f.readline()
            )
    except (OSError, UnicodeDecodeError, ValueError):
        return False


def is_generated_file(file_path: Path, repo_root: Path = REPO_ROOT) -> bool:
    """Check if a file is a verified generator-owned artifact requiring no companion test.

    Requires BOTH: (1) exact (directory, filename) match AND (2) generator header verification.
    This prevents hand-crafted files with deceptive names from bypassing the TDD gate.
    """
    # Check against known generated patterns: (directory, filename)
    for gen_dir, gen_name in GENERATED_FILE_PATTERNS:
        gen_dir_path = Path(gen_dir)
        if file_path.parent == gen_dir_path and file_path.name == gen_name:
            # Verify generator header before exempting
            full_path = repo_root / file_path
            if _has_generator_header(full_path):
                return True
    return False


def is_production_file(file_path: Path, repo_root: Path = REPO_ROOT) -> bool:
    """Identify actual source files, excluding tests and development tooling."""
    if file_path.suffix not in SOURCE_SUFFIXES:
        return False

    if file_path.name in {"__init__.py", "conftest.py"}:
        return False

    if any(part in NONPRODUCTION_DIRS for part in file_path.parts):
        return False

    if file_path.parts[:2] == (".claude", "hooks"):
        return False

    if file_path.parts[:2] == (".claude", "workflows"):
        return False

    if file_path.name.startswith("test_"):
        return False

    if ".test" in file_path.stem or ".spec" in file_path.stem:
        return False

    # Exempt verified generated artifacts (requires header verification)
    return not is_generated_file(file_path, repo_root)


def _test_names(file_path: Path) -> tuple[str, str, str]:
    return (
        f"test_{file_path.stem}{file_path.suffix}",
        f"{file_path.stem}.test{file_path.suffix}",
        f"{file_path.stem}.spec{file_path.suffix}",
    )


def find_test_file(file_path: Path, indexed_files: set[Path]) -> Path | None:
    """Find a matching test path in Git's index, not merely on disk."""
    names = _test_names(file_path)

    for directory in (
        file_path.parent,
        file_path.parent / "tests",
        file_path.parent / "__tests__",
        file_path.parent.parent / "tests",
    ):
        for name in names:
            candidate = directory / name
            if candidate in indexed_files:
                return candidate

    # Framework files in .claude/ can have tests in root-level tests/ directory
    if file_path.parts[:1] == (".claude",):
        for name in names:
            candidate = Path("tests") / name
            if candidate in indexed_files:
                return candidate

    # Preserve the repository's existing convention: Python backend tests may
    # live anywhere underneath backend/app/tests (e.g. api/ or services/).
    if file_path.parts[:2] == ("backend", "app"):
        app_tests = Path("backend/app/tests")
        for candidate in sorted(indexed_files):
            if candidate.is_relative_to(app_tests) and candidate.name in names:
                return candidate

    # BLS evaluation modules use the shared evaluation test directory.
    if file_path.parts[:2] == ("eval", "bls"):
        companion_names = {
            "runner.py": "test_bls_evals.py",
            "transcript.py": "test_bls_evals.py",
        }

        for name in [*names, companion_names.get(file_path.name)]:
            if name is None:
                continue
            candidate = Path("tests/evals") / name
            if candidate in indexed_files:
                return candidate
    # PARS uses package-local tests that mirror production directories.
    if file_path.parts[:2] == ("src", "pars_local_mcp"):
        relative = file_path.relative_to(Path("src/pars_local_mcp"))
        for name in names:
            candidate = Path("src/pars_local_mcp/tests") / relative.parent / name
            if candidate in indexed_files:
                return candidate
    return None


def main(repo_root: Path | None = None) -> int:
    root = repo_root if repo_root is not None else REPO_ROOT
    try:
        staged_files = get_staged_files(root)
        indexed_files = get_indexed_files(root)
        from_trunk = trunk_identical_paths(root)
    except GitIndexError as exc:
        print(f"TDD Companion Gate error: {exc}", file=sys.stderr)
        return 1

    production_files = sorted(
        path
        for path in staged_files
        if path not in from_trunk and is_production_file(path, root)
    )
    if not production_files:
        print("TDD Companion Gate: no production code changes detected.")
        return 0

    missing_tests = [
        path for path in production_files if find_test_file(path, indexed_files) is None
    ]
    if missing_tests:
        print("\nTDD Companion Gate Failed")
        print("Production code must have a matching test file in the Git index.\n")
        for path in missing_tests:
            print(f"  {path}")
            print("    Expected one of:")
            for name in _test_names(path):
                print(f"      {name}")
        print("\nStage a companion test or add an existing tracked test.")
        return 1

    print("TDD Companion Gate: all staged production files have companion tests.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
