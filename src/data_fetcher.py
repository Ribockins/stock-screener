"""Data Fetcher Module - Retrieve historical data from TradingView"""

import pandas as pd
from typing import Optional, List
from tvdatafeed import TvDatafeed, Interval
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TradingViewFetcher:
    """Fetch historical OHLCV data from TradingView"""

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize TradingView data fetcher.
        
        Args:
            username: TradingView username (optional for free data)
            password: TradingView password (optional for free data)
        """
        try:
            self.tv = TvDatafeed(username=username, password=password)
        except Exception as e:
            logger.warning(f"Could not authenticate with TradingView: {e}. Using free mode.")
            self.tv = TvDatafeed()

    def fetch_h1_data(self, symbol: str, bars: int = 100) -> Optional[pd.DataFrame]:
        """
        Fetch 1-hour (H1) historical data for a symbol.
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'MSFT')
            bars: Number of bars to fetch (default 100)
            
        Returns:
            DataFrame with OHLCV data or None if fetch fails
        """
        try:
            data = self.tv.get_hist(
                symbol=symbol,
                exchange="US",  # Can be changed to "UK", "EURONEXT" etc
                interval=Interval.in_1_hour,
                n_bars=bars
            )
            
            if data is not None and not data.empty:
                # Rename columns to standard format
                data.columns = ['open', 'high', 'low', 'close', 'volume']
                logger.info(f"Fetched {len(data)} bars for {symbol}")
                return data
            else:
                logger.warning(f"No data returned for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")
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
        Fetch data with specific exchange.
        
        Args:
            symbol: Stock symbol
            exchange: Exchange code (US, UK, EURONEXT, etc.)
            bars: Number of bars to fetch
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            data = self.tv.get_hist(
                symbol=symbol,
                exchange=exchange,
                interval=Interval.in_1_hour,
                n_bars=bars
            )
            
            if data is not None and not data.empty:
                data.columns = ['open', 'high', 'low', 'close', 'volume']
                return data
            return None
            
        except Exception as e:
            logger.error(f"Error fetching {symbol} from {exchange}: {e}")
            return None
