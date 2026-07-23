#!/usr/bin/env python3
"""
Finviz screen → GEM My List (colour-coded MTF scan).

Edit config/watchlist_finviz_screen.json with tickers from your Finviz screener.
Finviz API is often blocked in cloud VMs — paste symbols into the config manually.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.gem_platform import GEMPlatform
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

CONFIG = ROOT / "config" / "watchlist_finviz_screen.json"
REPORTS = ROOT / "reports"


def build_report(scans, wl: dict) -> str:
    ts = datetime.now(timezone.utc)
    n_req = len(wl.get("instruments", []))
    trade_ready = sum(1 for s in scans if s.checklist and s.checklist.trade_ok)
    filters = wl.get("filters", "")

    scans.sort(
        key=lambda s: (
            s.checklist.trade_ok if s.checklist else False,
            abs(s.combined_rating.score) if s.combined_rating else 0,
            s.dashboards.get("60").score if s.dashboards.get("60") else 0,
        ),
        reverse=True,
    )

    lines = [
        f"# {PRODUCT_NAME} — Finviz screen — {ts.strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        f"**{len(scans)}/{n_req}** symbols · **{trade_ready}** trade-ready",
    ]
    if filters:
        lines.append(f"**Filters:** `{filters}`")
    lines.append("")
    lines.extend(render_colour_legend_markdown())
    lines.extend(render_gem_my_list_markdown(scans, trade_ready_only=True))
    if trade_ready == 0:
        lines.append("_No trade-ready rows; full board below._")
        lines.append("")
    lines.extend(render_gem_my_list_markdown(scans, trade_ready_only=False)[2:])
    lines.extend(render_reflection_table_markdown(scans))
    lines.extend(render_terminal_matrix_markdown(scans))
    lines.extend(render_timeframe_tables_markdown(scans))
    lines.append("---")
    lines.append("_Config: `config/watchlist_finviz_screen.json` · paste Finviz tickers when cloud fetch blocked._")
    lines.append("")
    return "\n".join(lines)


def main():
    wl = load_watchlist(CONFIG)
    print(f"Finviz screen GEM scan — {len(wl.get('instruments', []))} symbols…")
    scans = GEMPlatform().scan_watchlist_mtf(wl)

    REPORTS.mkdir(parents=True, exist_ok=True)
    md = build_report(scans, wl)
    md_path = REPORTS / "gem_my_list_finviz.md"
    md_path.write_text(md, encoding="utf-8")

    payload = {
        "scanned_at_utc": datetime.now(timezone.utc).isoformat(),
        "watchlist": str(CONFIG.relative_to(ROOT)),
        "filters": wl.get("filters"),
        "symbols_ok": len(scans),
        "trade_ready": sum(1 for s in scans if s.checklist and s.checklist.trade_ok),
        "gem_my_list": [
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
            for r in build_gem_my_list_rows(scans)
        ],
        "terminal_matrix": terminal_matrix_payload(scans),
        "timeframe_tables": timeframe_tables_payload(scans),
    }
    (REPORTS / "gem_my_list_finviz.json").write_text(
        json.dumps(payload, indent=2, default=str), encoding="utf-8"
    )

    print(md)
    print(f"\n(JSON: {REPORTS / 'gem_my_list_finviz.json'})")


if __name__ == "__main__":
    main()
