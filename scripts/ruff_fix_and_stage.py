#!/usr/bin/env python3
"""Run ruff with automatic fixes and re-stage modified files."""

import subprocess
import sys


def main(arguments: list[str] | None = None) -> int:
    """Fix files with ruff and re-stage them."""
    args = arguments if arguments is not None else sys.argv[1:]

    # Run ruff check --fix on the files
    check_result = subprocess.run(
        ["uv", "run", "ruff", "check", "--fix"] + args,
        capture_output=False,
    )

    # Run ruff format on the files
    format_result = subprocess.run(
        ["uv", "run", "ruff", "format"] + args,
        capture_output=False,
    )

    # Re-stage the files
    if args:
        subprocess.run(["git", "add"] + args, capture_output=True)

    # Return failure only if both succeeded (no changes needed)
    # If either made changes, return 1 to let pre-commit re-check
    return 1 if (check_result.returncode or format_result.returncode) else 0


if __name__ == "__main__":
    raise SystemExit(main())
