"""Signal Strength Analysis Module - Combines multiple indicators for signal quality assessment"""

import logging
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class SignalStrength:
    """Data class for signal strength assessment"""
    symbol: str
    rsi_value: float
    rsi_signal: str  # OVERSOLD, OVERBOUGHT, NEUTRAL
    rsi_divergence: bool

    macd_histogram: float
    macd_weakening: bool
    macd_divergence: bool

    volume_divergence: bool

    key_level_nearby: bool
    key_level_distance_pct: float

    wick_present: bool
    wick_strength: str  # WEAK, MEDIUM, STRONG

    signal_strength: str  # WEAK, MEDIUM, STRONG, VERY_STRONG, PREMIUM_WARNING
    confidence: float  # 0-1
    factors_count: int  # How many factors aligned
    recommendation: str
    divergence_bias: str = "NONE"
    macd_divergence_bias: str = "NONE"
    quality_score: int = 0
    premium_entry: bool = False
    volume_spike: bool = False
    mtf_alignment: bool = False
    zone_confirmed: bool = False
    rebound_confirmed: bool = False
    adx_value: float = 0.0
    adx_filter: bool = False
    volatility_ok: bool = False
    recent_rejection: bool = False
    recent_swing_distance: int = 0
    risk_reward_ratio: float = 0.0


