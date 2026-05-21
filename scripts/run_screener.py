#!/usr/bin/env python
"""Run screener once"""

import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.screener import StockScreener
from src.utils import setup_logging, format_result_for_display
import rsiconfig


def main():
    """Run screening once and display results"""
    
    # Setup logging
    setup_logging(rsiconfig.LOG_LEVEL, rsiconfig.LOG_FILE)
    logger = logging.getLogger(__name__)
    
    logger.info("="*60)
    logger.info("Starting Stock Screener Scan")
    logger.info(f"RSI Period: {rsiconfig.RSI_PERIOD}")
    logger.info(f"Oversold Threshold: {rsiconfig.RSI_OVERSOLD}")
    logger.info(f"Overbought Threshold: {rsiconfig.RSI_OVERBOUGHT}")
    logger.info("="*60)
    
    # Initialize screener
    screener = StockScreener()
    
    # Scan all markets
    all_results = screener.scan_all_markets()
    
    # Display and save results
    total_signals = 0
    
    for market, results in all_results.items():
        logger.info(f"\n{market}: {len(results)} signals found")
        total_signals += len(results)
        
        # Save to database
        if results:
            screener.save_results(results)
            
            # Display top signals
            oversold = [r for r in results if r.get('rsi_signal') == 'OVERSOLD']
            overbought = [r for r in results if r.get('rsi_signal') == 'OVERBOUGHT']
            bullish_div = [r for r in results if r.get('divergence_type') == 'BULLISH']
            bearish_div = [r for r in results if r.get('divergence_type') == 'BEARISH']
            
            logger.info(f"  - Oversold ({rsiconfig.RSI_OVERSOLD}): {len(oversold)}")
            logger.info(f"  - Overbought ({rsiconfig.RSI_OVERBOUGHT}): {len(overbought)}")
            logger.info(f"  - Bullish Divergences: {len(bullish_div)}")
            logger.info(f"  - Bearish Divergences: {len(bearish_div)}")
            
            # Show top 5 by RSI extreme
            top_oversold = sorted(oversold, key=lambda x: x['rsi'])[:5]
            if top_oversold:
                logger.info(f"\n  Top Oversold in {market}:")
                for r in top_oversold:
                    logger.info(f"    {r['symbol']}: RSI {r['rsi']}")
    
    logger.info(f"\n{'='*60}")
    logger.info(f"Scan Complete: {total_signals} total signals across all markets")
    logger.info(f"{'='*60}")


if __name__ == "__main__":
    main()
