"""GEM My List — compact trade board + per-timeframe score tables."""

from __future__ import annotations

from typing import Dict, List, Tuple

from src.gem.timeframes import DEFAULT_TIMEFRAMES, TF_SHORT
from src.gem_platform import InstrumentMTFScan
from src.execution_tier import TIER_WAIT, execution_tier, tier_label
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

    nat = scan.primary_native()
    if nat and nat.score > 0:
        bits.append(f"EDGE2.9 {nat.label}")
    if scan.native_super_buy:
        bits.append("SUPER ALIGN BUY")
    elif scan.native_super_sell:
        bits.append("SUPER ALIGN SELL")

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
    nat = scan.native_signals.get(tf)
    if nat and nat.score > 0:
        bits.append(nat.label)
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
        rows.append(
            (
                s.display_name,
                format_checklist_cell(s),
                format_mtf_cell(s),
                format_sme_cell(s),
                format_svi_cell(s),
                str(edge_plus) if sme_h1 else "—",
                format_edge_cell(s),
                tier,
                _notes(s),
                prio,
                score,
                edge_plus,
            )
        )
    rows.sort(key=lambda r: (r[9], r[10], r[11]), reverse=True)
    return [tuple(r[:9]) for r in rows]


def render_gem_my_list_markdown(
    scans: List[InstrumentMTFScan],
    *,
    trade_ready_only: bool = False,
) -> List[str]:
    heading = f"{PRODUCT_NAME} — trade-ready" if trade_ready_only else f"{PRODUCT_NAME} — all instruments"
    lines = [
        f"## {heading}",
        "",
        "| Instrument | Checklist | MTF | SME (H1) | SVI | EDGE+ | Combo | Exec | Notes |",
        "|------------|-----------|-----|----------|-----|-------|-------|------|-------|",
    ]
    board = build_gem_my_list_rows(scans, trade_ready_only=trade_ready_only)
    if not board:
        lines.append("| _none_ | — | — | — | — | — | — | WAIT | No rows |")
    else:
        for inst, chk, mtf, sme, svi, eplus, combo, ex, notes in board:
            lines.append(
                f"| **{inst}** | {chk} | {mtf} | {sme} | {svi} | **{eplus}** | {combo} | {ex} | {notes} |"
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
            f"| **{s.display_name}** | {r.signal_name} | {sme.spc if sme else 0} | {sse} | {sfm} | {rqs} | "
            f"{sme.svi_weight if sme else 0:+d} | **{sme.edge_plus if sme else 0}** | {sme.src_summary if sme else '—'} |"
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
            str_cell = f"{strength_badge(strength)} {strength}"
            if direction in ("BULLISH", "BEARISH"):
                str_cell += f" {direction.lower()}"
            rsi_s = f"{rsi:.1f}" if rsi else "—"
            mfi_s = f"{mfi:.0f}" if mfi else "—"
            lines.append(
                f"| **{inst}** | {score_s} | {str_cell} | {signal} | {rsi_s} | {mfi_s} | {combo}/4 | **{eplus}** | {notes} |"
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
