"""Shared records. Prices stay as Decimal so pip math does not depend on binary floats."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class Bar:
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None = None
    bid_volume: Decimal | None = None
    ask_volume: Decimal | None = None

    def price_tuple(self) -> tuple[Decimal, Decimal, Decimal, Decimal]:
        return (self.open, self.high, self.low, self.close)


@dataclass(frozen=True)
class ParseIssue:
    line: int
    reason: str


@dataclass(frozen=True)
class Feature:
    bar_index: int
    decision_time: datetime
    bar_open: datetime
    session: str
    bucket: str
    h1_trend_score: Decimal
    h4_score: Decimal | None
    momentum: Decimal | None
    acceleration: Decimal | None
    atr: Decimal
    atr_percentile: Decimal | None
    adr_completion: Decimal | None
    dist_day_high_pips: Decimal
    dist_day_low_pips: Decimal
    bullish_engulfing: bool
    bearish_engulfing: bool
    bullish_pin: bool
    bearish_pin: bool
    inside_bar: bool
    broke_london_high: bool
    broke_london_low: bool
    volume_imbalance: Decimal | None

    def as_json(self) -> dict:
        def num(value: Decimal | None):
            return None if value is None else format(value, "f")

        return {
            "session": self.session,
            "bucket": self.bucket,
            "h1_trend_score": num(self.h1_trend_score),
            "h4_score": num(self.h4_score),
            "momentum": num(self.momentum),
            "acceleration": num(self.acceleration),
            "atr": num(self.atr),
            "atr_percentile": num(self.atr_percentile),
            "adr_completion": num(self.adr_completion),
            "dist_day_high_pips": num(self.dist_day_high_pips),
            "dist_day_low_pips": num(self.dist_day_low_pips),
            "bullish_engulfing": self.bullish_engulfing,
            "bearish_engulfing": self.bearish_engulfing,
            "bullish_pin": self.bullish_pin,
            "bearish_pin": self.bearish_pin,
            "inside_bar": self.inside_bar,
            "broke_london_high": self.broke_london_high,
            "broke_london_low": self.broke_london_low,
            "volume_imbalance": num(self.volume_imbalance),
        }


@dataclass(frozen=True)
class Label:
    klass: str
    gross_pips: Decimal


@dataclass(frozen=True)
class ForecastDraft:
    symbol: str
    timeframe_seconds: int
    decision_time: datetime
    horizon_hours: Decimal
    model_name: str
    model_version: str
    definition_id: str
    trigger_reason: str
    bucket: str
    probability_status: str
    n_samples: int
    n_up: int
    n_down: int
    n_flat: int
    q25_pips: Decimal | None
    q75_pips: Decimal | None
    analogue_status: str
    analogue_n: int
    analogue_n_up: int
    analogue_n_down: int
    analogue_n_flat: int
    analogue_median_pips: Decimal | None
    feature: dict
    volume_kind: str


@dataclass(frozen=True)
class StoredForecast:
    draft: ForecastDraft
    actual_status: str
    actual_class: str | None
    actual_gross_pips: Decimal | None
    actual_time: datetime | None
    created_at: datetime


@dataclass(frozen=True)
class Event:
    available_at: datetime
    name: str
    currency: str
    impact: int | None
    actual: Decimal | None
    forecast: Decimal | None
    previous: Decimal | None
    kind: str
    eurusd_sign: int | None = None


@dataclass(frozen=True)
class ExternalSignal:
    name: str
    bar_open: datetime
    value: Decimal
    label: str | None = None


@dataclass(frozen=True)
class QualityReport:
    n_bars: int
    n_gaps: int
    n_rejected: int
    n_conflicts: int
    n_forming_dropped: int
    fatal: tuple[str, ...]
    gap_examples: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.fatal
