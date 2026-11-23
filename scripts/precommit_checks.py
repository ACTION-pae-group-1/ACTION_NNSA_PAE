"""Small offline-friendly repository hygiene checks for pre-commit."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10
    import tomli as tomllib
from collections.abc import Iterable

import yaml

MAX_TEXT_BYTES = 5 * 1024 * 1024
MERGE_MARKERS = ("<<<<<<< ", "=======", ">>>>>>> ")
PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"
)


def _iter_paths(arguments: Iterable[str]) -> Iterable[Path]:
    for value in arguments:
        path = Path(value)
        if path.is_file():
            yield path


def _read_text(path: Path) -> str | None:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        print(f"{path}: cannot read file: {exc}", file=sys.stderr)
        return None
    if len(payload) > MAX_TEXT_BYTES:
        print(
            f"{path}: text file exceeds {MAX_TEXT_BYTES // (1024 * 1024)} MiB",
            file=sys.stderr,
        )
        return None
    try:
        return payload.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _syntax_error(path: Path, text: str) -> str | None:
    try:
        if path.suffix == ".json":
            json.loads(text)
        elif path.suffix == ".toml":
            tomllib.loads(text)
        elif path.suffix in {".yaml", ".yml"}:
            yaml.safe_load(text)
    except Exception as exc:  # noqa: BLE001 - user-facing validation summary
        return f"invalid {path.suffix.lstrip('.').upper()}: {exc}"
    return None


def check_path(path: Path) -> list[str]:
    text = _read_text(path)
    if text is None:
        return []
    problems: list[str] = []
    if text and not text.endswith("\n"):
        problems.append("missing final newline")
    if any(
        line.rstrip("\r\n") != line.rstrip("\r\n ") for line in text.splitlines(True)
    ):
        problems.append("trailing whitespace")
    # Check for actual merge conflict markers
    # Markers must match the exact pattern:
    # <<<<<<< (with space), ======= (alone), >>>>>>> (with space)
    for line in text.splitlines():
        if line.startswith("<<<<<<< ") or line.startswith(">>>>>>> "):
            problems.append("unresolved merge-conflict marker")
            break
        # For the middle marker, match exactly "======="
        # and nothing else (or only whitespace after)
        if line == "=======" or (line.startswith("=======") and line[7:].strip() == ""):
            problems.append("unresolved merge-conflict marker")
            break
    # Check for private key material, but skip lines with pragma: allowlist secret
    for line in text.splitlines():
        if PRIVATE_KEY_PATTERN.search(line) and "pragma: allowlist secret" not in line:
            problems.append("private-key material detected")
            break
    syntax_problem = _syntax_error(path, text)
    if syntax_problem:
        problems.append(syntax_problem)
    return problems


def main(arguments: list[str] | None = None) -> int:
    failures = 0
    for path in _iter_paths(arguments if arguments is not None else sys.argv[1:]):
        for problem in check_path(path):
            failures += 1
            print(f"{path}: {problem}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
