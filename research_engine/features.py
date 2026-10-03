"""Causal bar features. Each row uses only bars at or before that index."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from research_engine.clock import bar_end, local_date, session_label
from research_engine.config import EngineConfig
from research_engine.records import Bar, Feature


def compute_features(bars: list[Bar], config: EngineConfig) -> list[Feature | None]:
    features: list[Feature | None] = [None] * len(bars)
    completed_ranges: list[Decimal] = []
    day_key = None
    day_high: Decimal | None = None
    day_low: Decimal | None = None
    london_day = None
    london_high: Decimal | None = None
    london_low: Decimal | None = None
    atr_history: list[Decimal] = []
    previous_momentum: Decimal | None = None

    for index, bar in enumerate(bars):
        end = bar_end(bar.timestamp, config.timeframe_seconds)
        day = local_date(end, config.session_timezone)
        if day != day_key:
            if day_high is not None and day_low is not None:
                completed_ranges.append(day_high - day_low)
            day_key = day
            day_high = bar.high
            day_low = bar.low
            london_high = None
            london_low = None
            london_day = day
        else:
            day_high = max(day_high, bar.high)  # type: ignore[type-var]
            day_low = min(day_low, bar.low)  # type: ignore[type-var]
        if london_day != day:
            london_high = None
            london_low = None
            london_day = day

        session = session_label(end, config.session_timezone, config.session_profile)
        in_london = session in {"london", "overlap"}
        broke_high = False
        broke_low = False
        if in_london:
            if london_high is None:
                london_high = bar.high
                london_low = bar.low
            else:
                broke_high = bar.high > london_high
                broke_low = bar.low < london_low
                london_high = max(london_high, bar.high)
                london_low = min(london_low, bar.low)  # type: ignore[type-var]

        if not _window_contiguous(bars, index, max(config.atr_period + 1, config.sma_period), config):
            previous_momentum = None
            continue
        atr = _atr(bars, index, config.atr_period)
        if atr is None or atr <= 0:
            previous_momentum = None
            continue
        sma = _mean([bars[pos].close for pos in range(index - config.sma_period + 1, index + 1)])
        trend = (bar.close - sma) / atr
        if trend > config.trend_band:
            direction = "up"
        elif trend < -config.trend_band:
            direction = "down"
        else:
            direction = "flat"
        h4_score = _ratio_over_atr(bars, index, 4, atr, config)
        momentum = _ratio_over_atr(bars, index, 3, atr, config)
        acceleration = None if momentum is None or previous_momentum is None else momentum - previous_momentum
        previous_momentum = momentum
        percentile = _percentile(atr_history, atr, config.atr_percentile_lookback)
        atr_history.append(atr)
        adr_completion = _adr_completion(completed_ranges, day_high - day_low, config)  # type: ignore[operator]
        bullish_engulf, bearish_engulf = _engulfing(bars, index, config)
        bullish_pin, bearish_pin = _pin(bar)
        inside = _inside(bars, index, config)
        features[index] = Feature(
            bar_index=index,
            decision_time=end,
            bar_open=bar.timestamp,
            session=session,
            bucket=f"{session}|trend_{direction}",
            h1_trend_score=trend,
            h4_score=h4_score,
            momentum=momentum,
            acceleration=acceleration,
            atr=atr,
            atr_percentile=percentile,
            adr_completion=adr_completion,
            dist_day_high_pips=(day_high - bar.close) / config.pip_size,  # type: ignore[operator]
            dist_day_low_pips=(bar.close - day_low) / config.pip_size,  # type: ignore[operator]
            bullish_engulfing=bullish_engulf,
            bearish_engulfing=bearish_engulf,
            bullish_pin=bullish_pin,
            bearish_pin=bearish_pin,
            inside_bar=inside,
            broke_london_high=broke_high,
            broke_london_low=broke_low,
            volume_imbalance=_imbalance(bar),
        )
    return features


def analogue_vector(feature: Feature) -> list[Decimal] | None:
    """Fixed feature order. A missing value excludes the row from the search."""
    session_flags = {
        "asia": Decimal(1 if feature.session == "asia" else 0),
        "london": Decimal(1 if feature.session == "london" else 0),
        "overlap": Decimal(1 if feature.session == "overlap" else 0),
        "ny": Decimal(1 if feature.session == "ny" else 0),
    }
    values = [
        feature.h1_trend_score,
        feature.h4_score,
        feature.momentum,
        feature.atr_percentile,
        feature.adr_completion,
        feature.dist_day_high_pips,
        feature.dist_day_low_pips,
        Decimal(int(feature.bullish_engulfing)),
        Decimal(int(feature.bearish_engulfing)),
        Decimal(int(feature.bullish_pin)),
        Decimal(int(feature.bearish_pin)),
        Decimal(int(feature.inside_bar)),
        Decimal(int(feature.broke_london_high)),
        Decimal(int(feature.broke_london_low)),
        session_flags["asia"],
        session_flags["london"],
        session_flags["overlap"],
        session_flags["ny"],
    ]
    if any(value is None for value in values):
        return None
    return [value for value in values if value is not None]


def _window_contiguous(bars: list[Bar], index: int, length: int, config: EngineConfig) -> bool:
    start = index - length + 1
    if start < 0:
        return False
    step = timedelta(seconds=config.timeframe_seconds)
    for pos in range(start, index):
        if bars[pos + 1].timestamp - bars[pos].timestamp != step:
            return False
    return True


def _atr(bars: list[Bar], index: int, period: int) -> Decimal | None:
    start = index - period + 1
    if start <= 0:
        return None
    true_ranges: list[Decimal] = []
    for pos in range(start, index + 1):
        previous_close = bars[pos - 1].close
        bar = bars[pos]
        true_ranges.append(
            max(bar.high - bar.low, abs(bar.high - previous_close), abs(bar.low - previous_close))
        )
    if len(true_ranges) != period:
        return None
    return _mean(true_ranges)


def _ratio_over_atr(
    bars: list[Bar], index: int, lookback: int, atr: Decimal, config: EngineConfig
) -> Decimal | None:
    if index < lookback or not _window_contiguous(bars, index, lookback + 1, config):
        return None
    return (bars[index].close - bars[index - lookback].close) / atr


def _percentile(history: list[Decimal], current: Decimal, lookback: int) -> Decimal | None:
    window = history[-lookback:]
    if not window:
        return None
    below = sum(1 for value in window if value <= current)
    return Decimal(below) / Decimal(len(window))


def _adr_completion(
    completed_ranges: list[Decimal], today_range: Decimal, config: EngineConfig
) -> Decimal | None:
    sample = completed_ranges[-20:]
    if not sample or today_range < 0:
        return None
    ordered = sorted(sample)
    median = ordered[len(ordered) // 2]
    if median <= 0:
        return None
    return today_range / median


def _adjacent(bars: list[Bar], index: int, config: EngineConfig) -> Bar | None:
    if index == 0:
        return None
    step = timedelta(seconds=config.timeframe_seconds)
    if bars[index].timestamp - bars[index - 1].timestamp != step:
        return None
    return bars[index - 1]


def _engulfing(bars: list[Bar], index: int, config: EngineConfig) -> tuple[bool, bool]:
    previous = _adjacent(bars, index, config)
    if previous is None:
        return False, False
    current = bars[index]
    previous_red = previous.close < previous.open
    previous_green = previous.close > previous.open
    current_green = current.close > current.open
    current_red = current.close < current.open
    bullish = (
        previous_red
        and current_green
        and current.open <= previous.close
        and current.close >= previous.open
    )
    bearish = (
        previous_green
        and current_red
        and current.open >= previous.close
        and current.close <= previous.open
    )
    return bullish, bearish


def _pin(bar: Bar) -> tuple[bool, bool]:
    span = bar.high - bar.low
    if span <= 0:
        return False, False
    body = abs(bar.close - bar.open)
    upper = bar.high - max(bar.open, bar.close)
    lower = min(bar.open, bar.close) - bar.low
    bullish = lower >= body * 2 and lower >= upper * 2 and bar.close >= bar.low + (span * 2) / Decimal(3)
    bearish = upper >= body * 2 and upper >= lower * 2 and bar.close <= bar.low + span / Decimal(3)
    return bullish, bearish


def _inside(bars: list[Bar], index: int, config: EngineConfig) -> bool:
    previous = _adjacent(bars, index, config)
    if previous is None:
        return False
    current = bars[index]
    return current.high <= previous.high and current.low >= previous.low


def _imbalance(bar: Bar) -> Decimal | None:
    if bar.bid_volume is None or bar.ask_volume is None:
        return None
    total = bar.bid_volume + bar.ask_volume
    if total == 0:
        return None
    return (bar.ask_volume - bar.bid_volume) / total


def _mean(values: list[Decimal]) -> Decimal:
    return sum(values, Decimal("0")) / Decimal(len(values))
