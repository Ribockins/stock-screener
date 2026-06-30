#!/usr/bin/env python
"""Backtest RSI divergence signals for NG over the last 30 days."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd
import yfinance as yf

import rsiconfig
from src.divergence_detector import Divergence, DivergenceDetector
from src.indicators import RSICalculator
from src.signal_strength import SignalStrengthAnalyzer


OUTPUT_FILE = Path("backtest_ng_results.json")
SYMBOL = "NG=F"
LOOKBACK_PERIOD = "30d"
INTERVAL = "1h"
EVALUATION_HOURS = 24
MIN_HISTORY_BARS = 60
STRENGTH_RANK = {"WEAK": 0, "MEDIUM": 1, "STRONG": 2}


@dataclass
class BacktestSignal:
    signal_datetime: str
    symbol: str
    divergence_type: str
    predicted_direction: str
    entry_price: float
    signal_strength: str
    divergence_strength: str
    profitable: bool
    price_movement_after_signal: float
    profit_loss_points: float
    max_favorable_points: float
    max_adverse_points: float
    close_after_24h: float
    rsi_value: float
    confidence: float


def fetch_ng_data() -> pd.DataFrame:
    """Download last 30 days of 1-hour NG data from yfinance."""
    data = yf.download(
        SYMBOL,
        period=LOOKBACK_PERIOD,
        interval=INTERVAL,
        auto_adjust=False,
        progress=False,
    )

    if data is None or data.empty:
        raise RuntimeError(f"Failed to download {SYMBOL} data from yfinance")

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [col[0] for col in data.columns]

    data.columns = [str(col).lower() for col in data.columns]
    required_columns = {"open", "high", "low", "close", "volume"}
    missing = required_columns - set(data.columns)
    if missing:
        raise RuntimeError(f"Downloaded data is missing columns: {sorted(missing)}")

    data = data.loc[:, ["open", "high", "low", "close", "volume"]].copy()
    data = data.dropna(subset=["open", "high", "low", "close"])
    data = data.sort_index()

    if len(data) < MIN_HISTORY_BARS + EVALUATION_HOURS:
        raise RuntimeError(f"Not enough hourly candles returned for {SYMBOL}")

    return data


def normalize_strength(signal_strength: str) -> str:
    """Match requested display names."""
    return "PREMIUM" if signal_strength == "PREMIUM_WARNING" else signal_strength


def select_current_divergence(divergences: List[Divergence], timestamp: pd.Timestamp) -> Optional[Divergence]:
    """Pick the strongest divergence that completes on the current candle."""
    matches = [div for div in divergences if div.timestamp_2 == timestamp]
    if not matches:
        return None

    return max(matches, key=lambda div: (STRENGTH_RANK.get(div.strength, -1), -div.bars_between))


def evaluate_signal(data: pd.DataFrame, index: int, direction: str) -> Dict[str, Union[float, bool]]:
    """Evaluate signal performance over the next 24 hourly candles."""
    future_window = data.iloc[index + 1:index + 1 + EVALUATION_HOURS]
    if len(future_window) != EVALUATION_HOURS:
        raise ValueError("Incomplete evaluation window for signal backtest")

    entry_price = float(data["close"].iloc[index])
    close_after_24h = float(future_window["close"].iloc[-1])
    raw_move = close_after_24h - entry_price

    if direction == "UP":
        profit_loss = raw_move
        max_favorable = float(future_window["high"].max() - entry_price)
        max_adverse = float(entry_price - future_window["low"].min())
    else:
        profit_loss = -raw_move
        max_favorable = float(entry_price - future_window["low"].min())
        max_adverse = float(future_window["high"].max() - entry_price)

    return {
        "profitable": profit_loss > 0,
        "price_movement_after_signal": round(raw_move, 4),
        "profit_loss_points": round(profit_loss, 4),
        "max_favorable_points": round(max_favorable, 4),
        "max_adverse_points": round(max_adverse, 4),
        "close_after_24h": round(close_after_24h, 4),
    }


def build_signal_record(
    timestamp: pd.Timestamp,
    entry_price: float,
    divergence: Divergence,
    direction: str,
    signal_strength: str,
    rsi_value: float,
    confidence: float,
    evaluation: Dict[str, Union[float, bool]],
) -> BacktestSignal:
    """Build a serializable signal record."""
    return BacktestSignal(
        signal_datetime=timestamp.isoformat(),
        symbol=SYMBOL,
        divergence_type=divergence.type,
        predicted_direction=direction,
        entry_price=round(entry_price, 4),
        signal_strength=normalize_strength(signal_strength),
        divergence_strength=divergence.strength,
        profitable=bool(evaluation["profitable"]),
        price_movement_after_signal=float(evaluation["price_movement_after_signal"]),
        profit_loss_points=float(evaluation["profit_loss_points"]),
        max_favorable_points=float(evaluation["max_favorable_points"]),
        max_adverse_points=float(evaluation["max_adverse_points"]),
        close_after_24h=float(evaluation["close_after_24h"]),
        rsi_value=round(rsi_value, 2),
        confidence=round(confidence, 3),
    )


def append_signal(
    signals: List[BacktestSignal],
    data: pd.DataFrame,
    index: int,
    timestamp: pd.Timestamp,
    entry_price: float,
    divergence: Divergence,
    direction: str,
    signal_strength: str,
    rsi_value: float,
    confidence: float,
) -> None:
    """Evaluate and append one signal record."""
    evaluation = evaluate_signal(data, index, direction)
    signals.append(
        build_signal_record(
            timestamp=timestamp,
            entry_price=entry_price,
            divergence=divergence,
            direction=direction,
            signal_strength=signal_strength,
            rsi_value=rsi_value,
            confidence=confidence,
            evaluation=evaluation,
        )
    )


def backtest_ng() -> Dict[str, object]:
    """Run the backtest and return a JSON-serializable report."""
    data = fetch_ng_data()
    rsi_calculator = RSICalculator()
    divergence_detector = DivergenceDetector()
    signal_analyzer = SignalStrengthAnalyzer()

    signals: List[BacktestSignal] = []

    for index in range(MIN_HISTORY_BARS, len(data) - EVALUATION_HOURS):
        history = data.iloc[:index + 1]
        close_prices = pd.to_numeric(history["close"], errors="coerce")
        volume = pd.to_numeric(history["volume"], errors="coerce").fillna(0)

        rsi = rsi_calculator.calculate_rsi(close_prices, rsiconfig.RSI_PERIOD)
        if rsi.empty or rsi.dropna().empty:
            continue

        bullish_divergences = divergence_detector.detect_bullish_divergence(close_prices, rsi)
        bearish_divergences = divergence_detector.detect_bearish_divergence(close_prices, rsi)
        current_timestamp = history.index[-1]

        current_bullish = select_current_divergence(bullish_divergences, current_timestamp)
        current_bearish = select_current_divergence(bearish_divergences, current_timestamp)
        if current_bullish is None and current_bearish is None:
            continue

        signal_analysis = signal_analyzer.analyze("NG", close_prices, rsi, volume)
        if signal_analysis is None:
            continue

        entry_price = float(close_prices.iloc[-1])
        rsi_value = float(rsi.dropna().iloc[-1])

        if current_bullish is not None:
            append_signal(
                signals=signals,
                data=data,
                index=index,
                timestamp=current_timestamp,
                entry_price=entry_price,
                divergence=current_bullish,
                direction="UP",
                signal_strength=signal_analysis.signal_strength,
                rsi_value=rsi_value,
                confidence=signal_analysis.confidence,
            )

        if current_bearish is not None:
            append_signal(
                signals=signals,
                data=data,
                index=index,
                timestamp=current_timestamp,
                entry_price=entry_price,
                divergence=current_bearish,
                direction="DOWN",
                signal_strength=signal_analysis.signal_strength,
                rsi_value=rsi_value,
                confidence=signal_analysis.confidence,
            )

    signal_dicts = [asdict(signal) for signal in signals]
    total_signals = len(signal_dicts)
    winning_signals = [signal for signal in signal_dicts if signal["profitable"]]
    average_profit = round(
        sum(signal["profit_loss_points"] for signal in signal_dicts) / total_signals, 4
    ) if total_signals else 0.0
    if total_signals:
        win_rate = round((len(winning_signals) / total_signals) * 100, 2)
    else:
        win_rate = 0.0
    best_signal = max(signal_dicts, key=lambda signal: signal["profit_loss_points"], default=None)
    worst_signal = min(signal_dicts, key=lambda signal: signal["profit_loss_points"], default=None)

    report = {
        "symbol": SYMBOL,
        "period": LOOKBACK_PERIOD,
        "interval": INTERVAL,
        "evaluation_window_hours": EVALUATION_HOURS,
        "generated_at": pd.Timestamp.utcnow().isoformat(),
        "statistics": {
            "total_signals_found": total_signals,
            "win_rate_percent": win_rate,
            "average_profit_per_signal_points": average_profit,
            "best_signal": best_signal,
            "worst_signal": worst_signal,
        },
        "signals": signal_dicts,
    }

    return report


def print_report(report: Dict[str, object]) -> None:
    """Print a readable console report."""
    stats = report["statistics"]
    signals = report["signals"]

    print("=" * 120)
    print(f"NG RSI Divergence Backtest | Period: {report['period']} | Interval: {report['interval']}")
    print(f"Signals found: {stats['total_signals_found']}")
    print(f"Win rate: {stats['win_rate_percent']}%")
    print(f"Average profit per signal: {stats['average_profit_per_signal_points']} points")
    print("=" * 120)
    print(
        f"{'Date/Time':25} {'Dir':5} {'Entry':>10} {'Strength':14} {'Div':8} "
        f"{'Win':4} {'24h Move':>10} {'P/L':>10} {'Max Fav':>10}"
    )
    print("-" * 120)

    for signal in signals:
        print(
            f"{signal['signal_datetime'][:25]:25} "
            f"{signal['predicted_direction']:5} "
            f"{signal['entry_price']:>10.4f} "
            f"{signal['signal_strength']:14} "
            f"{signal['divergence_strength']:8} "
            f"{'Y' if signal['profitable'] else 'N':4} "
            f"{signal['price_movement_after_signal']:>10.4f} "
            f"{signal['profit_loss_points']:>10.4f} "
            f"{signal['max_favorable_points']:>10.4f}"
        )

    print("-" * 120)
    if stats["best_signal"] is None:
        print("No completed signals to rank.")
    else:
        print("Best signal:", stats["best_signal"])
        print("Worst signal:", stats["worst_signal"])


def main() -> None:
    report = backtest_ng()
    print_report(report)
    OUTPUT_FILE.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nSaved results to {OUTPUT_FILE.resolve()}")


if __name__ == "__main__":
    main()
