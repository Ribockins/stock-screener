#!/usr/bin/env python3
"""Cloud GEM scan — MTF strength, checklist, SME memory, heatmap-ready report."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"

from src.gem_platform import GEMPlatform, InstrumentMTFScan
from src.heatmap_data import mtf_rows_to_dataframe
from src.gem_my_list import (
    PRODUCT_NAME,
    build_gem_my_list_rows,
    render_colour_legend_markdown,
    render_gem_my_list_markdown,
    render_reflection_table_markdown,
    render_terminal_matrix_markdown,
    render_timeframe_tables_markdown,
    terminal_matrix_payload,
    timeframe_tables_payload,
)
from src.watchlist import load_watchlist


def build_and_write_report(
    mtf_scans: List[InstrumentMTFScan],
    wl: dict,
    *,
    print_output: bool = True,
) -> Path:
    """Write latest_gem_report.md and latest_gem_scan.json from existing scans."""
    REPORTS.mkdir(parents=True, exist_ok=True)
    df = mtf_rows_to_dataframe(mtf_scans)
    ts = datetime.now(timezone.utc)
    stamp = ts.strftime("%Y%m%d_%H%M%S")

    payload = {
        "scanned_at_utc": ts.isoformat(),
        "mode": "mtf+sme",
        "timeframes": wl.get("timeframes", ["15", "60", "240", "1d"]),
        "symbols_requested": len(wl.get("instruments", [])),
        "symbols_ok": len(mtf_scans),
        "trade_ready": sum(1 for s in mtf_scans if s.checklist and s.checklist.trade_ok),
        "instruments": [],
    }

    for scan in mtf_scans:
        cr = scan.combined_rating
        payload["instruments"].append(
            {
                "symbol": scan.symbol,
                "display_name": scan.display_name,
                "combined": cr.__dict__ if cr else {},
                "checklist": scan.checklist.to_dict() if scan.checklist else {},
                "timeframes": {
                    tf: {
                        "analysis": scan.analyses[tf].to_dict(),
                        "rating": scan.ratings[tf].__dict__,
                        "edge": scan.edge_signals[tf].to_dict()
                        if tf in scan.edge_signals
                        else {},
                        "sme": scan.sme_scores[tf].to_dict()
                        if tf in scan.sme_scores
                        else {},
                    }
                    for tf in scan.ratings
                },
            }
        )

    json_path = REPORTS / f"gem_scan_{stamp}.json"
    md_path = REPORTS / "latest_gem_report.md"
    json_latest = REPORTS / "latest_gem_scan.json"

    payload["gem_my_list"] = [
        {
            "instrument": r[0],
            "direction": r[1],
            "checklist": r[2],
            "mtf": r[3],
            "sme_h1": r[4],
            "svi": r[5],
            "edge_plus": r[6],
            "combo_h1": r[7],
            "exec_tier": r[8],
            "signal": r[9],
            "notes": r[10],
        }
        for r in build_gem_my_list_rows(mtf_scans)
    ]

    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    lines = [
        f"# {PRODUCT_NAME} — {ts.strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        f"**{payload['symbols_ok']}/{payload['symbols_requested']}** instruments · "
        f"**{payload['trade_ready']}** trade-ready · TFs: **15m · 1h · 4h · Daily**",
        "",
        "**Layers:** GEM Logic · EDGE (RSI+MFI+vol) · **SME** (SFM/SSE/SPC/RQS) · **SVI** (instrument profile)",
        "",
    ]
    lines.extend(render_colour_legend_markdown())
    lines.extend(render_gem_my_list_markdown(mtf_scans, trade_ready_only=True))
    if payload["trade_ready"] == 0:
        lines.append("_No trade-ready rows; see full board below._")
        lines.append("")
    lines.append(f"### Full {PRODUCT_NAME} (all instruments)")
    lines.append("")
    lines.extend(render_gem_my_list_markdown(mtf_scans, trade_ready_only=False)[2:])
    lines.extend(render_reflection_table_markdown(mtf_scans))

    payload["timeframe_tables"] = timeframe_tables_payload(mtf_scans)
    payload["terminal_matrix"] = terminal_matrix_payload(mtf_scans)
    lines.extend(render_terminal_matrix_markdown(mtf_scans))
    lines.extend(render_timeframe_tables_markdown(mtf_scans))

    lines.append("## Strength heatmap (compact)")
    lines.append("")
    lines.append("| Instrument | M15 | H1 | H4 | D1 | MTF | Check |")
    lines.append("|------------|-----|----|----|-----|-----|-------|")
    for _, row in df.iterrows():
        cols = [f"{row.get(f'{tf} str', '—')}" for tf in ["M15", "H1", "H4", "D1"]]
        lines.append(
            f"| **{row['Instrument']}** | {' | '.join(cols)} | "
            f"{row['MTF badge']} {row['MTF strength']} | {row['Checklist']} |"
        )
    lines.append("")

    lines.append("## Pre-trade checklist (detail)")
    lines.append("")
    for s in mtf_scans:
        if not s.checklist:
            continue
        cl = s.checklist
        lines.append(f"### {s.display_name} — {cl.summary}")
        for item in cl.items:
            mark = "✓" if item.passed else "✗"
            lines.append(f"- [{mark}] **{item.label}** — {item.detail}")
        sme = s.primary_sme()
        if sme:
            lines.append(
                f"- SME (H1): **{sme.src_summary}** · EDGE+ **{sme.edge_plus}** · SVI {sme.svi_weight:+d}"
            )
        lines.append("")

    lines.append("---")
    lines.append(
        "_Data: `data/signal_ledger.csv` (all TFs) · `data/signal_journal.csv` (H1 discipline)._"
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    json_latest.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    if print_output:
        print(md_path.read_text(encoding="utf-8"))
        print(f"\n(JSON: {json_latest})")
    return md_path


def main(mtf_scans: Optional[List[InstrumentMTFScan]] = None):
    wl = load_watchlist()
    if mtf_scans is None:
        platform = GEMPlatform()
        mtf_scans = platform.scan_watchlist_mtf(wl)
    build_and_write_report(mtf_scans, wl)


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(ROOT))
    main()
