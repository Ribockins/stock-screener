"""Time, session, and timeframe helpers. Bar grids stay on UTC."""

from __future__ import annotations

import re
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

_TIMEFRAME = re.compile(r"^(\d+)(m|min|h|d)$")


def parse_timeframe(text: str) -> int:
    match = _TIMEFRAME.fullmatch(text.strip().lower())
    if not match:
        raise ValueError(f"unrecognized timeframe: {text!r}")
    count = int(match.group(1))
    unit = match.group(2)
    seconds = {"m": 60, "min": 60, "h": 3600, "d": 86400}[unit]
    if count <= 0:
        raise ValueError(f"unrecognized timeframe: {text!r}")
    return count * seconds


def format_utc(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc(text: str) -> datetime:
    raw = text.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    parsed = datetime.fromisoformat(raw)
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp {text!r} needs a timezone offset")
    return parsed.astimezone(timezone.utc)


def localize(date_text: str, time_text: str | None, source_timezone: str) -> datetime:
    """Interpret a naive chart timestamp in source_timezone and return UTC."""
    date_text = date_text.strip()
    if time_text is None and ("T" in date_text or " " in date_text):
        date_text, _, time_text = date_text.replace("T", " ").partition(" ")
    if not time_text:
        raise ValueError("missing time")
    time_text = time_text.strip()
    if len(time_text) == 5:
        time_text += ":00"
    year, month, day = _parse_date(date_text)
    hour, minute, second = (int(part) for part in time_text.split(":"))
    local = datetime(year, month, day, hour, minute, second, tzinfo=ZoneInfo(source_timezone))
    return local.astimezone(timezone.utc)


def _parse_date(text: str) -> tuple[int, int, int]:
    cleaned = text.replace("/", "-").replace(".", "-")
    parts = cleaned.split("-")
    if len(parts) != 3:
        raise ValueError(f"unrecognized date: {text!r}")
    if len(parts[0]) == 4:
        year, month, day = (int(parts[0]), int(parts[1]), int(parts[2]))
    else:
        raise ValueError(f"date must be YYYY-MM-DD, got {text!r}")
    return year, month, day


def bar_end(bar_open: datetime, timeframe_seconds: int) -> datetime:
    return bar_open + timedelta(seconds=timeframe_seconds)


def horizon_bars(hours, timeframe_seconds: int) -> int | None:
    from decimal import Decimal

    seconds = Decimal(hours) * Decimal(3600)
    step = Decimal(timeframe_seconds)
    if seconds % step != 0:
        return None
    count = int(seconds // step)
    if count <= 0:
        return None
    return count


def session_label(moment: datetime, session_timezone: str) -> str:
    """Session of a completed bar, classified on its end time.

    Half-open London-clock windows: Asia 00:00-07:00, London 07:00-16:00,
    New York 13:00-22:00. The overlap is its own label.
    """
    local_time = moment.astimezone(ZoneInfo(session_timezone)).time()
    london = time(7, 0) <= local_time < time(16, 0)
    new_york = time(13, 0) <= local_time < time(22, 0)
    asia = time(0, 0) <= local_time < time(7, 0)
    if london and new_york:
        return "overlap"
    if london:
        return "london"
    if new_york:
        return "ny"
    if asia:
        return "asia"
    return "off"


def local_date(moment: datetime, session_timezone: str):
    return moment.astimezone(ZoneInfo(session_timezone)).date()
