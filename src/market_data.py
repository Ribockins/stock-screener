"""Unified market data access for live GEM scans."""

import logging
from typing import List, Optional, Tuple

import pandas as pd

from src.data_fetcher import TradingViewFetcher

logger = logging.getLogger(__name__)

YFINANCE_INTERVALS = {
    "5": ("5m", "5d"),
    "15": ("15m", "5d"),
    "60": ("1h", "60d"),
    "240": ("1h", "60d"),  # yfinance has no 4h; approximate with 1h
    "1d": ("1d", "1y"),
    "1wk": ("1wk", "2y"),
}


def normalize_ohlcv(df: Optional[pd.DataFrame]) -> Optional[pd.DataFrame]:
    if df is None or df.empty:
        return None
    out = df.copy()
    if isinstance(out.columns, pd.MultiIndex):
        out.columns = out.columns.get_level_values(0)
    out.columns = [str(c).lower() for c in out.columns]
    required = ("open", "high", "low", "close", "volume")
    if not all(c in out.columns for c in required):
        return None
    out = out[list(required)].apply(pd.to_numeric, errors="coerce")
    return out.dropna(subset=["open", "high", "low", "close"])


class MarketDataService:
    """Fetch OHLCV for watchlist symbols (TradingView + yfinance fallback)."""

    def __init__(self, tv_username: Optional[str] = None, tv_password: Optional[str] = None):
        self._fetcher = TradingViewFetcher(username=tv_username, password=tv_password)

    def fetch_bars(
        self,
        symbol: str,
        bars: int = 120,
        exchange: str = "NASDAQ",
        interval_key: str = "60",
    ) -> Tuple[Optional[pd.DataFrame], str]:
        """
        Fetch OHLCV history for GEM analysis.

        Returns:
            (dataframe, source_label)
        """
        data = self._fetcher.fetch_h1_data(symbol, bars=bars)
        if data is not None:
            data = normalize_ohlcv(data)
            if data is not None and len(data) >= 30:
                return data.tail(bars), "tradingview/yfinance"

        data = self._fetch_yfinance(symbol, bars, interval_key)
        if data is not None:
            return data, "yfinance"
        return None, ""

    def _fetch_yfinance(self, symbol: str, bars: int, interval_key: str) -> Optional[pd.DataFrame]:
        try:
            import yfinance as yf
            from datetime import datetime, timedelta

            interval, period_days = YFINANCE_INTERVALS.get(interval_key, ("1h", "60d"))
            end = datetime.now()
            start = end - timedelta(days=period_days)
            raw = yf.download(
                symbol,
                start=start,
                end=end,
                interval=interval,
                progress=False,
                timeout=15,
            )
            data = normalize_ohlcv(raw)
            if data is not None and not data.empty:
                return data.tail(bars)
        except Exception as e:
            logger.debug("yfinance fetch failed for %s: %s", symbol, e)
        return None

    def fetch_many(
        self,
        instruments: List[dict],
        bars: int = 120,
        interval_key: str = "60",
    ) -> dict:
        out = {}
        for inst in instruments:
            sym = inst.get("symbol") or inst.get("ticker")
            if not sym:
                continue
            ex = inst.get("exchange", "NASDAQ")
            df, src = self.fetch_bars(sym, bars=bars, exchange=ex, interval_key=interval_key)
            if df is not None:
                out[sym] = (df, src)
        return out
