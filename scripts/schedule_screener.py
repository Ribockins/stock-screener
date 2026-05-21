#!/usr/bin/env python
"""Run screener on a schedule"""

import sys
import logging
import schedule
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.screener import StockScreener
from src.utils import setup_logging
import rsiconfig


class ScheduledScreener:
    """Manages scheduled screening runs"""
    
    def __init__(self):
        self.screener = StockScreener()
        self.logger = logging.getLogger(__name__)
    
    def run_scan(self):
        """Execute a complete scan"""
        self.logger.info("="*60)
        self.logger.info(f"Scheduled scan started at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("="*60)
        
        try:
            all_results = self.screener.scan_all_markets()
            
            total = sum(len(results) for results in all_results.values())
            
            for market, results in all_results.items():
                if results:
                    self.screener.save_results(results)
                    self.logger.info(f"{market}: {len(results)} signals")
            
            self.logger.info(f"Scan complete: {total} total signals")
            
        except Exception as e:
            self.logger.error(f"Error during scan: {e}", exc_info=True)
    
    def start(self):
        """Start scheduled scanning"""
        self.logger.info(f"Scheduled screener started. Running every {rsiconfig.SCAN_INTERVAL} minutes.")
        
        # Schedule the job
        schedule.every(rsiconfig.SCAN_INTERVAL).minutes.do(self.run_scan)
        
        # Keep scheduler running
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)
        except KeyboardInterrupt:
            self.logger.info("Scheduled screener stopped by user")


def main():
    """Main entry point"""
    setup_logging(rsiconfig.LOG_LEVEL, rsiconfig.LOG_FILE)
    logger = logging.getLogger(__name__)
    
    logger.info("Initializing Scheduled Stock Screener")
    logger.info(f"Scan Interval: {rsiconfig.SCAN_INTERVAL} minutes")
    logger.info(f"Database Type: {rsiconfig.DB_TYPE}")
    
    scheduler = ScheduledScreener()
    scheduler.start()


if __name__ == "__main__":
    main()
