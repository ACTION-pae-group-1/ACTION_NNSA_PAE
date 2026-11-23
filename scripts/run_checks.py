"""Run Poe quality checks with explicit step labels and actionable errors.

The checks remain defined in ``pyproject.toml``; this runner calls each Poe
subtask rather than duplicating its underlying command or changing its behavior.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHECKS = (
    "lint",
    "format-check",
    "typecheck",
    "pyright-check",
    "manifest-check",
    "test",
)
REMEDIES = {
    "lint": "Inspect Ruff violations: uv run --locked poe lint",
    "format-check": "Apply Ruff formatting: uv run --locked poe format",
    "typecheck": "Inspect typing errors: uv run --locked poe typecheck",
    "pyright-check": "Inspect eval typing: uv run --locked poe pyright-check",
    "manifest-check": (
        "Inspect pinned-file hash drift: uv run --locked poe manifest-check"
        " (if the files are right: uv run --locked poe manifest-fix)"
    ),
    "test": "Inspect failing tests: uv run --locked poe test",
}


def main() -> int:
    total = len(CHECKS)
    for number, task in enumerate(CHECKS, start=1):
        print(f"\n[check {number}/{total}] START {task}", flush=True)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "poethepoet", task],
                cwd=PROJECT_ROOT,
                check=False,
            )
        except KeyboardInterrupt:
            print(f"\n[check {number}/{total}] INTERRUPTED {task}", file=sys.stderr)
            return 130
        except OSError as exc:
            print(
                f"\n[check {number}/{total}] FAILED {task}: could not launch: {exc}",
                file=sys.stderr,
            )
            return 1

        if result.returncode != 0:
            print(
                f"\n[check {number}/{total}] FAILED {task} "
                f"(exit code {result.returncode})",
                file=sys.stderr,
            )
            print(f"  Next: {REMEDIES[task]}", file=sys.stderr)
            print("  Remaining checks were not run.", file=sys.stderr)
            return result.returncode if result.returncode > 0 else 1

        print(f"[check {number}/{total}] PASS {task}", flush=True)

    print(f"\n[check] PASS: all {total} checks completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
