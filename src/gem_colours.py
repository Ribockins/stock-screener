"""
GEM report colour codes — aligned with TradingView GEM Logic 1.5 palette.

Markdown tables use emoji + hex tags so reports read clearly in GitHub / Cursor.
"""

from __future__ import annotations

from typing import Optional

# Pine GEM Logic 1.5 palette (hex)
C_EMERALD = "#00c896"
C_EMERALD_CORE = "#00ffa5"
C_RUBY = "#c62828"
C_RUBY_CORE = "#ff0055"
C_NEUTRAL = "#9e9e9e"
C_AMBER = "#f0ad4e"
C_BLUE = "#7896d2"

CHIP_BULL = "🟢"
CHIP_BEAR = "🔴"
CHIP_NEUTRAL = "⚪"
CHIP_WARN = "🟡"


def hex_tag(hex_code: str) -> str:
    return f"`{hex_code}`"


def bull_chip(label: str = "", *, core: bool = False) -> str:
    h = C_EMERALD_CORE if core else C_EMERALD
    text = f"{label} " if label else ""
    return f"{CHIP_BULL} {text}{hex_tag(h)}".strip()


def bear_chip(label: str = "", *, core: bool = False) -> str:
    h = C_RUBY_CORE if core else C_RUBY
    text = f"{label} " if label else ""
    return f"{CHIP_BEAR} {text}{hex_tag(h)}".strip()


def neutral_chip(label: str = "neutral") -> str:
    return f"{CHIP_NEUTRAL} {label} {hex_tag(C_NEUTRAL)}"


def warn_chip(label: str = "warn") -> str:
    return f"{CHIP_WARN} {label} {hex_tag(C_AMBER)}"


def direction_chip(direction: str) -> str:
    d = (direction or "").upper()
    if d == "BULLISH":
        return bull_chip("BULL")
    if d == "BEARISH":
        return bear_chip("BEAR")
    return neutral_chip()


def tier_chip(tier: str) -> str:
    t = (tier or "").upper()
    if t == "CONFIRMED":
        return f"{CHIP_BULL} **CONFIRMED** {hex_tag(C_EMERALD)}"
    if t == "WARNING":
        return f"{CHIP_WARN} **WARNING** {hex_tag(C_AMBER)}"
    return f"{CHIP_NEUTRAL} WAIT {hex_tag(C_NEUTRAL)}"


def signal_chip(signal: str) -> str:
    s = (signal or "").upper()
    if not s or s == "—":
        return neutral_chip("—")
    if "EMERALD" in s or "BUY" in s or "LONG" in s or "OVERSOLD" in s:
        return bull_chip(signal.split(" (")[0], core="GEM" in s)
    if "RUBY" in s or "SELL" in s or "SHORT" in s or "OVERBOUGHT" in s:
        return bear_chip(signal.split(" (")[0], core="GEM" in s)
    return neutral_chip(signal)


def dashboard_cell(text: str, state: int, *, rsi_zone: bool = False) -> str:
    """
    Colour a terminal-matrix cell.

    state: -1 bear, 0 neutral, +1 bull (packed ternary)
    rsi_zone: R1/MF use OS/OB labels instead of B/S
    """
    if not text or text == "—":
        return "—"
    if state > 0:
        if rsi_zone and text == "OS":
            return f"{CHIP_BULL} **OS** {hex_tag(C_EMERALD)}"
        return f"{CHIP_BULL} **{text}** {hex_tag(C_EMERALD)}"
    if state < 0:
        if rsi_zone and text == "OB":
            return f"{CHIP_BEAR} **OB** {hex_tag(C_RUBY)}"
        return f"{CHIP_BEAR} **{text}** {hex_tag(C_RUBY)}"
    return f"{CHIP_NEUTRAL} {text} {hex_tag(C_NEUTRAL)}"


