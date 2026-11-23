"""Contract tests: the fake PARS client answers every builder in PARS shapes."""

from cost_intel_app import pars_panels as pp
from cost_intel_app.tests.fake_pars import FakeParsMock, _like


def guarded(fake=None):
    return pp.GuardedClient(fake or FakeParsMock())


def test_every_builder_loads_from_the_fake_pars_data():
    client = guarded()
    assert pp.project_list(client)["state"] == "loaded"
    assert pp.project_header(client, "100")["state"] == "loaded"
    assert pp.hierarchy(client, "100", "1")["state"] == "loaded"
    assert pp.search(client, "100", "1.2")["state"] == "loaded"
    assert pp.lineage(client, "100", "1.2.1")["state"] == "loaded"
    assert pp.leaf_nodes(client, "100")["state"] == "loaded"
    assert pp.by_level(client, "100", 2)["state"] == "loaded"
    evidence = pp.evidence(client)
    assert evidence["state"] == "loaded"
    assert evidence["read_only_views"] is True
    assert pp.run_status(client, "r1")["state"] == "loaded"
    assert pp.read_only_data(client, "descriptions", True)["state"] == "loaded"
    assert pp.read_only_data(client, "rows", True)["state"] == "loaded"


def test_a_failing_tool_shows_only_its_own_error_state():
    client = guarded(FakeParsMock(fail={"get_leaf_nodes"}))
    assert pp.leaf_nodes(client, "100")["state"] == "error"
    assert pp.project_header(client, "100")["state"] == "loaded"


def test_fake_data_is_labeled_synthetic():
    assert pp.evidence(guarded())["label"] == "synthetic"


PARS_DESCRIPTION_COLUMNS = [
    "parsid",
    "program",
    "project_name",
    "project_status",
    "project_type",
    "project_description",
]
PARS_WBS_COLUMNS = [
    "parsid",
    "program",
    "project_name",
    "wbs",
    "wbs_level",
    "wbs_title",
]


def test_source_reads_use_the_pars_column_names():
    # Pinned to src/pars_local_mcp/wbs_port/pipeline.py (SOURCE_READS, feat/pars_mcp).
    descriptions = FakeParsMock().call("get_wbs_project_descriptions", {"limit": 20})
    rows = FakeParsMock().call("get_wbs_rows", {"limit": 20})
    assert descriptions["columns"] == PARS_DESCRIPTION_COLUMNS
    assert rows["columns"] == PARS_WBS_COLUMNS
    assert all(set(r) == set(PARS_WBS_COLUMNS) for r in rows["rows"])
    assert all(set(r) == set(PARS_DESCRIPTION_COLUMNS) for r in descriptions["rows"])


def test_search_matches_wbs_codes_not_titles_like_pars():
    assert pp.search(guarded(), "100", "pump")["state"] == "empty"
    panel = pp.search(guarded(), "100", "1.2")
    assert panel["state"] == "loaded"
    assert panel["rows"][0]["wbs_code"] == "1.2.1"


def test_fake_search_uses_sql_like_semantics_as_pars_does():
    fake = FakeParsMock()
    assert fake.call("search_wbs", {"wbs_pattern": "1.2"})["elements"] == []
    matched = fake.call("search_wbs", {"wbs_pattern": "1.2%"})["elements"]
    assert [e["wbs_code"] for e in matched] == ["1.2.1"]


def test_like_treats_the_dot_as_a_literal_and_underscore_as_one_character():

    assert _like("1.2", "1.2")
    assert not _like("1x2", "1.2")
    assert _like("12", "1_")
    assert not _like("1", "1_")


def test_like_percent_matches_newlines_as_duckdb_does():

    assert _like("a\nb", "a%b")


def test_fake_search_with_an_empty_pattern_applies_no_filter():
    response = FakeParsMock().call("search_wbs", {"wbs_pattern": ""})
    assert [e["wbs_code"] for e in response["elements"]] == ["1.2.1"]
