#!/usr/bin/env python3
"""
Index basket connectivity test + 2-month H1 EDGE backtest.

Filter: GEM EDGE score >= 2 (MEDIUM+) and edge_combo >= 2.
Simulation: narrow spread, 10x leverage, tight take-profit.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.edge_engine import analyze_edge_bar
from src.edge_score import edge_score_from_strength
from src.gem.analyzer import GEMAnalyzer
from src.gem_strength import rate_gem_analysis
from src.market_data import normalize_ohlcv

WATCHLIST = ROOT / "config" / "watchlist_index_baskets.json"
REPORT_DIR = ROOT / "reports"
MONTHS = 2
TF = "60"
MIN_WARMUP = 50

# Simulation params (user: narrow spread, 1:10, tight TP)
SPREAD_BPS_INDEX = 2.0
SPREAD_BPS_STOCK = 5.0
LEVERAGE = 10
TP_PCT = 0.35  # tight take profit on underlying price
SL_PCT = 0.25  # tight stop
MAX_HOLD_BARS = 16
MIN_EDGE_SCORE = 2
MIN_EDGE_COMBO = 2


@dataclass
class ConnectivityResult:
    symbol: str
    name: str
    group: str
    source: str
    ok: bool
    bars: int
    start: str
    end: str
    error: str = ""


@dataclass
class TradeResult:
    symbol: str
    name: str
    group: str
    entry_time: str
    direction: str
    edge_score: int
    edge_combo: int
    signal_name: str
    entry_price: float
    exit_price: float
    exit_reason: str
    hold_bars: int
    pnl_pct_underlying: float
    pnl_pct_margin: float
    mfe_pct: float
    mae_pct: float


@dataclass
class SymbolStats:
    symbol: str
    name: str
    group: str
    signals: int = 0
    trades: int = 0
    wins: int = 0
    losses: int = 0
    total_margin_pct: float = 0.0
    max_dd_margin_pct: float = 0.0
    trades_list: List[TradeResult] = field(default_factory=list)


def load_instruments() -> List[dict]:
    data = json.loads(WATCHLIST.read_text(encoding="utf-8"))
    return data["instruments"]


def spread_bps(symbol: str) -> float:
    return SPREAD_BPS_INDEX if symbol.startswith("^") else SPREAD_BPS_STOCK


def fetch_yfinance_h1(symbol: str, months: int = MONTHS) -> Tuple[Optional[pd.DataFrame], str]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=months * 31)
    try:
        df = yf.download(
            symbol,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            interval="1h",
            progress=False,
            auto_adjust=True,
            threads=False,
        )
        if df is None or df.empty:
            return None, "yfinance: empty"
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = normalize_ohlcv(df)
        if df is None or len(df) < MIN_WARMUP:
            return None, f"yfinance: only {0 if df is None else len(df)} bars"
        return df, "yfinance"
    except Exception as e:
        return None, f"yfinance: {e}"


def test_tradingview(symbol: str, exchange: str) -> Tuple[bool, str]:
    try:
        from src.data_fetcher import TradingViewFetcher

        tv = TradingViewFetcher()
        df = tv.fetch_h1_data(symbol, bars=30)
        if df is not None and len(df) >= 10:
            return True, f"tradingview: {len(df)} bars"
        return False, "tradingview: no data"
    except Exception as e:
        return False, f"tradingview: {e}"


def test_connectivity(instruments: List[dict]) -> List[ConnectivityResult]:
    results = []
    for inst in instruments:
        sym = inst["symbol"]
        df, yf_msg = fetch_yfinance_h1(sym)
        ok = df is not None
        start = end = ""
        bars = len(df) if df is not None else 0
        if ok:
            start = str(df.index[0])[:19]
            end = str(df.index[-1])[:19]
        tv_ok, tv_msg = test_tradingview(sym, inst.get("exchange", ""))
        source = yf_msg if ok else yf_msg
        if tv_ok:
            source = f"{source}; {tv_msg}"
        results.append(
            ConnectivityResult(
                symbol=sym,
                name=inst["name"],
                group=inst.get("group", ""),
                source=source,
                ok=ok,
                bars=bars,
                start=start,
                end=end,
                error="" if ok else yf_msg,
            )
        )
    return results


def simulate_trade(
    df: pd.DataFrame,
    bar_i: int,
    direction: str,
    symbol: str,
    meta: dict,
) -> Optional[TradeResult]:
    entry = float(df["close"].iloc[bar_i])
    spread = spread_bps(symbol) / 10000.0
    if direction == "BULLISH":
        entry_eff = entry * (1 + spread / 2)
        tp = entry_eff * (1 + TP_PCT / 100)
        sl = entry_eff * (1 - SL_PCT / 100)
    else:
        entry_eff = entry * (1 - spread / 2)
        tp = entry_eff * (1 - TP_PCT / 100)
        sl = entry_eff * (1 + SL_PCT / 100)

    mfe = 0.0
    mae = 0.0
    exit_price = entry_eff
    exit_reason = "timeout"
    hold = 0

    end_i = min(len(df) - 1, bar_i + MAX_HOLD_BARS)
    for j in range(bar_i + 1, end_i + 1):
        hold += 1
        hi = float(df["high"].iloc[j])
        lo = float(df["low"].iloc[j])
        cl = float(df["close"].iloc[j])

        if direction == "BULLISH":
            mfe = max(mfe, (hi - entry_eff) / entry_eff * 100)
            mae = max(mae, (entry_eff - lo) / entry_eff * 100)
            if lo <= sl:
                exit_price, exit_reason = sl, "stop"
                break
            if hi >= tp:
                exit_price, exit_reason = tp, "take_profit"
                break
            exit_price = cl
        else:
            mfe = max(mfe, (entry_eff - lo) / entry_eff * 100)
            mae = max(mae, (hi - entry_eff) / entry_eff * 100)
            if hi >= sl:
                exit_price, exit_reason = sl, "stop"
                break
            if lo <= tp:
                exit_price, exit_reason = tp, "take_profit"
                break
            exit_price = cl

    if direction == "BULLISH":
        pnl_u = (exit_price - entry_eff) / entry_eff * 100
    else:
        pnl_u = (entry_eff - exit_price) / entry_eff * 100
    pnl_m = pnl_u * LEVERAGE

    return TradeResult(
        symbol=symbol,
        name=meta["name"],
        group=meta.get("group", ""),
        entry_time=str(df.index[bar_i])[:19],
        direction=direction,
        edge_score=meta["edge_score"],
        edge_combo=meta["edge_combo"],
        signal_name=meta["signal_name"],
        entry_price=round(entry_eff, 4),
        exit_price=round(exit_price, 4),
        exit_reason=exit_reason,
        hold_bars=hold,
        pnl_pct_underlying=round(pnl_u, 4),
        pnl_pct_margin=round(pnl_m, 4),
        mfe_pct=round(mfe, 4),
        mae_pct=round(mae, 4),
    )


def backtest_symbol(inst: dict, df: pd.DataFrame) -> SymbolStats:
    sym = inst["symbol"]
    analyzer = GEMAnalyzer()
    stats = SymbolStats(symbol=sym, name=inst["name"], group=inst.get("group", ""))
    last_signal_bar = -999

    for i in range(MIN_WARMUP, len(df) - 1):
        window = df.iloc[: i + 1]
        analysis = analyzer.analyze(sym, window, "backtest")
        if not analysis:
            continue
        rating = rate_gem_analysis(analysis, TF)
        edge_score = edge_score_from_strength(rating.strength)
        edge = analyze_edge_bar(window)
        combo = edge.edge_combo_score if edge else 0

        if edge_score < MIN_EDGE_SCORE or combo < MIN_EDGE_COMBO:
            continue
        if rating.direction not in ("BULLISH", "BEARISH"):
            continue
        # Debounce: one signal per 8 bars
        if i - last_signal_bar < 8:
            continue
        stats.signals += 1
        last_signal_bar = i

        trade = simulate_trade(
            df,
            i,
            rating.direction,
            sym,
            {
                "name": inst["name"],
                "group": inst.get("group", ""),
                "edge_score": edge_score,
                "edge_combo": combo,
                "signal_name": rating.signal_name,
            },
        )
        if trade:
            stats.trades += 1
            stats.trades_list.append(trade)
            stats.total_margin_pct += trade.pnl_pct_margin
            if trade.pnl_pct_margin > 0:
                stats.wins += 1
            elif trade.pnl_pct_margin < 0:
                stats.losses += 1

    # Max drawdown on cumulative margin PnL (sequential)
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in stats.trades_list:
        equity += t.pnl_pct_margin
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    stats.max_dd_margin_pct = round(max_dd, 4)
    return stats


def aggregate_by_group(all_stats: List[SymbolStats]) -> Dict[str, dict]:
    groups: Dict[str, dict] = {}
    for s in all_stats:
        for g in s.group.split(","):
            g = g.strip()
            if not g:
                continue
            if g not in groups:
                groups[g] = {"signals": 0, "trades": 0, "wins": 0, "pnl_margin": 0.0, "max_dd": 0.0}
            groups[g]["signals"] += s.signals
            groups[g]["trades"] += s.trades
            groups[g]["wins"] += s.wins
            groups[g]["pnl_margin"] += s.total_margin_pct
            groups[g]["max_dd"] = max(groups[g]["max_dd"], s.max_dd_margin_pct)
    for g in groups:
        t = groups[g]["trades"]
        groups[g]["win_rate"] = round(groups[g]["wins"] / t * 100, 1) if t else 0
        groups[g]["pnl_margin"] = round(groups[g]["pnl_margin"], 2)
    return groups


def write_report(conn: List[ConnectivityResult], stats: List[SymbolStats], groups: Dict[str, dict]) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / "index_edge_backtest_2m.md"
    ok_n = sum(1 for c in conn if c.ok)
    total_signals = sum(s.signals for s in stats)
    total_trades = sum(s.trades for s in stats)
    total_wins = sum(s.wins for s in stats)
    total_pnl = sum(s.total_margin_pct for s in stats)
    max_dd_all = max((s.max_dd_margin_pct for s in stats), default=0)

    lines = [
        f"# Index EDGE Backtest — {MONTHS} months H1",
        "",
        f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Parameters",
        f"- Filter: EDGE score ≥ {MIN_EDGE_SCORE}, edge_combo ≥ {MIN_EDGE_COMBO}",
        f"- Spread: {SPREAD_BPS_INDEX} bps indices / {SPREAD_BPS_STOCK} bps stocks",
        f"- Leverage: **1:{LEVERAGE}**",
        f"- TP: **{TP_PCT}%** underlying · SL: **{SL_PCT}%** · max hold {MAX_HOLD_BARS} H1 bars",
        "",
        "## Connectivity (Yahoo Finance + TV probe)",
        "",
        f"**{ok_n}/{len(conn)}** symbols with ≥{MIN_WARMUP} H1 bars",
        "",
        "| Symbol | Name | Bars | Start | End | Source |",
        "|--------|------|------|-------|-----|--------|",
    ]
    for c in conn:
        status = "✅" if c.ok else "❌"
        lines.append(
            f"| {status} `{c.symbol}` | {c.name} | {c.bars} | {c.start} | {c.end} | {c.source} |"
        )

    lines += [
        "",
        "## Summary",
        "",
        f"- **Signals (EDGE≥2, combo≥2):** {total_signals}",
        f"- **Simulated trades:** {total_trades}",
        f"- **Win rate:** {round(total_wins/total_trades*100,1) if total_trades else 0}%",
        f"- **Total PnL (margin %, non-compounded):** {round(total_pnl,2)}%",
        f"- **Worst symbol sequential max DD (margin %):** {max_dd_all}%",
        "",
        "## By instrument group",
        "",
        "| Group | Signals | Trades | Win% | PnL margin% | Max DD% |",
        "|-------|---------|--------|------|-------------|---------|",
    ]
    for g, v in sorted(groups.items()):
        lines.append(
            f"| **{g}** | {v['signals']} | {v['trades']} | {v['win_rate']}% | {v['pnl_margin']} | {v['max_dd']} |"
        )

    lines += [
        "",
        "## Per symbol",
        "",
        "| Symbol | Signals | Trades | Wins | Win% | PnL margin% | Max DD% |",
        "|--------|---------|--------|------|------|-------------|---------|",
    ]
    for s in sorted(stats, key=lambda x: -x.total_margin_pct):
        wr = round(s.wins / s.trades * 100, 1) if s.trades else 0
        lines.append(
            f"| {s.name} (`{s.symbol}`) | {s.signals} | {s.trades} | {s.wins} | {wr}% | {round(s.total_margin_pct,2)} | {s.max_dd_margin_pct} |"
        )

    lines += [
        "",
        "## Exit reasons (all trades)",
        "",
    ]
    reasons: Dict[str, int] = {}
    for s in stats:
        for t in s.trades_list:
            reasons[t.exit_reason] = reasons.get(t.exit_reason, 0) + 1
    for r, n in sorted(reasons.items(), key=lambda x: -x[1]):
        lines.append(f"- **{r}:** {n}")

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def main():
    instruments = load_instruments()
    print("=== Connectivity test ===")
    conn = test_connectivity(instruments)
    for c in conn:
        mark = "OK" if c.ok else "FAIL"
        print(f"  [{mark}] {c.symbol}: {c.bars} bars ({c.start} → {c.end})")

    ok_instruments = [i for i, c in zip(instruments, conn) if c.ok]
    print(f"\n=== Backtest {len(ok_instruments)} symbols, EDGE>={MIN_EDGE_SCORE}, combo>={MIN_EDGE_COMBO} ===")

    all_stats: List[SymbolStats] = []
    for inst in ok_instruments:
        df, _ = fetch_yfinance_h1(inst["symbol"])
        st = backtest_symbol(inst, df)
        all_stats.append(st)
        print(
            f"  {inst['name']}: signals={st.signals} trades={st.trades} "
            f"win={st.wins} pnl_margin={st.total_margin_pct:.2f}% maxDD={st.max_dd_margin_pct:.2f}%"
        )

    groups = aggregate_by_group(all_stats)
    report = write_report(conn, all_stats, groups)
    print(f"\nReport: {report}")


if __name__ == "__main__":
    main()
