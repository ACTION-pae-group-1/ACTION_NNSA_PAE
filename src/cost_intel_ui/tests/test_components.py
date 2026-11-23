"""Tests for shared HTML fragments styled by theme.app_css()."""

from cost_intel_ui.components import (
    allocation_ribbon,
    badge,
    card,
    meta_chips,
    stat_tiles,
    tool_trace,
)
from cost_intel_ui.results_view import RibbonSegment, Stat


def test_badge_uses_tone_class_and_escapes_text():
    assert badge("<b>", "amber") == '<span class="badge amber">&lt;b&gt;</span>'


def test_meta_chips_render_in_a_wrapper():
    html = meta_chips(("A", "B & C"))
    assert html.startswith('<div class="result-meta">')
    assert '<span class="meta-chip">B &amp; C</span>' in html


def test_stat_tiles_apply_green_tone():
    html = stat_tiles((Stat("Base", "1.0000", None), Stat("Up", "+1%", "green")))
    assert '<strong class="green">+1%</strong>' in html
    assert "<small>Base</small>" in html


def test_tool_trace_lists_chips():
    html = tool_trace(("Project context", "PPI candidates"))
    assert html.count('class="tool-chip"') == 2


def test_allocation_ribbon_uses_component_colors_and_labels():
    segment = RibbonSegment("steel", "Steel", "#4F83E6", 0.15, "15.00%", "d")
    html = allocation_ribbon((segment,))
    assert "background:#4F83E6" in html
    assert "flex:0.15" in html
    assert 'aria-label="Steel 15.00%"' in html


def test_allocation_ribbon_drops_unsafe_colors():
    segment = RibbonSegment("x", "X", "red;}body{", 1.0, "100.00%", "d")
    assert "body{" not in allocation_ribbon((segment,))


def test_card_combines_title_subtitle_badge_and_body():
    html = card("Title", "Sub", badge("ok", "green"), "<p>body</p>")
    assert html.startswith('<div class="artifact-card">')
    assert "<h3>Title</h3>" in html and "<p>Sub</p>" in html
    assert html.endswith("<p>body</p></div>")
