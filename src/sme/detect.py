"""Detect historical GEM signal events on OHLCV for SME."""

from __future__ import annotations

from typing import List, Optional

import pandas as pd

from src.gem.analyzer import GEMAnalyzer
from src.gem.config import GEMConfig
from src.gem.models import GEMAnalysis
from src.sme.models import SignalEvent


def _direction_from_analysis(a: GEMAnalysis) -> Optional[str]:
    if a.sell_gem or a.sell_setup or a.raw_sell_div:
        return "BEARISH"
    if a.buy_gem or a.buy_setup or a.raw_buy_div:
        return "BULLISH"
    return None


def _signal_type(a: GEMAnalysis) -> str:
    if a.sell_gem or a.buy_gem:
        return "GEM"
    if a.sell_setup or a.buy_setup:
        return "SETUP"
    return "DIV"


def detect_signal_events(
    df: pd.DataFrame,
    *,
    lookback: int = 40,
    analyzer: Optional[GEMAnalyzer] = None,
    zone_atr_mult: float = 0.8,
) -> List[SignalEvent]:
    """Walk recent bars; record each bar where GEM fires a trackable signal."""
    if df is None or len(df) < 30:
        return []

    out = df.copy()
    out.columns = [str(c).lower() for c in out.columns]
    n = len(out)
    start = max(30, n - lookback)
    gem = analyzer or GEMAnalyzer(GEMConfig())

    atr = _atr(out, 14)
    events: List[SignalEvent] = []

    for i in range(start, n):
        slice_df = out.iloc[: i + 1].copy()
        a = gem.analyze(out.index[i] if hasattr(out.index[i], "year") else "X", slice_df)
        if not a:
            continue
        direction = _direction_from_analysis(a)
        if not direction:
            continue
        price = float(out["close"].iloc[i])
        atr_i = float(atr.iloc[i]) if not pd.isna(atr.iloc[i]) and atr.iloc[i] > 0 else price * 0.01
        zone_key = round(price / (atr_i * zone_atr_mult), 0)
        events.append(
            SignalEvent(
                bar_index=i,
                direction=direction,
                signal_type=_signal_type(a),
                price=price,
                rsi=float(a.rsi),
                zone_key=zone_key,
            )
        )
    return events


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"].astype(float)
    low = df["low"].astype(float)
    close = df["close"].astype(float)
    tr = pd.concat(
        [
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period, min_periods=1).mean()
