"""Design tokens extracted from docs/ai_mcp_cost_intelligence_nnsa_spec_aligned.html.

Source of truth for colors is the prototype's ``:root`` block; component
colors, sizes, and radii come from its class rules. Everything here is plain
data so it can feed Streamlit's theme config and an injected stylesheet.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from importlib.resources import files


@dataclass(frozen=True)
class Palette:
    bg: str = "#12171d"
    rail: str = "#10151b"
    main: str = "#171d24"
    aside: str = "#141b22"
    surface: str = "#202a33"
    surface2: str = "#25323d"
    line: str = "#33414d"
    line_soft: str = "#29343f"
    text: str = "#ecf4f5"
    muted: str = "#9eb1bd"
    quiet: str = "#718797"
    mint: str = "#8be6c9"
    mintdeep: str = "#17493f"
    blue: str = "#9bc8fc"
    gold: str = "#f5cf8b"
    danger: str = "#ff9494"
    shadow: str = "0 12px 40px #0003"


@dataclass(frozen=True)
class Typography:
    family: str = (
        'Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",'
        "sans-serif"
    )
    mono: str = "ui-monospace,SFMono-Regular,Consolas,monospace"
    base_size_px: int = 14
    base_line_height: float = 1.5
    eyebrow_px: int = 10
    caption_px: int = 11
    body_px: int = 13
    card_title_px: int = 15
    stat_px: int = 24
    modal_title_px: int = 23
    welcome_title_css: str = "clamp(32px,3.7vw,47px)"


@dataclass(frozen=True)
class Layout:
    left_rail_px: int = 245
    right_panel_px: int = 302
    topbar_px: int = 68
    message_max_px: int = 840
    composer_max_px: int = 780
    hide_right_panel_below_px: int = 1220
    hide_left_rail_below_px: int = 760
    radius_card_px: int = 13
    radius_button_px: int = 8
    radius_chip_px: int = 6
    radius_pill_px: int = 25
    radius_modal_px: int = 16


PALETTE = Palette()
TYPOGRAPHY = Typography()
LAYOUT = Layout()


def css_variables(palette: Palette = PALETTE) -> str:
    """Render the ``:root`` custom-property block with the HTML's names."""
    body = ";".join(
        f"--{f.name.replace('_', '-')}:{getattr(palette, f.name)}"
        for f in fields(palette)
    )
    return ":root{" + body + "}"


def component_css() -> str:
    """Component rules ported from the HTML (see components.css)."""
    return files("cost_intel_ui").joinpath("components.css").read_text(encoding="utf-8")


def app_css(palette: Palette = PALETTE, typography: Typography = TYPOGRAPHY) -> str:
    """Return the full offline stylesheet: variables, base, and components."""
    base = (
        "html,body{color-scheme:dark;background:var(--bg);color:var(--text);"
        f"font:{typography.base_size_px}px/{typography.base_line_height} "
        f"{typography.family}}}"
        ":focus-visible{outline:2px solid var(--mint);outline-offset:2px}"
    )
    return "\n".join((css_variables(palette), base, component_css()))


def streamlit_config(palette: Palette = PALETTE) -> dict[str, dict[str, object]]:
    """Return the expected contents of .streamlit/config.toml.

    Streamlit offers one secondary background for both the sidebar and input
    widgets; the HTML uses the rail color for the sidebar and near-rail
    colors (#14222d) for inputs, so ``rail`` is the closer single choice.
    """
    return {
        "browser": {"gatherUsageStats": False},
        "theme": {
            "base": "dark",
            "primaryColor": palette.mint,
            "backgroundColor": palette.main,
            "secondaryBackgroundColor": palette.rail,
            "textColor": palette.text,
            "font": "sans serif",
        },
    }
