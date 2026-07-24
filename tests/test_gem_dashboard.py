"""Tests for GEM Logic 1.5 terminal dashboard (Pine f_local_tf_pack port)."""

import numpy as np
import pandas as pd

from src.gem.config import GEMConfig
from src.gem.dashboard import (
    compute_tf_dashboard,
    pack_dashboard,
    r_cycle_bars,
    unpack_dashboard,
)


def _synthetic_ohlcv(n: int = 120, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    close = 100 + np.sin(t / 8) * 5 + t * 0.02
    spread = close * 0.003
    return pd.DataFrame(
        {
            "open": close - spread * 0.2,
            "high": close + spread,
            "low": close - spread,
            "close": close,
            "volume": 1000 + rng.integers(0, 500, n),
        },
        index=pd.date_range("2024-01-01", periods=n, freq="h"),
    )


def test_pack_unpack_roundtrip():
    pack = pack_dashboard(1, -1, 0, 1, 0, -1, 1, -1, 1, 1, 1, 9)
    state = unpack_dashboard(pack)
    assert state.r1 == 1
    assert state.r2 == -1
    assert state.d3 == -1
    assert state.gm == 1
    assert state.bias == 1
    assert state.score == 9
    assert state.pack == pack


def test_r_cycle_bars_by_timeframe():
    assert r_cycle_bars(900) == 192  # 48h on M15
    assert r_cycle_bars(3600) == 120
    assert r_cycle_bars(14400) == 48  # 190h on H4 -> ceil(190*3600/14400)
    assert r_cycle_bars(86400) == 17  # 400h on D1


def test_compute_tf_dashboard_returns_bounded_score():
    df = _synthetic_ohlcv()
    state = compute_tf_dashboard(df, GEMConfig(), interval_seconds=3600)
    assert state is not None
    assert 0 <= state.score <= 11
    assert state.bias in (-1, 0, 1)
    assert all(v in (-1, 0, 1) for v in (state.r1, state.r2, state.r3, state.d1, state.d2, state.d3))
    roundtrip = unpack_dashboard(state.pack)
    assert roundtrip.score == state.score
    assert roundtrip.bias == state.bias


def test_dashboard_on_trending_series():
    df = _synthetic_ohlcv(n=100, seed=7)
    state = compute_tf_dashboard(df, GEMConfig(), interval_seconds=900)
    assert state is not None
    assert len(state.row_cells()) == 11
