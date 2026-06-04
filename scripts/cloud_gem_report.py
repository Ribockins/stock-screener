#!/usr/bin/env python3
"""Cloud GEM scan — MTF strength, checklist, heatmap-ready report."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.gem.timeframes import TF_SHORT
from src.gem_platform import GEMPlatform
from src.gem_strength import strength_badge
from src.heatmap_data import mtf_rows_to_dataframe
from src.gem_my_list import (
    PRODUCT_NAME,
    build_gem_my_list_rows,
    render_gem_my_list_markdown,
    render_timeframe_tables_markdown,
    timeframe_tables_payload,
)
from src.watchlist import load_watchlist

REPORTS = ROOT / "reports"


def main():
    REPORTS.mkdir(parents=True, exist_ok=True)
    platform = GEMPlatform()
    wl = load_watchlist()
    mtf_scans = platform.scan_watchlist_mtf(wl)
    df = mtf_rows_to_dataframe(mtf_scans)

    ts = datetime.now(timezone.utc)
    stamp = ts.strftime("%Y%m%d_%H%M%S")

    payload = {
        "scanned_at_utc": ts.isoformat(),
        "mode": "mtf",
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
                    }
                    for tf in scan.ratings
                },
            }
        )

    json_path = REPORTS / f"gem_scan_{stamp}.json"
    md_path = REPORTS / "latest_gem_report.md"
    json_latest = REPORTS / "latest_gem_scan.json"

    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    json_latest.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    payload["gem_my_list"] = [
        {"instrument": r[0], "checklist": r[1], "mtf": r[2], "exec_tier": r[3], "notes": r[4]}
        for r in build_gem_my_list_rows(mtf_scans)
    ]

    lines = [
        f"# {PRODUCT_NAME} — {ts.strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        f"**{payload['symbols_ok']}/{payload['symbols_requested']}** instruments · "
        f"**{payload['trade_ready']}** trade-ready · TFs: **15m · 1h · 4h · Daily**",
        "",
    ]
    lines.extend(render_gem_my_list_markdown(mtf_scans, trade_ready_only=True))
    if payload["trade_ready"] == 0:
        lines.append("_No trade-ready rows; see full board below._")
        lines.append("")
    lines.append(f"### Full {PRODUCT_NAME} (all instruments)")
    lines.append("")
    lines.extend(render_gem_my_list_markdown(mtf_scans, trade_ready_only=False)[2:])

    payload["timeframe_tables"] = timeframe_tables_payload(mtf_scans)
    lines.extend(render_timeframe_tables_markdown(mtf_scans))

    lines.append("## Strength heatmap (compact)")
    lines.append("")
    lines.append("| Instrument | M15 | H1 | H4 | D1 | MTF | Check |")
    lines.append("|------------|-----|----|----|-----|-----|-------|")
    for _, row in df.iterrows():
        cols = []
        for tf in ["M15", "H1", "H4", "D1"]:
            cols.append(f"{row.get(f'{tf} str', '—')}")
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
        lines.append("")

    lines.append("")
    lines.append("---")
    lines.append("_Douglas: CONFIRMED = plan · WARNING = candidate · Journal: scripts/signal_journal.py_")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(md_path.read_text(encoding="utf-8"))
    print(f"\n(JSON: {json_latest})")


if __name__ == "__main__":
    main()
