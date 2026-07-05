"""Tests for EDGE 2.9 native hybrid engine."""

import numpy as np
import pandas as pd

from src.edge_native import NativeConfig, analyze_native_engine, side_score, super_alignment
from src.edge_native import NativeEngineResult


def test_side_score_pine_logic():
    assert side_score(0, False, False) == 0
    assert side_score(1, False, False) == 1
    assert side_score(2, False, False) == 2
    assert side_score(1, True, False) == 3
    assert side_score(2, True, False) == 3
    assert side_score(2, True, True) == 4


def test_native_engine_runs_on_synthetic_ohlcv():
    n = 120
    rng = np.random.default_rng(42)
    close = 100 + np.cumsum(rng.normal(0, 0.5, n))
    high = close + rng.uniform(0.1, 1.0, n)
    low = close - rng.uniform(0.1, 1.0, n)
    open_ = close + rng.normal(0, 0.2, n)
    vol = rng.integers(1000, 5000, n)
    df = pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": vol},
        index=pd.date_range("2026-01-01", periods=n, freq="h"),
    )
    cfg = NativeConfig(zone_lookback=40, lookback_bars=40)
    result = analyze_native_engine(df, cfg)
    assert result is not None
    assert 0 <= result.score <= 4
    assert result.score_dir in (-1, 0, 1)


def test_super_alignment_requires_same_direction():
    by_tf = {
        "15": NativeEngineResult(score=3, score_dir=1),
        "60": NativeEngineResult(score=4, score_dir=1),
        "240": NativeEngineResult(score=3, score_dir=1),
        "1d": NativeEngineResult(score=3, score_dir=1),
    }
    s = super_alignment(by_tf)
    assert s["super_buy"] is True
    assert s["super_sell"] is False

    by_tf["240"] = NativeEngineResult(score=3, score_dir=-1)
    s2 = super_alignment(by_tf)
    assert s2["super_buy"] is False
