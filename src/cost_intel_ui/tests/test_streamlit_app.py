"""Rendering tests for the Streamlit shell and the basket screen (AppTest)."""

import re
from pathlib import Path

import pytest

pytest.importorskip("streamlit")

from streamlit.testing.v1 import AppTest  # noqa: E402

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"
TIMEOUT = 30


def _run(at: AppTest) -> AppTest:
    at.run(timeout=TIMEOUT)
    assert not at.exception, [e.value for e in at.exception]
    return at


@pytest.fixture
def at() -> AppTest:
    return _run(AppTest.from_file(str(APP), default_timeout=TIMEOUT))


@pytest.fixture
def basket(at: AppTest) -> AppTest:
    at.button(key="welcome-start-y12").click()
    return _run(at)


def _html(at: AppTest) -> str:
    return "\n".join(h.value for h in [*at.sidebar.html, *at.main.html])


def _toasts(at: AppTest) -> list[str]:
    return [t.value for t in at.toast]


def test_welcome_shows_html_copy_and_one_starter_per_project(at):
    html = _html(at)
    assert "Talk to your data. Keep the evidence." in html
    assert "Ask a project question." in html
    labels = [
        at.button(key=f"welcome-start-{k}").label for k in ("y12", "pantex", "lanl")
    ]
    assert labels == [
        "▤ Y-12 utility resilience",
        "▥ Pantex facility renewal",
        "◈ Los Alamos lab expansion",
    ]


def test_sidebar_has_brand_sections_and_resources(at):
    html = "\n".join(h.value for h in at.sidebar.html)
    assert "AI MCP" in html
    for title in ("Your conversations", "NNSA example projects", "Resources"):
        assert title in html
    assert at.sidebar.button(key="nav-mission").label == "◎ Why this matters"
    assert at.sidebar.button(key="nav-audit").label == "◫ Evidence & audit"


def test_starting_a_project_renders_the_basket_with_labelled_inputs(basket):
    html = _html(basket)
    assert "Recommended PPI escalation basket" in html
    assert "Requires approval" in html
    assert "100.00%" in html
    assert "✓ Precomputed result ready" in html
    assert [c.label for c in basket.checkbox] == [
        "Include Structural steel",
        "Include Concrete",
        "Include Electrical systems",
        "Include Mechanical / equipment",
    ]
    assert [n.label for n in basket.number_input] == [
        "Allocation percent for Structural steel",
        "Allocation percent for Concrete",
        "Allocation percent for Electrical systems",
        "Allocation percent for Mechanical / equipment",
    ]
    assert [n.value for n in basket.number_input] == [15.0, 15.0, 45.0, 25.0]
    assert "+18.80%" in html
    assert not basket.button(key="basket-1-approve").disabled


def test_current_preset_is_marked_in_the_button_text(basket):
    assert basket.button(key="basket-1-preset-recommended").label == (
        "✓ Recommended (current)"
    )
    assert basket.button(key="basket-1-preset-materials").label == "Materials-heavy"


def test_invalid_total_disables_approve_and_explains_why(basket):
    basket.number_input(key="basket-1-weight-0").set_value(10.0)
    html = _html(_run(basket))
    assert "95.00%" in html
    assert "Weights must equal 100%" in html
    assert basket.button(key="basket-1-approve").disabled


def test_custom_valid_weights_offer_local_calculation(basket):
    basket.number_input(key="basket-1-weight-0").set_value(16.0)
    basket.number_input(key="basket-1-weight-1").set_value(14.0)
    html = _html(_run(basket))
    assert "Custom calculation ready" in html
    assert "Custom weights use the local synthetic PPI calculator" in html


def test_choosing_a_preset_updates_every_weight_input(basket):
    basket.button(key="basket-1-preset-materials").click()
    _run(basket)
    assert [n.value for n in basket.number_input] == [35.0, 30.0, 20.0, 15.0]
    assert "Precomputed materials scenario loaded for review." in _toasts(basket)
    assert basket.button(key="basket-1-preset-materials").label.startswith("✓")


def test_normalize_rescales_to_100_percent(basket):
    basket.number_input(key="basket-1-weight-0").set_value(30.0)
    _run(basket)
    basket.button(key="basket-1-normalize").click()
    html = _html(_run(basket))
    assert "100.00%" in html
    assert (
        "Allocation normalized. Review the weights, then approve to calculate locally."
        in _toasts(basket)
    )


def test_unchecking_a_row_disables_its_weight_input(basket):
    basket.checkbox(key="basket-1-enable-1").uncheck()
    _run(basket)
    assert basket.number_input(key="basket-1-weight-1").disabled


def test_approve_locks_the_basket(basket):
    basket.button(key="basket-1-approve").click()
    html = _html(_run(basket))
    assert "✓ Approved fixture" in html
    assert basket.button(key="basket-1-approve").label == "✓ Approved"
    assert all(c.disabled for c in basket.checkbox)
    assert all(n.disabled for n in basket.number_input)
    assert "Validated sample result displayed." in _toasts(basket)


def test_why_link_adds_the_explanation_to_the_conversation(basket):
    basket.button(key="basket-1-why").click()
    _run(basket)
    text = "\n".join(m.value for m in basket.markdown) + _html(basket)
    assert "Why these PPI indices?" in text


def test_quick_prompt_routes_through_the_intent_handler(basket):
    basket.button(key="quick-1").click()
    _run(basket)
    text = "\n".join(m.value for m in basket.markdown) + _html(basket)
    assert "Why these PPI indices?" in text


def test_context_panel_tracks_the_session(basket):
    html = _html(basket)
    assert "Project &amp; evidence" in html
    assert "DEMO-NNSA-Y12-001" in html
    assert "Reviewing" in html


def test_headings_never_skip_a_level(basket):
    levels = [int(n) for n in re.findall(r"<h([1-6])\b", _html(basket))]
    assert levels[0] == 1
    assert all(b - a <= 1 for a, b in zip(levels, levels[1:], strict=False))


def test_page_injects_theme_css_with_visible_focus(at):
    # Style-only st.html goes to Streamlit's event container, not main.
    css = "\n".join(h.value for h in at.get("html") if "<style>" in h.value)
    assert ":focus-visible{outline:2px solid var(--mint)" in css


def test_evidence_and_audit_opens_a_dialog_with_the_audit_json(at):
    at.sidebar.button(key="nav-audit").click()
    _run(at)
    code = [c.value for c in at.get("code")]
    assert any('"application": "NNSA AI MCP Cost Intelligence"' in c for c in code)
    assert len(at.get("download_button")) == 1


def test_mission_overview_opens_a_dialog(at):
    at.button(key="top-mission").click()
    _run(at)
    assert at.warning[0].value.startswith("This local demonstration contains no live")


def test_pars_prompt_opens_the_preview_dialog(basket):
    basket.button(key="basket-1-approve").click()
    _run(basket)
    basket.chat_input(key="composer").set_value("save to PARS")
    _run(basket)
    code = "\n".join(c.value for c in basket.get("code"))
    assert '"mode": "PREVIEW_ONLY"' in code
    assert '"executed": false' in code
