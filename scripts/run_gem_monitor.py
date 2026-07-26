#!/usr/bin/env python3
"""CLI GEM monitor — scans watchlist on an interval (no GUI)."""

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.gem_platform import GEMPlatform
from src.watchlist import load_watchlist

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("gem_monitor")


def print_results(results):
    print("\n" + "=" * 72)
    for r in results:
        flag = ""
        if r.buy_gem:
            flag = " *** EMERALD GEM ***"
        elif r.sell_gem:
            flag = " *** RUBY GEM ***"
        elif r.buy_entry or r.sell_entry:
            flag = " ** ENTRY **"
        elif r.buy_setup or r.sell_setup:
            flag = " * SETUP *"
        print(
            f"{r.symbol:8} RSI={r.rsi:5.1f}  {r.exec_state:16}  "
            f"score={r.gem_score}  B/S events={r.buy_div_events}/{r.sell_div_events}{flag}"
        )
        if flag:
            print(f"         → {r.recommendation}")
    print("=" * 72 + "\n")


def main():
    parser = argparse.ArgumentParser(description="GEM Logic watchlist monitor")
    parser.add_argument("--once", action="store_true", help="Run one scan and exit")
    args = parser.parse_args()

    wl = load_watchlist()
    interval = max(1, int(wl.get("refresh_minutes", 5)))
    platform = GEMPlatform()

    while True:
        results = platform.scan_watchlist(wl)
        actionable = platform.priority_signals(results)
        logger.info("Scanned %s symbols, %s actionable", len(results), len(actionable))
        print_results(results)
        if args.once:
            break
        time.sleep(interval * 60)


if __name__ == "__main__":
    main()
