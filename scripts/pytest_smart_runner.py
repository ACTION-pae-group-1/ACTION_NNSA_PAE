#!/usr/bin/env python3
"""Smart pytest runner for pre-commit: runs tests for changed files and companions.

Runs:
1. Staged test files, and tests for staged Python files
   (e.g., src/foo.py -> tests/test_foo.py)
2. Companion test files in same directory

Only staged files and files already committed to HEAD are considered; untracked
and unstaged files are ignored. Tests in shared directories are not run unless
they are companions of a staged file.

Only runs fast tests (not slow, not integration).
"""

import subprocess
import sys
from pathlib import Path


def find_companion_tests(py_file: Path) -> list[Path]:
    """Find test files that correspond to a changed Python file."""
    tests = []

    # Pattern 1: test_<name>.py in same directory
    same_dir_test = py_file.parent / f"test_{py_file.stem}.py"
    if same_dir_test.exists():
        tests.append(same_dir_test)

    # Pattern 2: <name>_test.py in same directory
    same_dir_suffix = py_file.parent / f"{py_file.stem}_test.py"
    if same_dir_suffix.exists():
        tests.append(same_dir_suffix)

    # Pattern 3: test_<name>.py in tests/ sibling directory
    tests_dir = py_file.parent / "tests"
    if tests_dir.exists():
        for pattern in [f"test_{py_file.stem}.py", f"{py_file.stem}_test.py"]:
            test_file = tests_dir / pattern
            if test_file.exists():
                tests.append(test_file)

    # Pattern 4: tests/ at parent level (for src/ layout)
    if py_file.parts[0:1] == ("src",) and len(py_file.parts) > 1:
        project_root = Path.cwd()
        tests_dir = project_root / "tests"
        if tests_dir.exists():
            # Look for tests that match the module path
            abs_py_file = (project_root / py_file).resolve()
            rel_path = abs_py_file.relative_to(project_root / "src")
            for pattern in [f"test_{rel_path.stem}.py", f"{rel_path.stem}_test.py"]:
                test_file = tests_dir / rel_path.parent / pattern
                if test_file.exists():
                    tests.append(test_file)

    return list(set(tests))


def get_git_python_files(*git_args: str) -> set[Path]:
    """Return the .py paths printed by a git command, or an empty set on failure."""
    try:
        result = subprocess.run(
            ["git", *git_args],
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        return set()
    return {Path(f) for f in result.stdout.splitlines() if f.endswith(".py")}


def get_changed_files() -> set[Path]:
    """Python files staged for the commit being checked."""
    return get_git_python_files("diff", "--cached", "--name-only", "--diff-filter=ACM")


def get_previously_committed_files() -> set[Path]:
    """Python files already committed (tracked in HEAD)."""
    return get_git_python_files("ls-tree", "-r", "--name-only", "HEAD")


def is_allowed(path: Path, allowed: set[Path]) -> bool:
    """True when path (relative or absolute) is in the allowed set of git paths."""
    try:
        rel = path.resolve().relative_to(Path.cwd().resolve())
    except ValueError:
        return False
    return rel in allowed


def get_affected_tests() -> set[Path]:
    """Find tests in shared directories that might be affected by changes.

    This helper is not part of the pre-commit selection: collect_test_files does
    not call it, so the hook runs only staged test files and the companions of
    staged files. It is kept for callers that want the wider shared-folder list.
    """
    shared_dirs = [
        Path("tests/hooks"),
        Path("src/pars_local_mcp/tests"),
        Path("tests/integration"),
    ]

    # Test files with pre-existing unresolved issues
    broken_tests = {
        Path(
            "src/pars_local_mcp/tests/test_client_all_tools.py"
        ),  # hiclass import error
        Path("src/pars_local_mcp/tests/test_fake_data.py"),  # missing CSV file
        Path("src/pars_local_mcp/tests/test_inference.py"),  # missing data dependencies
        Path("src/pars_local_mcp/tests/test_labels.py"),  # missing data dependencies
        Path("src/pars_local_mcp/tests/test_readme_structure.py"),  # dependency issue
        Path(
            "src/pars_local_mcp/tests/test_server_initialization.py"
        ),  # dependency issue
        Path("src/pars_local_mcp/tests/test_splits.py"),  # missing data dependencies
        Path("src/pars_local_mcp/tests/test_tools.py"),  # dependency issue
        Path("src/pars_local_mcp/tests/test_training.py"),  # dependency issue
        Path(
            "src/pars_local_mcp/tests/integration/test_pars_tools_client.py"
        ),  # hiclass error
        Path("src/pars_local_mcp/tests/unit/test_pars_connection.py"),  # import error
        Path("src/pars_local_mcp/tests/unit/test_pars_models.py"),  # import error
        Path("src/pars_local_mcp/tests/unit/test_pars_snapshots.py"),  # import error
    }

    affected = set()
    for shared_dir in shared_dirs:
        if shared_dir.exists():
            for test_file in shared_dir.glob("test_*.py"):
                if test_file.is_file() and test_file not in broken_tests:
                    affected.add(test_file)

    return affected


def collect_test_files(argv_files: list[str]) -> set[Path]:
    """Select staged test files and the companions of staged files.

    Untracked and unstaged files are never selected.
    """
    staged = get_changed_files()
    # Also include files passed as arguments (from pre-commit)
    staged.update(Path(f) for f in argv_files if Path(f).suffix == ".py")
    allowed = staged | get_previously_committed_files()

    test_files = set()
    for changed_file in staged:
        if not changed_file.exists() or changed_file.suffix != ".py":
            continue
        if changed_file.name.startswith("test_") or changed_file.name.endswith(
            "_test.py"
        ):
            # A staged test file runs itself
            test_files.add(changed_file)
        else:
            # Companions count only when they are staged or committed
            companions = find_companion_tests(changed_file)
            test_files.update(c for c in companions if is_allowed(c, allowed))

    return test_files


def main():
    """Collect and run relevant tests."""
    test_files = collect_test_files(sys.argv[1:])

    # If no tests found, pass (nothing to test)
    if not test_files:
        print("OK: no tests to run (no changes or test files found)")
        return 0

    # Run pytest on collected test files with fast markers
    test_files_list = sorted(str(f) for f in test_files)
    cmd = [
        "uv",
        "run",
        "python",
        "-m",
        "pytest",
        "-p",
        "no:phoenix",
        "-m",
        "not slow and not integration",
        "--maxfail=1",
        "--disable-warnings",
        "-v",
    ] + test_files_list

    print("Running tests for changed files and companions:")
    for f in test_files_list:
        print(f"  • {f}")
    print()

    result = subprocess.run(cmd)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
