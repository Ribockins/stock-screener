#!/usr/bin/env python3
"""Build synthetic pair indices A10/B12 and backtest 2-month co-movement."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.pair_indices import (
    INDEX_TARGET,
    backtest_pair,
    build_pair_indices,
    cap_weighted_series,
    fetch_history,
    fetch_pool_metadata,
    load_universe,
    save_config,
)

CONFIG_OUT = ROOT / "config" / "synthetic_pair_a10_b12.json"
REPORT_OUT = ROOT / "reports" / "synthetic_pair_backtest.md"


def main():
    print("Loading universe (~140 FTSE + CAC)...")
    rows = load_universe()
    print(f"  {len(rows)} symbols in config")

    print("Fetching metadata (yfinance)...")
    pool = fetch_pool_metadata(rows)
    print(f"  {len(pool)} stocks with valid cap/price/volume")

    if len(pool) < 30:
        print("ERROR: insufficient valid stocks")
        sys.exit(1)

    print("Building balanced pair A10 / B12...")
    result = build_pair_indices(pool)
    save_config(result, CONFIG_OUT)
    print(f"  Saved {CONFIG_OUT}")

    a_syms = [m.symbol for m in result.index_a.members]
    b_syms = [m.symbol for m in result.index_b.members]
    print(f"  A10: {result.index_a.n} stocks | B12: {result.index_b.n} stocks")
    bal = result.balance["ratios"]
    print(
        f"  Balance ratios cap={bal['cap_a_over_b']} price={bal['price_a_over_b']} "
        f"vol={bal['volume_a_over_b']}"
    )

    all_syms = list(dict.fromkeys(a_syms + b_syms))
    print(f"\nFetching 2-month H1 history for {len(all_syms)} members...")
    prices = fetch_history(all_syms, months=2, interval="1h")
    if prices.empty:
        print("ERROR: no price history")
        sys.exit(1)
    print(f"  {len(prices)} bars | {prices.index[0]} → {prices.index[-1]}")

    level_a = cap_weighted_series(result.index_a.members, prices)
    level_b = cap_weighted_series(result.index_b.members, prices)
    stats = backtest_pair(level_a, level_b)

    # Level at end
    end_a, end_b = float(level_a.iloc[-1]), float(level_b.iloc[-1])

    lines = [
        "# Synthetic Pair Indices — A10 vs B12",
        "",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Design",
        f"- Pool: **{len(rows)}** configured · **{len(pool)}** with live metadata",
        f"- **A10**: {result.index_a.n} stocks (cap-weighted synthetic index)",
        f"- **B12**: {result.index_b.n} stocks",
        f"- Base level: **{INDEX_TARGET:,.0f}** each at start of backtest window",
        "",
        "## Balance at construction",
        "",
        "| Metric | A10 | B12 | A/B ratio |",
        "|--------|-----|-----|-----------|",
    ]
    ta = result.index_a.totals()
    tb = result.index_b.totals()
    lines.append(
        f"| Price sum | {ta['price_sum']:,.1f} | {tb['price_sum']:,.1f} | {bal['price_a_over_b']:.4f} |"
    )
    lines.append(
        f"| Market cap | {ta['market_cap']/1e9:,.1f}B | {tb['market_cap']/1e9:,.1f}B | {bal['cap_a_over_b']:.4f} |"
    )
    lines.append(
        f"| Volume | {ta['volume']/1e6:,.1f}M | {tb['volume']/1e6:,.1f}M | {bal['volume_a_over_b']:.4f} |"
    )
    lines.append(
        f"| End index level (2m) | {end_a:,.1f} | {end_b:,.1f} | {end_a/end_b:.4f} |"
    )

    lines += [
        "",
        "### A10 members",
        "",
        "| Symbol | Name | Sector | Weight% |",
        "|--------|------|--------|---------|",
    ]
    cap_a = sum(m.market_cap for m in result.index_a.members) or 1
    for m in result.index_a.members:
        w = m.market_cap / cap_a * 100
        lines.append(f"| `{m.symbol}` | {m.name} | {m.sector} | {w:.1f}% |")

    lines += [
        "",
        "### B12 members",
        "",
        "| Symbol | Name | Sector | Weight% |",
        "|--------|------|--------|---------|",
    ]
    cap_b = sum(m.market_cap for m in result.index_b.members) or 1
    for m in result.index_b.members:
        w = m.market_cap / cap_b * 100
        lines.append(f"| `{m.symbol}` | {m.name} | {m.sector} | {w:.1f}% |")

    lines += [
        "",
        "## 2-month backtest (H1)",
        "",
        f"- **Return correlation:** {stats['correlation']}",
        f"- **Spread (A10−B12):** mean {stats['spread_mean']} · σ {stats['spread_std']} · "
        f"range [{stats['spread_min']}, {stats['spread_max']}]",
        f"- **Ratio A10/B12:** mean {stats['ratio_mean']} · σ {stats['ratio_std']}",
        f"- **Z-score range:** [{stats['z_min']}, {stats['z_max']}]",
        f"- **Simple pair strategy** (z>2 short spread, z<-2 long, exit |z|<0.5):",
        f"  - Cumulative PnL: **{stats['pair_trades_pnl_pct']}%** (spread legs, unlevered)",
        f"  - Max drawdown: **{stats['pair_max_dd_pct']}%**",
        "",
        "## Pair-trading read",
        "",
    ]

    if stats["correlation"] >= 0.85:
        lines.append("✅ **High co-movement** — indices oscillate in tandem; spread mean-reversion feasible.")
    elif stats["correlation"] >= 0.7:
        lines.append("⚠️ **Moderate co-movement** — hedge works with tighter risk controls.")
    else:
        lines.append("❌ **Low correlation** — revisit basket balance or member selection.")

    if abs(end_a - end_b) / INDEX_TARGET < 0.05:
        lines.append(f"✅ **End levels within 5%** of each other ({end_a:,.0f} vs {end_b:,.0f}).")
    else:
        lines.append(f"⚠️ **End level drift** — rebalance weights periodically ({end_a:,.0f} vs {end_b:,.0f}).")

    lines += [
        "",
        f"Config: `{CONFIG_OUT.relative_to(ROOT)}`",
    ]

    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport: {REPORT_OUT}")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
