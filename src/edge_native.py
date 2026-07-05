"""
EDGE 2.9 Native Hybrid Engine — Python port of TradingView Pine f_engine().

Score 0–4 per bar (native), separate from GEM strength tiers:
  1 = one divergence in memory (RSI or MFI)
  2 = both RSI and MFI divergence in memory
  3 = div + near support/resistance zone
  4 = div + zone + price reaction (wick / engulf / close back inside)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.edge_combos import calculate_mfi
from src.gem.rsi import calculate_rsi

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "edge_native_29.json"


@dataclass
class NativeConfig:
    rsi_length: int = 14
    overbought_level: float = 72.0
    oversold_level: float = 28.0
    lookback_bars: int = 84
    extreme_memory_bars: int = 10
    divergence_memory_bars: int = 5
    mfi_length: int = 14
    mfi_overbought: float = 80.0
    mfi_oversold: float = 20.0
    zone_lookback: int = 80
    zone_width_pct: float = 0.15
    reaction_wick_min: float = 0.45
    reaction_close_pct: float = 0.55
    use_engulfing: bool = True
    use_close_back_inside: bool = True
    super_min_score: int = 3
    super_tfs: Tuple[str, ...] = ("5", "15", "60", "240", "1d")


@dataclass
class NativeEngineResult:
    """Last-bar native EDGE 2.9 read."""

    score: int = 0
    score_dir: int = 0  # 1 bull, -1 bear, 0 conflict/none
    buy_score: int = 0
    sell_score: int = 0
    rsi_buy_memory: bool = False
    rsi_sell_memory: bool = False
    mfi_buy_memory: bool = False
    mfi_sell_memory: bool = False
    raw_buy_rsi: bool = False
    raw_sell_rsi: bool = False
    raw_buy_mfi: bool = False
    raw_sell_mfi: bool = False
    near_support: bool = False
    near_resistance: bool = False
    buy_reaction: bool = False
    sell_reaction: bool = False
    rsi: float = 0.0
    mfi: float = 0.0

    @property
    def label(self) -> str:
        if self.score == 0:
            return "—"
        d = "↑" if self.score_dir == 1 else "↓" if self.score_dir == -1 else "⚡"
        return f"NAT{self.score}{d}"

    def to_dict(self) -> dict:
        return {
            "native_score": self.score,
            "native_dir": self.score_dir,
            "native_buy_score": self.buy_score,
            "native_sell_score": self.sell_score,
            "rsi_buy_memory": self.rsi_buy_memory,
            "rsi_sell_memory": self.rsi_sell_memory,
            "mfi_buy_memory": self.mfi_buy_memory,
            "mfi_sell_memory": self.mfi_sell_memory,
            "near_support": self.near_support,
            "near_resistance": self.near_resistance,
            "buy_reaction": self.buy_reaction,
            "sell_reaction": self.sell_reaction,
            "rsi": round(self.rsi, 2),
            "mfi": round(self.mfi, 2) if self.mfi == self.mfi else None,
        }


def load_native_config(path: Path = CONFIG_PATH) -> NativeConfig:
    if not path.exists():
        return NativeConfig()
    data = json.loads(path.read_text(encoding="utf-8"))
    c = data.get("core", {})
    m = data.get("mfi", {})
    z = data.get("zone", {})
    r = data.get("reaction", {})
    s = data.get("super_alignment", {})
    return NativeConfig(
        rsi_length=int(c.get("rsi_length", 14)),
        overbought_level=float(c.get("overbought_level", 72)),
        oversold_level=float(c.get("oversold_level", 28)),
        lookback_bars=int(c.get("lookback_bars", 84)),
        extreme_memory_bars=int(c.get("extreme_memory_bars", 10)),
        divergence_memory_bars=int(c.get("divergence_memory_bars", 5)),
        mfi_length=int(m.get("length", 14)),
        mfi_overbought=float(m.get("overbought_level", 80)),
        mfi_oversold=float(m.get("oversold_level", 20)),
        zone_lookback=int(z.get("lookback", 80)),
        zone_width_pct=float(z.get("width_pct_of_range", 0.15)),
        reaction_wick_min=float(r.get("wick_min", 0.45)),
        reaction_close_pct=float(r.get("close_strength", 0.55)),
        use_engulfing=bool(r.get("use_engulfing", True)),
        use_close_back_inside=bool(r.get("use_close_back_inside", True)),
        super_min_score=int(s.get("min_score", 3)),
        super_tfs=tuple(s.get("required_timeframes", ["5", "15", "60", "240", "1d"])),
    )


def side_score(core_count: int, near_zone: bool, reaction: bool) -> int:
    """Pine f_side_score — native 0–4."""
    score = 0
    if core_count == 1:
        score = 1
    elif core_count >= 2:
        score = 2
    if core_count > 0 and near_zone:
        score = max(score, 3)
    if core_count > 0 and near_zone and reaction:
        score = 4
    return score


def _bars_since(series: pd.Series) -> int:
    """Like ta.barssince(condition) at last bar."""
    cond = series.fillna(False).astype(bool)
    if not cond.any():
        return 10**9
    last_true = int(np.where(cond.values)[0][-1])
    return len(cond) - 1 - last_true


def analyze_native_engine(
    df: pd.DataFrame,
    config: Optional[NativeConfig] = None,
) -> Optional[NativeEngineResult]:
    """
    Run EDGE 2.9 native hybrid engine on OHLCV (last bar output).
    Mirrors Pine f_engine() state machine.
    """
    if df is None or df.empty:
        return None
    cfg = config or load_native_config()
    out = df.copy()
    out.columns = [str(c).lower() for c in out.columns]
    n = len(out)
    if n < max(cfg.zone_lookback, cfg.rsi_length) + 5:
        return None

    rsi = calculate_rsi(out["close"], cfg.rsi_length)
    mfi = calculate_mfi(out, cfg.mfi_length)
    if rsi.dropna().empty:
        return None

    high = out["high"].astype(float).values
    low = out["low"].astype(float).values
    open_ = out["open"].astype(float).values
    close = out["close"].astype(float).values
    rsi_v = rsi.values
    mfi_v = mfi.values if not mfi.dropna().empty else np.full(n, np.nan)

    in_rsi_ob = rsi > cfg.overbought_level
    in_rsi_os = rsi < cfg.oversold_level
    in_mfi_ob = mfi > cfg.mfi_overbought if not mfi.dropna().empty else pd.Series(False, index=out.index)
    in_mfi_os = mfi < cfg.mfi_oversold if not mfi.dropna().empty else pd.Series(False, index=out.index)

    raw_buy_rsi = np.zeros(n, dtype=bool)
    raw_sell_rsi = np.zeros(n, dtype=bool)
    raw_buy_mfi = np.zeros(n, dtype=bool)
    raw_sell_mfi = np.zeros(n, dtype=bool)

    prev_high_rsi = np.nan
    prev_rsi_h = np.nan
    prev_bar_high_rsi = -1
    prev_low_rsi = np.nan
    prev_rsi_l = np.nan
    prev_bar_low_rsi = -1

    prev_high_mfi = np.nan
    prev_mfi_h = np.nan
    prev_bar_high_mfi = -1
    prev_low_mfi = np.nan
    prev_mfi_l = np.nan
    prev_bar_low_mfi = -1

    for i in range(n):
        recent_rsi_ob = False
        recent_rsi_os = False
        recent_mfi_ob = False
        recent_mfi_os = False
        for j in range(max(0, i - cfg.extreme_memory_bars), i + 1):
            if in_rsi_ob.iloc[j]:
                recent_rsi_ob = True
            if in_rsi_os.iloc[j]:
                recent_rsi_os = True
            if not mfi.dropna().empty:
                if in_mfi_ob.iloc[j]:
                    recent_mfi_ob = True
                if in_mfi_os.iloc[j]:
                    recent_mfi_os = True

        # RSI sell divergence
        valid_sell_rsi = (
            recent_rsi_ob
            and not np.isnan(prev_high_rsi)
            and high[i] > prev_high_rsi
            and not np.isnan(rsi_v[i])
            and rsi_v[i] < prev_rsi_h
        )
        if valid_sell_rsi and (i == 0 or not (
            recent_rsi_ob
            and not np.isnan(prev_high_rsi)
            and high[i - 1] > prev_high_rsi
            and rsi_v[i - 1] < prev_rsi_h
        )):
            raw_sell_rsi[i] = True

        if in_rsi_ob.iloc[i]:
            if np.isnan(prev_high_rsi) or (not np.isnan(rsi_v[i]) and rsi_v[i] > prev_rsi_h):
                prev_high_rsi = high[i]
                prev_rsi_h = rsi_v[i]
                prev_bar_high_rsi = i
        if prev_bar_high_rsi >= 0 and i - prev_bar_high_rsi > cfg.lookback_bars:
            prev_high_rsi = np.nan
            prev_rsi_h = np.nan
            prev_bar_high_rsi = -1

        # RSI buy divergence
        valid_buy_rsi = (
            recent_rsi_os
            and not np.isnan(prev_low_rsi)
            and low[i] < prev_low_rsi
            and not np.isnan(rsi_v[i])
            and rsi_v[i] > prev_rsi_l
        )
        if valid_buy_rsi and (i == 0 or not (
            recent_rsi_os
            and not np.isnan(prev_low_rsi)
            and low[i - 1] < prev_low_rsi
            and rsi_v[i - 1] > prev_rsi_l
        )):
            raw_buy_rsi[i] = True

        if in_rsi_os.iloc[i]:
            if np.isnan(prev_low_rsi) or (not np.isnan(rsi_v[i]) and rsi_v[i] < prev_rsi_l):
                prev_low_rsi = low[i]
                prev_rsi_l = rsi_v[i]
                prev_bar_low_rsi = i
        if prev_bar_low_rsi >= 0 and i - prev_bar_low_rsi > cfg.lookback_bars:
            prev_low_rsi = np.nan
            prev_rsi_l = np.nan
            prev_bar_low_rsi = -1

        if not mfi.dropna().empty and not np.isnan(mfi_v[i]):
            valid_sell_mfi = (
                recent_mfi_ob
                and not np.isnan(prev_high_mfi)
                and high[i] > prev_high_mfi
                and mfi_v[i] < prev_mfi_h
            )
            if valid_sell_mfi and (i == 0 or not (
                recent_mfi_ob
                and not np.isnan(prev_high_mfi)
                and high[i - 1] > prev_high_mfi
                and mfi_v[i - 1] < prev_mfi_h
            )):
                raw_sell_mfi[i] = True

            if in_mfi_ob.iloc[i]:
                if np.isnan(prev_high_mfi) or mfi_v[i] > prev_mfi_h:
                    prev_high_mfi = high[i]
                    prev_mfi_h = mfi_v[i]
                    prev_bar_high_mfi = i
            if prev_bar_high_mfi >= 0 and i - prev_bar_high_mfi > cfg.lookback_bars:
                prev_high_mfi = np.nan
                prev_mfi_h = np.nan
                prev_bar_high_mfi = -1

            valid_buy_mfi = (
                recent_mfi_os
                and not np.isnan(prev_low_mfi)
                and low[i] < prev_low_mfi
                and mfi_v[i] > prev_mfi_l
            )
            if valid_buy_mfi and (i == 0 or not (
                recent_mfi_os
                and not np.isnan(prev_low_mfi)
                and low[i - 1] < prev_low_mfi
                and mfi_v[i - 1] > prev_mfi_l
            )):
                raw_buy_mfi[i] = True

            if in_mfi_os.iloc[i]:
                if np.isnan(prev_low_mfi) or mfi_v[i] < prev_mfi_l:
                    prev_low_mfi = low[i]
                    prev_mfi_l = mfi_v[i]
                    prev_bar_low_mfi = i
            if prev_bar_low_mfi >= 0 and i - prev_bar_low_mfi > cfg.lookback_bars:
                prev_low_mfi = np.nan
                prev_mfi_l = np.nan
                prev_bar_low_mfi = -1

    mem = cfg.divergence_memory_bars
    rsi_buy = _bars_since(pd.Series(raw_buy_rsi)) <= mem
    rsi_sell = _bars_since(pd.Series(raw_sell_rsi)) <= mem
    mfi_buy = _bars_since(pd.Series(raw_buy_mfi)) <= mem
    mfi_sell = _bars_since(pd.Series(raw_sell_mfi)) <= mem

    # Zone (prior bar range like Pine [1])
    start = max(1, n - cfg.zone_lookback)
    range_high = float(np.max(high[start - 1 : n - 1])) if n > 1 else float(high[0])
    range_low = float(np.min(low[start - 1 : n - 1])) if n > 1 else float(low[0])
    range_size = range_high - range_low
    support_top = range_low + range_size * cfg.zone_width_pct
    resistance_bottom = range_high - range_size * cfg.zone_width_pct
    near_support = range_size > 0 and low[-1] <= support_top
    near_resistance = range_size > 0 and high[-1] >= resistance_bottom

    # Price reaction (last bar)
    candle_range = high[-1] - low[-1]
    upper_wick = high[-1] - max(open_[-1], close[-1])
    lower_wick = min(open_[-1], close[-1]) - low[-1]
    upper_wick_ratio = upper_wick / candle_range if candle_range > 0 else 0.0
    lower_wick_ratio = lower_wick / candle_range if candle_range > 0 else 0.0
    close_strong_bull = candle_range > 0 and close[-1] >= low[-1] + candle_range * cfg.reaction_close_pct
    close_strong_bear = candle_range > 0 and close[-1] <= high[-1] - candle_range * cfg.reaction_close_pct
    bull_reject = lower_wick_ratio >= cfg.reaction_wick_min and close_strong_bull
    bear_reject = upper_wick_ratio >= cfg.reaction_wick_min and close_strong_bear
    bull_engulf = (
        cfg.use_engulfing
        and n >= 2
        and close[-1] > open_[-1]
        and close[-2] < open_[-2]
        and close[-1] >= open_[-2]
        and open_[-1] <= close[-2]
    )
    bear_engulf = (
        cfg.use_engulfing
        and n >= 2
        and close[-1] < open_[-1]
        and close[-2] > open_[-2]
        and close[-1] <= open_[-2]
        and open_[-1] >= close[-2]
    )
    close_back_above = (
        cfg.use_close_back_inside
        and range_size > 0
        and low[-1] < range_low
        and close[-1] > range_low
    )
    close_back_below = (
        cfg.use_close_back_inside
        and range_size > 0
        and high[-1] > range_high
        and close[-1] < range_high
    )
    buy_reaction = bull_reject or bull_engulf or close_back_above
    sell_reaction = bear_reject or bear_engulf or close_back_below

    buy_core = int(rsi_buy) + int(mfi_buy)
    sell_core = int(rsi_sell) + int(mfi_sell)
    buy_score = side_score(buy_core, near_support, buy_reaction)
    sell_score = side_score(sell_core, near_resistance, sell_reaction)

    score, score_dir = 0, 0
    if buy_score > sell_score:
        score, score_dir = buy_score, 1
    elif sell_score > buy_score:
        score, score_dir = sell_score, -1
    elif buy_score > 0 and sell_score > 0:
        score, score_dir = buy_score, 0

    cur_mfi = float(mfi.iloc[-1]) if not mfi.dropna().empty and not np.isnan(mfi.iloc[-1]) else float("nan")

    return NativeEngineResult(
        score=score,
        score_dir=score_dir,
        buy_score=buy_score,
        sell_score=sell_score,
        rsi_buy_memory=rsi_buy,
        rsi_sell_memory=rsi_sell,
        mfi_buy_memory=mfi_buy,
        mfi_sell_memory=mfi_sell,
        raw_buy_rsi=bool(raw_buy_rsi[-1]),
        raw_sell_rsi=bool(raw_sell_rsi[-1]),
        raw_buy_mfi=bool(raw_buy_mfi[-1]),
        raw_sell_mfi=bool(raw_sell_mfi[-1]),
        near_support=near_support,
        near_resistance=near_resistance,
        buy_reaction=buy_reaction,
        sell_reaction=sell_reaction,
        rsi=float(rsi.iloc[-1]),
        mfi=cur_mfi,
    )


def super_alignment(
    by_tf: Dict[str, NativeEngineResult],
    config: Optional[NativeConfig] = None,
) -> Dict[str, bool]:
    """Pine SUPER ALIGNMENT on scanned TFs: same direction, score >= min."""
    cfg = config or load_native_config()
    tfs = [tf for tf in cfg.super_tfs if tf in by_tf and by_tf[tf] is not None]
    if len(tfs) < 3:
        return {"super_buy": False, "super_sell": False}
    present = [by_tf[tf] for tf in tfs]
    dirs = [r.score_dir for r in present]
    scores = [r.score for r in present]
    ok = all(s >= cfg.super_min_score for s in scores)
    super_buy = ok and all(d == 1 for d in dirs)
    super_sell = ok and all(d == -1 for d in dirs)
    return {"super_buy": super_buy, "super_sell": super_sell}


def native_scan_row(
    by_tf: Dict[str, NativeEngineResult],
) -> str:
    """Compact MTF native scores for reports: M5:3↑ H1:4↓ ..."""
    order = [("5", "M5"), ("15", "M15"), ("60", "H1"), ("240", "H4"), ("1d", "D")]
    parts = []
    for key, label in order:
        r = by_tf.get(key)
        if r and r.score > 0:
            parts.append(f"{label}:{r.label}")
    return " ".join(parts) if parts else "—"
