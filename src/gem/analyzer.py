"""Bar-by-bar GEM Logic engine (Pine GEM Logic 1.5)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from src.gem.candles import detect_candle_signals
from src.gem.config import GEMConfig
from src.gem.models import GEMAnalysis
from src.gem.rsi import calculate_rsi


class GEMAnalyzer:
    """Analyze OHLCV history and emit current-bar GEM signals."""

    def __init__(self, config: Optional[GEMConfig] = None):
        self.config = config or GEMConfig()

    def analyze(self, symbol: str, df: pd.DataFrame, data_source: str = "") -> Optional[GEMAnalysis]:
        df = self._normalize_ohlcv(df)
        if df is None or len(df) < self.config.rsi_length + 10:
            return None

        cfg = self.config
        rsi = calculate_rsi(df["close"], cfg.rsi_length)
        if rsi.dropna().empty:
            return None

        in_ob = rsi > cfg.overbought_level
        in_os = rsi < cfg.oversold_level

        bull_candle, bear_candle = detect_candle_signals(df)

        n = len(df)
        raw_buy = np.zeros(n, dtype=bool)
        raw_sell = np.zeros(n, dtype=bool)

        prev_high = np.nan
        prev_rsi_h = np.nan
        prev_bar_high = -1

        prev_low = np.nan
        prev_rsi_l = np.nan
        prev_bar_low = -1

        high = df["high"].values
        low = df["low"].values
        close = df["close"].values
        rsi_v = rsi.values

        for i in range(n):
            if in_ob.iloc[i]:
                if np.isnan(prev_high) or (not np.isnan(rsi_v[i]) and rsi_v[i] > prev_rsi_h):
                    prev_high = high[i]
                    prev_rsi_h = rsi_v[i]
                    prev_bar_high = i

            if prev_bar_high >= 0 and i - prev_bar_high > cfg.lookback_bars:
                prev_high = np.nan
                prev_rsi_h = np.nan
                prev_bar_high = -1

            if in_os.iloc[i]:
                if np.isnan(prev_low) or (not np.isnan(rsi_v[i]) and rsi_v[i] < prev_rsi_l):
                    prev_low = low[i]
                    prev_rsi_l = rsi_v[i]
                    prev_bar_low = i

            if prev_bar_low >= 0 and i - prev_bar_low > cfg.lookback_bars:
                prev_low = np.nan
                prev_rsi_l = np.nan
                prev_bar_low = -1

            if in_ob.iloc[i] and not np.isnan(prev_high):
                if high[i] > prev_high and not np.isnan(rsi_v[i]) and rsi_v[i] < prev_rsi_h:
                    raw_sell[i] = True

            if in_os.iloc[i] and not np.isnan(prev_low):
                if low[i] < prev_low and not np.isnan(rsi_v[i]) and rsi_v[i] > prev_rsi_l:
                    raw_buy[i] = True

        raw_buy_s = pd.Series(raw_buy, index=df.index)
        raw_sell_s = pd.Series(raw_sell, index=df.index)

        buy_count = raw_buy_s.rolling(cfg.lookback_bars, min_periods=1).sum()
        sell_count = raw_sell_s.rolling(cfg.lookback_bars, min_periods=1).sum()

        buy3 = raw_buy_s & (buy_count >= cfg.div_count_required)
        sell3 = raw_sell_s & (sell_count >= cfg.div_count_required)

        buy_div_base = buy3 if cfg.gem_use_strong_div_only else (buy3 | raw_buy_s)
        sell_div_base = sell3 if cfg.gem_use_strong_div_only else (sell3 | raw_sell_s)

        buy_entry, buy_setup_low = self._simulate_long_execution(df, buy3)
        sell_entry, sell_setup_high = self._simulate_short_execution(df, sell3)

        buy_gem_raw, sell_gem_raw = self._gem_confluence(
            in_os, in_ob, buy_div_base, sell_div_base, bull_candle, bear_candle, cfg.gem_confirm_window
        )
        buy_gem = buy_gem_raw & ~buy_gem_raw.shift(1).fillna(False)
        sell_gem = sell_gem_raw & ~sell_gem_raw.shift(1).fillna(False)

        range_high = df["high"].rolling(cfg.range_lookback, min_periods=1).max()
        range_low = df["low"].rolling(cfg.range_lookback, min_periods=1).min()
        zone = (range_high - range_low).clip(lower=1e-8) * cfg.zone_pct_of_range
        res_bottom = range_high - zone
        sup_top = range_low + zone
        near_res = df["close"] >= res_bottom
        near_sup = df["close"] <= sup_top

        i = n - 1
        cur_rsi = float(rsi.iloc[i])
        cur_price = float(close[i])

        div_state = "BUY" if buy3.iloc[i] else "SELL" if sell3.iloc[i] else (
            "BUY" if raw_buy_s.iloc[i] else "SELL" if raw_sell_s.iloc[i] else "NONE"
        )

        exec_state = self._exec_state(buy_entry.iloc[i], sell_entry.iloc[i], buy3.iloc[i], sell3.iloc[i])

        stop, tp1, tp2 = self._risk_levels(
            exec_state,
            cur_price,
            buy_setup_low.iloc[i] if buy_entry.iloc[i] else np.nan,
            sell_setup_high.iloc[i] if sell_entry.iloc[i] else np.nan,
            cfg,
        )

        gem_score = self._local_score(
            in_ob.iloc[i], in_os.iloc[i], raw_buy_s.iloc[i], raw_sell_s.iloc[i],
            bull_candle.iloc[i], bear_candle.iloc[i], buy_gem_raw.iloc[i] or sell_gem_raw.iloc[i],
        )

        ts = df.index[i]
        if not isinstance(ts, datetime):
            ts = datetime.utcnow()

        rec = self._recommendation(
            buy_gem.iloc[i], sell_gem.iloc[i], buy3.iloc[i], sell3.iloc[i],
            buy_entry.iloc[i], sell_entry.iloc[i], div_state,
        )

        return GEMAnalysis(
            symbol=symbol,
            timestamp=ts,
            price=cur_price,
            rsi=cur_rsi,
            in_oversold=bool(in_os.iloc[i]),
            in_overbought=bool(in_ob.iloc[i]),
            raw_buy_div=bool(raw_buy_s.iloc[i]),
            raw_sell_div=bool(raw_sell_s.iloc[i]),
            buy_setup=bool(buy3.iloc[i]),
            sell_setup=bool(sell3.iloc[i]),
            buy_entry=bool(buy_entry.iloc[i]),
            sell_entry=bool(sell_entry.iloc[i]),
            exec_state=exec_state,
            bull_candle=bool(bull_candle.iloc[i]),
            bear_candle=bool(bear_candle.iloc[i]),
            buy_gem=bool(buy_gem.iloc[i]),
            sell_gem=bool(sell_gem.iloc[i]),
            divergence_state=div_state,
            buy_div_events=int(buy_count.iloc[i]),
            sell_div_events=int(sell_count.iloc[i]),
            near_support=bool(near_sup.iloc[i]),
            near_resistance=bool(near_res.iloc[i]),
            stop_price=stop,
            tp1_price=tp1,
            tp2_price=tp2,
            gem_score=gem_score,
            recommendation=rec,
            data_source=data_source,
        )

    @staticmethod
    def _normalize_ohlcv(df: pd.DataFrame) -> Optional[pd.DataFrame]:
        if df is None or df.empty:
            return None
        out = df.copy()
        if isinstance(out.columns, pd.MultiIndex):
            out.columns = out.columns.get_level_values(0)
        out.columns = [str(c).lower() for c in out.columns]
        for col in ("open", "high", "low", "close", "volume"):
            if col not in out.columns:
                return None
        out = out[["open", "high", "low", "close", "volume"]].apply(pd.to_numeric, errors="coerce")
        out = out.dropna(subset=["open", "high", "low", "close"])
        return out if len(out) > 0 else None

    def _simulate_long_execution(self, df: pd.DataFrame, buy3: pd.Series):
        cfg = self.config
        n = len(df)
        buy_entry = pd.Series(False, index=df.index)
        setup_low_at_entry = pd.Series(np.nan, index=df.index)

        active_bar = -1
        setup_high = np.nan
        setup_low = np.nan

        for i in range(n):
            if buy3.iloc[i]:
                active_bar = i
                setup_high = df["high"].iloc[i]
                setup_low = df["low"].iloc[i]

            if active_bar >= 0 and i > active_bar and i - active_bar <= cfg.signal_life_bars:
                if df["close"].iloc[i] > setup_high:
                    buy_entry.iloc[i] = True
                    setup_low_at_entry.iloc[i] = setup_low
                    active_bar = -1
                elif df["low"].iloc[i] < setup_low:
                    active_bar = -1
            elif active_bar >= 0 and i - active_bar > cfg.signal_life_bars:
                active_bar = -1

        return buy_entry, setup_low_at_entry

    def _simulate_short_execution(self, df: pd.DataFrame, sell3: pd.Series):
        cfg = self.config
        n = len(df)
        sell_entry = pd.Series(False, index=df.index)
        setup_high_at_entry = pd.Series(np.nan, index=df.index)

        active_bar = -1
        setup_high = np.nan
        setup_low = np.nan

        for i in range(n):
            if sell3.iloc[i]:
                active_bar = i
                setup_high = df["high"].iloc[i]
                setup_low = df["low"].iloc[i]

            if active_bar >= 0 and i > active_bar and i - active_bar <= cfg.signal_life_bars:
                if df["close"].iloc[i] < setup_low:
                    sell_entry.iloc[i] = True
                    setup_high_at_entry.iloc[i] = setup_high
                    active_bar = -1
                elif df["high"].iloc[i] > setup_high:
                    active_bar = -1
            elif active_bar >= 0 and i - active_bar > cfg.signal_life_bars:
                active_bar = -1

        return sell_entry, setup_high_at_entry

    @staticmethod
    def _gem_confluence(in_os, in_ob, buy_div, sell_div, bull, bear, window: int):
        def bars_since(cond: pd.Series) -> pd.Series:
            idx = np.where(cond.values, np.arange(len(cond)), np.nan)
            last = pd.Series(idx, index=cond.index).ffill()
            cur = np.arange(len(cond))
            return pd.Series(cur - last.values, index=cond.index)

        recent_os = bars_since(in_os) <= window
        recent_ob = bars_since(in_ob) <= window
        recent_buy = bars_since(buy_div) <= window
        recent_sell = bars_since(sell_div) <= window
        recent_bull = bars_since(bull) <= window
        recent_bear = bars_since(bear) <= window

        buy_gem = recent_os & recent_buy & recent_bull
        sell_gem = recent_ob & recent_sell & recent_bear
        return buy_gem.fillna(False), sell_gem.fillna(False)

    @staticmethod
    def _exec_state(buy_entry: bool, sell_entry: bool, buy3: bool, sell3: bool) -> str:
        if buy_entry:
            return "TRIGGERED_LONG"
        if sell_entry:
            return "TRIGGERED_SHORT"
        if buy3:
            return "ARMED_LONG"
        if sell3:
            return "ARMED_SHORT"
        return "WAIT"

    @staticmethod
    def _risk_levels(exec_state, price, buy_low, sell_high, cfg: GEMConfig):
        if exec_state == "TRIGGERED_LONG" and not np.isnan(buy_low):
            stop = min(buy_low * (1 - cfg.stop_buffer_pct / 100), price * (1 - cfg.stop_buffer_pct / 100))
            risk = max(price - stop, 1e-8)
            return stop, price + risk * cfg.tp1_rr, price + risk * cfg.tp2_rr
        if exec_state == "TRIGGERED_SHORT" and not np.isnan(sell_high):
            stop = max(sell_high * (1 + cfg.stop_buffer_pct / 100), price * (1 + cfg.stop_buffer_pct / 100))
            risk = max(stop - price, 1e-8)
            return stop, price - risk * cfg.tp1_rr, price - risk * cfg.tp2_rr
        return None, None, None

    @staticmethod
    def _local_score(in_ob, in_os, raw_buy, raw_sell, bull, bear, gem) -> int:
        score = 0
        if in_ob or in_os:
            score += 1
        if raw_buy or raw_sell:
            score += 1
        if bull or bear:
            score += 1
        if gem:
            score += 1
        return score

    @staticmethod
    def _recommendation(buy_gem, sell_gem, buy3, sell3, buy_entry, sell_entry, div_state) -> str:
        if buy_gem:
            return "EMERALD GEM — oversold + bullish divergence + bullish candle aligned"
        if sell_gem:
            return "RUBY GEM — overbought + bearish divergence + bearish candle aligned"
        if buy_entry:
            return "LONG ENTRY — price broke above setup high after 3rd bullish divergence"
        if sell_entry:
            return "SHORT ENTRY — price broke below setup low after 3rd bearish divergence"
        if buy3:
            return "BUY SETUP — 3rd bullish RSI divergence in oversold zone"
        if sell3:
            return "SELL SETUP — 3rd bearish RSI divergence in overbought zone"
        if div_state == "BUY":
            return "Bullish divergence event — watch for setup count"
        if div_state == "SELL":
            return "Bearish divergence event — watch for setup count"
        return "No active GEM signal — monitoring"
