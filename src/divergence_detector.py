"""Divergence Detection Module - Identifies bullish and bearish divergences"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Divergence:
    """Data class for divergence information"""
    type: str  # 'BULLISH' or 'BEARISH'
    price_low_1: float
    price_low_2: float
    rsi_low_1: float
    rsi_low_2: float
    bars_between: int
    strength: str  # 'WEAK', 'MEDIUM', 'STRONG'
    timestamp_1: pd.Timestamp
    timestamp_2: pd.Timestamp


class DivergenceDetector:
    """Detect bullish and bearish divergences between price and RSI"""

    def __init__(self, min_bars_apart: int = 5, max_bars_apart: int = 50):
        """
        Initialize divergence detector.
        
        Args:
            min_bars_apart: Minimum bars between divergence points
            max_bars_apart: Maximum bars between divergence points
        """
        self.min_bars_apart = min_bars_apart
        self.max_bars_apart = max_bars_apart

    def detect_bullish_divergence(self, prices: pd.Series, rsi: pd.Series) -> List[Divergence]:
        """
        Detect bullish divergence: Price makes lower low, RSI makes higher low.
        
        Args:
            prices: Series of price data
            rsi: Series of RSI values
            
        Returns:
            List of detected bullish divergences
        """
        # Validate inputs
        if not self._validate_series(prices, rsi):
            return []
        
        divergences = []
        
        try:
            # Find local lows in price
            price_lows = self._find_local_lows(prices)
            
            if len(price_lows) < 2:
                return []
            
            # Match price lows with RSI lows
            for i in range(len(price_lows) - 1):
                idx1 = price_lows[i]
                
                for j in range(i + 1, len(price_lows)):
                    idx2 = price_lows[j]
                    bars_between = idx2 - idx1
                    
                    if bars_between < self.min_bars_apart or bars_between > self.max_bars_apart:
                        continue
                    
                    # Check if price made lower low
                    try:
                        price_1 = float(prices.iloc[idx1])
                        price_2 = float(prices.iloc[idx2])
                        if pd.isna(price_1) or pd.isna(price_2) or price_2 >= price_1:
                            continue
                    except (ValueError, TypeError):
                        continue
                    
                    # Find corresponding RSI lows
                    rsi_idx1 = self._find_nearest_low(rsi, idx1, window=3)
                    rsi_idx2 = self._find_nearest_low(rsi, idx2, window=3)
                    
                    if rsi_idx1 is None or rsi_idx2 is None:
                        continue
                    
                    # Check if RSI made higher low
                    try:
                        rsi_1 = float(rsi.iloc[rsi_idx1])
                        rsi_2 = float(rsi.iloc[rsi_idx2])
                        if pd.isna(rsi_1) or pd.isna(rsi_2) or rsi_2 <= rsi_1:
                            continue
                    except (ValueError, TypeError):
                        continue
                    
                    strength = self._calculate_divergence_strength(price_1, price_2, rsi_1, rsi_2)
                    
                    divergences.append(Divergence(
                        type="BULLISH",
                        price_low_1=price_1,
                        price_low_2=price_2,
                        rsi_low_1=rsi_1,
                        rsi_low_2=rsi_2,
                        bars_between=bars_between,
                        strength=strength,
                        timestamp_1=prices.index[idx1],
                        timestamp_2=prices.index[idx2]
                    ))
        except Exception as e:
            logger.error(f"Error detecting bullish divergence: {e}")
        
        return divergences

    def detect_bearish_divergence(self, prices: pd.Series, rsi: pd.Series) -> List[Divergence]:
        """
        Detect bearish divergence: Price makes higher high, RSI makes lower high.
        
        Args:
            prices: Series of price data
            rsi: Series of RSI values
            
        Returns:
            List of detected bearish divergences
        """
        # Validate inputs
        if not self._validate_series(prices, rsi):
            return []
        
        divergences = []
        
        try:
            # Find local highs in price
            price_highs = self._find_local_highs(prices)
            
            if len(price_highs) < 2:
                return []
            
            # Match price highs with RSI highs
            for i in range(len(price_highs) - 1):
                idx1 = price_highs[i]
                
                for j in range(i + 1, len(price_highs)):
                    idx2 = price_highs[j]
                    bars_between = idx2 - idx1
                    
                    if bars_between < self.min_bars_apart or bars_between > self.max_bars_apart:
                        continue
                    
                    # Check if price made higher high
                    try:
                        price_1 = float(prices.iloc[idx1])
                        price_2 = float(prices.iloc[idx2])
                        if pd.isna(price_1) or pd.isna(price_2) or price_2 <= price_1:
                            continue
                    except (ValueError, TypeError):
                        continue
                    
                    # Find corresponding RSI highs
                    rsi_idx1 = self._find_nearest_high(rsi, idx1, window=3)
                    rsi_idx2 = self._find_nearest_high(rsi, idx2, window=3)
                    
                    if rsi_idx1 is None or rsi_idx2 is None:
                        continue
                    
                    # Check if RSI made lower high
                    try:
                        rsi_1 = float(rsi.iloc[rsi_idx1])
                        rsi_2 = float(rsi.iloc[rsi_idx2])
                        if pd.isna(rsi_1) or pd.isna(rsi_2) or rsi_2 >= rsi_1:
                            continue
                    except (ValueError, TypeError):
                        continue
                    
                    strength = self._calculate_divergence_strength(price_1, price_2, rsi_1, rsi_2)
                    
                    divergences.append(Divergence(
                        type="BEARISH",
                        price_low_1=price_1,
                        price_low_2=price_2,
                        rsi_low_1=rsi_1,
                        rsi_low_2=rsi_2,
                        bars_between=bars_between,
                        strength=strength,
                        timestamp_1=prices.index[idx1],
                        timestamp_2=prices.index[idx2]
                    ))
        except Exception as e:
            logger.error(f"Error detecting bearish divergence: {e}")
        
        return divergences

    @staticmethod
    def _validate_series(prices: pd.Series, rsi: pd.Series) -> bool:
        """Validate that both series are valid and have sufficient data."""
        if prices is None or prices.empty or rsi is None or rsi.empty:
            return False
        
        if len(prices) < 10 or len(rsi) < 10:
            return False
        
        # Check if series has mostly NaN values
        if prices.isna().sum() / len(prices) > 0.5 or rsi.isna().sum() / len(rsi) > 0.5:
            return False
        
        return True

    @staticmethod
    def _find_local_lows(series: pd.Series, window: int = 3) -> List[int]:
        """Find local minima in a series."""
        if series.empty or len(series) < window * 2 + 1:
            return []
        
        lows = []
        try:
            for i in range(window, len(series) - window):
                if pd.isna(series.iloc[i]):
                    continue
                window_data = series.iloc[i-window:i+window+1]
                if window_data.isna().all():
                    continue
                if series.iloc[i] == window_data.min():
                    lows.append(i)
        except Exception as e:
            logger.warning(f"Error finding local lows: {e}")
        
        return lows

    @staticmethod
    def _find_local_highs(series: pd.Series, window: int = 3) -> List[int]:
        """Find local maxima in a series."""
        if series.empty or len(series) < window * 2 + 1:
            return []
        
        highs = []
        try:
            for i in range(window, len(series) - window):
                if pd.isna(series.iloc[i]):
                    continue
                window_data = series.iloc[i-window:i+window+1]
                if window_data.isna().all():
                    continue
                if series.iloc[i] == window_data.max():
                    highs.append(i)
        except Exception as e:
            logger.warning(f"Error finding local highs: {e}")
        
        return highs

    @staticmethod
    def _find_nearest_low(series: pd.Series, idx: int, window: int = 3) -> Optional[int]:
        """Find nearest local low to a given index."""
        try:
            start = max(0, idx - window)
            end = min(len(series), idx + window + 1)
            window_data = series.iloc[start:end]
            
            if window_data.isna().all():
                return None
            
            local_min_idx = window_data.idxmin()
            return local_min_idx if not pd.isna(local_min_idx) else None
        except Exception:
            return None

    @staticmethod
    def _find_nearest_high(series: pd.Series, idx: int, window: int = 3) -> Optional[int]:
        """Find nearest local high to a given index."""
        try:
            start = max(0, idx - window)
            end = min(len(series), idx + window + 1)
            window_data = series.iloc[start:end]
            
            if window_data.isna().all():
                return None
            
            local_max_idx = window_data.idxmax()
            return local_max_idx if not pd.isna(local_max_idx) else None
        except Exception:
            return None

    @staticmethod
    def _calculate_divergence_strength(price1: float, price2: float, rsi1: float, rsi2: float) -> str:
        """
        Calculate divergence strength based on price and RSI differences.
        
        Returns:
            'WEAK', 'MEDIUM', or 'STRONG'
        """
        try:
            if price1 == 0 or pd.isna(price1) or pd.isna(price2) or pd.isna(rsi1) or pd.isna(rsi2):
                return "WEAK"
            
            price_change = abs((price2 - price1) / price1) * 100
            rsi_change = abs(rsi2 - rsi1)
            
            if price_change > 3 and rsi_change > 15:
                return "STRONG"
            elif price_change > 1.5 and rsi_change > 8:
                return "MEDIUM"
            else:
                return "WEAK"
        except Exception:
            return "WEAK"
