#!/usr/bin/env python3
"""
Append GEM scan rows to signal journal.

Douglas: evaluate series, not one trade.
Hougaard: fill result_r and loss_quality after the trade.
"""

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.edge_score import edge_score_from_strength
from src.execution_tier import execution_tier, tier_label
from src.gem_platform import GEMPlatform
from src.watchlist import load_watchlist

JOURNAL = ROOT / "data" / "signal_journal.csv"
SCAN_JSON = ROOT / "reports" / "latest_gem_scan.json"

FIELDS = [
    "logged_at_utc",
    "instrument",
    "symbol",
    "tf_primary",
    "edge_score",
    "edge_plus",
    "svi_weight",
    "spc",
    "sse_active",
    "sme_summary",
    "mtf_strength",
    "mtf_score",
    "direction",
    "exec_tier",
    "checklist_score",
    "trade_ok",
    "signal_name",
    "rsi_h1",
    "exec_state",
    "entry_trigger",
    "candle_closed",
    "result_r",
    "loss_quality",
    "mistake",
    "notes",
]


def append_from_mtf_scans(scans, source: str = "live_scan"):
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    new_file = not JOURNAL.exists()
    ts = datetime.now(timezone.utc).isoformat()

    rows = []
    for s in scans:
        primary = s.analyses.get("60") or s.primary_analysis()
        cr = s.combined_rating
        cl = s.checklist
        sme = s.sme_scores.get("60") or s.primary_sme()
        if not primary or not cr:
            continue
        tier = tier_label(execution_tier(primary, cr, cl))
        rows.append(
            {
                "logged_at_utc": ts,
                "instrument": s.display_name,
                "symbol": s.symbol,
                "tf_primary": "H1",
                "edge_score": edge_score_from_strength(cr.strength),
                "edge_plus": sme.edge_plus if sme else "",
                "svi_weight": sme.svi_weight if sme else "",
                "spc": sme.spc if sme else "",
                "sse_active": sme.sse_active if sme else "",
                "sme_summary": sme.src_summary if sme else "",
                "mtf_strength": cr.strength,
                "mtf_score": cr.score,
                "direction": cr.direction,
                "exec_tier": tier,
                "checklist_score": cl.score if cl else 0,
                "trade_ok": cl.trade_ok if cl else False,
                "signal_name": cr.signal_name,
                "rsi_h1": round(primary.rsi, 2),
                "exec_state": primary.exec_state,
                "entry_trigger": "",
                "candle_closed": "yes",
                "result_r": "",
                "loss_quality": "",
                "mistake": "",
                "notes": source,
            }
        )

    with open(JOURNAL, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new_file:
            w.writeheader()
        w.writerows(rows)
    return len(rows)


def main():
    if SCAN_JSON.exists() and "--from-last-json" in sys.argv:
        data = json.loads(SCAN_JSON.read_text(encoding="utf-8"))
        print(f"Snapshot: {SCAN_JSON} ({data.get('scanned_at_utc')})")
        print("Run without --from-last-json to scan and append.")
        return

    platform = GEMPlatform()
    wl = load_watchlist()
    scans = platform.scan_watchlist_mtf(wl)
    n = append_from_mtf_scans(scans)
    print(f"Appended {n} rows to {JOURNAL}")
    print("After trades, edit CSV:")
    print("  entry_trigger: Yes/No")
    print("  result_r: +1.5R / -1R")
    print("  loss_quality: good_loss | bad_loss | win | execution_error")
    print("  mistake: none | early_entry | widen_sl | revenge | fear_exit")


if __name__ == "__main__":
    main()
