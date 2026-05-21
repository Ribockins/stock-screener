"""Divergence Detection Module - Identifies bullish and bearish divergences"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass


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
        divergences = []
        
        # Find local lows in price
        price_lows = self._find_local_lows(prices)
        rsi_lows = self._find_local_lows(rsi)
        
        # Match price lows with RSI lows
        for i in range(len(price_lows) - 1):
            idx1 = price_lows[i]
            
            for j in range(i + 1, len(price_lows)):
                idx2 = price_lows[j]
                bars_between = idx2 - idx1
                
                if bars_between < self.min_bars_apart or bars_between > self.max_bars_apart:
                    continue
                
                # Check if price made lower low
                if prices.iloc[idx2] >= prices.iloc[idx1]:
                    continue
                
                # Find corresponding RSI lows
                rsi_idx1 = self._find_nearest_low(rsi, idx1, window=3)
                rsi_idx2 = self._find_nearest_low(rsi, idx2, window=3)
                
                if rsi_idx1 is None or rsi_idx2 is None:
                    continue
                
                # Check if RSI made higher low
                if rsi.iloc[rsi_idx2] <= rsi.iloc[rsi_idx1]:
                    continue
                
                strength = self._calculate_divergence_strength(
                    prices.iloc[idx1], prices.iloc[idx2],
                    rsi.iloc[rsi_idx1], rsi.iloc[rsi_idx2]
                )
                
                divergences.append(Divergence(
                    type="BULLISH",
                    price_low_1=prices.iloc[idx1],
                    price_low_2=prices.iloc[idx2],
                    rsi_low_1=rsi.iloc[rsi_idx1],
                    rsi_low_2=rsi.iloc[rsi_idx2],
                    bars_between=bars_between,
                    strength=strength,
                    timestamp_1=prices.index[idx1],
                    timestamp_2=prices.index[idx2]
                ))
        
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
        divergences = []
        
        # Find local highs in price
        price_highs = self._find_local_highs(prices)
        rsi_highs = self._find_local_highs(rsi)
        
        # Match price highs with RSI highs
        for i in range(len(price_highs) - 1):
            idx1 = price_highs[i]
            
            for j in range(i + 1, len(price_highs)):
                idx2 = price_highs[j]
                bars_between = idx2 - idx1
                
                if bars_between < self.min_bars_apart or bars_between > self.max_bars_apart:
                    continue
                
                # Check if price made higher high
                if prices.iloc[idx2] <= prices.iloc[idx1]:
                    continue
                
                # Find corresponding RSI highs
                rsi_idx1 = self._find_nearest_high(rsi, idx1, window=3)
                rsi_idx2 = self._find_nearest_high(rsi, idx2, window=3)
                
                if rsi_idx1 is None or rsi_idx2 is None:
                    continue
                
                # Check if RSI made lower high
                if rsi.iloc[rsi_idx2] >= rsi.iloc[rsi_idx1]:
                    continue
                
                strength = self._calculate_divergence_strength(
                    prices.iloc[idx1], prices.iloc[idx2],
                    rsi.iloc[rsi_idx1], rsi.iloc[rsi_idx2]
                )
                
                divergences.append(Divergence(
                    type="BEARISH",
                    price_low_1=prices.iloc[idx1],
                    price_low_2=prices.iloc[idx2],
                    rsi_low_1=rsi.iloc[rsi_idx1],
                    rsi_low_2=rsi.iloc[rsi_idx2],
                    bars_between=bars_between,
                    strength=strength,
                    timestamp_1=prices.index[idx1],
                    timestamp_2=prices.index[idx2]
                ))
        
        return divergences

    @staticmethod
    def _find_local_lows(series: pd.Series, window: int = 3) -> List[int]:
        """Find local minima in a series."""
        lows = []
        for i in range(window, len(series) - window):
            if series.iloc[i] == series.iloc[i-window:i+window+1].min():
                lows.append(i)
        return lows

    @staticmethod
    def _find_local_highs(series: pd.Series, window: int = 3) -> List[int]:
        """Find local maxima in a series."""
        highs = []
        for i in range(window, len(series) - window):
            if series.iloc[i] == series.iloc[i-window:i+window+1].max():
                highs.append(i)
        return highs

    @staticmethod
    def _find_nearest_low(series: pd.Series, idx: int, window: int = 3) -> int:
        """Find nearest local low to a given index."""
        start = max(0, idx - window)
        end = min(len(series), idx + window + 1)
        local_min_idx = series.iloc[start:end].idxmin()
        return local_min_idx if local_min_idx is not None else None

    @staticmethod
    def _find_nearest_high(series: pd.Series, idx: int, window: int = 3) -> int:
        """Find nearest local high to a given index."""
        start = max(0, idx - window)
        end = min(len(series), idx + window + 1)
        local_max_idx = series.iloc[start:end].idxmax()
        return local_max_idx if local_max_idx is not None else None

    @staticmethod
    def _calculate_divergence_strength(price1: float, price2: float, rsi1: float, rsi2: float) -> str:
        """
        Calculate divergence strength based on price and RSI differences.
        
        Returns:
            'WEAK', 'MEDIUM', or 'STRONG'
        """
        price_change = abs((price2 - price1) / price1) * 100
        rsi_change = abs(rsi2 - rsi1)
        
        if price_change > 3 and rsi_change > 15:
            return "STRONG"
        elif price_change > 1.5 and rsi_change > 8:
            return "MEDIUM"
        else:
            return "WEAK"
