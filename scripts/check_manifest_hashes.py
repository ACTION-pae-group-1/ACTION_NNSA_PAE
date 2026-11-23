"""Check that every checksum-pinned data file still matches its manifest.

Several manifests here record the SHA-256 and byte size of the files they pin:
the BLS sample inputs that ``poe sample-snapshot`` builds from, the legacy
ingestion receipts, and the PARS reference workbook. ``bls-data build`` refuses
a pinned file whose bytes differ from its manifest, so a stale hash breaks the
Quick Start on every fresh clone.

The usual cause is line endings. A manifest written from a Windows working copy
whose files were converted to CRLF records hashes that match only on that
machine. So this check hashes the bytes Git stores (the index), not the working
tree, and it also fails when:

* the working copy of a pinned file differs from Git's copy;
* Git may convert a pinned file's line endings (it needs ``-text`` in
  ``.gitattributes``, or must be binary);
* a pinned file is not committed;
* a tracked manifest-shaped JSON file is not registered in ``MANIFESTS``.

Run from the repository root::

    uv run --locked poe manifest-check   # report drift; exit 1 if any
    uv run --locked poe manifest-fix     # rewrite sha256/size_bytes from Git's bytes
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class ManifestSpec:
    """Where a manifest lives and how its entries name the files they pin.

    ``base`` is the repository-relative directory that entry paths are relative
    to; an empty string means the repository root.
    """

    manifest: str
    path_key: str
    base: str


MANIFESTS: tuple[ManifestSpec, ...] = (
    ManifestSpec(
        "src/bls_mcp/docs/sample_data/pc-sample-input.json",
        "path",
        "src/bls_mcp/docs/sample_data",
    ),
    ManifestSpec(
        "src/bls_mcp/docs/sample_data/ci-sample-input.json",
        "path",
        "src/bls_mcp/docs/sample_data",
    ),
    ManifestSpec("data/manifest.json", "path_in_repo", ""),
    ManifestSpec("src/bls_mcp/data/manifest.json", "path_in_repo", "src/bls_mcp"),
    ManifestSpec("src/pars_local_mcp/data/PARS_MANIFEST.json", "path_in_repo", ""),
)

PATH_KEYS = ("path", "path_in_repo")
SKIPPED_DIRS = ("docs/vendor/",)


@dataclass(frozen=True)
class Problem:
    """One way a manifest and the files it pins disagree.

    ``kind`` is one of: ``missing``, ``untracked``, ``worktree`` (the working
    copy differs from Git's), ``attribute`` (Git may convert line endings),
    ``hash``, ``size``, ``manifest`` or ``unregistered``.
    """

    manifest: str
    file: str
    kind: str
    message: str

    def __str__(self) -> str:
        where = f"{self.manifest} -> {self.file}" if self.file else self.manifest
        return f"{where}: {self.message}"


class FixRefusedError(RuntimeError):
    """Raised when rewriting hashes would record bytes Git doesn't hold."""


class _Git:
    """The few Git queries the check needs, or None when not in a checkout."""

    def __init__(self, root: Path) -> None:
        self.root = root

    @classmethod
    def open(cls, root: Path) -> _Git | None:
        try:
            result = subprocess.run(
                ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                capture_output=True,
                check=False,
            )
        except OSError:
            return None
        if result.returncode != 0:
            return None
        top = Path(result.stdout.decode().strip()).resolve()
        return cls(root) if top == root.resolve() else None

    def _run(self, *args: str) -> bytes:
        result = subprocess.run(
            ["git", "-C", str(self.root), *args], capture_output=True, check=False
        )
        if result.returncode != 0:
            message = result.stderr.decode(errors="replace").strip()
            raise RuntimeError(f"git {' '.join(args)} failed: {message}")
        return result.stdout

    def tracked(self) -> set[str]:
        return {
            name for name in self._run("ls-files", "-z").decode().split("\0") if name
        }

    def index_bytes(self, path: str) -> bytes:
        return self._run("cat-file", "blob", f":{path}")

    def eol_info(self, paths: Sequence[str]) -> dict[str, tuple[str, str]]:
        """Map each path to Git's (index line-ending info, attribute) pair."""
        if not paths:
            return {}
        info: dict[str, tuple[str, str]] = {}
        raw = self._run("ls-files", "--eol", "-z", "--", *paths).decode()
        for record in filter(None, raw.split("\0")):
            meta, _, name = record.partition("\t")
            fields = meta.split()
            index_eol = fields[0] if fields else ""
            attr = fields[2] if len(fields) > 2 else ""
            info[name] = (index_eol, attr)
        return info


def _pinned_entries(document: Any, path_key: str) -> Iterator[dict[str, Any]]:
    """Yield every dict in a manifest that pins a file by path and SHA-256."""
    if isinstance(document, dict):
        if "sha256" in document and isinstance(document.get(path_key), str):
            yield document
        for value in document.values():
            yield from _pinned_entries(value, path_key)
    elif isinstance(document, list):
        for item in document:
            yield from _pinned_entries(item, path_key)


def _repo_path(spec: ManifestSpec, entry: dict[str, Any]) -> str:
    return str(PurePosixPath(spec.base, entry[spec.path_key]))


def _load(root: Path, spec: ManifestSpec) -> Any:
    return json.loads((root / spec.manifest).read_text(encoding="utf-8-sig"))


def _line_ending_hint(data: bytes, recorded: str) -> str:
    lf = data.replace(b"\r\n", b"\n")
    if hashlib.sha256(lf.replace(b"\n", b"\r\n")).hexdigest() == recorded:
        return (
            " The recorded hash matches this file with CRLF line endings, so it was"
            " taken from a working copy whose line endings Git converted."
        )
    if hashlib.sha256(lf).hexdigest() == recorded:
        return " The recorded hash matches this file with LF line endings."
    return ""


def _entry_problems(
    root: Path,
    git: _Git | None,
    spec: ManifestSpec,
    entry: dict[str, Any],
    tracked: set[str],
    eol: dict[str, tuple[str, str]],
) -> list[Problem]:
    path = _repo_path(spec, entry)
    problems: list[Problem] = []

    def report(kind: str, message: str) -> None:
        problems.append(Problem(spec.manifest, path, kind, message))

    on_disk = root / path
    if git is not None:
        if path not in tracked:
            report(
                "untracked",
                "pinned file is not in Git (never added, or deleted); `git add` or"
                " restore it, or remove it from the manifest.",
            )
            return problems
        data = git.index_bytes(path)
        index_eol, attr = eol.get(path, ("", ""))
        if "-text" not in attr and index_eol != "i/-text":
            report(
                "attribute",
                "Git may convert this file's line endings on checkout; add a"
                " `-text` rule for it to .gitattributes.",
            )
        if not on_disk.is_file() or on_disk.read_bytes() != data:
            report(
                "worktree",
                "working copy differs from Git's copy (often a checkout converted"
                " to CRLF before `-text` applied). Delete the file and run"
                " `git checkout -- <file>` to restore Git's bytes, or `git add` it"
                " if the edit is intended.",
            )
    else:
        if not on_disk.is_file():
            report("missing", "pinned file is missing.")
            return problems
        data = on_disk.read_bytes()

    recorded = str(entry["sha256"]).lower()
    actual = hashlib.sha256(data).hexdigest()
    if actual != recorded:
        report(
            "hash",
            f"sha256 is recorded as {recorded[:12]}… but the file is"
            f" {actual[:12]}….{_line_ending_hint(data, recorded)}",
        )
    size = entry.get("size_bytes")
    if size is not None and size != len(data):
        report(
            "size",
            f"size_bytes is recorded as {size} but the file is {len(data)} bytes.",
        )
    return problems


def check(root: Path, specs: Sequence[ManifestSpec]) -> list[Problem]:
    """Compare each registered manifest with the bytes Git stores."""
    git = _Git.open(root)
    tracked = git.tracked() if git is not None else set()
    problems: list[Problem] = []
    for spec in specs:
        if not (root / spec.manifest).is_file():
            problems.append(
                Problem(spec.manifest, "", "missing", "manifest file is missing.")
            )
            continue
        entries = list(_pinned_entries(_load(root, spec), spec.path_key))
        if not entries:
            problems.append(
                Problem(spec.manifest, "", "manifest", "no pinned files found.")
            )
            continue
        paths = [_repo_path(spec, entry) for entry in entries]
        eol = git.eol_info([p for p in paths if p in tracked]) if git else {}
        for entry in entries:
            problems += _entry_problems(root, git, spec, entry, tracked, eol)
    return problems


def find_unregistered(root: Path, specs: Sequence[ManifestSpec]) -> list[Problem]:
    """Find tracked manifest-shaped JSON files that ``check`` would never see."""
    git = _Git.open(root)
    if git is None:
        return []
    registered = {spec.manifest for spec in specs}
    problems: list[Problem] = []
    for name in sorted(git.tracked()):
        lower = name.lower()
        is_candidate = lower.endswith(".json") and (
            "manifest" in PurePosixPath(lower).name or lower.endswith("-input.json")
        )
        if not is_candidate or name in registered or lower.startswith(SKIPPED_DIRS):
            continue
        try:
            document = json.loads((root / name).read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if any(next(_pinned_entries(document, key), None) for key in PATH_KEYS):
            problems.append(
                Problem(
                    name,
                    "",
                    "unregistered",
                    "pins files by SHA-256 but is not registered in MANIFESTS in"
                    " scripts/check_manifest_hashes.py.",
                )
            )
    return problems


def _dump_like(original: str, document: Any) -> str:
    """Serialize with the original indent when it round-trips, else indent 2."""
    normalized = original.replace("\r\n", "\n")
    reference = json.loads(normalized)
    for indent in (2, 4):
        if json.dumps(
            reference, indent=indent, ensure_ascii=False
        ) == normalized.rstrip("\n"):
            break
    else:
        indent = 2
    return json.dumps(document, indent=indent, ensure_ascii=False) + "\n"


def fix(root: Path, specs: Sequence[ManifestSpec]) -> list[str]:
    """Rewrite sha256 and size_bytes from Git's bytes; return manifests changed."""
    blocking = [
        problem
        for problem in check(root, specs)
        if problem.kind in {"missing", "untracked", "worktree"}
    ]
    if blocking:
        details = "\n".join(f"  {problem}" for problem in blocking)
        raise FixRefusedError(
            "Refusing to rewrite hashes until every pinned file matches Git's copy"
            f" (the working copy is what the build reads):\n{details}"
        )
    git = _Git.open(root)
    updated: list[str] = []
    for spec in specs:
        manifest_path = root / spec.manifest
        original = manifest_path.read_text(encoding="utf-8-sig")
        document = json.loads(original)
        changed = False
        for entry in _pinned_entries(document, spec.path_key):
            path = _repo_path(spec, entry)
            data = git.index_bytes(path) if git else (root / path).read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            if str(entry["sha256"]).lower() != digest:
                entry["sha256"] = digest
                changed = True
            if "size_bytes" in entry and entry["size_bytes"] != len(data):
                entry["size_bytes"] = len(data)
                changed = True
        if changed:
            manifest_path.write_text(
                _dump_like(original, document), encoding="utf-8", newline="\n"
            )
            updated.append(spec.manifest)
    return updated


def main(
    argv: Sequence[str] | None = None,
    specs: Sequence[ManifestSpec] = MANIFESTS,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--fix",
        action="store_true",
        help="rewrite sha256 and size_bytes from the bytes Git stores",
    )
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = args.root.resolve()

    if args.fix:
        try:
            updated = fix(root, specs)
        except FixRefusedError as exc:
            print(f"manifest-fix: {exc}", file=sys.stderr)
            return 1
        for name in updated:
            print(f"manifest-fix: updated {name}; review and stage it.")
        if not updated:
            print("manifest-fix: nothing to update.")

    problems = check(root, specs) + find_unregistered(root, specs)
    if problems:
        print(f"manifest-check: FAIL ({len(problems)} problem(s))", file=sys.stderr)
        for problem in problems:
            print(f"  {problem}", file=sys.stderr)
        print(
            "  Next: if the pinned files are correct, run"
            " `uv run --locked poe manifest-fix`, review the diff, and stage it.",
            file=sys.stderr,
        )
        return 1
    total = sum(1 for _ in specs)
    print(f"manifest-check: PASS ({total} manifests match the bytes Git stores)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
