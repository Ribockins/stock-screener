"""Candlestick pattern detection (GEM Logic 1.5 rules)."""

import numpy as np
import pandas as pd


def _body_ohlc(df: pd.DataFrame) -> pd.Series:
    return (df["close"] - df["open"]).abs()


def detect_candle_signals(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """
    Return (bull_candle_signal, bear_candle_signal) boolean series per bar.
    """
    o = df["open"].astype(float)
    h = df["high"].astype(float)
    l = df["low"].astype(float)
    c = df["close"].astype(float)

    body = (c - o).abs()
    body_prev = body.shift(1)
    rng = (h - l).clip(lower=1e-8)
    upper = h - np.maximum(o, c)
    lower = np.minimum(o, c) - l
    avg_body = body.rolling(20, min_periods=1).mean()

    bull = c > o
    bear = c < o
    prior_down = c.shift(1) < c.shift(5)
    prior_up = c.shift(1) > c.shift(5)

    raw_bull_engulf = bull & (c.shift(1) < o.shift(1)) & (c > o.shift(1)) & (o < c.shift(1)) & (body > body_prev)
    raw_bear_engulf = bear & (c.shift(1) > o.shift(1)) & (c < o.shift(1)) & (o > c.shift(1)) & (body > body_prev)

    raw_bull_pin = (lower >= body * 2.0) & (upper <= body * 1.2) & (c > l + rng * 0.60)
    raw_bear_pin = (upper >= body * 2.0) & (lower <= body * 1.2) & (c < h - rng * 0.60)

    raw_hammer = prior_down & (lower >= body * 2.0) & (upper <= body * 0.8) & (c > l + rng * 0.60)
    raw_shooting = prior_up & (upper >= body * 2.0) & (lower <= body * 0.8) & (c < h - rng * 0.60)

    raw_morning = (
        (c.shift(2) < o.shift(2))
        & (body.shift(2) > avg_body.shift(2) * 0.8)
        & (body.shift(1) < body.shift(2) * 0.55)
        & bull
        & (c > (o.shift(2) + c.shift(2)) / 2)
    )
    raw_evening = (
        (c.shift(2) > o.shift(2))
        & (body.shift(2) > avg_body.shift(2) * 0.8)
        & (body.shift(1) < body.shift(2) * 0.55)
        & bear
        & (c < (o.shift(2) + c.shift(2)) / 2)
    )

    inside_prev = (h.shift(1) < h.shift(2)) & (l.shift(1) > l.shift(2))
    raw_inside_bull = inside_prev & (c > h.shift(1))
    raw_inside_bear = inside_prev & (c < l.shift(1))

    raw_outside = (h > h.shift(1)) & (l < l.shift(1)) & (body > body_prev)
    raw_outside_bull = raw_outside & bull
    raw_outside_bear = raw_outside & bear

    raw_marubozu = (body / rng >= 0.75) & (upper <= rng * 0.12) & (lower <= rng * 0.12)
    raw_bull_maru = raw_marubozu & bull
    raw_bear_maru = raw_marubozu & bear

    bull_signal = (
        raw_bull_engulf
        | raw_bull_pin
        | raw_hammer
        | raw_morning
        | raw_inside_bull
        | raw_outside_bull
        | raw_bull_maru
    ).fillna(False)

    bear_signal = (
        raw_bear_engulf
        | raw_bear_pin
        | raw_shooting
        | raw_evening
        | raw_inside_bear
        | raw_outside_bear
        | raw_bear_maru
    ).fillna(False)

    return bull_signal, bear_signal
