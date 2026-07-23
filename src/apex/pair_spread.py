"""Spread math for cointegrated pairs."""

from __future__ import annotations

import math
from typing import Tuple

import numpy as np
import pandas as pd


def hedge_ratio(y: np.ndarray, x: np.ndarray) -> float:
    """OLS slope: log(y) ~ alpha + beta * log(x)."""
    lx = np.log(x.astype(float))
    ly = np.log(y.astype(float))
    x_m = lx - lx.mean()
    y_m = ly - ly.mean()
    denom = float(np.dot(x_m, x_m))
    if denom <= 0:
        return float("nan")
    return float(np.dot(x_m, y_m) / denom)


def spread_series(
    y: pd.Series,
    x: pd.Series,
    beta: float,
) -> pd.Series:
    aligned = pd.concat([y, x], axis=1, join="inner").dropna()
    if aligned.empty:
        return pd.Series(dtype=float)
    ly = np.log(aligned.iloc[:, 0].astype(float))
    lx = np.log(aligned.iloc[:, 1].astype(float))
    return pd.Series(ly - beta * lx, index=aligned.index, name="spread")


def zscore(spread: pd.Series, mean: float | None = None, std: float | None = None) -> pd.Series:
    if mean is None:
        mean = float(spread.mean())
    if std is None:
        std = float(spread.std())
    if std <= 0:
        return spread * 0.0
    return (spread - mean) / std


def calibrate_from_daily(
    y_daily: pd.Series,
    x_daily: pd.Series,
    lookback_days: int = 120,
) -> Tuple[float, float, float]:
    """Return beta, spread_mean, spread_std from trailing daily window."""
    frame = pd.concat([y_daily, x_daily], axis=1, join="inner").dropna().tail(lookback_days)
    if len(frame) < 30:
        raise ValueError("Not enough daily bars to calibrate pair")
    beta = hedge_ratio(frame.iloc[:, 0].values, frame.iloc[:, 1].values)
    sp = spread_series(frame.iloc[:, 0], frame.iloc[:, 1], beta)
    return beta, float(sp.mean()), float(sp.std())


def simulate_spread_trades(
    z: pd.Series,
    entry_z: float = 2.0,
    exit_z: float = 0.5,
) -> pd.DataFrame:
    """
    Mean-reversion on spread z-score.
    Long spread when z < -entry_z; short spread when z > entry_z.
    Flat when |z| < exit_z.
    """
    rows: list[dict] = []
    pos = 0  # 1 long spread, -1 short spread
    entry_i = None
    entry_z_val = None

    for ts, zval in z.items():
        if not math.isfinite(float(zval)):
            continue
        zf = float(zval)
        if pos == 0:
            if zf <= -entry_z:
                pos = 1
                entry_i = ts
                entry_z_val = zf
            elif zf >= entry_z:
                pos = -1
                entry_i = ts
                entry_z_val = zf
        elif pos == 1:
            if zf >= -exit_z:
                rows.append(
                    {
                        "entry_time": entry_i,
                        "exit_time": ts,
                        "side": "LONG_SPREAD",
                        "entry_z": entry_z_val,
                        "exit_z": zf,
                    }
                )
                pos = 0
                entry_i = None
        elif pos == -1:
            if zf <= exit_z:
                rows.append(
                    {
                        "entry_time": entry_i,
                        "exit_time": ts,
                        "side": "SHORT_SPREAD",
                        "entry_z": entry_z_val,
                        "exit_z": zf,
                    }
                )
                pos = 0
                entry_i = None

    if pos != 0 and entry_i is not None:
        last_ts = z.index[-1]
        if last_ts != entry_i:
            rows.append(
            {
                "entry_time": entry_i,
                "exit_time": last_ts,
                "side": "LONG_SPREAD" if pos == 1 else "SHORT_SPREAD",
                "entry_z": entry_z_val,
                "exit_z": float(z.iloc[-1]),
                "forced_exit": True,
            }
        )

    return pd.DataFrame(rows)


def spread_pnl_pct(trades: pd.DataFrame, spread: pd.Series) -> pd.DataFrame:
    """Approximate PnL as change in spread (log space) over each trade."""
    if trades.empty:
        return trades
    out = trades.copy()
    pnls: list[float] = []
    for _, row in out.iterrows():
        s0 = spread.get(row["entry_time"], np.nan)
        s1 = spread.get(row["exit_time"], np.nan)
        if not (math.isfinite(s0) and math.isfinite(s1)):
            pnls.append(float("nan"))
            continue
        delta = float(s1 - s0)
        if row["side"] == "SHORT_SPREAD":
            delta = -delta
        pnls.append(delta * 100.0)  # as % in log-return approx
    out["pnl_pct_log"] = pnls
    return out
