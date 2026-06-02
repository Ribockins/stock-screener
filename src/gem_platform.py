"""GEM platform — live scan orchestration for watchlist instruments."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from src.gem.analyzer import GEMAnalyzer
from src.gem.config import GEMConfig
from src.gem.models import GEMAnalysis
from src.market_data import MarketDataService
from src.watchlist import load_watchlist

logger = logging.getLogger(__name__)


class GEMPlatform:
    """
    Scans user watchlist with live market data and GEM Logic signals.
    """

    def __init__(self, gem_config: Optional[GEMConfig] = None):
        self.gem_config = gem_config or GEMConfig()
        self.analyzer = GEMAnalyzer(self.gem_config)
        self.market = MarketDataService()
        self.last_scan_at: Optional[datetime] = None
        self.last_results: Dict[str, GEMAnalysis] = {}

    def scan_watchlist(self, watchlist: dict = None) -> List[GEMAnalysis]:
        wl = watchlist or load_watchlist()
        instruments = wl.get("instruments", [])
        bars = int(wl.get("bars", 120))
        tf = str(wl.get("timeframe", "60"))

        results: List[GEMAnalysis] = []
        fetched = self.market.fetch_many(instruments, bars=bars, interval_key=tf)

        for inst in instruments:
            sym = inst.get("symbol")
            if not sym or sym not in fetched:
                logger.warning("No data for %s", sym)
                continue
            df, source = fetched[sym]
            analysis = self.analyzer.analyze(sym, df, data_source=source)
            if analysis:
                results.append(analysis)
                self.last_results[sym] = analysis

        self.last_scan_at = datetime.utcnow()
        results.sort(
            key=lambda a: (
                a.buy_gem or a.sell_gem,
                a.buy_setup or a.sell_setup,
                a.buy_entry or a.sell_entry,
                a.gem_score,
            ),
            reverse=True,
        )
        logger.info("GEM scan complete: %s/%s symbols", len(results), len(instruments))
        return results

    def priority_signals(self, results: List[GEMAnalysis] = None) -> List[GEMAnalysis]:
        """Return actionable signals (GEM, setup, or entry)."""
        rows = results if results is not None else list(self.last_results.values())
        return [
            r
            for r in rows
            if r.buy_gem
            or r.sell_gem
            or r.buy_setup
            or r.sell_setup
            or r.buy_entry
            or r.sell_entry
        ]
