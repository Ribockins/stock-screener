"""Main Screener Module - Orchestrates scanning across all markets"""

import pandas as pd
import logging
from typing import List, Dict, Optional
from datetime import datetime
from src.data_fetcher import TradingViewFetcher
from src.indicators import RSICalculator
from src.divergence_detector import DivergenceDetector
from src.database import get_database_manager
import rsiconfig

logger = logging.getLogger(__name__)


class StockScreener:
    """Main screener class orchestrating RSI and divergence scanning"""

    def __init__(self):
        self.fetcher = TradingViewFetcher()
        self.rsi_calc = RSICalculator()
        self.divergence_detector = DivergenceDetector()
        self.db_manager = get_database_manager(
            rsiconfig.DB_TYPE,
            db_path=rsiconfig.DB_PATH,
            uri=rsiconfig.MONGO_URI
        )
        self.results = []
        self.skipped_count = 0

    def scan_symbol(self, symbol: str, market: str = "US500") -> Optional[Dict]:
        """
        Scan a single symbol for RSI signals and divergences.
        
        Args:
            symbol: Stock symbol to scan
            market: Market the symbol belongs to
            
        Returns:
            Dict with screening results or None if failed
        """
        try:
            # Fetch H1 data
            data = self.fetcher.fetch_h1_data(symbol, bars=100)
            if data is None or data.empty:
                logger.warning(f"Skipping {symbol}: No data available")
                self.skipped_count += 1
                return None
            
            # Validate data has required columns
            if 'close' not in data.columns:
                logger.warning(f"Skipping {symbol}: Missing 'close' column")
                self.skipped_count += 1
                return None
            
            # Reset index to get integer-based indexing
            close_prices = data['close'].reset_index(drop=True)
            
            # Validate close prices
            close_prices = pd.to_numeric(close_prices, errors='coerce')
            if close_prices.isna().all():
                logger.warning(f"Skipping {symbol}: All close prices are invalid")
                self.skipped_count += 1
                return None
            
            # Calculate RSI
            rsi = self.rsi_calc.calculate_rsi(close_prices, rsiconfig.RSI_PERIOD)
            
            # Validate RSI output
            if rsi.empty or rsi.isna().all():
                logger.warning(f"Skipping {symbol}: RSI calculation failed or returned NaN")
                self.skipped_count += 1
                return None
            
            # Get last valid RSI value
            rsi_clean = rsi.dropna()
            if rsi_clean.empty:
                logger.warning(f"Skipping {symbol}: No valid RSI values")
                self.skipped_count += 1
                return None
            
            current_rsi = float(rsi_clean.iloc[-1])
            
            # Validate RSI range
            if pd.isna(current_rsi) or current_rsi < 0 or current_rsi > 100:
                logger.warning(f"Skipping {symbol}: Invalid RSI value {current_rsi}")
                self.skipped_count += 1
                return None
            
            # Get RSI signal
            rsi_signal = self.rsi_calc.get_rsi_signal(
                current_rsi,
                rsiconfig.RSI_OVERSOLD,
                rsiconfig.RSI_OVERBOUGHT
            )
            
            # Detect divergences (safe: they handle NaN gracefully)
            try:
                bullish_divs = self.divergence_detector.detect_bullish_divergence(close_prices, rsi)
                bearish_divs = self.divergence_detector.detect_bearish_divergence(close_prices, rsi)
            except Exception as e:
                logger.warning(f"{symbol}: Error detecting divergences: {e}")
                bullish_divs = []
                bearish_divs = []
            
            divergence_type = "NONE"
            divergence_strength = ""
            
            if bullish_divs:
                divergence_type = "BULLISH"
                divergence_strength = bullish_divs[-1].strength
            elif bearish_divs:
                divergence_type = "BEARISH"
                divergence_strength = bearish_divs[-1].strength
            
            # Get current price
            current_price = float(close_prices.iloc[-1])
            if pd.isna(current_price) or current_price <= 0:
                logger.warning(f"Skipping {symbol}: Invalid price {current_price}")
                self.skipped_count += 1
                return None
            
            result = {
                'symbol': symbol,
                'market': market,
                'timestamp': datetime.utcnow(),
                'price': current_price,
                'rsi': round(current_rsi, 2),
                'rsi_signal': rsi_signal,
                'divergence_type': divergence_type,
                'divergence_strength': divergence_strength,
                'bullish_divergences': len(bullish_divs),
                'bearish_divergences': len(bearish_divs)
            }
            
            logger.info(f"{symbol}: RSI={current_rsi:.2f} ({rsi_signal}), Divergence={divergence_type}")
            return result
            
        except Exception as e:
            logger.error(f"Error scanning {symbol}: {e}", exc_info=False)
            self.skipped_count += 1
            return None

    def scan_market(self, market: str, symbols: List[str]) -> List[Dict]:
        """
        Scan all symbols in a market.
        
        Args:
            market: Market name (US500, UK100, etc.)
            symbols: List of symbols to scan
            
        Returns:
            List of screening results
        """
        results = []
        logger.info(f"Scanning {market} ({len(symbols)} symbols)...")
        
        self.skipped_count = 0
        
        for symbol in symbols:
            result = self.scan_symbol(symbol, market)
            if result is not None:
                results.append(result)
        
        logger.info(f"Completed {market} scan: {len(results)} signals found, {self.skipped_count} symbols skipped")
        return results

    def scan_all_markets(self) -> Dict[str, List[Dict]]:
        """
        Scan all configured markets.
        
        Returns:
            Dictionary with market names as keys and result lists as values
        """
        all_results = {}
        total_skipped = 0
        
        for market, stock_list_path in rsiconfig.STOCK_LISTS.items():
            try:
                with open(stock_list_path, 'r') as f:
                    symbols = [line.strip() for line in f if line.strip()]
                
                if not symbols:
                    logger.warning(f"Stock list is empty: {stock_list_path}")
                    continue
                
                market_results = self.scan_market(market, symbols)
                all_results[market] = market_results
                total_skipped += self.skipped_count
                
            except FileNotFoundError:
                logger.error(f"Stock list not found: {stock_list_path}")
            except Exception as e:
                logger.error(f"Error scanning {market}: {e}")
        
        if total_skipped > 0:
            logger.info(f"Total symbols skipped: {total_skipped}")
        
        return all_results

    def save_results(self, results: List[Dict]):
        """
        Save screening results to database.
        
        Args:
            results: List of screening results
        """
        if results:
            try:
                self.db_manager.save_results(results)
                logger.info(f"Saved {len(results)} results to database")
            except Exception as e:
                logger.error(f"Error saving results to database: {e}")

    def get_signals(self, signal_type: str = "OVERSOLD") -> List[Dict]:
        """
        Get results filtered by signal type.
        
        Args:
            signal_type: OVERSOLD, OVERBOUGHT, or NEUTRAL
            
        Returns:
            Filtered results
        """
        filtered = [r for r in self.results if r.get('rsi_signal') == signal_type]
        return filtered

    def get_divergences(self, div_type: str = "BULLISH") -> List[Dict]:
        """
        Get results with specific divergence type.
        
        Args:
            div_type: BULLISH or BEARISH
            
        Returns:
            Filtered results with divergences
        """
        filtered = [r for r in self.results if r.get('divergence_type') == div_type]
        return filtered
