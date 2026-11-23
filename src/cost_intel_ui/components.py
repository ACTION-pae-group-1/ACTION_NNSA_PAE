"""Shared HTML fragments styled by ``theme.app_css()``.

A Streamlit adapter renders these with ``st.markdown(..., unsafe_allow_html=True)``
(or ``st.html``). Every text value is escaped and every color is checked, so
payload strings cannot inject markup or CSS.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from html import escape
from typing import Literal

from cost_intel_ui.results_view import RibbonSegment, Stat

_SAFE_COLOR = re.compile(r"^#[0-9A-Fa-f]{6}$")
NEUTRAL_COLOR = "#718797"


def safe_color(value: str, fallback: str = NEUTRAL_COLOR) -> str:
    """Return ``value`` if it is a #RRGGBB color, else a neutral fallback."""
    return value if _SAFE_COLOR.match(value or "") else fallback


def badge(label: str, tone: Literal["amber", "green"]) -> str:
    return f'<span class="badge {tone}">{escape(label)}</span>'


def meta_chips(chips: Sequence[str]) -> str:
    inner = "".join(f'<span class="meta-chip">{escape(c)}</span>' for c in chips)
    return f'<div class="result-meta">{inner}</div>'


def stat_tiles(stats: Sequence[Stat]) -> str:
    tiles = []
    for s in stats:
        css_class = ' class="green"' if s.tone == "green" else ""
        tiles.append(
            f'<div class="result-stat"><small>{escape(s.label)}</small>'
            f"<strong{css_class}>{escape(s.value)}</strong></div>"
        )
    return f'<div class="result-stats">{"".join(tiles)}</div>'


def tool_trace(labels: Sequence[str]) -> str:
    chips = "".join(
        f'<span class="tool-chip">{escape(label)}</span>' for label in labels
    )
    return f'<div class="tool-trace">{chips}</div>'


def allocation_ribbon(segments: Sequence[RibbonSegment]) -> str:
    pieces = "".join(
        f'<span class="ribbon-piece" style="background:{safe_color(s.color_hex)};'
        f'flex:{float(s.weight)}" title="{escape(s.name)} · {escape(s.percent_label)}'
        f' · {escape(s.description)}" '
        f'aria-label="{escape(s.name)} {escape(s.percent_label)}"></span>'
        for s in segments
    )
    return (
        '<div class="allocation-ribbon" role="img" '
        f'aria-label="Component allocation ribbon">{pieces}</div>'
    )


def card(title: str, subtitle: str, badge_html: str, body_html: str) -> str:
    """Artifact card. ``badge_html`` and ``body_html`` must already be safe."""
    return (
        '<div class="artifact-card"><div class="artifact-top"><div>'
        f"<h3>{escape(title)}</h3><p>{escape(subtitle)}</p></div>{badge_html}</div>"
        f"{body_html}</div>"
    )
