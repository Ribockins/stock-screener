#!/usr/bin/env python3
"""One command: live MTF scan → journal → SME ledger → GEM My List report."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.cloud_gem_report import build_and_write_report
from scripts.signal_journal import append_from_mtf_scans
from src.gem_platform import GEMPlatform
from src.sme.ledger import append_scan_ledger, ledger_summary_path
from src.watchlist import load_watchlist


def main():
    wl = load_watchlist()
    print("Scanning watchlist (live markets)…")
    scans = GEMPlatform().scan_watchlist_mtf(wl)
    n_journal = append_from_mtf_scans(scans, source="gem_scan_pipeline")
    n_ledger = append_scan_ledger(scans)
    print(f"Journal: +{n_journal} rows → data/signal_journal.csv")
    print(f"Ledger:  +{n_ledger} rows → {ledger_summary_path()}")
    build_and_write_report(scans, wl)


if __name__ == "__main__":
    main()
