#!/usr/bin/env python3
"""
Gala002 / Gala_010-style backtest on Sierra Chart M1 SCID bars.

Uses M1 OHLC for intrabar BE/SL/TP path; H1 bars for signal (UseNewBarOnly).
Modelling quality equivalent: 100% on M1 path within each minute (OHLC ordering).
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

ET = __import__("zoneinfo").ZoneInfo("America/New_York")

# Gala_010_LockedBar (from MT4 report) — TP/SL pips inferred from $ P/L @ 0.02 lot
GALA_010 = dict(
    lot=0.02,
    tp_pips=98.0,
    sl_pips=309.0,
    negative_close_minutes=180,
    min_negative_pips=50.0,
    be_trigger_pips=41.0,
    be_sl_buffer_pips=36.0,
    be_close_pips=3.0,
    be_max_loss_pips=10.0,
    basket_profit_money=35.0,
    daily_loss_limit=35.0,
    daily_profit_target=99999.0,
    use_be_market_close=False,
    min_score=5.0,
    max_trades_per_day=7,
    max_open=7,
    max_same_dir=2,
    min_minutes_between=25,
    session_start=(8, 30),
    session_end=(17, 30),
    spread_points=30,  # ~0.30 on gold 2-digit
)

GALA_002_DEFAULT = dict(
    lot=0.01,
    tp_pips=50.0,
    sl_pips=500.0,
    negative_close_minutes=35,
    min_negative_pips=80.0,
    be_trigger_pips=25.0,
    be_sl_buffer_pips=2.0,
    be_close_pips=3.0,
    be_max_loss_pips=10.0,
    basket_profit_money=25.0,
    daily_loss_limit=25.0,
    daily_profit_target=40.0,
    use_be_market_close=False,
    min_score=5.0,
    max_trades_per_day=7,
    max_open=7,
    max_same_dir=2,
    min_minutes_between=25,
    session_start=(8, 30),
    session_end=(17, 30),
    spread_points=30,
)

PIP = 0.1  # XAUUSD broker pip (10 points @ 2 decimals)
PIP_VALUE = 0.20  # $ per pip @ 0.02 lot (100 oz contract)


def load_scid(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path)
    raw.columns = [c.strip() for c in raw.columns]
    raw["dt"] = pd.to_datetime(
        raw["Date"].astype(str).str.strip() + " " + raw["Time"].astype(str).str.strip()
    ).dt.tz_localize(ET)
    raw = raw.sort_values("dt").reset_index(drop=True)
    for c in ["Open", "High", "Low", "Last"]:
        raw[c.lower()] = raw[c].astype(float)
    raw.rename(columns={"last": "close"}, inplace=True)
    return raw[["dt", "open", "high", "low", "close"]]


def to_h1(m1: pd.DataFrame) -> pd.DataFrame:
    g = m1.set_index("dt")
    h1 = g.resample("1h", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    ).dropna()
    return h1.reset_index()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def momentum(series: pd.Series, period: int = 14) -> pd.Series:
    return 100.0 * series / series.shift(period)


def gala_signal_row(h1: pd.DataFrame, i: int, d1: pd.DataFrame) -> int:
    """Return 1 buy, -1 sell, 0 none. Mirrors Gala_Signal.mqh on bar i (signal uses bar i-1)."""
    if i < 220:
        return 0
    sub = h1.iloc[: i + 1]
    close = sub["close"]
    high = sub["high"]
    low = sub["low"]
    open_ = sub["open"]

    rsi1 = rsi(close).iloc[-2]
    mom1 = momentum(close).iloc[-2]
    mom2 = momentum(close).iloc[-3]
    atr1 = atr(sub).iloc[-2]
    ema = close.ewm(span=20, adjust=False).mean().iloc[-2]
    close1 = close.iloc[-2]

    impulse_move = close1 - close.iloc[-2 - 3]
    impulse_abs = abs(impulse_move)
    upward = impulse_move > 0 and atr1 > 0 and impulse_abs >= atr1 * 0.9
    downward = impulse_move < 0 and atr1 > 0 and impulse_abs >= atr1 * 0.9

    pip = PIP
    dist_mean = abs(close1 - ema) / pip
    above_far = close1 > ema and dist_mean >= 80
    below_far = close1 < ema and dist_mean >= 80

    r1 = high.iloc[-2] - low.iloc[-2]
    r2 = high.iloc[-3] - low.iloc[-3]
    slowdown = r1 > 0 and r2 > 0 and r1 <= r2 * 0.8

    o1, c1, h1_, l1 = open_.iloc[-2], close.iloc[-2], high.iloc[-2], low.iloc[-2]
    body = abs(c1 - o1) or (h1_ - l1) * 0.1
    bear_rej = (h1_ - max(o1, c1)) >= body * 1.2
    bull_rej = (min(o1, c1) - l1) >= body * 1.2

    sell_score = buy_score = 0.0
    if rsi1 >= 68:
        sell_score += 1.0
    if rsi1 <= 32:
        buy_score += 1.0
    if mom1 >= 100.5:
        sell_score += 1.0
    if mom1 <= 99.5:
        buy_score += 1.0
    if mom1 < mom2:
        sell_score += 0.5
    if mom1 > mom2:
        buy_score += 0.5
    if upward:
        sell_score += 1.5
    if downward:
        buy_score += 1.5
    if above_far:
        sell_score += 1.5
    if below_far:
        buy_score += 1.5
    if slowdown and upward:
        sell_score += 1.0
    if slowdown and downward:
        buy_score += 1.0
    if bear_rej:
        sell_score += 1.2
    if bull_rej:
        buy_score += 1.2

    # daily high/low levels (approx from H1)
    day = sub.iloc[-2]["dt"].date()
    dsub = sub[sub["dt"].dt.date == day]
    if len(dsub):
        tdh, tdl = dsub["high"].max(), dsub["low"].min()
        if abs(close1 - tdh) / pip <= 80:
            sell_score += 0.8
        if abs(close1 - tdl) / pip <= 80:
            buy_score += 0.8

    min_score = 5.0
    if sell_score >= min_score and sell_score > buy_score:
        return -1
    if buy_score >= min_score and buy_score > sell_score:
        return 1
    return 0


@dataclass
class Position:
    direction: int  # 1 long -1 short
    entry_time: pd.Timestamp
    entry_price: float
    sl: float
    tp: float
    best_pips: float = 0.0
    be_armed: bool = False
    be_sl_moved: bool = False


@dataclass
class Trade:
    entry_time: str
    exit_time: str
    direction: str
    entry: float
    exit: float
    pips: float
    profit: float
    reason: str


@dataclass
class BacktestResult:
    trades: List[Trade] = field(default_factory=list)
    net_profit: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    max_dd_pct: float = 0.0
    exit_mix: Dict[str, int] = field(default_factory=dict)


def pips_long(price: float, entry: float) -> float:
    return (price - entry) / PIP


def pips_short(price: float, entry: float) -> float:
    return (entry - price) / PIP


def profit_from_pips(pips: float, lot: float) -> float:
    return pips * (lot / 0.02) * PIP_VALUE


def in_session(ts: pd.Timestamp, start: Tuple[int, int], end: Tuple[int, int]) -> bool:
    t = ts.timetz()
    mins = t.hour * 60 + t.minute
    s = start[0] * 60 + start[1]
    e = end[0] * 60 + end[1]
    return s <= mins <= e


def bar_path_prices(o: float, h: float, l: float, c: float) -> List[float]:
    """OHLC path for intrabar stop checks."""
    if c >= o:
        return [o, l, h, c]
    return [o, h, l, c]


def run_backtest(
    m1: pd.DataFrame,
    cfg: dict,
    start: Optional[pd.Timestamp] = None,
    end: Optional[pd.Timestamp] = None,
    deposit: float = 1000.0,
) -> BacktestResult:
    if start is not None:
        m1 = m1[m1["dt"] >= start].reset_index(drop=True)
    if end is not None:
        m1 = m1[m1["dt"] <= end].reset_index(drop=True)

    h1 = to_h1(m1)
    h1_idx = {t: i for i, t in enumerate(h1["dt"])}

    spread = cfg["spread_points"] * 0.01  # points to price
    lot = cfg["lot"]
    positions: List[Position] = []
    closed: List[Trade] = []
    equity = deposit
    peak = deposit
    max_dd = 0.0

    day_key = None
    today_trades = 0
    today_profit = 0.0
    last_open_time: Optional[pd.Timestamp] = None
    exit_mix: Dict[str, int] = {}

    def close_pos(pos: Position, exit_price: float, ts: pd.Timestamp, reason: str):
        nonlocal equity, peak, max_dd, today_profit
        if pos.direction == 1:
            pips = pips_long(exit_price, pos.entry_price)
        else:
            pips = pips_short(exit_price, pos.entry_price)
        pl = profit_from_pips(pips, lot)
        equity += pl
        today_profit += pl
        peak = max(peak, equity)
        dd = (peak - equity) / peak * 100 if peak > 0 else 0
        max_dd = max(max_dd, dd)
        closed.append(
            Trade(
                str(pos.entry_time),
                str(ts),
                "BUY" if pos.direction == 1 else "SELL",
                pos.entry_price,
                exit_price,
                pips,
                pl,
                reason,
            )
        )
        exit_mix[reason] = exit_mix.get(reason, 0) + 1

    last_h1: Optional[pd.Timestamp] = None

    for _, row in m1.iterrows():
        ts = row["dt"]
        dk = ts.year * 1000 + int(ts.dayofyear)
        if day_key != dk:
            day_key = dk
            today_trades = 0
            today_profit = 0.0

        bid = row["close"]
        ask = bid + spread
        o, h, l, c = row["open"], row["high"], row["low"], row["close"]

        # --- protection on M1 ---
        basket_pl = 0.0
        for pos in positions:
            mid = bid if pos.direction == 1 else ask
            cur_pips = pips_long(mid, pos.entry_price) if pos.direction == 1 else pips_short(mid, pos.entry_price)
            pos.best_pips = max(pos.best_pips, cur_pips)
            basket_pl += profit_from_pips(cur_pips, lot)

        if basket_pl >= cfg["basket_profit_money"] and positions:
            for pos in list(positions):
                px = bid if pos.direction == 1 else ask
                close_pos(pos, px, ts, "BASKET_PROFIT")
            positions.clear()
            continue

        to_remove = []
        for pos in positions:
            elapsed_min = (ts - pos.entry_time).total_seconds() / 60.0
            mid = bid if pos.direction == 1 else ask
            cur_pips = pips_long(mid, pos.entry_price) if pos.direction == 1 else pips_short(mid, pos.entry_price)

            if elapsed_min >= cfg["negative_close_minutes"] and cur_pips <= -cfg["min_negative_pips"]:
                px = bid if pos.direction == 1 else ask
                close_pos(pos, px, ts, "NEGATIVE_TIME_CLOSE")
                to_remove.append(pos)
                continue

            if pos.best_pips >= cfg["be_trigger_pips"]:
                pos.be_armed = True
                if not pos.be_sl_moved:
                    buf = cfg["be_sl_buffer_pips"] * PIP
                    if pos.direction == 1:
                        pos.sl = pos.entry_price + buf
                    else:
                        pos.sl = pos.entry_price - buf
                    pos.be_sl_moved = True

                if cfg["use_be_market_close"]:
                    if -cfg["be_max_loss_pips"] <= cur_pips <= cfg["be_close_pips"]:
                        px = bid if pos.direction == 1 else ask
                        close_pos(pos, px, ts, "BREAK_EVEN_PROTECTION")
                        to_remove.append(pos)
                        continue

            # intrabar SL/TP
            hit_reason = None
            hit_price = None
            for px in bar_path_prices(o, h, l, c):
                if pos.direction == 1:
                    if px <= pos.sl:
                        hit_reason = "SL" if not pos.be_sl_moved else "BE_SL"
                        hit_price = pos.sl
                        break
                    if px >= pos.tp:
                        hit_reason = "TP"
                        hit_price = pos.tp
                        break
                else:
                    if px >= pos.sl:
                        hit_reason = "SL" if not pos.be_sl_moved else "BE_SL"
                        hit_price = pos.sl
                        break
                    if px <= pos.tp:
                        hit_reason = "TP"
                        hit_price = pos.tp
                        break

            if hit_reason:
                close_pos(pos, hit_price, ts, hit_reason)
                to_remove.append(pos)

        for pos in to_remove:
            if pos in positions:
                positions.remove(pos)

        if today_profit <= -cfg["daily_loss_limit"]:
            continue
        if today_profit >= cfg["daily_profit_target"]:
            continue

        # new H1 bar entries
        h1_open = ts.floor("h")
        if last_h1 is not None and h1_open == last_h1:
            continue
        last_h1 = h1_open

        if h1_open not in h1_idx:
            continue
        hi = h1_idx[h1_open]
        if hi < 2:
            continue

        if not in_session(ts, cfg["session_start"], cfg["session_end"]):
            continue
        if today_trades >= cfg["max_trades_per_day"]:
            continue
        if len(positions) >= cfg["max_open"]:
            continue
        if last_open_time is not None:
            gap = (ts - last_open_time).total_seconds() / 60.0
            if gap < cfg["min_minutes_between"]:
                continue

        sig = gala_signal_row(h1, hi, m1)
        if sig == 0:
            continue

        buys = sum(1 for p in positions if p.direction == 1)
        sells = sum(1 for p in positions if p.direction == -1)
        if sig == 1 and buys >= cfg["max_same_dir"]:
            continue
        if sig == -1 and sells >= cfg["max_same_dir"]:
            continue

        if sig == 1:
            entry = ask
            sl = entry - cfg["sl_pips"] * PIP
            tp = entry + cfg["tp_pips"] * PIP
            direction = 1
        else:
            entry = bid
            sl = entry + cfg["sl_pips"] * PIP
            tp = entry - cfg["tp_pips"] * PIP
            direction = -1

        positions.append(
            Position(direction=direction, entry_time=ts, entry_price=entry, sl=sl, tp=tp)
        )
        today_trades += 1
        last_open_time = ts

    wins = sum(1 for t in closed if t.profit > 0)
    gross_win = sum(t.profit for t in closed if t.profit > 0)
    gross_loss = abs(sum(t.profit for t in closed if t.profit < 0))
    pf = gross_win / gross_loss if gross_loss > 0 else float("inf")

    return BacktestResult(
        trades=closed,
        net_profit=equity - deposit,
        win_rate=100.0 * wins / len(closed) if closed else 0.0,
        profit_factor=pf,
        max_dd_pct=max_dd,
        exit_mix=exit_mix,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scid", type=Path, required=True)
    ap.add_argument("--preset", choices=["gala_010", "gala_002"], default="gala_010")
    ap.add_argument("--start", default=None)
    ap.add_argument("--end", default=None)
    ap.add_argument("--out", type=Path, default=Path("/workspace/reports/gala_scid_backtest.json"))
    args = ap.parse_args()

    cfg = GALA_010 if args.preset == "gala_010" else GALA_002_DEFAULT
    m1 = load_scid(args.scid)
    start = pd.Timestamp(args.start, tz=ET) if args.start else None
    end = pd.Timestamp(args.end, tz=ET) if args.end else None

    res = run_backtest(m1, cfg, start=start, end=end)

    summary = {
        "file": str(args.scid),
        "preset": args.preset,
        "data_from": str(m1["dt"].iloc[0]),
        "data_to": str(m1["dt"].iloc[-1]),
        "test_start": args.start,
        "test_end": args.end,
        "trades": len(res.trades),
        "net_profit": round(res.net_profit, 2),
        "win_rate_pct": round(res.win_rate, 2),
        "profit_factor": round(res.profit_factor, 2),
        "max_drawdown_pct": round(res.max_dd_pct, 2),
        "exit_mix": res.exit_mix,
        "sample_trades": [
            {"dir": t.direction, "profit": round(t.profit, 2), "reason": t.reason}
            for t in res.trades[:5]
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
