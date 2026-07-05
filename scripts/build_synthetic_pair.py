#!/usr/bin/env python3
"""Build synthetic pair indices A10/B12 — balanced or channel (fewer stocks, wider range)."""

from __future__ import annotations

import argparse
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
    build_pair_indices_channel,
    cap_weighted_series,
    channel_metrics,
    channel_roundtrip_trades,
    fetch_history,
    fetch_pool_history,
    fetch_pool_metadata,
    load_universe,
    save_config,
)

CONFIG_OUT = ROOT / "config" / "synthetic_pair_a10_b12.json"
REPORT_OUT = ROOT / "reports" / "synthetic_pair_backtest.md"


def write_report(result, pool, rows, level_a, level_b, stats, channel_stats, mode: str):
    end_a, end_b = float(level_a.iloc[-1]), float(level_b.iloc[-1])
    bal = result.balance["ratios"]
    ta = result.index_a.totals()
    tb = result.index_b.totals()
    ch = result.balance.get("channel", {})

    lines = [
        f"# Synthetic Pair — A10 vs B12 ({mode})",
        "",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Design",
        f"- Mode: **{mode}**",
        f"- Pool: **{len(rows)}** configured · **{len(pool)}** with metadata",
        f"- **A10**: {result.index_a.n} stocks · **B12**: {result.index_b.n} stocks",
        f"- Base level: **{INDEX_TARGET:,.0f}** each",
        "",
    ]

    if mode == "channel":
        lines += [
            "## Straight channel",
            "",
            f"- **Channel width (spread):** {channel_stats['channel_width']} pts",
            f"- **Lower / Mid / Upper:** {channel_stats['channel_lower']} / "
            f"{channel_stats['channel_mid']} / {channel_stats['channel_upper']}",
            f"- **Spread range (2m):** {ch.get('spread_min')} → {ch.get('spread_max')} "
            f"(Δ {ch.get('spread_range')})",
            f"- **Line R² (A vs B):** {ch.get('line_r2')} — straight co-movement",
            f"- **Drift ratio:** {ch.get('drift_ratio')} (lower = flatter channel)",
            f"- **Round-trips (buy/sell):** {channel_stats['roundtrips']}",
            f"- **Channel strategy PnL:** {channel_stats['pnl_pct']}% · DD {channel_stats['max_dd_pct']}%",
            "",
            "### How to trade",
            "",
            "| Spread at | Action |",
            "|-----------|--------|",
            f"| ≤ **{channel_stats['channel_lower']}** (lower rail) | **BUY spread** — long A10, short B12 |",
            f"| ≥ **{channel_stats['channel_upper']}** (upper rail) | **SELL spread** — flat / reverse |",
            f"| ~ **{channel_stats['channel_mid']}** | Neutral — wait |",
            "",
        ]

    lines += [
        "## Balance",
        "",
        "| Metric | A10 | B12 | A/B |",
        "|--------|-----|-----|-----|",
        f"| Price sum | {ta['price_sum']:,.0f} | {tb['price_sum']:,.0f} | {bal['price_a_over_b']:.3f} |",
        f"| Market cap | {ta['market_cap']/1e9:,.0f}B | {tb['market_cap']/1e9:,.0f}B | {bal['cap_a_over_b']:.3f} |",
        f"| End level | {end_a:,.0f} | {end_b:,.0f} | {end_a/end_b:.3f} |",
        "",
        "### A10",
        "",
        "| Symbol | Name | Sector |",
        "|--------|------|--------|",
    ]
    for m in result.index_a.members:
        lines.append(f"| `{m.symbol}` | {m.name} | {m.sector} |")

    lines += ["", "### B12", "", "| Symbol | Name | Sector |", "|--------|------|--------|"]
    for m in result.index_b.members:
        lines.append(f"| `{m.symbol}` | {m.name} | {m.sector} |")

    lines += [
        "",
        "## Backtest (2m H1)",
        "",
        f"- Correlation: **{stats['correlation']}**",
        f"- Spread σ: **{stats['spread_std']}** · z-range [{stats['z_min']}, {stats['z_max']}]",
        f"- Z-score strategy PnL: {stats['pair_trades_pnl_pct']}% · DD {stats['pair_max_dd_pct']}%",
        "",
        f"Config: `{CONFIG_OUT.name}`",
    ]

    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    REPORT_OUT.write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--mode",
        choices=("balanced", "channel"),
        default="channel",
        help="balanced=15+15 matched; channel=6+6 max spread in straight channel",
    )
    ap.add_argument("--stocks-per-side", type=int, default=6)
    args = ap.parse_args()

    print(f"Mode: {args.mode}")
    rows = load_universe()
    pool = fetch_pool_metadata(rows)
    print(f"Pool: {len(pool)} valid stocks")

    symbols = [s.symbol for s in pool]
    print("Downloading 2m H1 for full pool...")
    prices = fetch_pool_history(symbols, months=2, interval="1h")
    print(f"  Price matrix: {prices.shape[1]} symbols × {len(prices)} bars")

    if args.mode == "channel":
        print(f"Optimising channel pair ({args.stocks_per_side} stocks per side)...")
        result = build_pair_indices_channel(
            pool, prices, n_per_side=args.stocks_per_side
        )
        ch = result.balance.get("channel", {})
        print(f"  Channel score={ch.get('channel_score')} range={ch.get('spread_range')} corr={ch.get('correlation')}")
    else:
        result = build_pair_indices(pool)

    save_config(result, CONFIG_OUT)

    all_syms = [m.symbol for m in result.index_a.members + result.index_b.members]
    sub = prices[all_syms].dropna(how="any")
    level_a = cap_weighted_series(result.index_a.members, sub)
    level_b = cap_weighted_series(result.index_b.members, sub)
    stats = backtest_pair(level_a, level_b)
    channel_stats = channel_roundtrip_trades(level_a, level_b)

    write_report(result, pool, rows, level_a, level_b, stats, channel_stats, args.mode)
    print(f"Report: {REPORT_OUT}")
    print(json.dumps({**stats, **channel_stats, "channel_meta": result.balance.get("channel", {})}, indent=2)[:2000])


if __name__ == "__main__":
    main()
