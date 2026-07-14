"""GEM My List — compact trade board + per-timeframe score tables.

Always colour-coded: 🟢 Emerald `#00c896` / 🔴 Ruby `#c62828` / 🟡 WARNING / ⚪ neutral.
User phrases "GEM my list", "gemlist", "mylist" imply colour codes + legend — never plain text only.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from src.gem.dashboard import TFDashboardState
from src.gem.timeframes import DEFAULT_TIMEFRAMES, TF_SHORT
from src.gem_platform import InstrumentMTFScan
from src.execution_tier import TIER_WAIT, execution_tier, tier_label
from src.gem_colours import (
    CHIP_BEAR,
    CHIP_BULL,
    checklist_chip,
    colour_legend_lines,
    coloured_dashboard_row,
    direction_chip,
    edge_plus_chip,
    mtf_strength_chip,
    signal_chip,
    tier_chip,
)
from src.gem_strength import strength_badge


PRODUCT_NAME = "GEM My List"
ALIASES = ("gemlist", "gemboard", "mylist", "4tables", "bytf")

TF_TABLE_TITLES: Dict[str, str] = {
    "15": "15 minute (M15)",
    "60": "1 hour (H1)",
    "240": "4 hour (H4)",
    "1d": "Daily (D1)",
}


def _edge_div_tag(edge) -> str:
    if not edge:
        return ""
    if edge.dual_bear_div:
        return "dual bear div"
    if edge.dual_bull_div:
        return "dual bull div"
    tags = []
    if edge.rsi_bear_div:
        tags.append("RSI↓")
    if edge.rsi_bull_div:
        tags.append("RSI↑")
    if edge.mfi_bear_div:
        tags.append("MFI↓")
    if edge.mfi_bull_div:
        tags.append("MFI↑")
    return " ".join(tags)


def format_sme_cell(scan: InstrumentMTFScan, tf: str = "60") -> str:
    sme = scan.sme_scores.get(tf)
    if not sme:
        return "—"
    short = sme.cell_short()
    if sme.src_summary and sme.src_summary != "—":
        return f"{short} ({sme.src_summary})" if short != "—" else sme.src_summary
    return short


def format_svi_cell(scan: InstrumentMTFScan, tf: str = "60") -> str:
    sme = scan.sme_scores.get(tf) or scan.primary_sme()
    if not sme:
        return "—"
    sign = "+" if sme.svi_weight >= 0 else ""
    return f"{sign}{sme.svi_weight}"


def format_edge_plus_cell(scan: InstrumentMTFScan, tf: str = "60") -> str:
    sme = scan.sme_scores.get(tf) or scan.primary_sme()
    if not sme:
        return "—"
    return str(sme.edge_plus)


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


def format_edge_cell(scan: InstrumentMTFScan, tf: str = "60") -> str:
    edge = scan.edge_signals.get(tf)
    if not edge:
        return "—"
    div = _edge_div_tag(edge)
    base = f"MFI {edge.mfi:.0f} · {edge.edge_combo_score}/4"
    return f"{base}" + (f" · {div}" if div else "")


def _notes(scan: InstrumentMTFScan) -> str:
    cr = scan.combined_rating
    primary = scan.analyses.get("60") or scan.primary_analysis()
    bits: List[str] = []

    if cr and cr.signal_name and cr.signal_name != "—":
        bits.append(cr.signal_name.split(" (")[0])

    tf = _tf_tags(scan)
    if tf:
        bits.append(tf)

    sme = scan.primary_sme()
    if sme and sme.sse_active:
        bits.append("SSE memory boost")
    if sme and sme.spc >= 2:
        bits.append(f"SPC{sme.spc}")

    edge = scan.primary_edge()
    if edge and edge.summary not in ("no edge", "volume neutral"):
        bits.append(edge.summary)

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
    sme = scan.sme_scores.get(tf)
    if sme and sme.cell_short() != "—":
        bits.append(sme.cell_short())
    edge = scan.edge_signals.get(tf)
    if edge:
        div = _edge_div_tag(edge)
        if div:
            bits.append(div)
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
        return neutral_fallback()
    return mtf_strength_chip(cr.strength, cr.direction, strength_badge(cr.strength))


def neutral_fallback() -> str:
    from src.gem_colours import neutral_chip
    return neutral_chip("—")


def format_checklist_cell(scan: InstrumentMTFScan) -> str:
    cl = scan.checklist
    if not cl:
        return neutral_fallback()
    return checklist_chip(cl.score, cl.trade_ok)


def render_colour_legend_markdown() -> List[str]:
    return colour_legend_lines()


def build_gem_my_list_rows(
    scans: List[InstrumentMTFScan],
    *,
    trade_ready_only: bool = False,
) -> List[Tuple[str, str, str, str, str, str, str, str]]:
    rows: List[Tuple] = []
    for s in scans:
        if trade_ready_only and not (s.checklist and s.checklist.trade_ok):
            continue
        cr = s.combined_rating
        score = abs(cr.score) if cr else 0
        prio = 1 if s.checklist and s.checklist.trade_ok else 0
        primary = s.analyses.get("60") or s.primary_analysis()
        rating = s.combined_rating
        tier = tier_label(
            execution_tier(primary, rating, s.checklist) if primary and rating else TIER_WAIT
        )
        sme_h1 = s.sme_scores.get("60")
        edge_plus = sme_h1.edge_plus if sme_h1 else 0
        dir_chip = direction_chip(cr.direction if cr else "NEUTRAL")
        rows.append(
            (
                s.display_name,
                dir_chip,
                format_checklist_cell(s),
                format_mtf_cell(s),
                format_sme_cell(s),
                format_svi_cell(s),
                edge_plus_chip(edge_plus) if sme_h1 else neutral_fallback(),
                format_edge_cell(s),
                tier_chip(tier),
                signal_chip(cr.signal_name if cr else "—"),
                _notes(s),
                prio,
                score,
                edge_plus,
            )
        )
    rows.sort(key=lambda r: (r[11], r[12], r[13]), reverse=True)
    return [tuple(r[:11]) for r in rows]


def render_gem_my_list_markdown(
    scans: List[InstrumentMTFScan],
    *,
    trade_ready_only: bool = False,
) -> List[str]:
    heading = f"{PRODUCT_NAME} — trade-ready" if trade_ready_only else f"{PRODUCT_NAME} — all instruments"
    lines = [
        f"## {heading}",
        "",
        "| Instrument | Dir | Checklist | MTF | SME (H1) | SVI | EDGE+ | Combo | Exec | Signal | Notes |",
        "|------------|-----|-----------|-----|----------|-----|-------|-------|------|--------|-------|",
    ]
    board = build_gem_my_list_rows(scans, trade_ready_only=trade_ready_only)
    if not board:
        lines.append("| _none_ | — | — | — | — | — | — | — | WAIT | — | No rows |")
    else:
        for inst, dir_c, chk, mtf, sme, svi, eplus, combo, ex, sig, notes in board:
            lines.append(
                f"| **{inst}** | {dir_c} | {chk} | {mtf} | {sme} | {svi} | {eplus} | {combo} | {ex} | {sig} | {notes} |"
            )
    lines.append("")
    return lines


def render_reflection_table_markdown(scans: List[InstrumentMTFScan]) -> List[str]:
    """SME reflection — H1 memory + SVI per instrument."""
    lines = [
        "## Reflection table (SME · H1)",
        "",
        "_Signal Memory: SPC=pressure count, SSE=2nd signal effect, SFM=prior weak/fail, EDGE+=combo+SME+SVI._",
        "",
        "| Instrument | Signal (H1) | SPC | SSE | SFM | RQS last | SVI | EDGE+ | SRC |",
        "|------------|-------------|-----|-----|-----|----------|-----|-------|-----|",
    ]
    for s in scans:
        a = s.analyses.get("60")
        r = s.ratings.get("60")
        sme = s.sme_scores.get("60")
        if not a or not r:
            lines.append(f"| **{s.display_name}** | — | — | — | — | — | — | — | — |")
            continue
        sse = "ON" if sme and sme.sse_active else "—"
        sfm = sme.sfm_label if sme and sme.sfm_active else "—"
        rqs = f"{sme.rqs_last:+d}" if sme and sme.rqs_last is not None else "—"
        lines.append(
            f"| **{s.display_name}** | {signal_chip(r.signal_name)} | {sme.spc if sme else 0} | {sse} | {sfm} | {rqs} | "
            f"{sme.svi_weight if sme else 0:+d} | {edge_plus_chip(sme.edge_plus if sme else 0)} | {sme.src_summary if sme else '—'} |"
        )
    lines.append("")
    return lines


def build_timeframe_table_rows(
    scans: List[InstrumentMTFScan],
    tf: str,
) -> List[Tuple]:
    rows = []
    for s in scans:
        r = s.ratings.get(tf)
        a = s.analyses.get(tf)
        edge = s.edge_signals.get(tf)
        sme = s.sme_scores.get(tf)
        if not r or not a:
            rows.append((s.display_name, 0, "NONE", "—", 0.0, 0.0, 0, 0, "—", "no data"))
            continue
        rows.append(
            (
                s.display_name,
                r.score,
                r.strength,
                r.direction,
                round(a.rsi, 1),
                edge.mfi if edge else 0.0,
                edge.edge_combo_score if edge else 0,
                sme.edge_plus if sme else 0,
                r.signal_name,
                _tf_notes(s, tf),
            )
        )
    rows.sort(key=lambda x: abs(x[1]), reverse=True)
    return rows


DASHBOARD_COLS = ("R1", "R2", "R3", "D1", "D2", "D3", "MF", "MV", "CDL", "GM", "Score")


def _dashboard_row_cells(d: TFDashboardState) -> str:
    return " · ".join(d.row_cells())


def render_terminal_matrix_markdown(scans: List[InstrumentMTFScan]) -> List[str]:
    """GEM Logic 1.5 terminal dashboard — one table per instrument (rows = TF)."""
    lines = [
        "## GEM Terminal Matrix (Logic 1.5)",
        "",
        "_Columns match TradingView dashboard. Cells use 🟢 Emerald / 🔴 Ruby / ⚪ neutral + hex codes._",
        "",
    ]
    for scan in scans:
        if not scan.dashboards:
            continue
        cr = scan.combined_rating
        head = scan.display_name
        if cr:
            head = f"{head} — {direction_chip(cr.direction)}"
        lines.append(f"### {head}")
        lines.append("")
        header = "| TF | " + " | ".join(DASHBOARD_COLS) + " |"
        sep = "|----|" + "|".join(["---"] * len(DASHBOARD_COLS)) + "|"
        lines.append(header)
        lines.append(sep)
        for tf in DEFAULT_TIMEFRAMES:
            d = scan.dashboards.get(tf)
            if not d:
                lines.append(f"| {TF_SHORT.get(tf, tf)} | " + " | ".join(["—"] * len(DASHBOARD_COLS)) + " |")
                continue
            cells = coloured_dashboard_row(d)
            lines.append(f"| {TF_SHORT.get(tf, tf)} | " + " | ".join(cells) + " |")
        lines.append("")
    return lines


def terminal_matrix_payload(scans: List[InstrumentMTFScan]) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for scan in scans:
        rows = {}
        for tf, d in scan.dashboards.items():
            rows[tf] = {
                "r1": d.r1,
                "r2": d.r2,
                "r3": d.r3,
                "d1": d.d1,
                "d2": d.d2,
                "d3": d.d3,
                "mf": d.mf,
                "mv": d.mv,
                "cdl": d.cdl,
                "gm": d.gm,
                "bias": d.bias,
                "score": d.score,
                "cells": d.row_cells(),
            }
        if rows:
            out[scan.symbol] = rows
    return out


def render_timeframe_tables_markdown(scans: List[InstrumentMTFScan]) -> List[str]:
    lines = [
        "## Scores by timeframe",
        "",
        "_GEM score + EDGE+ (combo + SME + SVI) per TF._",
        "",
    ]
    for tf in DEFAULT_TIMEFRAMES:
        label = TF_TABLE_TITLES.get(tf, TF_SHORT.get(tf, tf))
        lines.append(f"### {label}")
        lines.append("")
        lines.append("| Instrument | Score | Strength | Signal | RSI | MFI | Combo | EDGE+ | Notes |")
        lines.append("|------------|-------|----------|--------|-----|-----|-------|-------|-------|")
        for row in build_timeframe_table_rows(scans, tf):
            inst, score, strength, direction, rsi, mfi, combo, eplus, signal, notes = row
            score_s = f"{score:+d}" if score else "0"
            if direction == "BULLISH":
                score_s = f"{CHIP_BULL} {score_s}"
            elif direction == "BEARISH":
                score_s = f"{CHIP_BEAR} {score_s}"
            str_cell = mtf_strength_chip(strength, direction, strength_badge(strength))
            rsi_s = f"{rsi:.1f}" if rsi else "—"
            mfi_s = f"{mfi:.0f}" if mfi else "—"
            lines.append(
                f"| **{inst}** | {score_s} | {str_cell} | {signal_chip(signal)} | {rsi_s} | {mfi_s} | "
                f"{combo}/4 | {edge_plus_chip(eplus)} | {notes} |"
            )
        lines.append("")
    return lines


def timeframe_tables_payload(scans: List[InstrumentMTFScan]) -> Dict[str, list]:
    out: Dict[str, list] = {}
    for tf in DEFAULT_TIMEFRAMES:
        out[tf] = [
            {
                "instrument": r[0],
                "score": r[1],
                "strength": r[2],
                "direction": r[3],
                "rsi": r[4],
                "mfi": r[5],
                "edge_combo_score": r[6],
                "edge_plus": r[7],
                "signal": r[8],
                "notes": r[9],
            }
            for r in build_timeframe_table_rows(scans, tf)
        ]
    return out