def dashboard_score_cell(score: int, bias: int) -> str:
    if score <= 0:
        return f"{CHIP_NEUTRAL} 0 {hex_tag(C_NEUTRAL)}"
    if bias > 0:
        return f"{CHIP_BULL} **{score}** {hex_tag(C_EMERALD)}"
    if bias < 0:
        return f"{CHIP_BEAR} **{score}** {hex_tag(C_RUBY)}"
    return f"{CHIP_NEUTRAL} **{score}** {hex_tag(C_NEUTRAL)}"


def edge_plus_chip(value: int | str) -> str:
    try:
        v = int(value)
    except (TypeError, ValueError):
        return str(value)
    if v >= 6:
        return f"{CHIP_BULL} **{v}** {hex_tag(C_EMERALD_CORE)}"
    if v >= 3:
        return f"{CHIP_BULL} **{v}** {hex_tag(C_EMERALD)}"
    if v <= -3:
        return f"{CHIP_BEAR} **{v}** {hex_tag(C_RUBY)}"
    if v < 0:
        return f"{CHIP_BEAR} **{v}** {hex_tag(C_RUBY)}"
    if v == 0:
        return f"{CHIP_NEUTRAL} 0 {hex_tag(C_NEUTRAL)}"
    return f"{CHIP_NEUTRAL} **{v}** {hex_tag(C_NEUTRAL)}"


def checklist_chip(score: int, trade_ok: bool) -> str:
    if trade_ok:
        return f"{CHIP_BULL} **{score}/6** ✅ {hex_tag(C_EMERALD)}"
    if score >= 4:
        return f"{CHIP_WARN} **{score}/6** ⚠️ {hex_tag(C_AMBER)}"
    return f"{CHIP_NEUTRAL} {score}/6 {hex_tag(C_NEUTRAL)}"


def mtf_strength_chip(strength: str, direction: str, badge: str) -> str:
    d = (direction or "").lower()
    if direction == "BULLISH":
        return f"{CHIP_BULL} {badge} {strength} {d} {hex_tag(C_EMERALD)}"
    if direction == "BEARISH":
        return f"{CHIP_BEAR} {badge} {strength} {d} {hex_tag(C_RUBY)}"
    return f"{CHIP_NEUTRAL} {badge} {strength} {hex_tag(C_NEUTRAL)}"


def colour_legend_lines() -> list[str]:
    return [
        "### Colour codes",
        "",
        "| Chip | Meaning | Hex |",
        "|------|---------|-----|",
        f"| {CHIP_BULL} | Bull / Emerald / OS / long | `{C_EMERALD}` · core `{C_EMERALD_CORE}` |",
        f"| {CHIP_BEAR} | Bear / Ruby / OB / short | `{C_RUBY}` · core `{C_RUBY_CORE}` |",
        f"| {CHIP_WARN} | WARNING / partial checklist | `{C_AMBER}` |",
        f"| {CHIP_NEUTRAL} | Neutral / WAIT / zero | `{C_NEUTRAL}` |",
        "",
    ]


def coloured_dashboard_row(d) -> list[str]:
    """Return coloured cells for a TFDashboardState (gem.dashboard)."""
    from src.gem.dashboard import TFDashboardState

    if not isinstance(d, TFDashboardState):
        return []
    return [
        dashboard_cell(d.rsi_text(d.r1), d.r1, rsi_zone=True),
        dashboard_cell(d.dir_text(d.r2), d.r2),
        dashboard_cell(d.dir_text(d.r3), d.r3),
        dashboard_cell(d.dir_text(d.d1), d.d1),
        dashboard_cell(d.dir_text(d.d2), d.d2),
        dashboard_cell(d.dir_text(d.d3), d.d3),
        dashboard_cell(d.rsi_text(d.mf), d.mf, rsi_zone=True),
        dashboard_cell(d.dir_text(d.mv), d.mv),
        dashboard_cell(d.dir_text(d.cdl), d.cdl),
        dashboard_cell(d.dir_text(d.gm), d.gm, rsi_zone=False),
        dashboard_score_cell(d.score, d.bias),
    ]
