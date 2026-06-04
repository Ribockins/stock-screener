#!/usr/bin/env python3
"""Append GEM scan rows to signal journal (Douglas: evaluate series, not one trade)."""

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

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
    "mtf_strength",
    "mtf_score",
    "direction",
    "exec_tier",
    "checklist_score",
    "trade_ok",
    "signal_name",
    "rsi_h1",
    "exec_state",
    "result_r",
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
        if not primary or not cr:
            continue
        tier = tier_label(execution_tier(primary, cr, cl))
        rows.append(
            {
                "logged_at_utc": ts,
                "instrument": s.display_name,
                "symbol": s.symbol,
                "tf_primary": "H1",
                "mtf_strength": cr.strength,
                "mtf_score": cr.score,
                "direction": cr.direction,
                "exec_tier": tier,
                "checklist_score": cl.score if cl else 0,
                "trade_ok": cl.trade_ok if cl else False,
                "signal_name": cr.signal_name,
                "rsi_h1": round(primary.rsi, 2),
                "exec_state": primary.exec_state,
                "result_r": "",
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
        print(f"Journal: snapshot already in {SCAN_JSON} ({data.get('scanned_at_utc')})")
        print("Run full scan to append fresh rows, or use default (scan + append).")
        return

    platform = GEMPlatform()
    wl = load_watchlist()
    scans = platform.scan_watchlist_mtf(wl)
    n = append_from_mtf_scans(scans)
    print(f"Appended {n} rows to {JOURNAL}")
    print("Fill column result_r manually after trades (+1.5R / -1R).")


if __name__ == "__main__":
    main()
