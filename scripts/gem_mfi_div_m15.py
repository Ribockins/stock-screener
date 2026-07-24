#!/usr/bin/env python3
"""GEM My List — M15 only, MFI divergence at last closed M15 bar (live)."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd

from src.edge_combos import calculate_mfi
from src.edge_combos import _simple_divergence
from src.market_data import MarketDataService
from src.watchlist import load_watchlist

REPORTS = ROOT / "reports"
TITLE = "GEM My List — MFI Divergence · M15 only"
MFI_PERIOD = 14
DIV_LOOKBACK = 10


@dataclass
class MFIM15Row:
    instrument: str
    symbol: str
    price: float
    mfi: Optional[float]
    div_type: str  # BULL | BEAR | NONE
    mfi_ok: bool
    bar_time: str
    source: str
    notes: str

    @property
    def colour(self) -> str:
        if self.div_type == "BULL":
            return "🟢 `#00c896`"
        if self.div_type == "BEAR":
            return "🔴 `#c62828`"
        return "⚪ `#9e9e9e`"

    @property
    def signal_label(self) -> str:
        if self.div_type == "BULL":
            return "MFI bull div"
        if self.div_type == "BEAR":
            return "MFI bear div"
        return "—"


def scan_mfi_m15(watchlist: dict | None = None) -> tuple[List[MFIM15Row], str]:
    wl = watchlist or load_watchlist()
    instruments = wl.get("instruments", [])
    bars = int(wl.get("bars", 120))
    market = MarketDataService()
    rows: List[MFIM15Row] = []

    for inst in instruments:
        sym = inst.get("symbol")
        name = inst.get("name") or sym
        if not sym:
            continue
        fetched = market.fetch_many([inst], bars=bars, interval_key="15")
        if sym not in fetched:
            rows.append(
                MFIM15Row(name, sym, 0.0, None, "NONE", False, "—", "—", "no data")
            )
            continue

        df, source = fetched[sym]
        df = df.copy()
        df.columns = [str(c).lower() for c in df.columns]
        vol_sum = float(df["volume"].fillna(0).sum()) if "volume" in df.columns else 0.0
        mfi = calculate_mfi(df, MFI_PERIOD)
        mfi_valid = mfi.dropna()

        if mfi_valid.empty or vol_sum <= 0:
            price = float(df["close"].iloc[-1])
            ts = _bar_ts(df)
            rows.append(
                MFIM15Row(
                    name,
                    sym,
                    price,
                    None,
                    "NONE",
                    False,
                    ts,
                    source,
                    "MFI N/A (no volume)",
                )
            )
            continue

        close = df["close"]
        mfi_bear = _simple_divergence(close, mfi, DIV_LOOKBACK, bearish=True)
        mfi_bull = _simple_divergence(close, mfi, DIV_LOOKBACK, bearish=False)
        div = "BEAR" if mfi_bear else ("BULL" if mfi_bull else "NONE")
        cur_mfi = float(mfi.iloc[-1])
        price = float(close.iloc[-1])
        notes = []
        if div == "BEAR":
            notes.append("price HH · MFI LH")
        elif div == "BULL":
            notes.append("price LL · MFI HL")
        else:
            notes.append("no MFI div this bar")

        rows.append(
            MFIM15Row(
                name,
                sym,
                price,
                round(cur_mfi, 1),
                div,
                True,
                _bar_ts(df),
                source,
                "; ".join(notes),
            )
        )

    scanned_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return rows, scanned_at


def _bar_ts(df: pd.DataFrame) -> str:
    try:
        t = df.index[-1]
        if hasattr(t, "strftime"):
            return t.strftime("%Y-%m-%d %H:%M")
        return str(t)[:16]
    except Exception:
        return "—"


def _sort_rows(rows: List[MFIM15Row]) -> List[MFIM15Row]:
    rank = {"BEAR": 2, "BULL": 2, "NONE": 0}

    def key(r: MFIM15Row):
        return (rank.get(r.div_type, 0), r.mfi_ok, abs(r.mfi or 0))

    return sorted(rows, key=key, reverse=True)


def render_markdown(rows: List[MFIM15Row], scanned_at: str) -> str:
    rows = _sort_rows(rows)
    active = [r for r in rows if r.div_type in ("BULL", "BEAR")]
    lines = [
        f"# {TITLE}",
        "",
        f"**{scanned_at}** · last **M15** bar per symbol · filter: **MFI divergence only**",
        "",
        f"**{len(active)}/{len(rows)}** with MFI div on current M15 bar",
        "",
    ]

    lines.append("## Active MFI divergence (M15)")
    lines.append("")
    lines.append("| Instrument | Signal | MFI % | Price | Bar (UTC/local) | Colour | Notes |")
    lines.append("|------------|--------|-------|-------|-----------------|--------|-------|")
    if not active:
        lines.append("| _none_ | — | — | — | — | ⚪ | No MFI div on this M15 close |")
    else:
        for r in active:
            mfi_s = f"{r.mfi:.1f}" if r.mfi is not None else "—"
            price_s = f"{r.price:.5g}" if r.price < 10 else f"{r.price:.2f}"
            lines.append(
                f"| **{r.instrument}** | **{r.signal_label}** | {mfi_s} | {price_s} | {r.bar_time} | {r.colour} | {r.notes} |"
            )
    lines.append("")

    lines.append("## Full watchlist (M15 · MFI check)")
    lines.append("")
    lines.append("| Instrument | MFI div | MFI % | Price | Bar | Source |")
    lines.append("|------------|---------|-------|-------|-----|--------|")
    for r in rows:
        div_cell = f"**{r.div_type}**" if r.div_type != "NONE" else "—"
        mfi_s = f"{r.mfi:.1f}" if r.mfi is not None else "N/A"
        price_s = f"{r.price:.5g}" if r.price < 10 else f"{r.price:.2f}"
        lines.append(
            f"| **{r.instrument}** | {div_cell} | {mfi_s} | {price_s} | {r.bar_time} | {r.source} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("_MFI period 14 · div lookback 10 bars · Forex may show N/A (zero volume feed)._")
    return "\n".join(lines) + "\n"


def main():
    REPORTS.mkdir(parents=True, exist_ok=True)
    rows, scanned_at = scan_mfi_m15()
    md = render_markdown(rows, scanned_at)
    out = REPORTS / "latest_mfi_div_m15.md"
    out.write_text(md, encoding="utf-8")
    payload = {
        "scanned_at_utc": datetime.now(timezone.utc).isoformat(),
        "timeframe": "15",
        "filter": "mfi_divergence_only",
        "rows": [
            {
                "instrument": r.instrument,
                "symbol": r.symbol,
                "div_type": r.div_type,
                "mfi": r.mfi,
                "price": r.price,
                "bar_time": r.bar_time,
                "source": r.source,
                "notes": r.notes,
            }
            for r in rows
        ],
    }
    (REPORTS / "latest_mfi_div_m15.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    print(md)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
