"""Signal Strength Analysis Module - Combines multiple indicators for signal quality assessment"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

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


class SignalStrengthAnalyzer:
    """Analyze and rate signal strength based on multiple factors"""
    
    def __init__(self, rsi_period: int = 14, macd_fast: int = 12, macd_slow: int = 26, macd_signal: int = 9):
        """
        Initialize signal strength analyzer.
        
        Args:
            rsi_period: RSI calculation period
            macd_fast: MACD fast EMA period
            macd_slow: MACD slow EMA period
            macd_signal: MACD signal line period
        """
        self.rsi_period = rsi_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
    
    def analyze(self, symbol: str, prices: pd.Series, rsi: pd.Series, volume: pd.Series) -> Optional[SignalStrength]:
        """
        Comprehensive signal strength analysis.
        
        Args:
            symbol: Stock symbol
            prices: Series of close prices
            rsi: Series of RSI values
            volume: Series of volume data
            
        Returns:
            SignalStrength object or None if analysis fails
        """
        try:
            if prices.empty or rsi.empty or volume.empty:
                logger.warning(f"{symbol}: Empty data for signal analysis")
                return None
            
            # Get latest values
            current_price = float(prices.iloc[-1])
            current_rsi = float(rsi.dropna().iloc[-1]) if not rsi.dropna().empty else None
            
            if pd.isna(current_price) or pd.isna(current_rsi):
                return None
            
            # 1. RSI Analysis
            rsi_signal = self._get_rsi_signal(current_rsi)
            rsi_divergence = self._detect_rsi_divergence(prices, rsi)
            
            # 2. MACD Analysis
            macd_line, signal_line, histogram = self._calculate_macd(prices)
            macd_histogram = float(histogram.iloc[-1]) if not histogram.empty else 0
            macd_weakening = self._detect_macd_weakening(histogram)
            macd_divergence = self._detect_macd_divergence(prices, macd_line)
            
            # 3. Volume Analysis
            volume_divergence = self._detect_volume_divergence(prices, volume)
            
            # 4. Key Level Analysis
            key_level_nearby, key_level_distance = self._detect_key_level(prices)
            
            # 5. Wick Analysis
            wick_present, wick_strength = self._detect_wick(prices)
            
            # 6. Calculate overall signal strength
            factors = self._count_aligned_factors(
                rsi_signal, rsi_divergence, macd_weakening, macd_divergence,
                volume_divergence, key_level_nearby, wick_present
            )
            
            signal_strength, confidence, recommendation = self._calculate_signal_strength(
                rsi_signal, rsi_divergence, macd_weakening, macd_divergence,
                volume_divergence, key_level_nearby, wick_present, factors
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
                recommendation=recommendation
            )
            
        except Exception as e:
            logger.error(f"{symbol}: Error in signal strength analysis: {e}")
            return None
    
    @staticmethod
    def _get_rsi_signal(rsi: float, oversold: int = 30, overbought: int = 70) -> str:
        """Get RSI signal type."""
        if rsi < oversold:
            return "OVERSOLD"
        elif rsi > overbought:
            return "OVERBOUGHT"
        else:
            return "NEUTRAL"
    
    @staticmethod
    def _detect_rsi_divergence(prices: pd.Series, rsi: pd.Series, lookback: int = 10) -> bool:
        """
        Detect RSI divergence.
        Bullish: Price makes lower low, RSI makes higher low
        Bearish: Price makes higher high, RSI makes lower high
        """
        try:
            if len(prices) < lookback or len(rsi) < lookback:
                return False
            
            prices_clean = prices.dropna()
            rsi_clean = rsi.dropna()
            
            if len(prices_clean) < lookback or len(rsi_clean) < lookback:
                return False
            
            # Check last lookback bars
            recent_prices = prices_clean.tail(lookback).values
            recent_rsi = rsi_clean.tail(lookback).values
            
            # Find local lows/highs
            min_price_idx = np.argmin(recent_prices)
            min_rsi_idx = np.argmin(recent_rsi)
            
            max_price_idx = np.argmax(recent_prices)
            max_rsi_idx = np.argmax(recent_rsi)
            
            # Bullish divergence: price low earlier, RSI low later (but higher)
            bullish = (min_price_idx < min_rsi_idx and 
                      recent_rsi[min_rsi_idx] > recent_rsi[min_price_idx])
            
            # Bearish divergence: price high earlier, RSI high later (but lower)
            bearish = (max_price_idx < max_rsi_idx and 
                      recent_rsi[max_rsi_idx] < recent_rsi[max_price_idx])
            
            return bullish or bearish
        except Exception:
            return False
    
    def _calculate_macd(self, prices: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate MACD, Signal line, and Histogram."""
        try:
            prices = pd.to_numeric(prices, errors='coerce').dropna()
            
            if len(prices) < self.macd_slow + 1:
                return pd.Series(), pd.Series(), pd.Series()
            
            ema_fast = prices.ewm(span=self.macd_fast, adjust=False).mean()
            ema_slow = prices.ewm(span=self.macd_slow, adjust=False).mean()
            
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=self.macd_signal, adjust=False).mean()
            histogram = macd_line - signal_line
            
            return macd_line, signal_line, histogram
        except Exception:
            return pd.Series(), pd.Series(), pd.Series()
    
    @staticmethod
    def _detect_macd_weakening(histogram: pd.Series, lookback: int = 5) -> bool:
        """
        Detect MACD histogram weakening.
        For bearish move: histogram should be decreasing (becoming less negative)
        For bullish move: histogram should be increasing (becoming more positive)
        """
        try:
            if histogram.empty or len(histogram) < lookback:
                return False
            
            hist_clean = histogram.dropna().tail(lookback).values
            if len(hist_clean) < 2:
                return False
            
            # Check if histogram values are getting closer to zero (weakening)
            recent_abs = np.abs(hist_clean[-1])
            previous_abs = np.abs(hist_clean[-2])
            
            # Weakening = getting smaller in absolute value
            return recent_abs < previous_abs * 0.95  # 5% threshold
        except Exception:
            return False
    
    @staticmethod
    def _detect_macd_divergence(prices: pd.Series, macd_line: pd.Series, lookback: int = 10) -> bool:
        """
        Detect MACD divergence similar to RSI divergence.
        """
        try:
            if len(prices) < lookback or len(macd_line) < lookback:
                return False
            
            prices_clean = prices.dropna().tail(lookback).values
            macd_clean = macd_line.dropna().tail(lookback).values
            
            if len(prices_clean) < lookback or len(macd_clean) < lookback:
                return False
            
            # Find local lows/highs
            min_price_idx = np.argmin(prices_clean)
            min_macd_idx = np.argmin(macd_clean)
            
            max_price_idx = np.argmax(prices_clean)
            max_macd_idx = np.argmax(macd_clean)
            
            # Bullish divergence
            bullish = (min_price_idx < min_macd_idx and 
                      macd_clean[min_macd_idx] > macd_clean[min_price_idx])
            
            # Bearish divergence
            bearish = (max_price_idx < max_macd_idx and 
                      macd_clean[max_macd_idx] < macd_clean[max_price_idx])
            
            return bullish or bearish
        except Exception:
            return False
    
    @staticmethod
    def _detect_volume_divergence(prices: pd.Series, volume: pd.Series, lookback: int = 5) -> bool:
        """
        Detect volume divergence.
        Strong signal: Price moving but volume declining or vice versa.
        """
        try:
            if len(prices) < lookback or len(volume) < lookback:
                return False
            
            prices_clean = prices.dropna().tail(lookback)
            volume_clean = volume.dropna().tail(lookback)
            
            if len(prices_clean) < lookback or len(volume_clean) < lookback:
                return False
            
            # Calculate price change and volume change
            price_change = prices_clean.iloc[-1] - prices_clean.iloc[-2]
            volume_change = volume_clean.iloc[-1] - volume_clean.iloc[-2]
            
            # Divergence: price strong movement but volume weak, or vice versa
            price_strong = abs(price_change / prices_clean.iloc[-2]) > 0.02  # 2% move
            volume_weak = volume_change < 0 or volume_clean.iloc[-1] < volume_clean.mean()
            
            price_weak = abs(price_change / prices_clean.iloc[-2]) < 0.01  # <1% move
            volume_strong = volume_change > 0 and volume_clean.iloc[-1] > volume_clean.mean()
            
            divergence = (price_strong and volume_weak) or (price_weak and volume_strong)
            return divergence
        except Exception:
            return False
    
    @staticmethod
    def _detect_key_level(prices: pd.Series, lookback: int = 20) -> Tuple[bool, float]:
        """
        Detect if price is near key level (support/resistance).
        Returns: (is_near_level, distance_percentage)
        """
        try:
            if len(prices) < lookback:
                return False, 0.0
            
            prices_clean = prices.dropna()
            current_price = prices_clean.iloc[-1]
            
            # Find support (recent low) and resistance (recent high)
            recent_high = prices_clean.tail(lookback).max()
            recent_low = prices_clean.tail(lookback).min()
            
            # Distance to key levels (in percentage)
            dist_to_high = abs(current_price - recent_high) / recent_high * 100
            dist_to_low = abs(current_price - recent_low) / recent_low * 100
            
            min_distance = min(dist_to_high, dist_to_low)
            
            # Key level nearby if within 1.5% of recent high/low
            is_nearby = min_distance < 1.5
            
            return is_nearby, min_distance
        except Exception:
            return False, 0.0
    
    @staticmethod
    def _detect_wick(prices: pd.Series, lookback: int = 1) -> Tuple[bool, str]:
        """
        Detect if recent candle(s) have significant wicks.
        Wick suggests rejection from level and potential reversal.
        """
        try:
            if len(prices) < lookback + 1:
                return False, "WEAK"
            
            prices_clean = prices.dropna()
            current_price = prices_clean.iloc[-1]
            previous_high = prices_clean.tail(lookback + 1).max()
            previous_low = prices_clean.tail(lookback + 1).min()
            
            # Wick length as percentage
            total_range = previous_high - previous_low
            if total_range == 0:
                return False, "WEAK"
            
            # Check for wick (difference between high/low and close)
            wick_size_pct = abs(current_price - previous_high) / total_range * 100
            wick_size_pct += abs(current_price - previous_low) / total_range * 100
            
            wick_present = wick_size_pct > 20  # >20% of range is wick
            
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
    def _count_aligned_factors(rsi_signal: str, rsi_div: bool, macd_weak: bool, 
                               macd_div: bool, vol_div: bool, key_level: bool, 
                               wick: bool) -> int:
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
        if key_level:
            count += 1
        if wick:
            count += 1
        return count
    
    @staticmethod
    def _calculate_signal_strength(rsi_signal: str, rsi_div: bool, macd_weak: bool,
                                   macd_div: bool, vol_div: bool, key_level: bool,
                                   wick: bool, factors: int) -> Tuple[str, float, str]:
        """
        Calculate overall signal strength.
        
        Returns:
            Tuple of (signal_strength, confidence, recommendation)
        """
        # Base scoring
        score = 0
        
        # Factor 1: RSI extremes (oversold/overbought)
        if rsi_signal != "NEUTRAL":
            score += 1
        
        # Factor 2: RSI divergence (strong)
        if rsi_div:
            score += 2
        
        # Factor 3: MACD weakening (medium)
        if macd_weak:
            score += 1
        
        # Factor 4: MACD divergence (strong)
        if macd_div:
            score += 2
        
        # Factor 5: Volume divergence (medium)
        if vol_div:
            score += 1.5
        
        # Factor 6: Key level nearby (medium)
        if key_level:
            score += 1.5
        
        # Factor 7: Wick present (weak)
        if wick:
            score += 0.5
        
        # Determine signal strength
        if score < 1.5:
            signal = "WEAK"
            confidence = 0.3
            rec = "Observation only - weak signal"
        elif score < 3:
            signal = "MEDIUM"
            confidence = 0.5
            rec = "Good warning - monitor closely"
        elif score < 5:
            signal = "STRONG"
            confidence = 0.7
            rec = "Strong signal - consider entry"
        elif score < 7:
            signal = "VERY_STRONG"
            confidence = 0.82
            rec = "Very strong signal - good entry opportunity"
        else:
            signal = "PREMIUM_WARNING"
            confidence = 0.92
            rec = "Premium signal - excellent entry setup"
        
        return signal, confidence, rec
