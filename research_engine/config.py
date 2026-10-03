"""Run configuration. Every field that changes a label is part of definition_id."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal


DEFINITION_RULE = (
    "close_to_close; UP if gross_pips > flat_band; "
    "DOWN if gross_pips < -flat_band; else FLAT; "
    "exact horizon bar required; no interpolation; "
    "UTC bar grid; session label uses the bar end"
)


@dataclass(frozen=True)
class EngineConfig:
    symbol: str = "EURUSD"
    timeframe_seconds: int = 3600
    source_timezone: str = "UTC"
    session_timezone: str = "Europe/London"
    pip_size: Decimal = Decimal("0.0001")
    flat_band_pips: Decimal = Decimal("1")
    horizons_hours: tuple[Decimal, ...] = (
        Decimal("1"),
        Decimal("3"),
        Decimal("6"),
        Decimal("24"),
    )
    min_samples: int = 30
    atr_period: int = 14
    sma_period: int = 20
    trend_band: Decimal = Decimal("0.25")
    analogue_k: int = 50
    atr_percentile_lookback: int = 100
    model_name: str = "bucket_empirical"
    model_version: str = "0.1.0"
    volume_kind: str = "unspecified"
    timestamp_is_bar_open: bool = True

    def __post_init__(self) -> None:
        if self.timeframe_seconds <= 0:
            raise ValueError("timeframe_seconds must be positive")
        if self.pip_size <= 0:
            raise ValueError("pip_size must be positive")
        if self.flat_band_pips < 0:
            raise ValueError("flat_band_pips must be >= 0")
        if self.min_samples < 1:
            raise ValueError("min_samples must be >= 1")
        if self.atr_period < 1 or self.sma_period < 1:
            raise ValueError("atr_period and sma_period must be >= 1")
        if self.analogue_k < 1:
            raise ValueError("analogue_k must be >= 1")

    def definition_id(self) -> str:
        payload = "|".join(
            [
                DEFINITION_RULE,
                f"pip={self.pip_size}",
                f"band={self.flat_band_pips}",
                f"session_tz={self.session_timezone}",
                f"trend_band={self.trend_band}",
                f"atr={self.atr_period}",
                f"sma={self.sma_period}",
                "grid=UTC",
            ]
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]
