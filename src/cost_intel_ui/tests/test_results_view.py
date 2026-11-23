"""Tests for the Custom PPI escalation index (results explorer) view models."""

import csv
import io

import pytest

from cost_intel_ui.data_access import ResultPacket
from cost_intel_ui.fake_data import InMemoryDataSource
from cost_intel_ui.results_view import (
    TABLE_FIELDS,
    AdjustmentUnavailable,
    BlockedResult,
    NoAdjustmentRequired,
    UnknownComponent,
    adjustment_view,
    component_detail,
    csv_export,
    eligible_adjustment_years,
    explorer_view,
    main_chart,
    table_view,
)


@pytest.fixture
def packet() -> ResultPacket:
    found = InMemoryDataSource().get_result("y12", "recommended")
    assert found is not None
    return found


def test_explorer_header_stats_and_chips(packet):
    view = explorer_view(packet, selected_comp="electric")
    assert view.title == "Custom PPI escalation index"
    assert view.subtitle == (
        "Y-12 Site Utility Resilience Upgrade PPI Escalation Index · "
        "Annual observations 2021–2026"
    )
    assert view.badge_label == "✓ Analysis approved"
    assert [(s.label, s.value, s.tone) for s in view.stats] == [
        ("Base factor", "1.0000", None),
        ("2026 composite factor", "1.1263", None),
        ("2026 vs. base", "+12.63%", "green"),
    ]
    assert view.meta_chips == (
        "Base year 2023 · 1.0 factor",
        "Annual · base year annual average",
        "Spec y12-recommended · rev 1",
        "Snapshot DEMO-ANNUAL-2021-2026-v1",
        "Method composite-index/1.0",
    )
    assert view.tabs == (
        ("component", "Component detail"),
        ("adjustment", "Adjustment to base"),
        ("table", "Data & CSV"),
    )


def test_ribbon_and_legend_follow_display_order(packet):
    view = explorer_view(packet, selected_comp="steel")
    assert [s.component_id for s in view.ribbon] == [
        "electric",
        "machinery",
        "steel",
        "concrete",
    ]
    assert view.ribbon[0].color_hex == "#E6A34B"
    assert view.ribbon[0].percent_label == "45.00%"
    selected = [o for o in view.legend if o.selected]
    assert [o.label for o in selected] == ["Steel mill products · 15.00%"]


def test_invalid_payload_returns_blocked_result_with_capped_issues():
    broken = ResultPacket(result={"schema_version": "0.9"}, presentation={})
    view = explorer_view(broken, selected_comp=None)
    assert isinstance(view, BlockedResult)
    assert view.title == "Result blocked — calculation contract failed"
    assert 0 < len(view.issues) <= 35


def test_main_chart_stacks_layers_and_scales_y_axis(packet):
    chart = main_chart(packet)
    assert chart.periods == ("2021", "2022", "2023", "2024", "2025", "2026")
    assert chart.y_max == pytest.approx(1.25)
    assert [s.component_id for s in chart.series][0] == "electric"
    assert chart.series[-1].tops[-1] == pytest.approx(1.126250052151)
    assert chart.composite[-1] == pytest.approx(1.126250052151)
    assert "annual base year 2023 = 1.0" in chart.footnote


def test_component_detail_normalized_mode(packet):
    detail = component_detail(packet, "steel", "normalized")
    assert detail.title == "Steel mill products · DEMO-WPU1017"
    assert detail.values[0] == pytest.approx(91.0)
    assert (detail.y_min, detail.y_max) == (90, 120)
    assert detail.reference_line == 100
    assert "Normalization: annual average in 2023." in detail.metadata


def test_component_detail_raw_mode(packet):
    detail = component_detail(packet, "steel", "raw")
    assert detail.values[2] == pytest.approx(242.6)
    assert detail.reference_line is None
    assert detail.y_min == pytest.approx(220.766 * 0.92)


def test_component_detail_unknown_component(packet):
    assert isinstance(component_detail(packet, "nope", "raw"), UnknownComponent)


def test_eligible_adjustment_years(packet):
    assert eligible_adjustment_years(packet) == [
        "2021",
        "2022",
        "2023",
        "2024",
        "2025",
        "2026",
    ]


def test_adjustment_view_for_latest_year(packet):
    view = adjustment_view(packet, "2026")
    assert view.source_composite == "1.126250052151"
    assert view.adjustment_factor == "0.887902289629"
    assert [b.label for b in view.bars] == [
        "Source year",
        "Electrical",
        "Machinery",
        "Steel",
        "Concrete",
        "To base",
    ]
    assert view.bars[1].value_label == "-4.63484995 pp"
    assert view.bars[-1].value_label == "88.79022896%"
    assert view.reconcile.startswith("-11.20977104% adjustment")
    assert view.math_rows[0] == ("Electrical equipment", "-4.63484995 pp")


def test_adjustment_view_for_base_year_requires_no_adjustment(packet):
    assert isinstance(adjustment_view(packet, "2023"), NoAdjustmentRequired)


def test_adjustment_view_for_missing_year(packet):
    view = adjustment_view(packet, "2030")
    assert isinstance(view, AdjustmentUnavailable)
    assert "missing or incomplete" in view.detail


def test_table_view_filters_sorts_and_formats(packet):
    view = table_view(packet, year="2026", component="all", sort="desc")
    assert view.columns == TABLE_FIELDS
    assert len(view.rows) == 4
    assert view.rows[0][TABLE_FIELDS.index("allocation_weight")] == "45.00%"
    assert view.rows[0][TABLE_FIELDS.index("normalized_percent")] == "111.60%"
    assert view.status.startswith("4 of 24 observations")
    assert view.year_options[0] == ("all", "All years")
    assert view.component_options[1] == ("electric", "Electrical equipment")


def test_table_view_sorts_by_period_then_display_order(packet):
    view = table_view(packet, year="all", component="all", sort="desc")
    first = [r[0] + r[2] for r in view.rows[:2]]
    assert first == ["2026electric", "2026machinery"]


def test_table_view_empty_filter(packet):
    view = table_view(packet, year="2026", component="missing", sort="asc")
    assert view.rows == ()
    assert view.empty_message == "No observations match these filters."


def test_csv_export_keeps_canonical_precision_and_names_the_file(packet):
    filename, content = csv_export(packet, year="all", component="steel", sort="asc")
    assert filename == (
        "custom-index_y12-recommended_rev-1_base-2023_DEMO-ANNUAL-2021-2026-v1.csv"
    )
    rows = list(csv.reader(io.StringIO(content)))
    assert tuple(rows[0]) == TABLE_FIELDS
    assert len(rows) == 7
    assert rows[1][TABLE_FIELDS.index("allocation_weight")] == "0.150000000000"
    assert content.endswith("\r\n")


def test_csv_export_neutralizes_formula_injection_in_text_cells(packet):
    tampered = ResultPacket(
        result=packet.result,
        presentation={
            **packet.presentation,
            "table_rows": [
                {
                    **packet.presentation["table_rows"][0],
                    "component_name": "=HYPERLINK()",
                }
            ],
        },
    )
    _, content = csv_export(tampered, year="all", component="all", sort="asc")
    assert "'=HYPERLINK()" in content
