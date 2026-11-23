"""Tests for scripts/check_manifest_hashes.py, the pinned-file hash guardrail.

Each test builds a throwaway Git repository so the check runs against real
Git index and attribute behaviour, not mocks. The last test runs the check on
this repository itself, which is what keeps a stale hash out of main.
"""

from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "check_manifest_hashes.py"
_SPEC = importlib.util.spec_from_file_location("check_manifest_hashes", SCRIPT)
assert _SPEC is not None and _SPEC.loader is not None
checker = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = checker  # dataclasses look the module up by name
_SPEC.loader.exec_module(checker)

LF_BYTES = b"series_id\tvalue\nA1\t100\nA2\t200\n"
CRLF_BYTES = LF_BYTES.replace(b"\n", b"\r\n")
SPEC = checker.ManifestSpec("pinned/input.json", "path", "pinned")

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git is required")


@pytest.fixture(autouse=True)
def isolate_git_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep temporary Git operations away from the parent repository."""
    for name in (
        "GIT_INDEX_FILE",
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_COMMON_DIR",
    ):
        monkeypatch.delenv(name, raising=False)


def _git(root: Path, *args: str) -> None:
    env = os.environ.copy()
    for name in (
        "GIT_INDEX_FILE",
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_COMMON_DIR",
    ):
        env.pop(name, None)

    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr


def _write_manifest(root: Path, entries: list[dict[str, object]]) -> Path:
    path = root / SPEC.manifest
    path.write_text(json.dumps({"files": entries}, indent=2) + "\n", encoding="utf-8")
    return path


def _entry(data: bytes, name: str = "a.txt") -> dict[str, object]:
    return {
        "path": name,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
    }


def _commit_all(root: Path, message: str = "update") -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "test")
    _git(tmp_path, "config", "core.autocrlf", "false")
    (tmp_path / ".gitattributes").write_text("pinned/** -text\n", encoding="utf-8")
    (tmp_path / "pinned").mkdir()
    (tmp_path / "pinned" / "a.txt").write_bytes(LF_BYTES)
    _write_manifest(tmp_path, [_entry(LF_BYTES)])
    _commit_all(tmp_path, "initial")
    return tmp_path


def test_matching_manifest_passes(repo: Path) -> None:
    assert checker.check(repo, [SPEC]) == []


def test_hash_from_a_crlf_copy_is_reported_with_a_line_ending_hint(repo: Path) -> None:
    _write_manifest(repo, [_entry(CRLF_BYTES)])

    problems = checker.check(repo, [SPEC])

    assert {problem.kind for problem in problems} == {"hash", "size"}
    assert all(problem.file == "pinned/a.txt" for problem in problems)
    hash_problem = next(problem for problem in problems if problem.kind == "hash")
    assert "CRLF" in str(hash_problem)


def test_working_copy_that_differs_from_git_is_reported(repo: Path) -> None:
    # A Windows checkout made before `-text` existed keeps CRLF files on disk,
    # and Git's stat cache can hide that from `git status`.
    (repo / "pinned" / "a.txt").write_bytes(CRLF_BYTES)

    problems = checker.check(repo, [SPEC])

    assert [problem.kind for problem in problems] == ["worktree"]


def test_file_git_may_convert_is_reported(repo: Path) -> None:
    (repo / ".gitattributes").write_text("", encoding="utf-8")
    _commit_all(repo)

    problems = checker.check(repo, [SPEC])

    assert [problem.kind for problem in problems] == ["attribute"]
    assert ".gitattributes" in str(problems[0])


def test_binary_file_without_attribute_is_accepted(repo: Path) -> None:
    binary = b"PK\x03\x04\x00\x00binary\x00content"
    (repo / "pinned" / "book.xlsx").write_bytes(binary)
    (repo / ".gitattributes").write_text("pinned/*.txt -text\n", encoding="utf-8")
    _write_manifest(repo, [_entry(LF_BYTES), _entry(binary, "book.xlsx")])
    _commit_all(repo)

    assert checker.check(repo, [SPEC]) == []


def test_pinned_file_missing_from_git_is_reported(repo: Path) -> None:
    (repo / "pinned" / "new.txt").write_bytes(LF_BYTES)
    _write_manifest(repo, [_entry(LF_BYTES), _entry(LF_BYTES, "new.txt")])

    problems = checker.check(repo, [SPEC])

    assert [problem.kind for problem in problems] == ["untracked"]


def test_size_mismatch_is_reported(repo: Path) -> None:
    entry = _entry(LF_BYTES)
    entry["size_bytes"] = len(LF_BYTES) + 1
    _write_manifest(repo, [entry])

    problems = checker.check(repo, [SPEC])

    assert [problem.kind for problem in problems] == ["size"]


def test_unregistered_manifest_is_reported(repo: Path) -> None:
    other = repo / "other"
    other.mkdir()
    (other / "extra-manifest.json").write_text(
        json.dumps({"files": [{"path": "x.txt", "sha256": "0" * 64}]}),
        encoding="utf-8",
    )
    (other / "notes.json").write_text(
        json.dumps({"sha256": "0" * 64}), encoding="utf-8"
    )
    _commit_all(repo)

    problems = checker.find_unregistered(repo, [SPEC])

    assert [(problem.manifest, problem.kind) for problem in problems] == [
        ("other/extra-manifest.json", "unregistered")
    ]


def test_fix_rewrites_hash_and_size_then_check_passes(repo: Path) -> None:
    _write_manifest(repo, [_entry(CRLF_BYTES)])

    updated = checker.fix(repo, [SPEC])

    assert updated == [SPEC.manifest]
    assert checker.check(repo, [SPEC]) == []
    entry = json.loads((repo / SPEC.manifest).read_text(encoding="utf-8"))["files"][0]
    assert entry["size_bytes"] == len(LF_BYTES)


def test_fix_refuses_when_working_copy_differs_from_git(repo: Path) -> None:
    (repo / "pinned" / "a.txt").write_bytes(CRLF_BYTES)
    _write_manifest(repo, [_entry(CRLF_BYTES)])

    with pytest.raises(checker.FixRefusedError, match="working copy"):
        checker.fix(repo, [SPEC])


def test_fix_leaves_matching_manifests_untouched(repo: Path) -> None:
    before = (repo / SPEC.manifest).read_bytes()

    assert checker.fix(repo, [SPEC]) == []
    assert (repo / SPEC.manifest).read_bytes() == before


def test_main_reports_drift_and_names_the_fix(repo: Path) -> None:
    _write_manifest(repo, [_entry(CRLF_BYTES)])
    out, err = io.StringIO(), io.StringIO()

    with redirect_stdout(out), redirect_stderr(err):
        code = checker.main(["--root", str(repo)], specs=[SPEC])

    assert code == 1
    assert "poe manifest-fix" in err.getvalue()


def test_main_passes_on_a_clean_repository(repo: Path) -> None:
    out = io.StringIO()

    with redirect_stdout(out):
        code = checker.main(["--root", str(repo)], specs=[SPEC])

    assert code == 0
    assert "PASS" in out.getvalue()


def test_check_without_git_hashes_the_working_tree(tmp_path: Path) -> None:
    (tmp_path / "pinned").mkdir()
    (tmp_path / "pinned" / "a.txt").write_bytes(LF_BYTES)
    _write_manifest(tmp_path, [_entry(LF_BYTES)])

    assert checker.check(tmp_path, [SPEC]) == []
    _write_manifest(tmp_path, [_entry(CRLF_BYTES)])
    kinds = {problem.kind for problem in checker.check(tmp_path, [SPEC])}
    assert kinds == {"hash", "size"}


def test_this_repository_pins_match_git() -> None:
    """The guardrail: every pinned file in this repository matches its manifest."""
    root = checker.REPO_ROOT
    if not (root / ".git").exists():
        pytest.skip("not a Git checkout")

    problems = checker.check(root, checker.MANIFESTS)
    problems += checker.find_unregistered(root, checker.MANIFESTS)

    assert problems == [], "\n".join(str(problem) for problem in problems)
