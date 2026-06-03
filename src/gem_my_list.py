"""GEM My List — compact trade board + per-timeframe score tables."""

from __future__ import annotations

from typing import Dict, List, Tuple

from src.gem.timeframes import DEFAULT_TIMEFRAMES, TF_SHORT
from src.gem_platform import InstrumentMTFScan
from src.gem_strength import strength_badge


PRODUCT_NAME = "GEM My List"
ALIASES = ("gemlist", "gemboard", "mylist", "4tables", "bytf")

# Report section titles per timeframe
TF_TABLE_TITLES: Dict[str, str] = {
    "15": "15 minute (M15)",
    "60": "1 hour (H1)",
    "240": "4 hour (H4)",
    "1d": "Daily (D1)",
}


def _tf_tags(scan: InstrumentMTFScan) -> str:
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


def _tf_notes(scan: InstrumentMTFScan, tf: str) -> str:
    a = scan.analyses.get(tf)
    r = scan.ratings.get(tf)
    if not a or not r:
        return "—"
    bits = [r.signal_name]
    if a.exec_state not in ("WAIT",):
        bits.append(a.exec_state.replace("_", " "))
    if a.near_support:
        bits.append("near support")
    elif a.near_resistance:
        bits.append("near resistance")
    return "; ".join(bits)


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


def build_timeframe_table_rows(
    scans: List[InstrumentMTFScan],
    tf: str,
) -> List[Tuple[str, int, str, str, float, str, str]]:
    """
    One timeframe: (instrument, score, strength, direction, rsi, signal, notes).
    Sorted by |score| descending.
    """
    rows = []
    for s in scans:
        r = s.ratings.get(tf)
        a = s.analyses.get(tf)
        if not r or not a:
            rows.append((s.display_name, 0, "NONE", "—", 0.0, "—", "no data"))
            continue
        rows.append(
            (
                s.display_name,
                r.score,
                r.strength,
                r.direction,
                round(a.rsi, 1),
                r.signal_name,
                _tf_notes(s, tf),
            )
        )
    rows.sort(key=lambda x: abs(x[1]), reverse=True)
    return rows


def render_gem_my_list_markdown(
    scans: List[InstrumentMTFScan],
    *,
    trade_ready_only: bool = False,
) -> List[str]:
    heading = f"{PRODUCT_NAME} — trade-ready" if trade_ready_only else f"{PRODUCT_NAME} — all instruments"
    lines = [
        f"## {heading}",
        "",
        "| Instrument | Checklist | MTF | Notes |",
        "|------------|-----------|-----|-------|",
    ]
    board = build_gem_my_list_rows(scans, trade_ready_only=trade_ready_only)
    if not board:
        lines.append("| _none_ | — | — | No rows this scan |")
    else:
        for inst, chk, mtf, notes in board:
            lines.append(f"| **{inst}** | {chk} | {mtf} | {notes} |")
    lines.append("")
    return lines


def render_timeframe_tables_markdown(scans: List[InstrumentMTFScan]) -> List[str]:
    """Four separate tables — all instruments, scores for one TF each."""
    lines = [
        "## Scores by timeframe",
        "",
        "_Same 12 instruments on each table; sorted by |score| (strongest bias first)._",
        "",
    ]
    for tf in DEFAULT_TIMEFRAMES:
        label = TF_TABLE_TITLES.get(tf, TF_SHORT.get(tf, tf))
        lines.append(f"### {label}")
        lines.append("")
        lines.append("| Instrument | Score | Strength | Signal | RSI | Notes |")
        lines.append("|------------|-------|----------|--------|-----|-------|")
        for inst, score, strength, direction, rsi, signal, notes in build_timeframe_table_rows(
            scans, tf
        ):
            score_s = f"{score:+d}" if score else "0"
            str_cell = f"{strength_badge(strength)} {strength}"
            if direction in ("BULLISH", "BEARISH"):
                str_cell += f" {direction.lower()}"
            rsi_s = f"{rsi:.1f}" if rsi else "—"
            lines.append(
                f"| **{inst}** | {score_s} | {str_cell} | {signal} | {rsi_s} | {notes} |"
            )
        lines.append("")
    return lines


def timeframe_tables_payload(scans: List[InstrumentMTFScan]) -> Dict[str, list]:
    """JSON-serializable tables keyed by interval (15, 60, 240, 1d)."""
    out: Dict[str, list] = {}
    for tf in DEFAULT_TIMEFRAMES:
        out[tf] = [
            {
                "instrument": r[0],
                "score": r[1],
                "strength": r[2],
                "direction": r[3],
                "rsi": r[4],
                "signal": r[5],
                "notes": r[6],
            }
            for r in build_timeframe_table_rows(scans, tf)
        ]
    return out
