#!/usr/bin/env python3
"""
Finviz gainers (separate watchlist): rank by market cap, take top N, show only bullish GEM signals.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yfinance as yf

from src.gem.models import GEMAnalysis
from src.gem_platform import GEMPlatform
from src.watchlist import load_watchlist

FINVIZ_CONFIG = ROOT / "config" / "finviz_gainers.json"
REPORTS = ROOT / "reports"
TOP_N = 10


def is_good_long_signal(r: GEMAnalysis) -> bool:
    """Bullish / constructive GEM — not overbought Ruby fade."""
    if r.sell_gem or r.sell_setup or r.sell_entry:
        return False
    if r.in_overbought and r.rsi >= 72:
        return False
    return bool(
        r.buy_gem
        or r.buy_setup
        or r.buy_entry
        or (r.raw_buy_div and r.divergence_state == "BUY")
        or (r.in_oversold and r.gem_score >= 2)
    )


def signal_label(r: GEMAnalysis) -> str:
    if r.buy_gem:
        return "EMERALD GEM"
    if r.buy_entry:
        return "LONG ENTRY"
    if r.buy_setup:
        return "BUY SETUP"
    if r.raw_buy_div:
        return "BUY DIV"
    if r.in_oversold:
        return "OVERSOLD"
    if r.sell_gem:
        return "RUBY GEM"
    if r.sell_setup:
        return "SELL SETUP"
    if r.in_overbought:
        return "OVERBOUGHT"
    return "NEUTRAL"


def fetch_market_caps(symbols: list[str]) -> dict[str, float | None]:
    caps: dict[str, float | None] = {}
    for sym in symbols:
        try:
            info = yf.Ticker(sym).info
            cap = info.get("marketCap")  # EV fallback mis-ranks thin tickers (e.g. LILKV)
            caps[sym] = float(cap) if cap else None
        except Exception:
            caps[sym] = None
    return caps


def fmt_cap(cap: float | None) -> str:
    if cap is None:
        return "—"
    if cap >= 1e12:
        return f"${cap / 1e12:.2f}T"
    if cap >= 1e9:
        return f"${cap / 1e9:.2f}B"
    if cap >= 1e6:
        return f"${cap / 1e6:.1f}M"
    return f"${cap:,.0f}"


def main():
    wl = load_watchlist(FINVIZ_CONFIG)
    symbols = [i["symbol"] for i in wl.get("instruments", [])]
    caps = fetch_market_caps(symbols)

    ranked = sorted(
        symbols,
        key=lambda s: caps.get(s) or 0,
        reverse=True,
    )
    top_symbols = ranked[:TOP_N]

    platform = GEMPlatform()
    results = platform.scan_watchlist(wl)
    by_sym = {r.symbol: r for r in results}

    top_rows = []
    good_rows = []
    for sym in top_symbols:
        r = by_sym.get(sym)
        row = {
            "symbol": sym,
            "market_cap": caps.get(sym),
            "market_cap_fmt": fmt_cap(caps.get(sym)),
            "has_data": r is not None,
            "good_signal": False,
        }
        if r:
            row.update(
                {
                    "price": r.price,
                    "rsi": round(r.rsi, 1),
                    "signal": signal_label(r),
                    "gem_score": r.gem_score,
                    "good_signal": is_good_long_signal(r),
                    "recommendation": r.recommendation,
                    "data_source": r.data_source,
                }
            )
            if row["good_signal"]:
                good_rows.append(row)
        top_rows.append(row)

    ts = datetime.now(timezone.utc)
    payload = {
        "scanned_at_utc": ts.isoformat(),
        "watchlist": "config/finviz_gainers.json",
        "top_n_by_market_cap": TOP_N,
        "top_by_cap": top_rows,
        "good_signals_in_top_n": good_rows,
        "good_count": len(good_rows),
    }

    REPORTS.mkdir(parents=True, exist_ok=True)
    out_json = REPORTS / "finviz_top_cap_gem.json"
    out_md = REPORTS / "finviz_top_cap_gem.md"
    out_json.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    lines = [
        f"# Finviz gainers — top {TOP_N} by market cap (GEM filter)",
        "",
        f"_Scanned {ts.strftime('%Y-%m-%d %H:%M UTC')} · separate from main watchlist_",
        "",
        f"**{len(good_rows)}** of **{TOP_N}** have **good (bullish) GEM signals**.",
        "",
    ]

    lines.append(f"## Top {TOP_N} by market cap (all)")
    lines.append("")
    lines.append("| Rank | Symbol | Market cap | Price | RSI | GEM signal | Good? |")
    lines.append("|------|--------|------------|-------|-----|------------|-------|")
    for i, row in enumerate(top_rows, 1):
        good = "yes" if row.get("good_signal") else "—"
        if not row.get("has_data"):
            lines.append(
                f"| {i} | **{row['symbol']}** | {row['market_cap_fmt']} | — | — | no data | — |"
            )
        else:
            lines.append(
                f"| {i} | **{row['symbol']}** | {row['market_cap_fmt']} | "
                f"${row['price']:.2f} | {row['rsi']} | {row['signal']} | {good} |"
            )
    lines.append("")

    if good_rows:
        lines.append("## Good signals only (bullish GEM, within top 10 by cap)")
        lines.append("")
        for row in good_rows:
            lines.append(
                f"- **{row['symbol']}** · {row['market_cap_fmt']} · "
                f"${row['price']:.2f} · RSI {row['rsi']} · **{row['signal']}** (score {row['gem_score']})"
            )
            if row.get("recommendation"):
                lines.append(f"  - {row['recommendation']}")
        lines.append("")
    else:
        lines.append("## Good signals only")
        lines.append("")
        lines.append(
            "_None of the top 10 by market cap pass the bullish GEM filter "
            "(no Ruby / overbought / sell setup)._"
        )
        lines.append("")

    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(out_md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
