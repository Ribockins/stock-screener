"""Technical Indicators Module - RSI and other momentum indicators"""

import pandas as pd
import numpy as np
from typing import Tuple, List


class RSICalculator:
    """Calculate Relative Strength Index (RSI) for price data"""

    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate RSI using pandas Series of close prices.
        
        Args:
            prices: Series of close prices
            period: RSI period (default 14)
            
        Returns:
            Series of RSI values
        """
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi

    @staticmethod
    def get_rsi_signal(rsi: float, oversold: int = 30, overbought: int = 70) -> str:
        """
        Get RSI signal based on threshold values.
        
        Args:
            rsi: Current RSI value
            oversold: Oversold threshold (default 30)
            overbought: Overbought threshold (default 70)
            
        Returns:
            Signal type: 'OVERSOLD', 'OVERBOUGHT', or 'NEUTRAL'
        """
        if rsi < oversold:
            return "OVERSOLD"
        elif rsi > overbought:
            return "OVERBOUGHT"
        else:
            return "NEUTRAL"


class MomentumIndicators:
    """Additional momentum indicators"""

    @staticmethod
    def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        Calculate MACD (Moving Average Convergence Divergence).
        
        Returns:
            Tuple of (MACD line, Signal line, Histogram)
        """
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram

    @staticmethod
    def calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """
        Calculate Stochastic Oscillator.
        
        Returns:
            Tuple of (K line, D line)
        """
        lowest_low = low.rolling(k_period).min()
        highest_high = high.rolling(k_period).max()
        
        k_line = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d_line = k_line.rolling(d_period).mean()
        
        return k_line, d_line
