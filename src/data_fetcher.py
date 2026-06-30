"""Data Fetcher Module - Retrieve historical data from TradingView with yfinance fallback"""

import pandas as pd
from typing import Optional, List
import yfinance as yf
import logging
from datetime import datetime, timedelta

try:
    from tvdatafeed import TvDatafeed, Interval
    TVDATAFEED_AVAILABLE = True
except ImportError:
    TvDatafeed = None
    Interval = None
    TVDATAFEED_AVAILABLE = False

logger = logging.getLogger(__name__)


class TradingViewFetcher:
    """Fetch historical OHLCV data from TradingView with yfinance fallback"""

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize TradingView data fetcher with yfinance fallback.
        
        Args:
            username: TradingView username (optional for free data)
            password: TradingView password (optional for free data)
        """
        if not TVDATAFEED_AVAILABLE:
            logger.warning("tvdatafeed is not installed. TradingView fetch disabled; using yfinance fallback only.")
            self.tv = None
        else:
            try:
                self.tv = TvDatafeed(username=username, password=password)
                logger.info("TradingView fetcher initialized")
            except Exception as e:
                logger.warning(f"Could not authenticate with TradingView: {e}. Using free mode.")
                self.tv = TvDatafeed()
        
        self.use_yfinance_fallback = True  # Enable fallback by default

    def fetch_h1_data(self, symbol: str, bars: int = 100) -> Optional[pd.DataFrame]:
        """
        Fetch 1-hour (H1) historical data for a symbol.
        Tries TradingView first, falls back to yfinance if needed.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'MSFT')
            bars: Number of bars to fetch (default 100)
            
        Returns:
            DataFrame with OHLCV data or None if fetch fails
        """
        # Try TradingView first
        data = self._fetch_from_tradingview(symbol, bars)
        if data is not None:
            return data
        
        # Fall back to yfinance
        if self.use_yfinance_fallback:
            logger.info(f"Falling back to yfinance for {symbol}")
            data = self._fetch_from_yfinance(symbol, bars)
            if data is not None:
                return data
        
        logger.warning(f"Failed to fetch data from both sources for {symbol}")
        return None

    def _fetch_from_tradingview(self, symbol: str, bars: int = 100) -> Optional[pd.DataFrame]:
        """
        Fetch data from TradingView only.
        
        Args:
            symbol: Stock symbol
            bars: Number of bars to fetch
            
        Returns:
            DataFrame with OHLCV data or None if fetch fails
        """
        if not TVDATAFEED_AVAILABLE or self.tv is None:
            return None

        try:
            logger.info(f"Trying {symbol} on NASDAQ (TradingView)")
            data = self.tv.get_hist(
                symbol=symbol,
                exchange="NASDAQ",
                interval=Interval.in_1_hour,
                n_bars=bars
            )
            
            if data is not None and not data.empty:
                # Rename columns to standard format
                data.columns = ['open', 'high', 'low', 'close', 'volume']
                logger.info(f"Fetched {len(data)} bars for {symbol} from TradingView")
                return data
            else:
                logger.debug(f"No data from TradingView for {symbol}")
                return None
                
        except Exception as e:
            logger.debug(f"TradingView error for {symbol}: {e}")
            return None

    def _fetch_from_yfinance(self, symbol: str, bars: int = 100) -> Optional[pd.DataFrame]:
        """
        Fetch data from yfinance as fallback.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'MSFT')
            bars: Number of bars to fetch (1-hour candles)
            
        Returns:
            DataFrame with OHLCV data or None if fetch fails
        """
        try:
            logger.info(f"Trying {symbol} on yfinance")
            
            # Calculate date range for 1-hour bars
            # Approximate: bars * 1 hour, assume ~8 trading hours per day
            end_date = datetime.now()
            start_date = end_date - timedelta(days=(bars // 8 + 5))  # Add buffer
            
            # Fetch 1-hour data
            data = yf.download(
                symbol,
                start=start_date,
                end=end_date,
                interval="1h",
                progress=False,
                timeout=10
            )
            
            if data is not None and not data.empty:
                # yfinance returns with columns: Open, High, Low, Close, Volume
                # Rename to lowercase for consistency
                data.columns = [col.lower() for col in data.columns]
                
                # Get the most recent 'bars' number of candles
                data = data.tail(bars)
                
                if not data.empty:
                    logger.info(f"Fetched {len(data)} bars for {symbol} from yfinance")
                    return data
            
            logger.debug(f"No data from yfinance for {symbol}")
            return None
            
        except Exception as e:
            logger.debug(f"yfinance error for {symbol}: {e}")
            return None

    def fetch_h1_data_multiple(self, symbols: List[str], bars: int = 100) -> dict:
        """
        Fetch 1-hour data for multiple symbols.
        
        Args:
            symbols: List of stock symbols
            bars: Number of bars to fetch for each symbol
            
        Returns:
            Dictionary with symbol as key and DataFrame as value
        """
        results = {}
        for symbol in symbols:
            data = self.fetch_h1_data(symbol, bars)
            if data is not None:
                results[symbol] = data
        
        logger.info(f"Successfully fetched data for {len(results)} out of {len(symbols)} symbols")
        return results

    def fetch_with_exchange(self, symbol: str, exchange: str = "US", bars: int = 100) -> Optional[pd.DataFrame]:
        """
        Fetch data with specific exchange (TradingView only).
        
        Args:
            symbol: Stock symbol
            exchange: Exchange code (US, UK, EURONEXT, etc.)
            bars: Number of bars to fetch
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            logger.info(f"Trying {symbol} on {exchange}")
            data = self.tv.get_hist(
                symbol=symbol,
                exchange=exchange,
                interval=Interval.in_1_hour,
                n_bars=bars
            )
            
            if data is not None and not data.empty:
                data.columns = ['open', 'high', 'low', 'close', 'volume']
                logger.info(f"Fetched {len(data)} bars for {symbol} from {exchange}")
                return data
            
            logger.debug(f"No data for {symbol} on {exchange}")
            return None
            
        except Exception as e:
            logger.debug(f"Error fetching {symbol} from {exchange}: {e}")
            return None

    def enable_fallback(self, enabled: bool = True):
        """
        Enable or disable yfinance fallback.
        
        Args:
            enabled: True to enable fallback, False to disable
        """
        self.use_yfinance_fallback = enabled
        logger.info(f"yfinance fallback: {'ENABLED' if enabled else 'DISABLED'}")
