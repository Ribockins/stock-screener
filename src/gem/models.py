"""Result models for GEM analysis."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional


@dataclass
class GEMAnalysis:
  symbol: str
  timestamp: datetime
  price: float
  rsi: float

  in_oversold: bool
  in_overbought: bool

  raw_buy_div: bool
  raw_sell_div: bool
  buy_setup: bool  # buy3 — Nth divergence event in lookback
  sell_setup: bool  # sell3

  buy_entry: bool
  sell_entry: bool
  exec_state: str  # WAIT | ARMED_LONG | ARMED_SHORT | TRIGGERED_LONG | TRIGGERED_SHORT

  bull_candle: bool
  bear_candle: bool
  buy_gem: bool
  sell_gem: bool

  divergence_state: str  # BUY | SELL | NONE
  buy_div_events: int
  sell_div_events: int

  near_support: bool
  near_resistance: bool

  stop_price: Optional[float] = None
  tp1_price: Optional[float] = None
  tp2_price: Optional[float] = None

  gem_score: int = 0  # 0–4 per-TF style score on chart TF
  mtf_ob_count: int = 0
  mtf_os_count: int = 0
  mtf_scores: Dict[str, int] = field(default_factory=dict)

  recommendation: str = ""
  data_source: str = ""

  def to_dict(self) -> dict:
    return {
      "symbol": self.symbol,
      "timestamp": self.timestamp,
      "price": self.price,
      "rsi": round(self.rsi, 2),
      "in_oversold": self.in_oversold,
      "in_overbought": self.in_overbought,
      "raw_buy_div": self.raw_buy_div,
      "raw_sell_div": self.raw_sell_div,
      "buy_setup": self.buy_setup,
      "sell_setup": self.sell_setup,
      "buy_entry": self.buy_entry,
      "sell_entry": self.sell_entry,
      "exec_state": self.exec_state,
      "bull_candle": self.bull_candle,
      "bear_candle": self.bear_candle,
      "buy_gem": self.buy_gem,
      "sell_gem": self.sell_gem,
      "divergence_state": self.divergence_state,
      "buy_div_events": self.buy_div_events,
      "sell_div_events": self.sell_div_events,
      "near_support": self.near_support,
      "near_resistance": self.near_resistance,
      "stop_price": self.stop_price,
      "tp1_price": self.tp1_price,
      "tp2_price": self.tp2_price,
      "gem_score": self.gem_score,
      "mtf_ob_count": self.mtf_ob_count,
      "mtf_os_count": self.mtf_os_count,
      "mtf_scores": self.mtf_scores,
      "recommendation": self.recommendation,
      "data_source": self.data_source,
    }
