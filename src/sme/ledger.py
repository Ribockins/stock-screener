"""Persist scan-time SME snapshots for long-run SVI / IRP stats."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from src.gem_platform import InstrumentMTFScan

ROOT = Path(__file__).resolve().parents[2]
LEDGER_PATH = ROOT / "data" / "signal_ledger.csv"

LEDGER_FIELDS = [
    "logged_at_utc",
    "symbol",
    "instrument",
    "timeframe",
    "signal_name",
    "direction",
    "strength",
    "gem_score",
    "rsi",
    "price",
    "spc",
    "sse_active",
    "sfm_active",
    "sfm_label",
    "rqs_last",
    "edge_combo",
    "sme_boost",
    "svi_weight",
    "edge_plus",
    "src_summary",
    "exec_state",
    "trade_ok",
    "checklist_score",
]


def append_scan_ledger(
    scans: List[InstrumentMTFScan],
    *,
    timeframes: tuple[str, ...] = ("15", "60", "240", "1d"),
) -> int:
    """Append one row per instrument×TF where GEM produced analysis."""
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    new_file = not LEDGER_PATH.exists()
    ts = datetime.now(timezone.utc).isoformat()
    rows = []

    for scan in scans:
        cl = scan.checklist
        for tf in timeframes:
            a = scan.analyses.get(tf)
            r = scan.ratings.get(tf)
            sme = scan.sme_scores.get(tf)
            edge = scan.edge_signals.get(tf)
            if not a or not r:
                continue
            combo = edge.edge_combo_score if edge else 0
            rows.append(
                {
                    "logged_at_utc": ts,
                    "symbol": scan.symbol,
                    "instrument": scan.display_name,
                    "timeframe": tf,
                    "signal_name": r.signal_name,
                    "direction": r.direction,
                    "strength": r.strength,
                    "gem_score": r.score,
                    "rsi": round(a.rsi, 2),
                    "price": round(a.price, 6),
                    "spc": sme.spc if sme else 0,
                    "sse_active": sme.sse_active if sme else False,
                    "sfm_active": sme.sfm_active if sme else False,
                    "sfm_label": sme.sfm_label if sme else "",
                    "rqs_last": sme.rqs_last if sme and sme.rqs_last is not None else "",
                    "edge_combo": combo,
                    "sme_boost": sme.sme_boost if sme else 0,
                    "svi_weight": sme.svi_weight if sme else 0,
                    "edge_plus": sme.edge_plus if sme else 0,
                    "src_summary": sme.src_summary if sme else "",
                    "exec_state": a.exec_state,
                    "trade_ok": cl.trade_ok if cl else False,
                    "checklist_score": cl.score if cl else 0,
                }
            )

    with open(LEDGER_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_FIELDS)
        if new_file:
            w.writeheader()
        w.writerows(rows)
    return len(rows)


def ledger_summary_path() -> Path:
    return LEDGER_PATH
