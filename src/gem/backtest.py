"""
GEM Logic 1.5 backtest — point-in-time replay on closed bars.

Rules (Technical Brief Task 2B):
- Entry: GEM edge fires AND score >= entry_score_threshold (default 7)
- Exit: GEM confluence disappears OR score < threshold - exit_score_drop (default 2)
- Stop: recent swing low (long) / swing high (short)
- Target: 2R from entry (configurable)
- No lookahead — signals evaluated on bar close; stops/targets use same-bar high/low after entry
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.gem.config import GEMConfig
from src.gem.dashboard import compute_dashboard_series
from src.gem.timeframes import TF_INTERVAL_SECONDS, TF_SHORT
from src.market_data import MarketDataService


@dataclass
class BacktestConfig:
    entry_score_threshold: int = 7
    exit_score_drop: int = 2
    target_rr: float = 2.0
    swing_lookback: int = 10
    stop_buffer_pct: float = 0.15
    backtest_timeframes: Tuple[str, ...] = ("60", "240")


@dataclass
class TradeRecord:
    direction: str  # "long" | "short"
    entry_idx: int
    exit_idx: int
    entry_price: float
    exit_price: float
    stop_price: float
    target_price: float
    r_multiple: float
    exit_reason: str


@dataclass
class BacktestResult:
    symbol: str
    display_name: str
    timeframe: str
    total_trades: int = 0
    wins: int = 0
    win_pct: float = 0.0
    avg_rr: float = 0.0
    best_trade_r: float = 0.0
    worst_trade_r: float = 0.0
    max_drawdown_pct: float = 0.0
    trades: List[TradeRecord] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def tf_label(self) -> str:
        return TF_SHORT.get(self.timeframe, self.timeframe)


def _swing_stop(
    direction: str,
    i: int,
    low: np.ndarray,
    high: np.ndarray,
    lookback: int,
    buffer_pct: float,
) -> float:
    start = max(0, i - lookback)
    if direction == "long":
        swing = float(np.min(low[start:i])) if i > start else float(low[i])
        return swing * (1.0 - buffer_pct / 100.0)
    swing = float(np.max(high[start:i])) if i > start else float(high[i])
    return swing * (1.0 + buffer_pct / 100.0)


def run_gem_backtest(
    df: pd.DataFrame,
    *,
    symbol: str = "",
    display_name: str = "",
    timeframe: str = "60",
    gem_config: Optional[GEMConfig] = None,
    bt_config: Optional[BacktestConfig] = None,
    interval_seconds: Optional[int] = None,
) -> BacktestResult:
    """Replay GEM entries/exits on historical OHLCV (closed bars only)."""
    cfg = gem_config or GEMConfig()
    btc = bt_config or BacktestConfig()
    name = display_name or symbol or "unknown"
    result = BacktestResult(symbol=symbol, display_name=name, timeframe=timeframe)

    sec = interval_seconds if interval_seconds is not None else TF_INTERVAL_SECONDS.get(timeframe)
    series = compute_dashboard_series(df, config=cfg, interval_seconds=sec)
    if series is None or series.empty:
        result.error = "insufficient data"
        return result

    valid = series["score"].notna()
    if valid.sum() < 30:
        result.error = "insufficient valid bars"
        return result

    s = series.loc[valid].copy()

    high = s["high"].astype(float).values
    low = s["low"].astype(float).values
    close = s["close"].astype(float).values
    score = s["score"].astype(int).values
    buy_gem = s["buy_gem"].astype(bool).values
    sell_gem = s["sell_gem"].astype(bool).values
    buy_raw = s["buy_gem_raw"].astype(bool).values
    sell_raw = s["sell_gem_raw"].astype(bool).values

    exit_floor = btc.entry_score_threshold - btc.exit_score_drop
    n = len(s)
    trades: List[TradeRecord] = []
    i = 1
    equity = 1.0
    peak = 1.0
    max_dd = 0.0

    while i < n:
        direction: Optional[str] = None
        if buy_gem[i] and score[i] >= btc.entry_score_threshold:
            direction = "long"
        elif sell_gem[i] and score[i] >= btc.entry_score_threshold:
            direction = "short"

        if direction is None:
            i += 1
            continue

        entry_price = float(close[i])
        entry_idx = i
        stop = _swing_stop(direction, i, low, high, btc.swing_lookback, btc.stop_buffer_pct)
        risk = abs(entry_price - stop)
        if risk <= 0:
            i += 1
            continue

        if direction == "long":
            target = entry_price + risk * btc.target_rr
        else:
            target = entry_price - risk * btc.target_rr

        exit_idx = entry_idx
        exit_price = entry_price
        exit_reason = "signal_end"
        j = i + 1

        while j < n:
            if direction == "long":
                if low[j] <= stop:
                    exit_price = stop
                    exit_reason = "stop"
                    exit_idx = j
                    break
                if high[j] >= target:
                    exit_price = target
                    exit_reason = "target"
                    exit_idx = j
                    break
                if not buy_raw[j] or score[j] < exit_floor:
                    exit_price = float(close[j])
                    exit_reason = "signal_end"
                    exit_idx = j
                    break
            else:
                if high[j] >= stop:
                    exit_price = stop
                    exit_reason = "stop"
                    exit_idx = j
                    break
                if low[j] <= target:
                    exit_price = target
                    exit_reason = "target"
                    exit_idx = j
                    break
                if not sell_raw[j] or score[j] < exit_floor:
                    exit_price = float(close[j])
                    exit_reason = "signal_end"
                    exit_idx = j
                    break
            j += 1
        else:
            exit_price = float(close[-1])
            exit_idx = n - 1
            exit_reason = "end_of_data"

        if direction == "long":
            r_mult = (exit_price - entry_price) / risk
        else:
            r_mult = (entry_price - exit_price) / risk

        trades.append(
            TradeRecord(
                direction=direction,
                entry_idx=entry_idx,
                exit_idx=exit_idx,
                entry_price=entry_price,
                exit_price=exit_price,
                stop_price=stop,
                target_price=target,
                r_multiple=round(r_mult, 3),
                exit_reason=exit_reason,
            )
        )

        equity *= 1.0 + r_mult * 0.01
        peak = max(peak, equity)
        dd = (peak - equity) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, dd)

        i = exit_idx + 1

    result.trades = trades
    result.total_trades = len(trades)
    if trades:
        wins = sum(1 for t in trades if t.r_multiple > 0)
        result.wins = wins
        result.win_pct = round(100.0 * wins / len(trades), 1)
        r_vals = [t.r_multiple for t in trades]
        result.avg_rr = round(float(np.mean(r_vals)), 2)
        result.best_trade_r = round(max(r_vals), 2)
        result.worst_trade_r = round(min(r_vals), 2)
    result.max_drawdown_pct = round(max_dd * 100.0, 2)
    return result


def run_backtest_batch(
    instruments: List[dict],
    *,
    bars: int = 500,
    gem_config: Optional[GEMConfig] = None,
    bt_config: Optional[BacktestConfig] = None,
    market: Optional[MarketDataService] = None,
) -> List[BacktestResult]:
    """Run backtest for each instrument on H1 and H4 (configurable)."""
    svc = market or MarketDataService()
    btc = bt_config or BacktestConfig()
    results: List[BacktestResult] = []

    for tf in btc.backtest_timeframes:
        fetched = svc.fetch_many(instruments, bars=bars, interval_key=tf)
        for inst in instruments:
            sym = inst.get("symbol")
            if not sym or sym not in fetched:
                results.append(
                    BacktestResult(
                        symbol=sym or "",
                        display_name=inst.get("display_name", sym or ""),
                        timeframe=tf,
                        error="no data",
                    )
                )
                continue
            df, _ = fetched[sym]
            results.append(
                run_gem_backtest(
                    df,
                    symbol=sym,
                    display_name=inst.get("display_name", sym),
                    timeframe=tf,
                    gem_config=gem_config,
                    bt_config=btc,
                )
            )
    return results


def backtest_rows(results: List[BacktestResult]) -> List[Tuple]:
    """Tabular rows: instrument, TF, trades, win%, avg R, best, worst, max DD."""
    rows = []
    for r in results:
        if r.error:
            rows.append(
                (
                    r.display_name,
                    r.tf_label,
                    0,
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    r.error,
                )
            )
            continue
        rows.append(
            (
                r.display_name,
                r.tf_label,
                r.total_trades,
                f"{r.win_pct:.1f}%",
                f"{r.avg_rr:.2f}R",
                f"{r.best_trade_r:.2f}R",
                f"{r.worst_trade_r:.2f}R",
                f"{r.max_drawdown_pct:.1f}%",
                "",
            )
        )
    return rows
