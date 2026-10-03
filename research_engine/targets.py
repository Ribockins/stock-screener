"""Close-to-close labels. A missing horizon bar is not interpolated."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from research_engine.clock import bar_end
from research_engine.config import EngineConfig
from research_engine.records import Bar, Label

UP = "UP"
DOWN = "DOWN"
FLAT = "FLAT"


def label_at(bars: list[Bar], index: int, horizon_bars: int, config: EngineConfig) -> Label | None:
    outcome = index + horizon_bars
    if outcome >= len(bars):
        return None
    step = timedelta(seconds=config.timeframe_seconds * horizon_bars)
    expected = bar_end(bars[index].timestamp, config.timeframe_seconds) + step
    actual = bar_end(bars[outcome].timestamp, config.timeframe_seconds)
    if actual != expected:
        return None
    gross = (bars[outcome].close - bars[index].close) / config.pip_size
    return Label(klass=classify(gross, config.flat_band_pips), gross_pips=gross)


def classify(gross_pips: Decimal, flat_band_pips: Decimal) -> str:
    if gross_pips > flat_band_pips:
        return UP
    if gross_pips < -flat_band_pips:
        return DOWN
    return FLAT
