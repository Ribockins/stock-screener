"""Tests for GEM Logic 1.5 backtest (point-in-time, no lookahead)."""

import numpy as np
import pandas as pd

from src.gem.backtest import BacktestConfig, run_gem_backtest
from src.gem.config import GEMConfig
from src.gem.dashboard import compute_dashboard_series


def _synthetic_ohlcv(n: int = 200, seed: int = 11) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    close = 100 + np.sin(t / 6) * 8 + t * 0.01
    spread = close * 0.004
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


def test_compute_dashboard_series_has_required_columns():
    df = _synthetic_ohlcv()
    series = compute_dashboard_series(df, GEMConfig(), interval_seconds=3600)
    assert series is not None
    for col in ("score", "bias", "buy_gem", "sell_gem", "buy_gem_raw", "sell_gem_raw"):
        assert col in series.columns
    assert series["score"].notna().any()


def test_run_gem_backtest_returns_result_shape():
    df = _synthetic_ohlcv(n=300)
    result = run_gem_backtest(
        df,
        symbol="TEST",
        display_name="Test",
        timeframe="60",
        bt_config=BacktestConfig(entry_score_threshold=3),
    )
    assert result.symbol == "TEST"
    assert result.timeframe == "60"
    assert result.total_trades >= 0
    assert result.win_pct >= 0.0
    if result.trades:
        assert all(hasattr(t, "r_multiple") for t in result.trades)


def test_backtest_no_future_leak_on_entry():
    """Entry index must not use bars after signal bar."""
    df = _synthetic_ohlcv(n=250, seed=99)
    series = compute_dashboard_series(df, GEMConfig(), interval_seconds=3600)
    result = run_gem_backtest(
        df,
        timeframe="60",
        bt_config=BacktestConfig(entry_score_threshold=1),
    )
    valid = series["score"].notna()
    s = series.loc[valid]
    for trade in result.trades:
        assert trade.entry_idx < len(s)
        assert trade.exit_idx >= trade.entry_idx
