#!/usr/bin/env python3
"""Cloud-only GEM scan — writes human-readable report under reports/."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.gem_platform import GEMPlatform
from src.watchlist import load_watchlist

REPORTS = ROOT / "reports"


def main():
    REPORTS.mkdir(parents=True, exist_ok=True)
    platform = GEMPlatform()
    wl = load_watchlist()
    results = platform.scan_watchlist(wl)
    actionable = platform.priority_signals(results)

    ts = datetime.now(timezone.utc)
    stamp = ts.strftime("%Y%m%d_%H%M%S")

    payload = {
        "scanned_at_utc": ts.isoformat(),
        "symbols_requested": len(wl.get("instruments", [])),
        "symbols_ok": len(results),
        "actionable_count": len(actionable),
        "results": [r.to_dict() for r in results],
    }

    json_path = REPORTS / f"gem_scan_{stamp}.json"
    md_path = REPORTS / "latest_gem_report.md"
    json_latest = REPORTS / "latest_gem_scan.json"

    json_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    json_latest.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    lines = [
        f"# GEM Logic scan — {ts.strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        f"Watchlist: **{payload['symbols_ok']}/{payload['symbols_requested']}** symbols | "
        f"**{payload['actionable_count']}** actionable",
        "",
    ]

    if actionable:
        lines.append("## Actionable signals")
        lines.append("")
        for r in actionable:
            tag = ""
            if r.buy_gem:
                tag = "**EMERALD GEM**"
            elif r.sell_gem:
                tag = "**RUBY GEM**"
            elif r.buy_entry:
                tag = "**LONG ENTRY**"
            elif r.sell_entry:
                tag = "**SHORT ENTRY**"
            elif r.buy_setup:
                tag = "BUY SETUP (3 div)"
            elif r.sell_setup:
                tag = "SELL SETUP (3 div)"
            lines.append(f"- **{r.symbol}** @ ${r.price:.2f} | RSI {r.rsi:.1f} | {tag}")
            lines.append(f"  - {r.recommendation}")
        lines.append("")
    else:
        lines.append("_No actionable GEM signals on this scan._")
        lines.append("")

    lines.append("## All symbols")
    lines.append("")
    lines.append("| Symbol | RSI | Signal | Exec | GEM score |")
    lines.append("|--------|-----|--------|------|-----------|")
    for r in results:
        sig = "—"
        if r.buy_gem:
            sig = "EMERALD GEM"
        elif r.sell_gem:
            sig = "RUBY GEM"
        elif r.buy_setup:
            sig = "BUY SETUP"
        elif r.sell_setup:
            sig = "SELL SETUP"
        elif r.in_oversold:
            sig = "Oversold"
        elif r.in_overbought:
            sig = "Overbought"
        lines.append(
            f"| {r.symbol} | {r.rsi:.1f} | {sig} | {r.exec_state} | {r.gem_score} |"
        )

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(md_path.read_text(encoding="utf-8"))
    print(f"\n(JSON: {json_latest})")


if __name__ == "__main__":
    main()
