"""
GEM Logic 1.5 terminal dashboard — port of Pine ``f_local_tf_pack()``.

Packs per-timeframe state into R1–R3, D1–D3, MF, MV, CDL, GM, bias, and score (0–11).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from src.edge_combos import calculate_mfi
from src.gem.candles import detect_candle_signals
from src.gem.config import GEMConfig
from src.gem.rsi import calculate_rsi

PACK_TERNARY_BASE = 4
PACK_SCORE_BASE = 16
PACK_SHIFT_BIAS = 16
PACK_SHIFT_GM = 64
PACK_SHIFT_CDL = 256
PACK_SHIFT_MV = 1024
PACK_SHIFT_MF = 4096
PACK_SHIFT_D3 = 16384
PACK_SHIFT_D2 = 65536
PACK_SHIFT_D1 = 262144
PACK_SHIFT_R3 = 1048576
PACK_SHIFT_R2 = 4194304
PACK_SHIFT_R1 = 16777216


@dataclass(frozen=True)
class TFDashboardState:
    """Unpacked terminal row for one timeframe (matches Pine table columns)."""

    r1: int = 0  # RSI zone: +1 OS, -1 OB
    r2: int = 0  # cycle tier 2
    r3: int = 0  # cycle tier 3
    d1: int = 0
    d2: int = 0
    d3: int = 0
    mf: int = 0  # MFI zone
    mv: int = 0  # MFI divergence direction
    cdl: int = 0  # candle pattern
    gm: int = 0  # universal GEM edge
    bias: int = 0
    score: int = 0
    pack: int = 0

    def rsi_text(self, state: int) -> str:
        if state > 0:
            return "OS"
        if state < 0:
            return "OB"
        return "0"

    def dir_text(self, state: int) -> str:
        if state > 0:
            return "B"
        if state < 0:
            return "S"
        return "0"

    def row_cells(self) -> list[str]:
        return [
            self.rsi_text(self.r1),
            self.dir_text(self.r2),
            self.dir_text(self.r3),
            self.dir_text(self.d1),
            self.dir_text(self.d2),
            self.dir_text(self.d3),
            self.rsi_text(self.mf),
            self.dir_text(self.mv),
            self.dir_text(self.cdl),
            self.dir_text(self.gm),
            str(self.score),
        ]


def r_cycle_hours(interval_seconds: int) -> float:
    if interval_seconds == 900:
        return 48.0
    if interval_seconds == 3600:
        return 120.0
    if interval_seconds == 14400:
        return 190.0
    if interval_seconds >= 86400:
        return 400.0
    return 48.0


def r_cycle_bars(interval_seconds: int) -> int:
    bars = int(np.ceil(r_cycle_hours(interval_seconds) * 3600.0 / max(interval_seconds, 1)))
    return max(1, bars)


def infer_interval_seconds(index: pd.Index, default: int = 3600) -> int:
    if len(index) < 2:
        return default
    try:
        delta = pd.Timestamp(index[-1]) - pd.Timestamp(index[-2])
        sec = int(delta.total_seconds())
        return sec if sec > 0 else default
    except (TypeError, ValueError):
        return default


def _pack_ternary(state: int) -> int:
    return int(state) + 1


def pack_dashboard(
    r1: int,
    r2: int,
    r3: int,
    d1: int,
    d2: int,
    d3: int,
    mf: int,
    mv: int,
    cdl: int,
    gm: int,
    bias: int,
    score: int,
) -> int:
    pack = _pack_ternary(r1)
    pack = pack * PACK_TERNARY_BASE + _pack_ternary(r2)
    pack = pack * PACK_TERNARY_BASE + _pack_ternary(r3)
    pack = pack * PACK_TERNARY_BASE + _pack_ternary(d1)
    pack = pack * PACK_TERNARY_BASE + _pack_ternary(d2)
    pack = pack * PACK_TERNARY_BASE + _pack_ternary(d3)
    pack = pack * PACK_TERNARY_BASE + _pack_ternary(mf)
    pack = pack * PACK_TERNARY_BASE + _pack_ternary(mv)
    pack = pack * PACK_TERNARY_BASE + _pack_ternary(cdl)
    pack = pack * PACK_TERNARY_BASE + _pack_ternary(gm)
    pack = pack * PACK_TERNARY_BASE + _pack_ternary(bias)
    pack = pack * PACK_SCORE_BASE + int(score)
    return pack


def _unpack(pack: int, shift: int) -> int:
    return int(pack // shift) % PACK_TERNARY_BASE - 1


def unpack_dashboard(pack: int) -> TFDashboardState:
    return TFDashboardState(
        r1=_unpack(pack, PACK_SHIFT_R1),
        r2=_unpack(pack, PACK_SHIFT_R2),
        r3=_unpack(pack, PACK_SHIFT_R3),
        d1=_unpack(pack, PACK_SHIFT_D1),
        d2=_unpack(pack, PACK_SHIFT_D2),
        d3=_unpack(pack, PACK_SHIFT_D3),
        mf=_unpack(pack, PACK_SHIFT_MF),
        mv=_unpack(pack, PACK_SHIFT_MV),
        cdl=_unpack(pack, PACK_SHIFT_CDL),
        gm=_unpack(pack, PACK_SHIFT_GM),
        bias=_unpack(pack, PACK_SHIFT_BIAS),
        score=int(pack % PACK_SCORE_BASE),
        pack=pack,
    )


def _valuewhen(cond: np.ndarray, source: np.ndarray, i: int, occurrence: int = 1) -> float:
    count = 0
    for j in range(i - 1, -1, -1):
        if cond[j]:
            if count == occurrence:
                return float(source[j])
            count += 1
    return np.nan


def _bars_since(cond: np.ndarray, i: int) -> int:
    for j in range(i, -1, -1):
        if cond[j]:
            return i - j
    return 100_000


def compute_tf_dashboard(
    df: pd.DataFrame,
    config: Optional[GEMConfig] = None,
    interval_seconds: Optional[int] = None,
) -> Optional[TFDashboardState]:
    """
    Run the full GEM 1.5 dashboard engine and return state at the last bar.
    """
    if df is None or df.empty:
        return None

    cfg = config or GEMConfig()
    out = df.copy()
    out.columns = [str(c).lower() for c in out.columns]
    for col in ("open", "high", "low", "close", "volume"):
        if col not in out.columns:
            return None

    n = len(out)
    if n < cfg.rsi_length + 10:
        return None

    sec = interval_seconds if interval_seconds is not None else infer_interval_seconds(out.index)
    window_bars = r_cycle_bars(sec)

    rsi = calculate_rsi(out["close"], cfg.rsi_length).values
    mfi = calculate_mfi(out, cfg.mfi_length).values

    high = out["high"].astype(float).values
    low = out["low"].astype(float).values
    close = out["close"].astype(float).values

    r_ob = rsi > cfg.overbought_level
    r_os = rsi < cfg.oversold_level
    m_ob = mfi > cfg.mfi_overbought
    m_os = mfi < cfg.mfi_oversold

    bull_candle, bear_candle = detect_candle_signals(out)
    bull = bull_candle.values
    bear = bear_candle.values

    buy_div_base_arr = np.zeros(n, dtype=bool)
    sell_div_base_arr = np.zeros(n, dtype=bool)
    raw_buy_rsi = np.zeros(n, dtype=bool)
    raw_sell_rsi = np.zeros(n, dtype=bool)
    raw_buy_mfi = np.zeros(n, dtype=bool)
    raw_sell_mfi = np.zeros(n, dtype=bool)

    buy_count = np.zeros(n, dtype=int)
    sell_count = np.zeros(n, dtype=int)

    bull_cycle = 0
    bear_cycle = 0
    bull_start = -1
    bear_start = -1
    bull_exited = False
    bear_exited = False
    bull_cross50 = False
    bear_cross50 = False
    bull_d1 = bull_d2 = bull_d3 = False
    bear_d1 = bear_d2 = bear_d3 = False

    buy_gem_raw_prev = False
    sell_gem_raw_prev = False

    last_state: Optional[TFDashboardState] = None

    for i in range(n):
        if np.isnan(rsi[i]):
            continue

        prev_high = _valuewhen(r_ob, high, i, 1)
        prev_rsi_h = _valuewhen(r_ob, rsi, i, 1)
        prev_low = _valuewhen(r_os, low, i, 1)
        prev_rsi_l = _valuewhen(r_os, rsi, i, 1)

        if r_ob[i] and not np.isnan(prev_high):
            raw_sell_rsi[i] = high[i] > prev_high and rsi[i] < prev_rsi_h
        if r_os[i] and not np.isnan(prev_low):
            raw_buy_rsi[i] = low[i] < prev_low and rsi[i] > prev_rsi_l

        prev_high_m = _valuewhen(m_ob, high, i, 1)
        prev_mfi_h = _valuewhen(m_ob, mfi, i, 1)
        prev_low_m = _valuewhen(m_os, low, i, 1)
        prev_mfi_l = _valuewhen(m_os, mfi, i, 1)

        if m_ob[i] and not np.isnan(prev_high_m) and not np.isnan(mfi[i]):
            raw_sell_mfi[i] = high[i] > prev_high_m and mfi[i] < prev_mfi_h
        if m_os[i] and not np.isnan(prev_low_m) and not np.isnan(mfi[i]):
            raw_buy_mfi[i] = low[i] < prev_low_m and mfi[i] > prev_mfi_l

        lb = min(cfg.lookback_bars, i + 1)
        buy_count[i] = int(np.sum(raw_buy_rsi[i - lb + 1 : i + 1]))
        sell_count[i] = int(np.sum(raw_sell_rsi[i - lb + 1 : i + 1]))

        buy3 = raw_buy_rsi[i] and buy_count[i] >= cfg.div_count_required
        sell3 = raw_sell_rsi[i] and sell_count[i] >= cfg.div_count_required

        if cfg.gem_use_strong_div_only:
            buy_div_base_arr[i] = buy3
            sell_div_base_arr[i] = sell3
        else:
            buy_div_base_arr[i] = buy3 or raw_buy_rsi[i]
            sell_div_base_arr[i] = sell3 or raw_sell_rsi[i]

        enter_os = r_os[i] and (i == 0 or not r_os[i - 1])
        exit_os = not r_os[i] and (i > 0 and r_os[i - 1])
        enter_ob = r_ob[i] and (i == 0 or not r_ob[i - 1])
        exit_ob = not r_ob[i] and (i > 0 and r_ob[i - 1])

        bull_expired = bull_cycle > 0 and bull_start >= 0 and i - bull_start > window_bars
        bear_expired = bear_cycle > 0 and bear_start >= 0 and i - bear_start > window_bars

        if bull_expired or r_ob[i]:
            bull_cycle = 0
            bull_start = -1
            bull_exited = False
            bull_cross50 = False
            bull_d1 = bull_d2 = bull_d3 = False

        if bear_expired or r_os[i]:
            bear_cycle = 0
            bear_start = -1
            bear_exited = False
            bear_cross50 = False
            bear_d1 = bear_d2 = bear_d3 = False

        if exit_os and bull_cycle > 0:
            bull_exited = True
        if exit_ob and bear_cycle > 0:
            bear_exited = True

        if bull_cycle > 0 and bull_exited and rsi[i] > 50:
            bull_cross50 = True
        if bear_cycle > 0 and bear_exited and rsi[i] < 50:
            bear_cross50 = True

        if enter_os:
            if bull_cycle == 0:
                bull_cycle = 1
                bull_start = i
                bull_exited = False
                bull_cross50 = False
                bull_d1 = bull_d2 = bull_d3 = False
            elif bull_cycle == 1 and bull_exited and bull_cross50:
                bull_cycle = 2
                bull_exited = False
                bull_cross50 = False
            elif bull_cycle == 2 and bull_exited and bull_cross50:
                bull_cycle = 3
                bull_exited = False
                bull_cross50 = False
            else:
                bull_cycle = 1
                bull_start = i
                bull_exited = False
                bull_cross50 = False
                bull_d1 = bull_d2 = bull_d3 = False

        if enter_ob:
            if bear_cycle == 0:
                bear_cycle = 1
                bear_start = i
                bear_exited = False
                bear_cross50 = False
                bear_d1 = bear_d2 = bear_d3 = False
            elif bear_cycle == 1 and bear_exited and bear_cross50:
                bear_cycle = 2
                bear_exited = False
                bear_cross50 = False
            elif bear_cycle == 2 and bear_exited and bear_cross50:
                bear_cycle = 3
                bear_exited = False
                bear_cross50 = False
            else:
                bear_cycle = 1
                bear_start = i
                bear_exited = False
                bear_cross50 = False
                bear_d1 = bear_d2 = bear_d3 = False

        if raw_buy_rsi[i]:
            if bull_cycle == 1:
                bull_d1 = True
            elif bull_cycle == 2:
                bull_d2 = True
            elif bull_cycle >= 3:
                bull_d3 = True

        if raw_sell_rsi[i]:
            if bear_cycle == 1:
                bear_d1 = True
            elif bear_cycle == 2:
                bear_d2 = True
            elif bear_cycle >= 3:
                bear_d3 = True

        r1_state = 1 if r_os[i] else (-1 if r_ob[i] else 0)
        r2_state = 1 if r_os[i] and bull_cycle >= 2 else (-1 if r_ob[i] and bear_cycle >= 2 else 0)
        r3_state = 1 if r_os[i] and bull_cycle >= 3 else (-1 if r_ob[i] and bear_cycle >= 3 else 0)

        d1_state = 1 if bull_d1 else (-1 if bear_d1 else 0)
        d2_state = 1 if bull_d2 else (-1 if bear_d2 else 0)
        d3_state = 1 if bull_d3 else (-1 if bear_d3 else 0)

        m_state = 1 if m_os[i] else (-1 if m_ob[i] else 0)
        mv_state = 1 if raw_buy_mfi[i] else (-1 if raw_sell_mfi[i] else 0)
        c_state = 1 if bull[i] else (-1 if bear[i] else 0)

        recent_os = _bars_since(r_os, i) <= cfg.gem_confirm_window
        recent_ob = _bars_since(r_ob, i) <= cfg.gem_confirm_window
        recent_buy_div = _bars_since(buy_div_base_arr, i) <= cfg.gem_confirm_window
        recent_sell_div = _bars_since(sell_div_base_arr, i) <= cfg.gem_confirm_window
        recent_bull = _bars_since(bull, i) <= cfg.gem_confirm_window
        recent_bear = _bars_since(bear, i) <= cfg.gem_confirm_window

        buy_gem_raw = recent_os and recent_buy_div and recent_bull
        sell_gem_raw = recent_ob and recent_sell_div and recent_bear
        gm_state = 1 if buy_gem_raw and not buy_gem_raw_prev else (-1 if sell_gem_raw and not sell_gem_raw_prev else 0)
        buy_gem_raw_prev = buy_gem_raw
        sell_gem_raw_prev = sell_gem_raw

        score = sum(
            [
                1 if r1_state != 0 else 0,
                1 if r2_state != 0 else 0,
                1 if r3_state != 0 else 0,
                1 if d1_state != 0 else 0,
                1 if d2_state != 0 else 0,
                2 if d3_state != 0 else 0,
                1 if m_state != 0 else 0,
                1 if mv_state != 0 else 0,
                1 if c_state != 0 else 0,
                1 if gm_state != 0 else 0,
            ]
        )

        bias_sum = (
            r1_state
            + r2_state
            + r3_state
            + d1_state
            + d2_state
            + d3_state * 2
            + m_state
            + mv_state
            + c_state
            + gm_state
        )
        if gm_state != 0:
            bias = gm_state
        elif bias_sum > 0:
            bias = 1
        elif bias_sum < 0:
            bias = -1
        else:
            bias = 0

        pack = pack_dashboard(
            r1_state,
            r2_state,
            r3_state,
            d1_state,
            d2_state,
            d3_state,
            m_state,
            mv_state,
            c_state,
            gm_state,
            bias,
            score,
        )
        last_state = TFDashboardState(
            r1=r1_state,
            r2=r2_state,
            r3=r3_state,
            d1=d1_state,
            d2=d2_state,
            d3=d3_state,
            mf=m_state,
            mv=mv_state,
            cdl=c_state,
            gm=gm_state,
            bias=bias,
            score=score,
            pack=pack,
        )

    return last_state
