"""Tests for the pure helper logic in the PARS gap-eval harness.

The harness's full main() flow (building an isolated environment, running all
16 tools through an in-process MCP client, checking deterministic
expectations) is exercised end-to-end by actually running it — see
eval/caef/results/release-2026-11-19/FINAL_EVALUATION_REPORT.md section 4.1
(81/81 rows pass). These tests cover the standalone helper functions that
don't require that full isolated environment: hashing, diffing, result
shaping, and the deterministic-check building blocks.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_pars_gap_eval as gap  # noqa: E402


def test_sha256_file_matches_hashlib(tmp_path):
    import hashlib

    f = tmp_path / "data.bin"
    f.write_bytes(b"some bytes to hash")
    assert gap.sha256_file(f) == hashlib.sha256(b"some bytes to hash").hexdigest()


def test_diff_snapshots_reports_changed_removed_and_added():
    before = {"a": "hash-a", "b": "hash-b", "c": "hash-c"}
    after = {"a": "hash-a", "b": "hash-b-changed", "d": "hash-d"}
    diff = gap.diff_snapshots(before, after)
    assert diff == {"changed": ["b"], "removed": ["c"], "added": ["d"]}


def test_diff_snapshots_reports_nothing_when_identical():
    snap = {"a": "hash-a", "b": "hash-b"}
    assert gap.diff_snapshots(snap, dict(snap)) == {
        "changed": [],
        "removed": [],
        "added": [],
    }


def test_error_text_prefers_error_then_text_then_exception():
    assert gap.error_text({"error": "boom"}) == "boom"
    assert gap.error_text({"__text__": "boom2"}) == "boom2"
    assert gap.error_text({"__exception__": "boom3"}) == "boom3"
    assert gap.error_text({}) == ""


def test_resolve_params_substitutes_dollar_prefixed_names():
    args = {"project_id": "proj_001", "level": 2}
    resolved = gap._resolve_params(["$project_id", "literal", "$level"], args)
    assert resolved == ["proj_001", "literal", 2]


def test_items_wraps_a_single_dict_and_walks_a_dotted_path():
    payload = {"result": {"rows": [{"id": 1}, {"id": 2}]}}
    assert gap._items(payload, None) == [payload]
    assert gap._items(payload, "result.rows") == [{"id": 1}, {"id": 2}]


def test_dotted_walks_nested_keys():
    payload = {"a": {"b": {"c": 42}}}
    assert gap._dotted(payload, "a.b.c") == 42


def test_check_builds_a_result_row_and_truncates_detail():
    row = gap.check("my_check", True, detail="x" * 500)
    assert row["name"] == "my_check"
    assert row["pass"] is True
    assert len(row["detail"]) == 300
    assert "observe_only" not in row


def test_check_marks_observe_only_checks():
    row = gap.check("observed", False, observe=True)
    assert row["observe_only"] is True


def test_gated_excludes_observe_only_checks():
    checks = [
        gap.check("gating", True),
        gap.check("observed", False, observe=True),
    ]
    assert gap.gated(checks) == [checks[0]]


def test_status_of_passes_only_when_every_gating_check_passes():
    assert gap.status_of([gap.check("a", True), gap.check("b", True)]) == "pass"
    assert gap.status_of([gap.check("a", True), gap.check("b", False)]) == "fail"
    # An observe-only failure must not gate the case.
    assert (
        gap.status_of([gap.check("a", True), gap.check("b", False, observe=True)])
        == "pass"
    )


def test_dir_listing_returns_empty_for_a_missing_root(tmp_path):
    assert gap.dir_listing(tmp_path / "does-not-exist") == {}


def test_dir_listing_lists_relative_paths_and_sizes(tmp_path):
    (tmp_path / "a.txt").write_text("hi", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.txt").write_text("hello", encoding="utf-8")
    listing = gap.dir_listing(tmp_path)
    assert listing == {"a.txt": 2, "sub/b.txt": 5}


def test_caef_source_sha256_is_a_well_formed_hex_digest():
    assert len(gap.CAEF_SOURCE_SHA256) == 64
    assert all(c in "0123456789abcdef" for c in gap.CAEF_SOURCE_SHA256)
