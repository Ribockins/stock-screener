"""GEM Logic parameters (defaults match GEM Logic 1.5 Pine inputs)."""

from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class GEMConfig:
  rsi_length: int = 14
  oversold_level: float = 28.0
  overbought_level: float = 72.0
  lookback_bars: int = 84
  div_count_required: int = 3

  signal_life_bars: int = 4
  stop_buffer_pct: float = 0.15
  tp1_rr: float = 1.0
  tp2_rr: float = 2.0

  gem_confirm_window: int = 8
  gem_use_strong_div_only: bool = False

  range_lookback: int = 50
  zone_pct_of_range: float = 0.10

  # MTF RSI fade (optional scoring)
  mtf_timeframes: List[Tuple[str, str]] = field(
    default_factory=lambda: [
      ("5m", "5"),
      ("15m", "15"),
      ("H1", "60"),
      ("H4", "240"),
      ("D", "1d"),
      ("W", "1wk"),
    ]
  )
