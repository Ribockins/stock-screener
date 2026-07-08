import numpy as np
import pandas as pd

from src.signal_strength import SignalStrengthAnalyzer
from test_backtest_ng import NGBacktester


def _build_market_frame(close_tail, rsi_tail, last_volume=220.0):
    index = pd.date_range('2025-01-01', periods=60, freq='4h')
    close = pd.Series(
        np.concatenate([np.linspace(100, 86, 50), np.array(close_tail, dtype=float)]),
        index=index,
    )
    open_ = close.shift(1).fillna(close.iloc[0] + 0.3)
    low = np.minimum(open_, close) - 0.5
    high = np.maximum(open_, close) + 0.7
    volume = pd.Series(np.full(60, 100.0), index=index)
    volume.iloc[-1] = last_volume
    rsi = pd.Series(
        np.concatenate([np.linspace(52, 26, 50), np.array(rsi_tail, dtype=float)]),
        index=index,
    )
    df = pd.DataFrame({
        'Open': open_,
        'High': high,
        'Low': low,
        'Close': close,
        'Volume': volume,
    }, index=index)
    return df, rsi


def test_high_confluence_setup_becomes_premium_entry():
    df, rsi = _build_market_frame(
        [84.0, 83.5, 83.0, 82.8, 82.6, 81.0, 81.5, 82.3, 83.4, 84.6],
        [22.0, 21.0, 20.0, 19.0, 18.0, 24.0, 25.0, 26.5, 28.0, 29.0],
        last_volume=220.0,
    )

    analysis = SignalStrengthAnalyzer().analyze('TEST', df['Close'], rsi, df['Volume'], market_data=df)

    assert analysis is not None
    assert analysis.divergence_bias == 'BULLISH'
    assert bool(analysis.premium_entry) is True
    assert analysis.quality_score >= 70
    assert bool(analysis.volume_spike) is True
    assert bool(analysis.mtf_alignment) is True
    assert bool(analysis.adx_filter) is True
    assert analysis.risk_reward_ratio >= 1.2


def test_recent_rejection_and_missing_volume_spike_reject_setup():
    df, rsi = _build_market_frame(
        [84.0, 83.5, 83.0, 82.6, 82.0, 81.6, 81.3, 81.0, 81.4, 81.8],
        [22.0, 21.0, 20.0, 19.0, 18.5, 18.0, 19.0, 21.0, 22.0, 23.0],
        last_volume=100.0,
    )

    analysis = SignalStrengthAnalyzer().analyze('TEST', df['Close'], rsi, df['Volume'], market_data=df)

    assert analysis is not None
    assert bool(analysis.premium_entry) is False
    assert analysis.quality_score < 70
    assert bool(analysis.volume_spike) is False
    assert bool(analysis.recent_rejection) is True


def test_ng_backtester_handles_empty_downloads_gracefully():
    backtester = NGBacktester()
    backtester.download_ng_data = lambda days=30: pd.DataFrame()

    assert backtester.backtest() is None
