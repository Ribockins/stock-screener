"""
EDGE indicator combinations — Phase 1: RSI + MFI.

See docs/edge-indicator-combos.md for full TOP 10 ranking.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class ComboSignal:
    """Dual-indicator read at last bar."""

    rsi: float
    mfi: float
    rsi_bear_div: bool
    rsi_bull_div: bool
    mfi_bear_div: bool
    mfi_bull_div: bool
    dual_bear_div: bool
    dual_bull_div: bool
    money_confirms_weakness: bool  # price up but MFI not supporting
    summary: str


def calculate_mfi(
    df: pd.DataFrame,
    period: int = 14,
) -> pd.Series:
    """
    Money Flow Index from OHLCV.
    Expects columns: high, low, close, volume (lowercase).
    """
    if df is None or len(df) < period + 2:
        return pd.Series(dtype=float)

    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    volume = df["volume"].astype(float).fillna(0)

    tp = (high + low + close) / 3.0
    raw_mf = tp * volume

    direction = tp.diff()
    pos_flow = raw_mf.where(direction > 0, 0.0)
    neg_flow = raw_mf.where(direction < 0, 0.0)

    pos_sum = pos_flow.rolling(period, min_periods=period).sum()
    neg_sum = neg_flow.rolling(period, min_periods=period).sum()

    ratio = pos_sum / neg_sum.replace(0, np.nan)
    mfi = 100 - (100 / (1 + ratio))
    return mfi


def _simple_divergence(
    price: pd.Series,
    indicator: pd.Series,
    lookback: int = 10,
    bearish: bool = True,
) -> bool:
    """One-bar divergence vs prior swing in lookback (lightweight)."""
    if len(price) < lookback + 2:
        return False
    p = price.iloc[-lookback:]
    ind = indicator.iloc[-lookback:]
    if p.isna().all() or ind.isna().all():
        return False

    if bearish:
        i_hi = int(np.nanargmax(p.values))
        if i_hi < len(p) - 2:
            return False
        prev = p.iloc[:-2]
        prev_ind = ind.iloc[:-2]
        if prev.empty:
            return False
        j = int(np.nanargmax(prev.values))
        return (
            float(p.iloc[-1]) >= float(prev.iloc[j])
            and float(ind.iloc[-1]) < float(prev_ind.iloc[j])
        )
    else:
        i_lo = int(np.nanargmin(p.values))
        if i_lo < len(p) - 2:
            return False
        prev = p.iloc[:-2]
        prev_ind = ind.iloc[:-2]
        if prev.empty:
            return False
        j = int(np.nanargmin(prev.values))
        return (
            float(p.iloc[-1]) <= float(prev.iloc[j])
            and float(ind.iloc[-1]) > float(prev_ind.iloc[j])
        )


def analyze_rsi_mfi(
    df: pd.DataFrame,
    rsi: pd.Series,
    mfi_period: int = 14,
    div_lookback: int = 10,
) -> Optional[ComboSignal]:
    """RSI + MFI combo at last bar (EDGE core pair #1)."""
    mfi = calculate_mfi(df, mfi_period)
    if rsi.dropna().empty or mfi.dropna().empty:
        return None

    close = df["close"]
    cur_rsi = float(rsi.iloc[-1])
    cur_mfi = float(mfi.iloc[-1])

    rsi_bear = _simple_divergence(close, rsi, div_lookback, bearish=True)
    rsi_bull = _simple_divergence(close, rsi, div_lookback, bearish=False)
    mfi_bear = _simple_divergence(close, mfi, div_lookback, bearish=True)
    mfi_bull = _simple_divergence(close, mfi, div_lookback, bearish=False)

    dual_bear = rsi_bear and mfi_bear
    dual_bull = rsi_bull and mfi_bull

  # price up last 3 bars but MFI falling
    money_weak = False
    if len(close) >= 4:
        price_up = float(close.iloc[-1]) > float(close.iloc[-4])
        mfi_falling = float(mfi.iloc[-1]) < float(mfi.iloc[-4])
        money_weak = price_up and mfi_falling and cur_rsi > 55

    parts = []
    if dual_bear:
        parts.append("DUAL bear div (RSI+MFI)")
    elif dual_bull:
        parts.append("DUAL bull div (RSI+MFI)")
    else:
        if rsi_bear:
            parts.append("RSI bear div")
        if mfi_bear:
            parts.append("MFI bear div")
        if rsi_bull:
            parts.append("RSI bull div")
        if mfi_bull:
            parts.append("MFI bull div")
    if money_weak:
        parts.append("price↑ MFI↓")

    return ComboSignal(
        rsi=round(cur_rsi, 2),
        mfi=round(cur_mfi, 2),
        rsi_bear_div=rsi_bear,
        rsi_bull_div=rsi_bull,
        mfi_bear_div=mfi_bear,
        mfi_bull_div=mfi_bull,
        dual_bear_div=dual_bear,
        dual_bull_div=dual_bull,
        money_confirms_weakness=money_weak,
        summary="; ".join(parts) if parts else "no combo edge",
    )
