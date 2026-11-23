#!/usr/bin/env python3
"""Run ``ruff check`` on committed content (HEAD) instead of the working tree.

Each tracked Python file is read from HEAD with ``git show`` and piped to ruff
under its real repository path, so ruff's project settings match a normal run.
Unstaged and untracked edits are ignored, so they cannot cause a failure.
"""

import subprocess
import sys


def committed_python_files(ref: str) -> list[str]:
    """Return tracked .py paths in ``ref``, skipping the .claude directory."""
    listing = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", ref],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [
        path
        for path in listing.splitlines()
        if path.endswith(".py") and not path.startswith(".claude/")
    ]


def main() -> int:
    failed = False
    for path in committed_python_files("HEAD"):
        content = subprocess.run(
            ["git", "show", f"HEAD:{path}"],
            capture_output=True,
            check=True,
        ).stdout
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                "--force-exclude",
                "--stdin-filename",
                path,
                "-",
            ],
            input=content,
        )
        failed = failed or result.returncode != 0
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