class SignalStrengthAnalyzer:
    """Analyze and rate signal strength based on multiple factors"""

    def __init__(self, rsi_period: int = 14, macd_fast: int = 12, macd_slow: int = 26, macd_signal: int = 9):
        self.rsi_period = rsi_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal

    def analyze(self, symbol: str, prices: pd.Series, rsi: pd.Series, volume: pd.Series,
                market_data: Optional[pd.DataFrame] = None) -> Optional[SignalStrength]:
        """Comprehensive signal strength analysis."""
        try:
            if prices.empty or rsi.empty or volume.empty:
                logger.warning(f"{symbol}: Empty data for signal analysis")
                return None

            current_price = float(prices.iloc[-1])
            current_rsi = float(rsi.dropna().iloc[-1]) if not rsi.dropna().empty else None

            if pd.isna(current_price) or pd.isna(current_rsi):
                return None

            rsi_signal = self._get_rsi_signal(current_rsi)
            divergence_bias = self._detect_rsi_divergence_type(prices, rsi)
            rsi_divergence = divergence_bias != "NONE"

            macd_line, signal_line, histogram = self._calculate_macd(prices)
            macd_histogram = float(histogram.iloc[-1]) if not histogram.empty else 0.0
            macd_weakening = self._detect_macd_weakening(histogram)
            macd_divergence_bias = self._detect_macd_divergence_type(prices, macd_line)
            macd_divergence = macd_divergence_bias != "NONE"

            volume_divergence = self._detect_volume_divergence(prices, volume)
            volume_spike = self._detect_volume_spike(volume)
            key_level_nearby, key_level_distance = self._detect_key_level(prices)

            trade_bias = self._resolve_trade_bias(divergence_bias, rsi_signal)
            zone_confirmed = self._detect_zone_persistence(rsi, trade_bias)
            rebound_confirmed = self._detect_rsi_rebound(rsi, trade_bias)
            mtf_alignment = self._detect_mtf_alignment(prices, rsi, trade_bias)

            normalized_market_data = self._normalize_market_data(market_data)
            wick_present, wick_strength = self._detect_wick(normalized_market_data, prices)
            adx_value = self._calculate_adx(normalized_market_data)
            adx_filter = adx_value >= 18
            volatility_ok = self._detect_volatility_ok(normalized_market_data)
            recent_rejection, recent_swing_distance = self._detect_recent_rejection(
                normalized_market_data, trade_bias
            )
            risk_reward_ratio = self._estimate_risk_reward(normalized_market_data, trade_bias)

            factors = self._count_aligned_factors(
                rsi_signal, rsi_divergence, macd_weakening, macd_divergence,
                volume_divergence, volume_spike, key_level_nearby, wick_present,
                zone_confirmed, rebound_confirmed, mtf_alignment, adx_filter,
                volatility_ok, risk_reward_ratio
            )

            signal_strength, confidence, recommendation, quality_score, premium_entry = self._calculate_signal_strength(
                rsi_signal, rsi_divergence, macd_weakening, macd_divergence,
                volume_divergence, volume_spike, key_level_nearby, wick_present,
                zone_confirmed, rebound_confirmed, mtf_alignment, adx_filter,
                volatility_ok, recent_rejection, risk_reward_ratio, factors
            )

            return SignalStrength(
                symbol=symbol,
                rsi_value=round(current_rsi, 2),
                rsi_signal=rsi_signal,
                rsi_divergence=rsi_divergence,
                macd_histogram=round(macd_histogram, 4),
                macd_weakening=macd_weakening,
                macd_divergence=macd_divergence,
                volume_divergence=volume_divergence,
                key_level_nearby=key_level_nearby,
                key_level_distance_pct=round(key_level_distance, 2),
                wick_present=wick_present,
                wick_strength=wick_strength,
                signal_strength=signal_strength,
                confidence=round(confidence, 3),
                factors_count=factors,
                recommendation=recommendation,
                divergence_bias=divergence_bias,
                macd_divergence_bias=macd_divergence_bias,
                quality_score=quality_score,
                premium_entry=premium_entry,
                volume_spike=volume_spike,
                mtf_alignment=mtf_alignment,
                zone_confirmed=zone_confirmed,
                rebound_confirmed=rebound_confirmed,
                adx_value=round(adx_value, 2),
                adx_filter=adx_filter,
                volatility_ok=volatility_ok,
                recent_rejection=recent_rejection,
                recent_swing_distance=recent_swing_distance,
                risk_reward_ratio=round(risk_reward_ratio, 2)
            )

        except Exception as e:
            logger.error(f"{symbol}: Error in signal strength analysis: {e}")
            return None

    @staticmethod
    def _get_rsi_signal(rsi: float, oversold: int = 30, overbought: int = 70) -> str:
        """Get RSI signal type."""
        if rsi < oversold:
            return "OVERSOLD"
        if rsi > overbought:
            return "OVERBOUGHT"
        return "NEUTRAL"

    @staticmethod
    def _detect_rsi_divergence(prices: pd.Series, rsi: pd.Series, lookback: int = 10) -> bool:
        return SignalStrengthAnalyzer._detect_rsi_divergence_type(prices, rsi, lookback) != "NONE"

    @staticmethod
    def _detect_rsi_divergence_type(prices: pd.Series, rsi: pd.Series, lookback: int = 10) -> str:
        """Detect divergence direction in the latest lookback window."""
        try:
            if len(prices) < lookback or len(rsi) < lookback:
                return "NONE"

            recent_prices = prices.dropna().tail(lookback).reset_index(drop=True)
            recent_rsi = rsi.dropna().tail(lookback).reset_index(drop=True)

            if len(recent_prices) < lookback or len(recent_rsi) < lookback:
                return "NONE"

            split = max(2, lookback // 2)
            earlier_prices = recent_prices.iloc[:split]
            later_prices = recent_prices.iloc[split:]
            earlier_rsi = recent_rsi.iloc[:split]
            later_rsi = recent_rsi.iloc[split:]

            bullish = (
                later_prices.min() < earlier_prices.min()
                and later_rsi.min() > earlier_rsi.min()
            )
            bearish = (
                later_prices.max() > earlier_prices.max()
                and later_rsi.max() < earlier_rsi.max()
            )

            if bullish and not bearish:
                return "BULLISH"
            if bearish and not bullish:
                return "BEARISH"
            return "NONE"
        except Exception:
            return "NONE"

    def _calculate_macd(self, prices: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD, Signal line, and Histogram."""
        try:
            prices = pd.to_numeric(prices, errors='coerce').dropna()
            if len(prices) < self.macd_slow + 1:
                return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)

            ema_fast = prices.ewm(span=self.macd_fast, adjust=False).mean()
            ema_slow = prices.ewm(span=self.macd_slow, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=self.macd_signal, adjust=False).mean()
            histogram = macd_line - signal_line
            return macd_line, signal_line, histogram
        except Exception:
            return pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)

    @staticmethod
    def _detect_macd_weakening(histogram: pd.Series, lookback: int = 5) -> bool:
        """Detect MACD histogram weakening."""
        try:
            if histogram.empty or len(histogram) < lookback:
                return False
            hist_clean = histogram.dropna().tail(lookback).values
            if len(hist_clean) < 2:
                return False
            recent_abs = np.abs(hist_clean[-1])
            previous_abs = np.abs(hist_clean[-2])
            return recent_abs < previous_abs * 0.95
        except Exception:
            return False

    @staticmethod
    def _detect_macd_divergence(prices: pd.Series, macd_line: pd.Series, lookback: int = 10) -> bool:
        return SignalStrengthAnalyzer._detect_macd_divergence_type(prices, macd_line, lookback) != "NONE"

    @staticmethod
    def _detect_macd_divergence_type(prices: pd.Series, macd_line: pd.Series, lookback: int = 10) -> str:
        """Detect MACD divergence direction in the latest lookback window."""
        try:
            if len(prices) < lookback or len(macd_line) < lookback:
                return "NONE"

            recent_prices = prices.dropna().tail(lookback).reset_index(drop=True)
            recent_macd = macd_line.dropna().tail(lookback).reset_index(drop=True)

            if len(recent_prices) < lookback or len(recent_macd) < lookback:
                return "NONE"

            split = max(2, lookback // 2)
            bullish = (
                recent_prices.iloc[split:].min() < recent_prices.iloc[:split].min()
                and recent_macd.iloc[split:].min() > recent_macd.iloc[:split].min()
            )
            bearish = (
                recent_prices.iloc[split:].max() > recent_prices.iloc[:split].max()
                and recent_macd.iloc[split:].max() < recent_macd.iloc[:split].max()
            )

            if bullish and not bearish:
                return "BULLISH"
            if bearish and not bullish:
                return "BEARISH"
            return "NONE"
        except Exception:
            return "NONE"

    @staticmethod
    def _detect_volume_divergence(prices: pd.Series, volume: pd.Series, lookback: int = 5) -> bool:
        """Detect volume divergence."""
        try:
            if len(prices) < lookback or len(volume) < lookback:
                return False

            prices_clean = prices.dropna().tail(lookback)
            volume_clean = volume.dropna().tail(lookback)

            if len(prices_clean) < lookback or len(volume_clean) < lookback:
                return False

            price_change = prices_clean.iloc[-1] - prices_clean.iloc[-2]
            volume_change = volume_clean.iloc[-1] - volume_clean.iloc[-2]

            price_strong = abs(price_change / prices_clean.iloc[-2]) > 0.02
            volume_weak = volume_change < 0 or volume_clean.iloc[-1] < volume_clean.mean()
            price_weak = abs(price_change / prices_clean.iloc[-2]) < 0.01
            volume_strong = volume_change > 0 and volume_clean.iloc[-1] > volume_clean.mean()
            return (price_strong and volume_weak) or (price_weak and volume_strong)
        except Exception:
            return False

    @staticmethod
    def _detect_volume_spike(volume: pd.Series, period: int = 20, multiplier: float = 1.5) -> bool:
        """Detect whether current volume is a meaningful spike above average."""
        try:
            volume_clean = pd.to_numeric(volume, errors='coerce').dropna()
            if len(volume_clean) < period:
                return False
            baseline = float(volume_clean.tail(period).mean())
            return baseline > 0 and float(volume_clean.iloc[-1]) > baseline * multiplier
        except Exception:
            return False

    @staticmethod
    def _detect_key_level(prices: pd.Series, lookback: int = 20) -> Tuple[bool, float]:
        """Detect if price is near key level (support/resistance)."""
        try:
            if len(prices) < lookback:
                return False, 0.0
            prices_clean = prices.dropna()
            current_price = prices_clean.iloc[-1]
            recent_high = prices_clean.tail(lookback).max()
            recent_low = prices_clean.tail(lookback).min()
            dist_to_high = abs(current_price - recent_high) / recent_high * 100
            dist_to_low = abs(current_price - recent_low) / recent_low * 100
            min_distance = min(dist_to_high, dist_to_low)
            return min_distance < 1.5, min_distance
        except Exception:
            return False, 0.0

    @staticmethod
    def _detect_wick(ohlc: Optional[pd.DataFrame], prices: pd.Series, lookback: int = 1) -> Tuple[bool, str]:
        """Detect if recent candle(s) have significant wicks."""
        try:
            if ohlc is None or ohlc.empty:
                if len(prices) < lookback + 1:
                    return False, "WEAK"
                prices_clean = prices.dropna()
                current_price = prices_clean.iloc[-1]
                previous_high = prices_clean.tail(lookback + 1).max()
                previous_low = prices_clean.tail(lookback + 1).min()
                total_range = previous_high - previous_low
                if total_range == 0:
                    return False, "WEAK"
                wick_size_pct = (
                    abs(current_price - previous_high) + abs(current_price - previous_low)
                ) / total_range * 100
            else:
                candle = ohlc.tail(1).iloc[0]
                total_range = candle['high'] - candle['low']
                if total_range == 0:
                    return False, "WEAK"
                upper_wick = candle['high'] - max(candle['open'], candle['close'])
                lower_wick = min(candle['open'], candle['close']) - candle['low']
                wick_size_pct = max(upper_wick, lower_wick) / total_range * 100

            wick_present = wick_size_pct > 20
            if wick_size_pct < 20:
                wick_strength = "WEAK"
            elif wick_size_pct < 40:
                wick_strength = "MEDIUM"
            else:
                wick_strength = "STRONG"
            return wick_present, wick_strength
        except Exception:
            return False, "WEAK"

    @staticmethod
    def _resolve_trade_bias(divergence_bias: str, rsi_signal: str) -> str:
        """Resolve trade direction from divergence and RSI state."""
        if divergence_bias in {"BULLISH", "BEARISH"}:
            return divergence_bias
        if rsi_signal == "OVERSOLD":
            return "BULLISH"
        if rsi_signal == "OVERBOUGHT":
            return "BEARISH"
        return "NONE"

    @staticmethod
    def _detect_zone_persistence(rsi: pd.Series, trade_bias: str,
                                 oversold: int = 30, overbought: int = 70,
                                 bars: int = 3) -> bool:
        """Require RSI to stay in the extreme zone for several bars."""
        try:
            rsi_clean = pd.to_numeric(rsi, errors='coerce').dropna()
            if len(rsi_clean) < bars:
                return False
            recent = rsi_clean.tail(bars)
            if trade_bias == "BULLISH":
                return bool((recent <= oversold + 2).all())
            if trade_bias == "BEARISH":
                return bool((recent >= overbought - 2).all())
            return False
        except Exception:
            return False

    @staticmethod
    def _detect_rsi_rebound(rsi: pd.Series, trade_bias: str,
                            lookback: int = 6, min_points: float = 4.0) -> bool:
        """Confirm RSI has bounced enough from its recent extreme."""
        try:
            rsi_clean = pd.to_numeric(rsi, errors='coerce').dropna()
            if len(rsi_clean) < lookback:
                return False
            recent = rsi_clean.tail(lookback)
            current = float(recent.iloc[-1])
            if trade_bias == "BULLISH":
                return current - float(recent.min()) >= min_points
            if trade_bias == "BEARISH":
                return float(recent.max()) - current >= min_points
            return False
        except Exception:
            return False

    @staticmethod
    def _detect_mtf_alignment(prices: pd.Series, rsi: pd.Series, trade_bias: str) -> bool:
        """Approximate multi-timeframe confluence with short/medium/long windows."""
        try:
            prices_clean = pd.to_numeric(prices, errors='coerce').dropna()
            rsi_clean = pd.to_numeric(rsi, errors='coerce').dropna()
            if len(prices_clean) < 24 or len(rsi_clean) < 24:
                return False
            short_price = prices_clean.tail(4).mean()
            medium_price = prices_clean.tail(8).mean()
            short_rsi = rsi_clean.tail(4).mean()
            medium_rsi = rsi_clean.tail(12).mean()
            long_rsi = rsi_clean.tail(24).mean()
            if trade_bias == "BULLISH":
                return short_price >= medium_price and short_rsi > medium_rsi >= long_rsi - 5
            if trade_bias == "BEARISH":
                return short_price <= medium_price and short_rsi < medium_rsi <= long_rsi + 5
            return False
        except Exception:
            return False

    @staticmethod
    def _normalize_market_data(market_data: Optional[pd.DataFrame]) -> pd.DataFrame:
        """Normalize OHLCV column casing when full market data is available."""
        if market_data is None or market_data.empty:
            return pd.DataFrame()
        normalized = market_data.copy()
        normalized.columns = [str(col).lower() for col in normalized.columns]
        required = {'open', 'high', 'low', 'close'}
        if not required.issubset(set(normalized.columns)):
            return pd.DataFrame()
        return normalized

    @staticmethod
    def _calculate_atr(ohlc: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate average true range."""
        if ohlc is None or ohlc.empty:
            return pd.Series(dtype=float)
        high = pd.to_numeric(ohlc['high'], errors='coerce')
        low = pd.to_numeric(ohlc['low'], errors='coerce')
        close = pd.to_numeric(ohlc['close'], errors='coerce')
        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)
        return tr.rolling(window=period, min_periods=period).mean()

    @classmethod
    def _calculate_adx(cls, ohlc: pd.DataFrame, period: int = 14) -> float:
        """Calculate ADX as a trend-strength filter."""
        try:
            if ohlc is None or ohlc.empty or len(ohlc) < period * 2:
                return 0.0
            high = pd.to_numeric(ohlc['high'], errors='coerce')
            low = pd.to_numeric(ohlc['low'], errors='coerce')
            up_move = high.diff()
            down_move = -low.diff()
            plus_dm = pd.Series(
                np.where((up_move > down_move) & (up_move > 0), up_move, 0.0),
                index=ohlc.index
            )
            minus_dm = pd.Series(
                np.where((down_move > up_move) & (down_move > 0), down_move, 0.0),
                index=ohlc.index
            )
            atr = cls._calculate_atr(ohlc, period)
            if atr.empty or pd.isna(atr.iloc[-1]) or atr.iloc[-1] == 0:
                return 0.0
            plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
            minus_di = 100 * (minus_dm.rolling(period).mean() / atr)
            dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
            adx = dx.rolling(period).mean().dropna()
            return float(adx.iloc[-1]) if not adx.empty else 0.0
        except Exception:
            return 0.0

    @classmethod
    def _detect_volatility_ok(cls, ohlc: pd.DataFrame) -> bool:
        """Reject dead zones and volatility spikes using ATR."""
        try:
            atr_clean = cls._calculate_atr(ohlc).dropna()
            close = pd.to_numeric(ohlc['close'], errors='coerce').dropna() if ohlc is not None and not ohlc.empty else pd.Series(dtype=float)
            if len(atr_clean) < 20 or close.empty:
                return False
            current_atr = float(atr_clean.iloc[-1])
            atr_mean = float(atr_clean.tail(20).mean())
            current_close = float(close.iloc[-1])
            if atr_mean <= 0 or current_close <= 0:
                return False
            atr_ratio = current_atr / atr_mean
            atr_pct = current_atr / current_close
            return 0.7 <= atr_ratio <= 1.8 and 0.001 <= atr_pct <= 0.12
        except Exception:
            return False

    @classmethod
    def _detect_recent_rejection(cls, ohlc: pd.DataFrame, trade_bias: str,
                                 lookback: int = 6) -> Tuple[bool, int]:
        """Skip trades that appear too close to a fresh swing rejection."""
        try:
            if ohlc is None or ohlc.empty or trade_bias == "NONE" or len(ohlc) < lookback:
                return False, 0
            close = pd.to_numeric(ohlc['close'], errors='coerce').dropna().tail(lookback)
            if len(close) < lookback:
                return False, 0
            swing_offset = int(np.argmin(close.values)) if trade_bias == "BULLISH" else int(np.argmax(close.values))
            distance = len(close) - 1 - swing_offset
            return distance < 4, distance
        except Exception:
            return False, 0

    @classmethod
    def _estimate_risk_reward(cls, ohlc: pd.DataFrame, trade_bias: str,
                              lookback: int = 20) -> float:
        """Estimate risk/reward from recent swing structure and ATR."""
        try:
            if ohlc is None or ohlc.empty or trade_bias == "NONE" or len(ohlc) < lookback:
                return 0.0
            close = pd.to_numeric(ohlc['close'], errors='coerce').dropna()
            current_price = float(close.iloc[-1])
            atr = cls._calculate_atr(ohlc).dropna()
            if atr.empty:
                return 0.0
            current_atr = float(atr.iloc[-1])
            recent = ohlc.tail(lookback)
            recent_high = float(pd.to_numeric(recent['high'], errors='coerce').max())
            recent_low = float(pd.to_numeric(recent['low'], errors='coerce').min())
            if trade_bias == "BULLISH":
                stop = min(current_price - current_atr, recent_low)
                target = recent_high
                risk = current_price - stop
                reward = target - current_price
            else:
                stop = max(current_price + current_atr, recent_high)
                target = recent_low
                risk = stop - current_price
                reward = current_price - target
            return max(0.0, reward / risk) if risk > 0 else 0.0
        except Exception:
            return 0.0

    @staticmethod
    def _count_aligned_factors(rsi_signal: str, rsi_div: bool, macd_weak: bool,
                               macd_div: bool, vol_div: bool, volume_spike: bool,
                               key_level: bool, wick: bool, zone_confirmed: bool,
                               rebound_confirmed: bool, mtf_alignment: bool,
                               adx_filter: bool, volatility_ok: bool,
                               risk_reward_ratio: float) -> int:
        """Count how many factors align for the signal."""
        count = 0
        if rsi_signal != "NEUTRAL":
            count += 1
        if rsi_div:
            count += 1
        if macd_weak:
            count += 1
        if macd_div:
            count += 1
        if vol_div:
            count += 1
        if volume_spike:
            count += 1
        if key_level:
            count += 1
        if wick:
            count += 1
        if zone_confirmed:
            count += 1
        if rebound_confirmed:
            count += 1
        if mtf_alignment:
            count += 1
        if adx_filter:
            count += 1
        if volatility_ok:
            count += 1
        if risk_reward_ratio >= 1.5:
            count += 1
        return count

    @staticmethod
    def _calculate_signal_strength(rsi_signal: str, rsi_div: bool, macd_weak: bool,
                                   macd_div: bool, vol_div: bool, volume_spike: bool,
                                   key_level: bool, wick: bool, zone_confirmed: bool,
                                   rebound_confirmed: bool, mtf_alignment: bool,
                                   adx_filter: bool, volatility_ok: bool,
                                   recent_rejection: bool, risk_reward_ratio: float,
                                   factors: int) -> Tuple[str, float, str, int, bool]:
        """Calculate overall signal strength and premium eligibility."""
        score = 0.0
        if rsi_signal != "NEUTRAL":
            score += 10
        if rsi_div:
            score += 18
        if macd_weak:
            score += 7
        if macd_div:
            score += 10
        if vol_div:
            score += 6
        if volume_spike:
            score += 10
        if key_level:
            score += 6
        if wick:
            score += 5
        if zone_confirmed:
            score += 8
        if rebound_confirmed:
            score += 8
        if mtf_alignment:
            score += 12
        if adx_filter:
            score += 6
        if volatility_ok:
            score += 4
        if risk_reward_ratio >= 2:
            score += 10
        elif risk_reward_ratio >= 1.5:
            score += 8
        elif risk_reward_ratio >= 1.2:
            score += 4
        if recent_rejection:
            score -= 12
        if factors < 5:
            score -= 8

        quality_score = int(max(0, min(100, round(score))))
        premium_entry = (
            quality_score >= 70
            and rsi_div
            and volume_spike
            and mtf_alignment
            and adx_filter
            and volatility_ok
            and risk_reward_ratio >= 1.2
            and not recent_rejection
        )

        if quality_score < 40:
            signal = "WEAK"
            confidence = 0.3
            rec = "Observation only - weak signal"
        elif quality_score < 55:
            signal = "MEDIUM"
            confidence = 0.55
            rec = "Monitor closely - filters are still incomplete"
        elif quality_score < 70:
            signal = "STRONG"
            confidence = 0.7
            rec = "Strong setup forming - wait for extra confluence"
        elif quality_score < 85:
            signal = "VERY_STRONG"
            confidence = quality_score / 100
            rec = "High-quality setup - selective entry only"
        else:
            signal = "PREMIUM_WARNING"
            confidence = quality_score / 100
            rec = "Premium signal - confluence and risk/reward aligned"

        return signal, confidence, rec, quality_score, premium_entry
