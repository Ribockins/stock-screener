"""Bar sources the research engine can collect itself.

A delay of a minute or more is expected. Yahoo FX volume is not bid/ask volume.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from research_engine.clock import bar_end
from research_engine.records import Bar

_TICKERS = {"EURUSD": "EURUSD=X"}


class SourceError(RuntimeError):
    pass


def fetch_yfinance_bars(symbol: str, now: datetime, timeframe_seconds: int = 3600) -> tuple[list[Bar], str]:
    ticker = _TICKERS.get(symbol, symbol)
    try:
        import yfinance as yf
    except ImportError as exc:
        raise SourceError("yfinance не установлен") from exc
    frame = yf.download(ticker, period="10d", interval="1h", progress=False, auto_adjust=False)
    if frame is None or len(frame) == 0:
        raise SourceError(f"yfinance не вернул бары для {ticker}")
    rows = []
    for timestamp, row in frame.iterrows():
        rows.append(
            (
                timestamp,
                _field(row, "open"),
                _field(row, "high"),
                _field(row, "low"),
                _field(row, "close"),
            )
        )
    return bars_from_ohlc(rows, now, timeframe_seconds), f"yfinance {ticker}"


def bars_from_ohlc(rows: list[tuple], now: datetime, timeframe_seconds: int) -> list[Bar]:
    bars: list[Bar] = []
    for timestamp, open_, high, low, close in rows:
        moment = _as_utc(timestamp)
        prices = [_price(open_), _price(high), _price(low), _price(close)]
        if any(price is None or price <= 0 for price in prices):
            continue
        if bar_end(moment, timeframe_seconds) > now:
            continue
        bars.append(Bar(timestamp=moment, open=prices[0], high=prices[1], low=prices[2], close=prices[3]))
    bars.sort(key=lambda bar: bar.timestamp)
    return bars


def _field(row, name: str):
    for key in row.index:
        label = key[0] if isinstance(key, tuple) else key
        if str(label).strip().lower() == name:
            return row[key]
    raise KeyError(name)


def _as_utc(timestamp) -> datetime:
    moment = timestamp.to_pydatetime() if hasattr(timestamp, "to_pydatetime") else timestamp
    if moment.tzinfo is None:
        return moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc)


def _price(value) -> Decimal | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return Decimal(f"{number:.5f}")
