"""Volume context for EDGE layer — relative volume, divergence, exhaustion."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class VolumeSignals:
    relative_volume: float  # last bar vs rolling mean
    volume_divergence: bool  # price vs volume disagreement (recent)
    volume_exhaustion: bool  # extended move with fading volume
    summary: str


def analyze_volume(
    df: pd.DataFrame,
    *,
    lookback: int = 20,
    short_lookback: int = 5,
) -> VolumeSignals:
    """
    Volume read at last bar. Expects lowercase OHLCV columns.
    """
    if df is None or len(df) < max(lookback, short_lookback) + 2:
        return VolumeSignals(0.0, False, False, "insufficient data")

    close = df["close"].astype(float)
    volume = df["volume"].astype(float).fillna(0)

    vol_tail = volume.iloc[-lookback:]
    mean_vol = float(vol_tail.mean()) if len(vol_tail) else 0.0
    last_vol = float(volume.iloc[-1])
    rel = last_vol / mean_vol if mean_vol > 0 else 0.0

    vol_div = _price_volume_divergence(close, volume, short_lookback)
    exhaustion = _volume_exhaustion(close, volume, short_lookback)

    parts = []
    if rel >= 1.5:
        parts.append(f"rel vol {rel:.1f}x")
    elif rel > 0 and rel < 0.7:
        parts.append(f"thin vol {rel:.1f}x")
    if vol_div:
        parts.append("vol divergence")
    if exhaustion:
        parts.append("vol exhaustion")

    return VolumeSignals(
        relative_volume=round(rel, 2),
        volume_divergence=vol_div,
        volume_exhaustion=exhaustion,
        summary="; ".join(parts) if parts else "volume neutral",
    )


def _price_volume_divergence(
    close: pd.Series,
    volume: pd.Series,
    lookback: int,
) -> bool:
    try:
        p = close.dropna().tail(lookback)
        v = volume.dropna().tail(lookback)
        if len(p) < lookback or len(v) < lookback:
            return False

        price_change = float(p.iloc[-1]) - float(p.iloc[-2])
        price_pct = abs(price_change / float(p.iloc[-2])) if float(p.iloc[-2]) else 0.0
        vol_change = float(v.iloc[-1]) - float(v.iloc[-2])
        vol_mean = float(v.mean())

        price_strong = price_pct > 0.015
        volume_weak = vol_change < 0 or float(v.iloc[-1]) < vol_mean * 0.9

        price_flat = price_pct < 0.005
        volume_strong = vol_change > 0 and float(v.iloc[-1]) > vol_mean * 1.1

        return (price_strong and volume_weak) or (price_flat and volume_strong)
    except Exception:
        return False


def _volume_exhaustion(close: pd.Series, volume: pd.Series, lookback: int) -> bool:
    """Price trend over lookback but volume declining into the close."""
    try:
        p = close.dropna().tail(lookback + 1)
        v = volume.dropna().tail(lookback + 1)
        if len(p) < lookback + 1 or len(v) < lookback + 1:
            return False

        price_trend = float(p.iloc[-1]) - float(p.iloc[0])
        vol_slope = np.polyfit(range(len(v)), v.values, 1)[0]

        meaningful_move = abs(price_trend / float(p.iloc[0])) > 0.02
        fading_volume = vol_slope < 0 and float(v.iloc[-1]) < float(v.iloc[:3].mean())

        return meaningful_move and fading_volume
    except Exception:
        return False
