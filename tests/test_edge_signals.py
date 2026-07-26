"""Tests for MFI, RSI/MFI divergence, and volume EDGE signals."""

import numpy as np
import pandas as pd

from src.edge_combos import ComboSignal, analyze_rsi_mfi, calculate_mfi
from src.edge_engine import analyze_edge_bar, edge_combo_score
from src.gem.rsi import calculate_rsi
from src.volume_signals import VolumeSignals, analyze_volume


def _ohlcv_from_close(close: list, volume: list | None = None) -> pd.DataFrame:
    c = np.array(close, dtype=float)
    n = len(c)
    vol = np.array(volume if volume is not None else [1000.0] * n, dtype=float)
    spread = c * 0.002
    return pd.DataFrame(
        {
            "open": c - spread * 0.3,
            "high": c + spread,
            "low": c - spread,
            "close": c,
            "volume": vol,
        }
    )


def test_calculate_mfi_bounds():
    close = list(100 + np.sin(np.linspace(0, 4, 40)) * 5)
    df = _ohlcv_from_close(close)
    mfi = calculate_mfi(df, period=14)
    valid = mfi.dropna()
    assert len(valid) > 0
    assert valid.min() >= 0
    assert valid.max() <= 100


def test_mfi_flat_price_may_be_nan():
    df = _ohlcv_from_close([100.0] * 30, volume=[500.0] * 30)
    mfi = calculate_mfi(df, period=14)
    assert len(mfi) == 30


def test_analyze_rsi_mfi_on_trending_data():
    n = 40
    close = list(100 + np.sin(np.linspace(0, 5, n)) * 8)
    df = _ohlcv_from_close(close)
    rsi = calculate_rsi(df["close"], 14)
    combo = analyze_rsi_mfi(df, rsi, div_lookback=10)
    assert combo is not None
    assert isinstance(combo.mfi, float)


def test_edge_combo_score_dual_and_volume():
    combo = ComboSignal(
        rsi=60,
        mfi=55,
        rsi_bear_div=True,
        rsi_bull_div=False,
        mfi_bear_div=True,
        mfi_bull_div=False,
        dual_bear_div=True,
        dual_bull_div=False,
        money_confirms_weakness=False,
        summary="test",
    )
    vol = VolumeSignals(1.5, True, False, "rel vol 1.5x")
    assert edge_combo_score(combo, vol) == 4


def test_analyze_edge_bar_integration():
    n = 50
    t = np.arange(n)
    close = 100 + np.sin(t / 5) * 3 + t * 0.05
    vol = 1000 + t * 10
    df = _ohlcv_from_close(close.tolist(), vol.tolist())
    edge = analyze_edge_bar(df)
    assert edge is not None
    assert 0 <= edge.mfi <= 100
    assert 0 <= edge.edge_combo_score <= 4


def test_volume_relative_spike():
    vol = [1000.0] * 24 + [2500.0]
    close = [100.0] * 25
    df = _ohlcv_from_close(close, vol)
    v = analyze_volume(df, lookback=20)
    assert v.relative_volume >= 2.0


def test_analyze_edge_bar_requires_ohlcv():
    assert analyze_edge_bar(pd.DataFrame({"close": [1, 2, 3]})) is None
