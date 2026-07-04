"""GEM platform — live scan orchestration for watchlist instruments."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from src.edge_engine import EdgeBarSignals, analyze_edge_bar
from src.gem.analyzer import GEMAnalyzer
from src.gem.config import GEMConfig
from src.gem.models import GEMAnalysis
from src.gem.timeframes import DEFAULT_TIMEFRAMES, TF_SHORT
from src.gem_strength import (
    STRENGTH_RANK,
    GemStrengthRating,
    combine_mtf_ratings,
    rate_gem_analysis,
)
from src.market_data import MarketDataService
from src.scan_checklist import ScanChecklist, build_combined_checklist
from src.sme.models import SMELiveScore
from src.sme.scorer import score_signal_memory
from src.watchlist import load_watchlist

logger = logging.getLogger(__name__)


@dataclass
class InstrumentMTFScan:
    symbol: str
    display_name: str
    analyses: Dict[str, GEMAnalysis] = field(default_factory=dict)
    ratings: Dict[str, GemStrengthRating] = field(default_factory=dict)
    edge_signals: Dict[str, EdgeBarSignals] = field(default_factory=dict)
    sme_scores: Dict[str, SMELiveScore] = field(default_factory=dict)
    combined_rating: Optional[GemStrengthRating] = None
    checklist: Optional[ScanChecklist] = None

    def primary_analysis(self) -> Optional[GEMAnalysis]:
        return self.analyses.get("60") or next(iter(self.analyses.values()), None)

    def primary_edge(self) -> Optional[EdgeBarSignals]:
        return self.edge_signals.get("60") or next(iter(self.edge_signals.values()), None)

    def primary_sme(self) -> Optional[SMELiveScore]:
        return self.sme_scores.get("60") or next(iter(self.sme_scores.values()), None)


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
        self.last_mtf: List[InstrumentMTFScan] = []

    def scan_watchlist(self, watchlist: dict = None) -> List[GEMAnalysis]:
        """Single-timeframe scan (primary TF from watchlist, default H1)."""
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

    def scan_watchlist_mtf(self, watchlist: dict = None) -> List[InstrumentMTFScan]:
        """Scan all instruments on 15m, 1h, 4h, and daily timeframes."""
        wl = watchlist or load_watchlist()
        instruments = wl.get("instruments", [])
        bars = int(wl.get("bars", 120))
        timeframes = wl.get("timeframes") or DEFAULT_TIMEFRAMES

        rows: List[InstrumentMTFScan] = []

        for inst in instruments:
            sym = inst.get("symbol")
            if not sym:
                continue
            name = inst.get("name") or sym
            row = InstrumentMTFScan(symbol=sym, display_name=name)

            for tf in timeframes:
                fetched = self.market.fetch_many([inst], bars=bars, interval_key=str(tf))
                if sym not in fetched:
                    logger.warning("No data for %s @ %s", sym, tf)
                    continue
                df, source = fetched[sym]
                analysis = self.analyzer.analyze(sym, df, data_source=f"{source}/{TF_SHORT.get(tf, tf)}")
                if analysis:
                    row.analyses[tf] = analysis
                    row.ratings[tf] = rate_gem_analysis(analysis, tf)
                    edge = analyze_edge_bar(
                        df,
                        rsi_period=self.gem_config.rsi_length,
                        mfi_period=self.gem_config.rsi_length,
                    )
                    if edge:
                        row.edge_signals[tf] = edge
                    combo = edge.edge_combo_score if edge else 0
                    row.sme_scores[tf] = score_signal_memory(
                        df,
                        analysis,
                        instrument_name=name,
                        timeframe=tf,
                        edge_combo_score=combo,
                    )

            if row.ratings:
                row.combined_rating = combine_mtf_ratings(list(row.ratings.values()))
                row.checklist = build_combined_checklist(sym, name, row.analyses, row.ratings)
                primary = row.analyses.get("60") or row.primary_analysis()
                if primary:
                    self.last_results[sym] = primary
                rows.append(row)

        self.last_mtf = rows
        self.last_scan_at = datetime.utcnow()
        rows.sort(
            key=lambda r: (
                r.checklist.trade_ok if r.checklist else False,
                STRENGTH_RANK.get(r.combined_rating.strength if r.combined_rating else "NONE", 0),
                (r.primary_sme().edge_plus if r.primary_sme() else 0),
                abs(r.combined_rating.score if r.combined_rating else 0),
            ),
            reverse=True,
        )
        logger.info("MTF GEM scan: %s instruments", len(rows))
        return rows

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
