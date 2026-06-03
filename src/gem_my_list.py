"""GEM My List — compact trade board format for the user's watchlist."""

from __future__ import annotations

from typing import List, Tuple

from src.gem.timeframes import DEFAULT_TIMEFRAMES, TF_SHORT
from src.gem_platform import InstrumentMTFScan
from src.gem_strength import strength_badge


PRODUCT_NAME = "GEM My List"
# One-word aliases users or agents can use
ALIASES = ("gemlist", "gemboard", "mylist")


def _tf_tags(scan: InstrumentMTFScan) -> str:
    """Which timeframes show STRONG+ in the same direction as combined."""
    cr = scan.combined_rating
    if not cr or cr.direction == "NEUTRAL":
        strong = []
        for tf, r in scan.ratings.items():
            if r.strength in ("STRONG", "VERY_STRONG", "PREMIUM"):
                strong.append(TF_SHORT.get(tf, tf))
        return " + ".join(strong) if strong else ""

    parts = []
    for tf in DEFAULT_TIMEFRAMES:
        r = scan.ratings.get(tf)
        if not r:
            continue
        if r.direction == cr.direction and r.strength in ("STRONG", "VERY_STRONG", "PREMIUM"):
            parts.append(TF_SHORT.get(tf, tf))
    return " + ".join(parts)


def _notes(scan: InstrumentMTFScan) -> str:
    cr = scan.combined_rating
    primary = scan.analyses.get("60") or scan.primary_analysis()
    bits: List[str] = []

    if cr and cr.signal_name and cr.signal_name != "—":
        bits.append(cr.signal_name.split(" (")[0])

    tf = _tf_tags(scan)
    if tf:
        bits.append(tf)

    if primary:
        if primary.exec_state in ("ARMED_SHORT", "ARMED_LONG"):
            bits.append(primary.exec_state.replace("_", " "))
        elif primary.exec_state.startswith("TRIGGERED"):
            bits.append(primary.exec_state.replace("_", " "))

    return "; ".join(bits) if bits else "monitor"


def format_mtf_cell(scan: InstrumentMTFScan) -> str:
    cr = scan.combined_rating
    if not cr:
        return "—"
    return f"{strength_badge(cr.strength)} {cr.strength} {cr.direction.lower()}"


def format_checklist_cell(scan: InstrumentMTFScan) -> str:
    cl = scan.checklist
    if not cl:
        return "—"
    mark = "✅" if cl.trade_ok else ("⚠️" if cl.score >= 4 else "—")
    return f"{cl.score}/6 {mark}"


def build_gem_my_list_rows(
    scans: List[InstrumentMTFScan],
    *,
    trade_ready_only: bool = False,
) -> List[Tuple[str, str, str, str]]:
    """
    Returns rows: (instrument, checklist, mtf, notes).
    Sorted: trade-ready first, then by abs(MTF score).
    """
    rows: List[Tuple[str, str, str, str, int, int]] = []
    for s in scans:
        if trade_ready_only and not (s.checklist and s.checklist.trade_ok):
            continue
        cr = s.combined_rating
        score = abs(cr.score) if cr else 0
        prio = 1 if s.checklist and s.checklist.trade_ok else 0
        rows.append(
            (
                s.display_name,
                format_checklist_cell(s),
                format_mtf_cell(s),
                _notes(s),
                prio,
                score,
            )
        )
    rows.sort(key=lambda r: (r[4], r[5]), reverse=True)
    return [(r[0], r[1], r[2], r[3]) for r in rows]


def render_gem_my_list_markdown(
    scans: List[InstrumentMTFScan],
    *,
    trade_ready_only: bool = False,
) -> List[str]:
    """Markdown section for reports and chat."""
    lines = [
        f"## {PRODUCT_NAME}",
        "",
        "| Instrument | Checklist | MTF | Notes |",
        "|------------|-----------|-----|-------|",
    ]
    board = build_gem_my_list_rows(scans, trade_ready_only=trade_ready_only)
    if not board:
        lines.append("| _none_ | — | — | No trade-ready names this scan |")
    else:
        for inst, chk, mtf, notes in board:
            lines.append(f"| **{inst}** | {chk} | {mtf} | {notes} |")
    lines.append("")
    return lines
