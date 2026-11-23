"""What sits directly above and beneath a series' code (get_series_hierarchy).

The rules are tested on their own first, then end to end on a small published
snapshot covering PPI (prefix nesting), CPI and ECI (display-level nesting).
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

pytest.importorskip("duckdb")

from bls_mcp.storage.connection import build_connection  # noqa: E402
from bls_mcp.storage.hierarchy import (  # noqa: E402
    industry_parents,
    level_parents,
    product_parents,
)
from bls_mcp.storage.models import SnapshotInfo, SourceFileReceipt  # noqa: E402
from bls_mcp.storage.schema import initialize_schema  # noqa: E402
from bls_mcp.storage.snapshots import (  # noqa: E402
    write_snapshot_info,
    write_source_file,
)
from bls_mcp.storage.store import BLSStore  # noqa: E402

# ---------------------------------------------------------------------------
# The nesting rules
# ---------------------------------------------------------------------------


def test_industry_codes_nest_by_prefix_ignoring_dash_padding() -> None:
    parents = industry_parents(["3211--", "32111-", "321113", "321114", "ATRADE"])
    assert parents == {
        "3211--": None,
        "32111-": "3211--",
        "321113": "32111-",
        "321114": "32111-",
        "ATRADE": None,  # special aggregates do not nest by prefix
    }


def test_product_codes_nest_by_longest_prefix_within_an_industry() -> None:
    parents = product_parents(
        "321113",
        ["321113", "3211133", "32111333", "321113P", "3241210", "3241210111"],
    )
    assert parents["3211133"] == "321113"  # top-level product -> industry total
    assert parents["32111333"] == "3211133"
    assert parents["321113P"] == "321113"
    # A code may skip lengths; the longest proper prefix is still the parent.
    assert parents["3241210111"] == "3241210"
    assert "321113" not in parents  # the industry total is the root


def test_display_levels_nest_by_nearest_shallower_code_in_sort_order() -> None:
    # (code, display_level, sort_sequence); deliberately unsorted input.
    rows = [
        ("530000", 3, 1376),  # real estate sits under financial activities
        ("000000", 0, 1),
        ("520A00", 2, 1311),
        ("520000", 3, 1312),
        ("522000", 4, 1316),
        ("336411", 6, 830),  # intermediate levels absent from the table
        ("300000", 2, 195),
    ]
    parents = level_parents(rows)
    assert parents["000000"] is None
    assert parents["520000"] == "520A00"
    assert parents["530000"] == "520A00"  # no shared prefix, still nested
    assert parents["522000"] == "520000"
    assert parents["336411"] == "300000"  # attaches to the nearest ancestor


def test_headings_bound_the_tree_but_are_never_a_parent() -> None:
    rows = [
        ("SA0", 0, 1),
        ("SAF", 1, 2),
        ("SAF1", 2, 3),
        ("SAX", 1, 4),  # "Special aggregate indexes", a heading
        ("SA0L1E", 2, 5),
    ]
    with_heading = level_parents(rows, frozenset({"SAX"}))
    # Without the heading's boundary SA0L1E would land under SAF.
    assert with_heading["SA0L1E"] == "SA0"
    assert with_heading["SAF1"] == "SAF"
    assert level_parents(rows)["SA0L1E"] == "SAX"


# ---------------------------------------------------------------------------
# End to end on a published snapshot
# ---------------------------------------------------------------------------

SAWMILLS = "PCU321113321113"
SOFTWOOD = "PCU3211133211133"
TWO_INCH = "PCU32111332111333"
GROUP = "PCU32111-32111-"
SAWMILLS_SA = "PCS321113321113"  # seasonally adjusted twin of SAWMILLS
CPI_FOOD = "CUUR0000SAF1"
CPI_FOOD_HOME = "CUUR0000SAF11"
CPI_ALL = "CUUR0000SA0"
ECI_TOTAL = "CIU2012300000000I"
ECI_WAGES = "CIU2022300000000I"
ECI_GOODS = "CIU201G000000000I"


def _catalog(series_id: str, program: str, title: str) -> tuple[object, ...]:
    return (series_id, program, title, None, False, 2020, "M01", 2025, "M12",
            "index", "base", True)  # fmt: skip


@pytest.fixture(scope="module")
def store(tmp_path_factory: pytest.TempPathFactory) -> BLSStore:
    path = tmp_path_factory.mktemp("hierarchy") / "snapshot.duckdb"
    with build_connection(path, threads=1) as conn:
        initialize_schema(conn)
        write_snapshot_info(
            conn, SnapshotInfo("hierarchy_test", datetime.now(UTC), ("pc", "cu", "ci"))
        )
        write_source_file(
            conn, SourceFileReceipt(1, "pc", "fixture.txt", "a" * 64, 1, "current")
        )
        conn.executemany(
            "INSERT INTO pc_industry VALUES (?, ?)",
            [
                ("3211--", "Sawmills and wood preservation"),
                ("32111-", "Sawmills and wood preservation"),
                ("321113", "Sawmills"),
                ("321114", "Wood preservation"),
            ],
        )
        conn.executemany(
            "INSERT INTO pc_product VALUES (?, ?, ?)",
            [
                ("321113", "321113", "Sawmills"),
                ("321113", "3211131", "Hardwood lumber, made in sawmills"),
                ("321113", "3211133", "Softwood lumber, made in sawmills"),
                ("321113", "32111333", "Softwood dressed 2-inch lumber"),
                ("321113", "3211135", "Wood chips, excluding field chips"),
                ("32111-", "32111-", "Sawmills and wood preservation"),
                ("321114", "321114", "Wood preservation"),
            ],
        )
        pc = [
            (GROUP, "32111-", "32111-", "U"),
            (SAWMILLS, "321113", "321113", "U"),
            (SAWMILLS_SA, "321113", "321113", "S"),
            (SOFTWOOD, "321113", "3211133", "U"),
            (TWO_INCH, "321113", "32111333", "U"),
            ("PCU3211133211131", "321113", "3211131", "U"),
            ("PCU321114321114", "321114", "321114", "U"),
        ]
        conn.executemany("INSERT INTO pc_series VALUES (?, ?, ?, ?, '201112')", pc)
        conn.executemany(
            "INSERT INTO cu_item VALUES (?, ?, ?, ?, ?)",
            [
                ("SA0", "All items", 0, True, 1),
                ("SAF", "Food and beverages", 1, True, 2),
                ("SAF1", "Food", 2, True, 3),
                ("SAF11", "Food at home", 3, True, 4),
                ("SAF116", "Alcoholic beverages", 3, True, 5),
                ("SAX", "Special aggregate indexes", 1, False, 6),  # a heading
                ("SA0L1E", "All items less food and energy", 2, True, 7),
            ],
        )
        conn.execute(
            "INSERT INTO cu_area VALUES ('0000', 'U.S. city average', 0, TRUE, 1)"
        )
        conn.executemany(
            "INSERT INTO cu_series VALUES (?, '0000', ?, 'U', 'R', 'S', '1982-84=100')",
            [(CPI_ALL, "SA0"), (CPI_FOOD, "SAF1"), (CPI_FOOD_HOME, "SAF11")],
        )
        conn.executemany(
            "INSERT INTO ci_dimension VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("owner", "2", "Private industry workers", 0, True, 1),
                ("industry", "000000", "All industries", 0, True, 1),
                ("industry", "G00000", "Goods-producing", 1, True, 2),
                ("industry", "230000", "Construction", 2, True, 3),
                ("occupation", "000000", "All occupations", 0, True, 1),
                ("subcell", "00", "All workers", 0, True, 1),
                ("subcell", "AD", "Bargaining Status", 1, False, 2),
                ("subcell", "23", "Union", 2, True, 3),
                ("area", "99999", "United States", 0, True, 1),
                ("estimate", "01", "Total compensation", 0, True, 1),
                ("estimate", "02", "Wages and salaries", 1, True, 2),
                ("estimate", "03", "Total benefits", 1, True, 3),
            ],
        )
        conn.executemany(
            "INSERT INTO ci_series VALUES "
            "(?, 'U', '2', ?, '000000', '00', '99999', ?, 'I')",
            [
                (ECI_TOTAL, "230000", "01"),
                (ECI_WAGES, "230000", "02"),
                (ECI_GOODS, "G00000", "01"),
            ],
        )
        titles = {
            GROUP: "Sawmills and wood preservation",
            SAWMILLS: "Sawmills",
            SAWMILLS_SA: "Sawmills (seasonally adjusted)",
            SOFTWOOD: "Sawmills-Softwood lumber",
            TWO_INCH: "Sawmills-Softwood dressed 2-inch lumber",
            "PCU3211133211131": "Sawmills-Hardwood lumber",
            "PCU321114321114": "Wood preservation",
        }
        conn.executemany(
            "INSERT INTO series_catalog VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [_catalog(sid, "pc", title) for sid, title in titles.items()]
            + [
                _catalog(CPI_ALL, "cu", "All items"),
                _catalog(CPI_FOOD, "cu", "Food"),
                _catalog(CPI_FOOD_HOME, "cu", "Food at home"),
                _catalog(ECI_TOTAL, "ci", "Total compensation, construction"),
                _catalog(ECI_WAGES, "ci", "Wages and salaries, construction"),
                _catalog(ECI_GOODS, "ci", "Total compensation, goods-producing"),
            ],
        )
        conn.executemany(
            "INSERT INTO observations VALUES (?, 2024, 'M13', 100.0, NULL, 1)",
            [(SOFTWOOD,), (ECI_WAGES,)],
        )
        conn.execute(
            "UPDATE snapshot_info "
            "SET lifecycle_state='PUBLISHED', validation_status='PASSED'"
        )
    return BLSStore(path)


def _codes(entries: tuple[object, ...]) -> list[tuple[str, str]]:
    return [(e.dimension, e.code) for e in entries]  # type: ignore[attr-defined]


def test_ppi_industry_total_lists_its_products_and_parent(store: BLSStore) -> None:
    found = store.series_hierarchy(SAWMILLS)
    assert found is not None
    assert found.snapshot_id == "hierarchy_test"
    assert _codes(found.parents) == [("industry", "32111-")]
    assert found.parents[0].series_id == GROUP
    assert _codes(found.sub_items) == [
        ("product", "3211131"),
        ("product", "3211133"),
        ("product", "3211135"),
    ]
    softwood = found.sub_items[1]
    assert (softwood.series_id, softwood.has_observations) == (SOFTWOOD, True)
    # Wood chips has a product code but no series in this snapshot.
    chips = found.sub_items[2]
    assert (chips.name, chips.series_id) == ("Wood chips, excluding field chips", None)


def test_ppi_product_lists_its_own_sub_products(store: BLSStore) -> None:
    found = store.series_hierarchy(SOFTWOOD)
    assert found is not None
    assert _codes(found.parents) == [("industry", "321113")]
    assert [(e.code, e.series_id) for e in found.sub_items] == [("32111333", TWO_INCH)]
    leaf = store.series_hierarchy(TWO_INCH)
    assert leaf is not None and leaf.sub_items == ()
    assert _codes(leaf.parents) == [("product", "3211133")]


def test_ppi_industry_group_lists_child_industries(store: BLSStore) -> None:
    found = store.series_hierarchy(GROUP)
    assert found is not None
    assert _codes(found.sub_items) == [("industry", "321113"), ("industry", "321114")]
    assert [e.series_id for e in found.sub_items] == [SAWMILLS, "PCU321114321114"]
    # The parent industry has no series in this snapshot, but is still named.
    assert [(e.code, e.series_id) for e in found.parents] == [("3211--", None)]


def test_ppi_links_series_with_the_same_seasonal_adjustment(store: BLSStore) -> None:
    found = store.series_hierarchy(SAWMILLS_SA)
    assert found is not None
    assert [e.series_id for e in found.sub_items] == [None, None, None]


def test_cpi_items_nest_by_display_level_skipping_headings(store: BLSStore) -> None:
    food = store.series_hierarchy(CPI_FOOD)
    assert food is not None
    assert [(e.code, e.series_id) for e in food.parents] == [("SAF", None)]
    assert [(e.code, e.series_id) for e in food.sub_items] == [
        ("SAF11", CPI_FOOD_HOME),
        ("SAF116", None),
    ]
    everything = store.series_hierarchy(CPI_ALL)
    assert everything is not None
    # "Special aggregate indexes" is a heading, so its item moves up a level.
    assert [e.code for e in everything.sub_items] == ["SAF", "SA0L1E"]


def test_eci_shows_what_total_compensation_includes(store: BLSStore) -> None:
    found = store.series_hierarchy(ECI_TOTAL)
    assert found is not None
    assert _codes(found.parents) == [("industry", "G00000")]
    assert found.parents[0].series_id == ECI_GOODS
    assert _codes(found.sub_items) == [("estimate", "02"), ("estimate", "03")]
    wages, benefits = found.sub_items
    assert (wages.series_id, wages.has_observations) == (ECI_WAGES, True)
    assert benefits.series_id is None
    # Worker cross-tabulations and geography are not composition.
    dimensions = {e.dimension for e in found.parents + found.sub_items}
    assert dimensions.isdisjoint({"subcell", "area", "owner"})


def test_unknown_series_is_none(store: BLSStore) -> None:
    assert store.series_hierarchy("PCU999999999999") is None


# ---------------------------------------------------------------------------
# Display order that is not a single hierarchy is not trusted
# ---------------------------------------------------------------------------


def test_display_order_with_several_top_level_codes_is_rejected() -> None:
    from bls_mcp.storage.hierarchy import display_order_problem

    # The published ECI occupation order: several codes share level 0, and
    # "Sales and office" (414300) sorts after "Office ..." (430000).
    occupations = [
        ("000000", 0, 1),
        ("410000", 0, 588),
        ("430000", 0, 621),
        ("414300", 1, 760),
    ]
    problem = display_order_problem(occupations)
    assert problem is not None and "3 codes at the top level" in problem
    # Followed blindly, the walk inverts the real relationship.
    assert level_parents(occupations)["414300"] == "430000"

    # A single root passes, and headings do not count as roots.
    industries = [("000000", 0, 1), ("230000", 2, 149), ("DISCON", 0, 1855)]
    assert display_order_problem(industries, frozenset({"DISCON"})) is None
    assert display_order_problem(industries) is not None


def test_status_is_unknown_when_no_dimension_could_be_identified() -> None:
    from bls_mcp.services.series_catalog import SeriesCatalogService
    from bls_mcp.storage.query_models import SeriesHierarchy

    class Store:
        def series_hierarchy(self, series_id: str) -> SeriesHierarchy:
            return SeriesHierarchy(
                "snap", series_id, "cu", "All items", (), (),
                ("item",), (("item", "not a single hierarchy"),),
            )  # fmt: skip

    found = SeriesCatalogService(Store()).hierarchy("CUUR0000SA0")  # type: ignore[arg-type]
    assert found is not None
    assert found.status == "unknown"
    assert [u.dimension for u in found.unverified] == ["item"]
    assert "No narrower codes could be identified in this snapshot" in found.note


# ---------------------------------------------------------------------------
# Regressions on the real BLS sample files (PR review findings)
# ---------------------------------------------------------------------------

SAMPLE = Path(__file__).resolve().parents[4] / "src/bls_mcp/docs/sample_data"
OFFICE_ADMIN = "CIS2010000220000I"  # Office and administrative support
SALES_AND_OFFICE = "CIS2010000200000I"  # Sales and office (contains the above)
TOTAL_MANUFACTURING = "PCUOMFG--OMFG--"


@pytest.fixture(scope="module")
def sample_store(tmp_path_factory: pytest.TempPathFactory) -> BLSStore:
    """The real PPI and ECI sample files, built and published once."""
    from bls_mcp.ingestion.lifecycle import build_candidate, validate_candidate
    from bls_mcp.ingestion.publish import (
        activate_snapshot,
        current_snapshot_path,
        publish_candidate,
    )

    root = tmp_path_factory.mktemp("sample")
    manifests = {
        "pc_manifest": SAMPLE / "pc-sample-input.json",
        "ci_manifest": SAMPLE / "ci-sample-input.json",
    }
    candidate = root / "sample.duckdb"
    build_candidate(candidate, "sample_review", **manifests)
    assert validate_candidate(candidate, **manifests).passed
    publish_candidate(candidate, root / "registry")
    activate_snapshot(root / "registry", "sample_review")
    return BLSStore(current_snapshot_path(root / "registry"))


def _related(store: BLSStore, series_id: str) -> set[str]:
    found = store.series_hierarchy(series_id)
    assert found is not None
    return {e.series_id for e in found.parents + found.sub_items if e.series_id}


def test_eci_office_support_is_not_reported_as_containing_sales_and_office(
    sample_store: BLSStore,
) -> None:
    """BLS lists office and administrative support under sales and office;
    the published display order says the reverse, so no occupation claim is
    made in either direction.
    """
    assert SALES_AND_OFFICE not in _related(sample_store, OFFICE_ADMIN)
    assert OFFICE_ADMIN not in _related(sample_store, SALES_AND_OFFICE)
    for series_id in (OFFICE_ADMIN, SALES_AND_OFFICE):
        found = sample_store.series_hierarchy(series_id)
        assert found is not None
        assert "occupation" in dict(found.unverified)
        assert all(e.dimension != "occupation" for e in found.parents + found.sub_items)


def test_eci_estimate_composition_is_still_reported(sample_store: BLSStore) -> None:
    found = sample_store.series_hierarchy("CIU2012300000000I")
    assert found is not None
    assert [(e.dimension, e.name) for e in found.sub_items] == [
        ("estimate", "Wages and salaries"),
        ("estimate", "Total benefits"),
    ]


def test_ppi_aggregate_does_not_claim_nothing_is_published(
    sample_store: BLSStore,
) -> None:
    from bls_mcp.services.series_catalog import SeriesCatalogService

    found = SeriesCatalogService(sample_store).hierarchy(TOTAL_MANUFACTURING)
    assert found is not None
    assert found.sub_items == []
    assert found.status == "partial"
    assert [u.dimension for u in found.unverified] == ["industry"]
    assert "No narrower codes could be identified in this snapshot" in found.note
    assert "published" not in found.note


def test_sawmills_path_on_real_files_is_complete(sample_store: BLSStore) -> None:
    from bls_mcp.services.series_catalog import SeriesCatalogService

    found = SeriesCatalogService(sample_store).hierarchy("PCU321113321113")
    assert found is not None
    assert found.status == "complete"
    assert "PCU3211133211133" in {e.series_id for e in found.sub_items}
