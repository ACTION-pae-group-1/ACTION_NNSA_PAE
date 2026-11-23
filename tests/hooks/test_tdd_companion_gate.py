"""TDD companion gate: a merge from trunk is not re-gated; the branch's own work is."""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude" / "hooks"))

import tdd_companion_gate as gate  # noqa: E402

GIT_IDENTITY = ["-c", "user.name=test", "-c", "user.email=test@example.invalid"]


def git(repo: Path, *args: str, check: bool = True) -> None:
    subprocess.run(
        ["git", *GIT_IDENTITY, *args], cwd=repo, check=check, capture_output=True
    )


def write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def commit(repo: Path, rel: str, text: str, message: str) -> None:
    write(repo, rel, text)
    git(repo, "add", "--", rel)
    git(repo, "commit", "-q", "-m", message)


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    commit(tmp_path, "README.md", "base\n", "base")
    git(tmp_path, "checkout", "-q", "-b", "feature")
    commit(tmp_path, "feature_note.txt", "feature\n", "feature work")
    git(tmp_path, "checkout", "-q", "main")
    return tmp_path


def test_production_file_that_arrives_unchanged_from_trunk_is_not_gated(repo):
    commit(repo, "pkg/widget.py", "VALUE = 1\n", "trunk adds widget")
    git(repo, "checkout", "-q", "feature")
    git(repo, "merge", "--no-commit", "--no-ff", "main")

    assert gate.main(repo) == 0


def test_branch_production_file_without_companion_is_still_gated(repo):
    write(repo, "pkg/own.py", "VALUE = 2\n")
    git(repo, "add", "--", "pkg/own.py")

    assert gate.main(repo) == 1


def test_branch_file_staged_during_a_trunk_merge_is_still_gated(repo):
    commit(repo, "pkg/widget.py", "VALUE = 1\n", "trunk adds widget")
    git(repo, "checkout", "-q", "feature")
    git(repo, "merge", "--no-commit", "--no-ff", "main")
    write(repo, "pkg/own.py", "VALUE = 2\n")
    git(repo, "add", "--", "pkg/own.py")

    assert gate.main(repo) == 1


def test_conflict_resolution_that_differs_from_trunk_is_still_gated(repo):
    commit(repo, "pkg/shared.py", "TRUNK = 1\n", "trunk adds shared")
    git(repo, "checkout", "-q", "feature")
    commit(repo, "pkg/shared.py", "FEATURE = 1\n", "feature adds shared")
    git(repo, "merge", "--no-commit", "--no-ff", "main", check=False)
    write(repo, "pkg/shared.py", "RESOLVED = 1\n")
    git(repo, "add", "--", "pkg/shared.py")

    assert gate.main(repo) == 1
