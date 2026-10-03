"""Timestamped events and external signals. They never write the probability."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from research_engine.clock import parse_utc
from research_engine.records import Event, ExternalSignal


def load_events(text: str) -> list[Event]:
    return [_event(row) for row in _rows(text)]


def load_signals(text: str) -> list[ExternalSignal]:
    loaded = []
    for row in _rows(text):
        loaded.append(
            ExternalSignal(
                name=row["name"].strip(),
                bar_open=parse_utc(row["bar_open"]),
                value=Decimal(row["value"]),
                label=(row.get("label") or "").strip() or None,
            )
        )
    return loaded


def visible_events(events: list[Event], decision_time: datetime) -> list[dict]:
    visible = []
    for event in events:
        if event.available_at > decision_time:
            continue
        surprise = None
        if event.actual is not None and event.forecast is not None:
            surprise = format(event.actual - event.forecast, "f")
        age_hours = (decision_time - event.available_at).total_seconds() / 3600
        visible.append(
            {
                "available_at": event.available_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "name": event.name,
                "currency": event.currency,
                "impact": event.impact,
                "actual": _num(event.actual),
                "forecast": _num(event.forecast),
                "previous": _num(event.previous),
                "kind": event.kind,
                "surprise": surprise,
                "eurusd_sign": event.eurusd_sign,
                "age_hours": round(age_hours, 4),
            }
        )
    return visible


def signals_asof(signals: list[ExternalSignal], bar_open: datetime) -> list[dict]:
    latest: dict[str, ExternalSignal] = {}
    for signal in signals:
        if signal.bar_open <= bar_open:
            current = latest.get(signal.name)
            if current is None or signal.bar_open >= current.bar_open:
                latest[signal.name] = signal
    return [
        {
            "name": signal.name,
            "bar_open": signal.bar_open.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "value": format(signal.value, "f"),
            "label": signal.label,
        }
        for signal in sorted(latest.values(), key=lambda item: item.name)
    ]


def _rows(text: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return []
    return [{(key or "").strip(): (value or "").strip() for key, value in row.items()} for row in reader]


def _event(row: dict[str, str]) -> Event:
    try:
        impact = int(row["impact"]) if row.get("impact") else None
    except ValueError as exc:
        raise ValueError("event impact must be an integer") from exc
    try:
        return Event(
            available_at=parse_utc(row["available_at"]),
            name=row["name"],
            currency=row.get("currency", ""),
            impact=impact,
            actual=_optional(row.get("actual", "")),
            forecast=_optional(row.get("forecast", "")),
            previous=_optional(row.get("previous", "")),
            kind=row.get("kind", "scheduled") or "scheduled",
            eurusd_sign=_sign(row.get("eurusd_sign", "")),
            signs=_signs(row),
        )
    except (KeyError, InvalidOperation) as exc:
        raise ValueError(f"invalid event row: {row}") from exc


def _signs(row: dict[str, str]) -> dict[str, int]:
    columns = {"ng_sign": "NG", "wti_sign": "WTI", "eurusd_sign": "EURUSD", "sign": "*"}
    parsed = {}
    for column, symbol in columns.items():
        if row.get(column):
            value = _sign(row[column])
            if value is not None:
                parsed[symbol] = value
    return parsed


def _sign(text: str) -> int | None:
    if text is None or not str(text).strip():
        return None
    value = int(str(text).strip())
    if value not in (-1, 0, 1):
        raise ValueError("eurusd_sign must be -1, 0, or 1")
    return value


def _optional(text: str) -> Decimal | None:
    if not text:
        return None
    return Decimal(text)


def _num(value: Decimal | None) -> str | None:
    return None if value is None else format(value, "f")
