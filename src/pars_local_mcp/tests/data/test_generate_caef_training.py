from __future__ import annotations

from pars_local_mcp.data.generate_caef_training import LABEL_COLUMNS, build_labeled_rows

# (wbs_code, CAEF label, level)
HIERARCHY = [
    ("1", "Root Label", 1),
    ("1.1", "Level Two Label", 2),
    ("1.1.1", "Level Three Label", 3),
    ("1.1.1.1", "Level Four Label", 4),
    ("1.1.1.1.1", "Level Five Label", 5),
    ("1.1.1.1.1.1", "Level Six Label", 6),
    ("1.1.1.1.1.1.1", "Level Seven Label", 7),
    ("1.1.1.1.1.1.1.1", "Level Eight Label", 8),
    ("1.2", "Sibling Two Label", 2),
]
LABELS = {code: label for code, label, _ in HIERARCHY}


def _rows_by_code(rows, project="SYN-001"):
    return {r["wbs_code"]: r for r in rows if r["parsid"] == project}


def test_deepest_leaf_carries_all_seven_ancestor_labels():
    rows = build_labeled_rows(HIERARCHY, ["SYN-001"], seed=1)

    leaf = next(r for r in rows if r["wbs_code"] == "1.1.1.1.1.1.1.1")
    assert leaf["caef_level_2"] == LABELS["1.1"]
    assert leaf["caef_level_3"] == LABELS["1.1.1"]
    assert leaf["caef_level_4"] == LABELS["1.1.1.1"]
    assert leaf["caef_level_5"] == LABELS["1.1.1.1.1"]
    assert leaf["caef_level_6"] == LABELS["1.1.1.1.1.1"]
    assert leaf["caef_level_7"] == LABELS["1.1.1.1.1.1.1"]
    assert leaf["caef_level_8"] == LABELS["1.1.1.1.1.1.1.1"]


def test_shallow_element_leaves_deeper_label_columns_empty():
    rows = build_labeled_rows(HIERARCHY, ["SYN-001"], seed=1)

    shallow = next(r for r in rows if r["wbs_code"] == "1.1.1.1")
    assert shallow["caef_level_4"] == LABELS["1.1.1.1"]
    assert shallow["caef_level_5"] == ""
    assert shallow["caef_level_8"] == ""


def test_parentage_follows_level_numbers_when_codes_are_broken():
    broken = [
        ("A", "Alpha", 2),
        ("A.B", "Bravo", 3),
        ("??", "Charlie", 4),
        ("zz", "Delta", 5),
        ("dup", "Echo", 3),
        ("q", "Foxtrot", 4),
    ]
    rows = build_labeled_rows(broken, ["SYN-001"], seed=1)

    leaf = next(r for r in rows if r["wbs_code"] == "zz")
    assert leaf["caef_level_2"] == "Alpha"
    assert leaf["caef_level_3"] == "Bravo"
    assert leaf["caef_level_4"] == "Charlie"
    assert leaf["caef_level_5"] == "Delta"

    after = next(r for r in rows if r["wbs_code"] == "q")
    assert after["caef_level_2"] == "Alpha"
    assert after["caef_level_3"] == "Echo"
    assert after["caef_level_4"] == "Foxtrot"
    assert after["caef_level_5"] == ""


def test_root_level_element_is_not_labelled():
    rows = build_labeled_rows(HIERARCHY, ["SYN-001"], seed=1)

    assert "1" not in {r["wbs_code"] for r in rows}


def test_one_row_per_element_per_project():
    rows = build_labeled_rows(HIERARCHY, ["SYN-001", "SYN-002"], seed=1)

    assert len(rows) == 16
    assert {r["parsid"] for r in rows} == {"SYN-001", "SYN-002"}


def test_titles_are_generated_unique_and_reproducible_with_seed():
    first = build_labeled_rows(HIERARCHY, ["SYN-001"], seed=7)
    second = build_labeled_rows(HIERARCHY, ["SYN-001"], seed=7)
    other = build_labeled_rows(HIERARCHY, ["SYN-001"], seed=8)

    titles = [r["title"] for r in first]
    assert all(titles)
    assert len(set(titles)) == len(titles)
    assert titles == [r["title"] for r in second]
    assert titles != [r["title"] for r in other]
    assert not set(titles) & set(LABELS.values())


def test_ancestor_labels_and_titles_match_across_projects():
    rows = build_labeled_rows(HIERARCHY, ["SYN-001", "SYN-002"], seed=1)

    def fingerprint(project):
        return sorted(
            (r["wbs_code"], r["title"], tuple(r[c] for c in LABEL_COLUMNS))
            for r in rows
            if r["parsid"] == project
        )

    assert fingerprint("SYN-001") == fingerprint("SYN-002")


def test_columns_match_labeled_wbs_schema():
    rows = build_labeled_rows(HIERARCHY, ["SYN-001"], seed=1)

    assert set(rows[0]) == {"parsid", "wbs_code", "title", *LABEL_COLUMNS}
