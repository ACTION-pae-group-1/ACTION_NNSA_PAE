"""Dataset integrity: schema, size, synthetic-only references, XML/CSV agreement."""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import pytest
import yaml

EVAL_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = EVAL_DIR.parents[1]
sys.path.insert(0, str(EVAL_DIR))
sys.path.insert(0, str(REPO_ROOT / "src"))

from agent import READ_ONLY_TOOLS  # noqa: E402

from pars_local_mcp.storage.initialization import (  # noqa: E402
    generate_synthetic_wbs_elements,
)

CONFIG = yaml.safe_load((EVAL_DIR / "datasets.yaml").read_text(encoding="utf-8"))[
    "datasets"
]
SYNTHETIC = {
    (p.upper(), code) for p, code, _title, _level in generate_synthetic_wbs_elements()
}
SYNTHETIC_PROJECTS = {p for p, _ in SYNTHETIC}
CATEGORIES = {
    "discovery",
    "search",
    "navigation",
    "complex",
    "edge_cases",
    "out_of_scope",
}
# Deliberately invalid references used by edge-case rows.
EDGE_CASE_PROJECTS = {"PROJ_999"}
EDGE_CASE_CODES = {"09.09"}
# Known defect inherited from frozen pars-eval-0 (row 17): PROJ_001 has no '02.01',
# so that row's reference answer is wrong. Allowed only within the inherited rows.
INHERITED_MISSING_CODES = {"02.01"}


def _csv(name: str) -> pd.DataFrame:
    return pd.read_csv(EVAL_DIR / CONFIG[name]["csv_path"])


def _xml_questions(name: str) -> list[ET.Element]:
    xml_path = (EVAL_DIR / CONFIG[name]["csv_path"]).parents[1] / "evaluation.xml"
    return ET.parse(xml_path).getroot().findall("question")


@pytest.mark.parametrize("name", sorted(CONFIG))
def test_schema_is_exactly_input_and_output_keys(name: str) -> None:
    df = _csv(name)
    expected = CONFIG[name]["input_keys"] + CONFIG[name]["output_keys"]
    # No extra columns: human labels are supplied separately by the user.
    assert list(df.columns) == expected
    assert not df.isna().any().any()
    assert (df.apply(lambda col: col.str.strip()) != "").all().all()
    assert not df["query"].duplicated().any()


def test_pars_eval_1_has_about_sixty_rows_and_keeps_pars_eval_0_first() -> None:
    v0, v1 = _csv("pars-eval-0"), _csv("pars-eval-1")
    assert 55 <= len(v1) <= 65
    pd.testing.assert_frame_equal(v1.head(len(v0)), v0)


def test_pars_eval_0_is_frozen_at_25_rows() -> None:
    assert len(_csv("pars-eval-0")) == 25


def test_pars_eval_1_xml_matches_csv_in_order() -> None:
    df = _csv("pars-eval-1")
    questions = _xml_questions("pars-eval-1")
    assert [q.findtext("text") for q in questions] == df["query"].tolist()
    assert [q.findtext("answer") for q in questions] == df["responses"].tolist()
    assert [int(q.get("id")) for q in questions] == list(range(1, len(df) + 1))


def test_pars_eval_1_xml_metadata_is_valid() -> None:
    for q in _xml_questions("pars-eval-1"):
        assert q.get("category") in CATEGORIES, q.get("id")
        assert q.findtext("difficulty") in {"easy", "medium", "hard"}, q.get("id")
        tools = [t.strip() for t in q.findtext("tools_expected").split(",")]
        if q.get("category") == "out_of_scope":
            assert tools == ["none"], q.get("id")
        else:
            assert set(tools) <= set(READ_ONLY_TOOLS), q.get("id")


def test_pars_eval_1_references_only_synthetic_projects_and_codes() -> None:
    inherited = len(_csv("pars-eval-0"))
    for idx, query in enumerate(_csv("pars-eval-1")["query"]):
        projects = {p.upper() for p in re.findall(r"proj_\d+", query, re.I)}
        assert projects <= SYNTHETIC_PROJECTS | EDGE_CASE_PROJECTS, query
        codes = set(re.findall(r"'(\d{2}(?:\.\d{2})*)'", query)) - EDGE_CASE_CODES
        if idx < inherited:
            codes -= INHERITED_MISSING_CODES
        real = projects & SYNTHETIC_PROJECTS
        for code in codes:
            assert any((p, code) in SYNTHETIC for p in real), (query, code)


def test_new_rows_do_not_use_the_inherited_missing_codes() -> None:
    new = _csv("pars-eval-1")["query"].iloc[len(_csv("pars-eval-0")) :]
    for query in new:
        assert not set(re.findall(r"'([\d.]+)'", query)) & INHERITED_MISSING_CODES
