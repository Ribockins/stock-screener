"""Sierra-style CSV parsing, bar quality checks, and UTC resampling."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from research_engine.clock import bar_end, format_utc, localize
from research_engine.config import EngineConfig
from research_engine.records import Bar, ParseIssue, QualityReport

_HEADER_ALIASES = {
    "date": "date",
    "datetime": "datetime",
    "date time": "datetime",
    "time": "time",
    "open": "open",
    "high": "high",
    "low": "low",
    "close": "close",
    "last": "close",
    "price": "close",
    "volume": "volume",
    "vol": "volume",
    "bidvolume": "bid_volume",
    "bid volume": "bid_volume",
    "bid vol": "bid_volume",
    "askvolume": "ask_volume",
    "ask volume": "ask_volume",
    "ask vol": "ask_volume",
}


def parse_sierra_csv(text: str, config: EngineConfig) -> tuple[list[Bar], list[ParseIssue]]:
    if not text.strip():
        return [], [ParseIssue(1, "empty file")]
    sample = text.splitlines()[0]
    delimiter = ";" if sample.count(";") > sample.count(",") else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    try:
        header = next(reader)
    except StopIteration:
        return [], [ParseIssue(1, "empty file")]
    columns = [_normalize_header(cell) for cell in header]
    if "close" not in columns or "open" not in columns:
        return [], [ParseIssue(1, "header needs Open and Close/Last")]
    bars: list[Bar] = []
    issues: list[ParseIssue] = []
    for line_number, row in enumerate(reader, start=2):
        if not row or all(not cell.strip() for cell in row):
            continue
        if len(row) < len(columns):
            issues.append(ParseIssue(line_number, "partial row"))
            continue
        mapped = {columns[index]: row[index].strip() for index in range(len(columns))}
        try:
            bar = _row_to_bar(mapped, config)
        except (ValueError, InvalidOperation) as exc:
            issues.append(ParseIssue(line_number, str(exc)))
            continue
        if not _ohlc_ok(bar):
            issues.append(ParseIssue(line_number, "invalid OHLC"))
            continue
        bars.append(bar)
    bars.sort(key=lambda bar: bar.timestamp)
    return bars, issues


def closed_bars(
    bars: list[Bar], timeframe_seconds: int, now: datetime
) -> tuple[list[Bar], int]:
    kept = [bar for bar in bars if bar_end(bar.timestamp, timeframe_seconds) <= now]
    return kept, len(bars) - len(kept)


def quality_report(
    bars: list[Bar],
    timeframe_seconds: int,
    *,
    n_rejected: int = 0,
    n_conflicts: int = 0,
    n_forming_dropped: int = 0,
) -> QualityReport:
    fatal: list[str] = []
    gaps: list[str] = []
    for index, bar in enumerate(bars):
        if not _ohlc_ok(bar):
            fatal.append(f"invalid OHLC at {format_utc(bar.timestamp)}")
        if index and bar.timestamp <= bars[index - 1].timestamp:
            fatal.append(f"duplicate or unsorted at {format_utc(bar.timestamp)}")
        elif index:
            delta = bar.timestamp - bars[index - 1].timestamp
            if delta > timedelta(seconds=timeframe_seconds * 1.5):
                gaps.append(format_utc(bars[index - 1].timestamp))
    return QualityReport(
        n_bars=len(bars),
        n_gaps=len(gaps),
        n_rejected=n_rejected,
        n_conflicts=n_conflicts,
        n_forming_dropped=n_forming_dropped,
        fatal=tuple(fatal),
        gap_examples=tuple(gaps[:5]),
    )


def resample(bars: list[Bar], source_seconds: int, target_seconds: int) -> tuple[list[Bar], int]:
    if target_seconds < source_seconds or target_seconds % source_seconds != 0:
        raise ValueError("target timeframe must be a multiple of the source timeframe")
    if target_seconds == source_seconds:
        return list(bars), 0
    ratio = target_seconds // source_seconds
    groups: dict[int, list[Bar]] = {}
    for bar in bars:
        epoch = int(bar.timestamp.timestamp())
        if epoch % source_seconds != 0:
            continue
        bucket = epoch // target_seconds * target_seconds
        groups.setdefault(bucket, []).append(bar)
    built: list[Bar] = []
    dropped = 0
    for bucket in sorted(groups):
        group = sorted(groups[bucket], key=lambda bar: bar.timestamp)
        if not _bucket_complete(group, bucket, source_seconds, ratio):
            dropped += 1
            continue
        built.append(_merge(group))
    return built, dropped


def _bucket_complete(group: list[Bar], bucket: int, source_seconds: int, ratio: int) -> bool:
    if len(group) != ratio:
        return False
    if int(group[0].timestamp.timestamp()) != bucket:
        return False
    for previous, current in zip(group, group[1:]):
        if current.timestamp - previous.timestamp != timedelta(seconds=source_seconds):
            return False
    return True


def _merge(group: list[Bar]) -> Bar:
    return Bar(
        timestamp=group[0].timestamp,
        open=group[0].open,
        high=max(bar.high for bar in group),
        low=min(bar.low for bar in group),
        close=group[-1].close,
        volume=_sum_optional([bar.volume for bar in group]),
        bid_volume=_sum_optional([bar.bid_volume for bar in group]),
        ask_volume=_sum_optional([bar.ask_volume for bar in group]),
    )


def _sum_optional(values: list[Decimal | None]) -> Decimal | None:
    if any(value is None for value in values):
        return None
    return sum(values, Decimal("0"))


def _normalize_header(cell: str) -> str:
    key = " ".join(cell.strip().lower().replace("_", " ").split())
    compact = key.replace(" ", "")
    return _HEADER_ALIASES.get(key) or _HEADER_ALIASES.get(compact) or key


def _row_to_bar(mapped: dict[str, str], config: EngineConfig) -> Bar:
    if "datetime" in mapped and "date" not in mapped:
        moment = localize(mapped["datetime"], None, config.source_timezone)
    else:
        moment = localize(mapped.get("date", ""), mapped.get("time"), config.source_timezone)
    if not config.timestamp_is_bar_open:
        moment = moment - timedelta(seconds=config.timeframe_seconds)
    return Bar(
        timestamp=moment,
        open=_decimal(mapped["open"], "open"),
        high=_decimal(mapped["high"], "high"),
        low=_decimal(mapped["low"], "low"),
        close=_decimal(mapped["close"], "close"),
        volume=_optional_decimal(mapped.get("volume", "")),
        bid_volume=_optional_decimal(mapped.get("bid_volume", "")),
        ask_volume=_optional_decimal(mapped.get("ask_volume", "")),
    )


def _decimal(text: str, field: str) -> Decimal:
    cleaned = text.replace(",", "")
    if not cleaned:
        raise ValueError(f"missing {field}")
    value = Decimal(cleaned)
    if not value.is_finite():
        raise ValueError(f"invalid {field}")
    return value


def _optional_decimal(text: str) -> Decimal | None:
    if text is None or not str(text).strip():
        return None
    return Decimal(str(text).replace(",", ""))


def _ohlc_ok(bar: Bar) -> bool:
    prices = bar.price_tuple()
    if any(price <= 0 for price in prices):
        return False
    if bar.high < bar.low:
        return False
    if bar.high < max(bar.open, bar.close):
        return False
    if bar.low > min(bar.open, bar.close):
        return False
    for volume in (bar.volume, bar.bid_volume, bar.ask_volume):
        if volume is not None and volume < 0:
            return False
    return True
