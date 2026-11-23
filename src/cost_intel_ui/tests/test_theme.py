"""Tests for design tokens extracted from the HTML prototype's CSS."""

import tomllib
from pathlib import Path

from cost_intel_ui.theme import (
    LAYOUT,
    PALETTE,
    TYPOGRAPHY,
    app_css,
    css_variables,
    streamlit_config,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = REPO_ROOT / ".streamlit" / "config.toml"


def test_palette_matches_the_html_root_custom_properties():
    assert PALETTE.bg == "#12171d"
    assert PALETTE.rail == "#10151b"
    assert PALETTE.main == "#171d24"
    assert PALETTE.aside == "#141b22"
    assert PALETTE.surface == "#202a33"
    assert PALETTE.surface2 == "#25323d"
    assert PALETTE.line == "#33414d"
    assert PALETTE.line_soft == "#29343f"
    assert PALETTE.text == "#ecf4f5"
    assert PALETTE.muted == "#9eb1bd"
    assert PALETTE.quiet == "#718797"
    assert PALETTE.mint == "#8be6c9"
    assert PALETTE.mintdeep == "#17493f"
    assert PALETTE.blue == "#9bc8fc"
    assert PALETTE.gold == "#f5cf8b"
    assert PALETTE.danger == "#ff9494"


def test_css_variables_reproduce_the_html_root_block_names():
    css = css_variables()
    assert css.startswith(":root{")
    assert "--bg:#12171d;" in css
    assert "--line-soft:#29343f;" in css
    assert "--mintdeep:#17493f;" in css
    assert "--shadow:0 12px 40px #0003" in css


def test_typography_uses_inter_with_system_fallbacks_and_14px_base():
    assert TYPOGRAPHY.family.startswith("Inter,")
    assert "system-ui" in TYPOGRAPHY.family
    assert TYPOGRAPHY.base_size_px == 14
    assert TYPOGRAPHY.base_line_height == 1.5
    assert "Consolas" in TYPOGRAPHY.mono


def test_layout_matches_the_three_column_grid_and_breakpoints():
    assert LAYOUT.left_rail_px == 245
    assert LAYOUT.right_panel_px == 302
    assert LAYOUT.topbar_px == 68
    assert LAYOUT.message_max_px == 840
    assert LAYOUT.composer_max_px == 780
    assert LAYOUT.hide_right_panel_below_px == 1220
    assert LAYOUT.hide_left_rail_below_px == 760


def test_app_css_is_offline_and_declares_dark_color_scheme():
    css = app_css()
    assert css_variables() in css
    assert "color-scheme:dark" in css
    assert "url(" not in css
    assert "@import" not in css
    for selector in (".artifact-card", ".badge.amber", ".badge.green", ".meta-chip"):
        assert selector in css


def test_streamlit_config_turns_off_usage_telemetry():
    config = streamlit_config()
    assert config["browser"]["gatherUsageStats"] is False


def test_streamlit_config_theme_uses_dark_base_and_palette_colors():
    theme = streamlit_config()["theme"]
    assert theme["base"] == "dark"
    assert theme["primaryColor"] == PALETTE.mint
    assert theme["backgroundColor"] == PALETTE.main
    assert theme["secondaryBackgroundColor"] == PALETTE.rail
    assert theme["textColor"] == PALETTE.text


def test_checked_in_streamlit_config_matches_tokens_and_disables_telemetry():
    on_disk = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    assert on_disk == streamlit_config()
    assert on_disk["browser"]["gatherUsageStats"] is False


def test_app_css_keeps_a_visible_focus_outline():
    css = app_css()
    assert ":focus-visible{outline:2px solid var(--mint);outline-offset:2px}" in css
    assert "outline:none" not in css
    assert "outline:0" not in css
