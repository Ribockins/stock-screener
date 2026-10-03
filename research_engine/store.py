"""Immutable bars and a first-write-wins forecast journal."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from research_engine.clock import bar_end, format_utc, parse_utc
from research_engine.config import EngineConfig
from research_engine.records import Bar, ForecastDraft, StoredForecast
from research_engine.targets import classify

_SCHEMA = """
CREATE TABLE IF NOT EXISTS bars (
    symbol TEXT NOT NULL,
    timeframe_seconds INTEGER NOT NULL,
    bar_open TEXT NOT NULL,
    open TEXT NOT NULL,
    high TEXT NOT NULL,
    low TEXT NOT NULL,
    close TEXT NOT NULL,
    volume TEXT,
    bid_volume TEXT,
    ask_volume TEXT,
    ingested_at TEXT NOT NULL,
    PRIMARY KEY (symbol, timeframe_seconds, bar_open)
);
CREATE TABLE IF NOT EXISTS forecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    timeframe_seconds INTEGER NOT NULL,
    decision_time TEXT NOT NULL,
    horizon_hours TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    definition_id TEXT NOT NULL,
    trigger_reason TEXT NOT NULL,
    bucket TEXT,
    probability_status TEXT NOT NULL,
    n_samples INTEGER NOT NULL,
    n_up INTEGER NOT NULL,
    n_down INTEGER NOT NULL,
    n_flat INTEGER NOT NULL,
    q25_pips TEXT,
    q75_pips TEXT,
    analogue_status TEXT NOT NULL,
    analogue_n INTEGER NOT NULL,
    analogue_n_up INTEGER NOT NULL,
    analogue_n_down INTEGER NOT NULL,
    analogue_n_flat INTEGER NOT NULL,
    analogue_median_pips TEXT,
    feature_json TEXT NOT NULL,
    volume_kind TEXT NOT NULL,
    actual_status TEXT NOT NULL,
    actual_class TEXT,
    actual_gross_pips TEXT,
    actual_time TEXT,
    created_at TEXT NOT NULL,
    UNIQUE (
        symbol, timeframe_seconds, decision_time, horizon_hours,
        model_name, model_version, definition_id
    )
);
CREATE TABLE IF NOT EXISTS direction_proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    decision_time TEXT NOT NULL,
    model_version TEXT NOT NULL,
    source TEXT NOT NULL,
    delay_seconds INTEGER,
    status TEXT NOT NULL,
    direction TEXT NOT NULL,
    strength TEXT,
    combined TEXT,
    disagreement INTEGER NOT NULL,
    geopolitical TEXT,
    fundamental TEXT,
    technical TEXT,
    candle TEXT,
    detail_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (symbol, decision_time, model_version)
);
"""


class Journal:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def insert_bars(self, symbol: str, timeframe_seconds: int, bars: list[Bar]) -> tuple[int, int, int]:
        inserted = duplicates = conflicts = 0
        now = format_utc(datetime.now(timezone.utc))
        with self._connect() as conn:
            for bar in bars:
                key = (symbol, timeframe_seconds, format_utc(bar.timestamp))
                row = conn.execute(
                    """
                    SELECT open, high, low, close, volume, bid_volume, ask_volume
                    FROM bars WHERE symbol=? AND timeframe_seconds=? AND bar_open=?
                    """,
                    key,
                ).fetchone()
                if row is None:
                    conn.execute(
                        """
                        INSERT INTO bars (
                            symbol, timeframe_seconds, bar_open, open, high, low, close,
                            volume, bid_volume, ask_volume, ingested_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        key
                        + (
                            _text(bar.open),
                            _text(bar.high),
                            _text(bar.low),
                            _text(bar.close),
                            _text(bar.volume),
                            _text(bar.bid_volume),
                            _text(bar.ask_volume),
                            now,
                        ),
                    )
                    inserted += 1
                    continue
                existing = (
                    Decimal(row[0]),
                    Decimal(row[1]),
                    Decimal(row[2]),
                    Decimal(row[3]),
                    _opt(row[4]),
                    _opt(row[5]),
                    _opt(row[6]),
                )
                incoming = (
                    bar.open,
                    bar.high,
                    bar.low,
                    bar.close,
                    bar.volume,
                    bar.bid_volume,
                    bar.ask_volume,
                )
                if existing == incoming:
                    duplicates += 1
                else:
                    conflicts += 1
        return inserted, duplicates, conflicts

    def load_bars(self, symbol: str, timeframe_seconds: int) -> list[Bar]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT bar_open, open, high, low, close, volume, bid_volume, ask_volume
                FROM bars WHERE symbol=? AND timeframe_seconds=? ORDER BY bar_open
                """,
                (symbol, timeframe_seconds),
            ).fetchall()
        return [
            Bar(
                timestamp=parse_utc(row[0]),
                open=Decimal(row[1]),
                high=Decimal(row[2]),
                low=Decimal(row[3]),
                close=Decimal(row[4]),
                volume=_opt(row[5]),
                bid_volume=_opt(row[6]),
                ask_volume=_opt(row[7]),
            )
            for row in rows
        ]

    def save_forecast(self, draft: ForecastDraft) -> str:
        with self._connect() as conn:
            exists = conn.execute(
                """
                SELECT id FROM forecasts
                WHERE symbol=? AND timeframe_seconds=? AND decision_time=? AND horizon_hours=?
                  AND model_name=? AND model_version=? AND definition_id=?
                """,
                _identity(draft),
            ).fetchone()
            if exists is not None:
                return "exists"
            conn.execute(
                """
                INSERT INTO forecasts (
                    symbol, timeframe_seconds, decision_time, horizon_hours, model_name,
                    model_version, definition_id, trigger_reason, bucket, probability_status,
                    n_samples, n_up, n_down, n_flat, q25_pips, q75_pips, analogue_status,
                    analogue_n, analogue_n_up, analogue_n_down, analogue_n_flat,
                    analogue_median_pips, feature_json, volume_kind, actual_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                _identity(draft)
                + (
                    draft.trigger_reason,
                    draft.bucket,
                    draft.probability_status,
                    draft.n_samples,
                    draft.n_up,
                    draft.n_down,
                    draft.n_flat,
                    _text(draft.q25_pips),
                    _text(draft.q75_pips),
                    draft.analogue_status,
                    draft.analogue_n,
                    draft.analogue_n_up,
                    draft.analogue_n_down,
                    draft.analogue_n_flat,
                    _text(draft.analogue_median_pips),
                    json.dumps(draft.feature, ensure_ascii=False, sort_keys=True),
                    draft.volume_kind,
                    "pending",
                    format_utc(datetime.now(timezone.utc)),
                ),
            )
        return "inserted"

    def load_forecasts(self, symbol: str, timeframe_seconds: int) -> list[StoredForecast]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT symbol, timeframe_seconds, decision_time, horizon_hours, model_name,
                       model_version, definition_id, trigger_reason, bucket, probability_status,
                       n_samples, n_up, n_down, n_flat, q25_pips, q75_pips, analogue_status,
                       analogue_n, analogue_n_up, analogue_n_down, analogue_n_flat,
                       analogue_median_pips, feature_json, volume_kind, actual_status,
                       actual_class, actual_gross_pips, actual_time, created_at
                FROM forecasts
                WHERE symbol=? AND timeframe_seconds=?
                ORDER BY decision_time, horizon_hours
                """,
                (symbol, timeframe_seconds),
            ).fetchall()
        loaded = []
        for row in rows:
            draft = ForecastDraft(
                symbol=row[0],
                timeframe_seconds=row[1],
                decision_time=parse_utc(row[2]),
                horizon_hours=Decimal(row[3]),
                model_name=row[4],
                model_version=row[5],
                definition_id=row[6],
                trigger_reason=row[7],
                bucket=row[8],
                probability_status=row[9],
                n_samples=row[10],
                n_up=row[11],
                n_down=row[12],
                n_flat=row[13],
                q25_pips=_opt(row[14]),
                q75_pips=_opt(row[15]),
                analogue_status=row[16],
                analogue_n=row[17],
                analogue_n_up=row[18],
                analogue_n_down=row[19],
                analogue_n_flat=row[20],
                analogue_median_pips=_opt(row[21]),
                feature=json.loads(row[22]),
                volume_kind=row[23],
            )
            loaded.append(
                StoredForecast(
                    draft=draft,
                    actual_status=row[24],
                    actual_class=row[25],
                    actual_gross_pips=_opt(row[26]),
                    actual_time=parse_utc(row[27]) if row[27] else None,
                    created_at=parse_utc(row[28]),
                )
            )
        return loaded

    def resolve(self, config: EngineConfig) -> tuple[int, int]:
        bars = self.load_bars(config.symbol, config.timeframe_seconds)
        by_open = {format_utc(bar.timestamp): bar for bar in bars}
        latest_end = bar_end(bars[-1].timestamp, config.timeframe_seconds) if bars else None
        resolved = unavailable = 0
        with self._connect() as conn:
            pending = conn.execute(
                """
                SELECT id, decision_time, horizon_hours
                FROM forecasts
                WHERE symbol=? AND timeframe_seconds=? AND actual_status='pending'
                  AND model_name=? AND model_version=? AND definition_id=?
                """,
                (
                    config.symbol,
                    config.timeframe_seconds,
                    config.model_name,
                    config.model_version,
                    config.definition_id(),
                ),
            ).fetchall()
            for row_id, decision_text, hours_text in pending:
                decision_time = parse_utc(decision_text)
                hours = Decimal(hours_text)
                outcome_time = decision_time + timedelta(seconds=int(hours * 3600))
                decision_open = decision_time - timedelta(seconds=config.timeframe_seconds)
                outcome_open = outcome_time - timedelta(seconds=config.timeframe_seconds)
                decision_bar = by_open.get(format_utc(decision_open))
                outcome_bar = by_open.get(format_utc(outcome_open))
                if decision_bar is not None and outcome_bar is not None:
                    gross = (outcome_bar.close - decision_bar.close) / config.pip_size
                    conn.execute(
                        """
                        UPDATE forecasts
                        SET actual_status='resolved', actual_class=?, actual_gross_pips=?, actual_time=?
                        WHERE id=? AND actual_status='pending'
                        """,
                        (
                            classify(gross, config.flat_band_pips),
                            _text(gross),
                            format_utc(outcome_time),
                            row_id,
                        ),
                    )
                    resolved += 1
                elif latest_end is not None and latest_end >= outcome_time:
                    conn.execute(
                        "UPDATE forecasts SET actual_status='unavailable' WHERE id=? AND actual_status='pending'",
                        (row_id,),
                    )
                    unavailable += 1
        return resolved, unavailable

    def save_proposal(self, symbol: str, model_version: str, proposal) -> str:
        decision = format_utc(proposal.decision_time)
        with self._connect() as conn:
            existing = conn.execute(
                """
                SELECT id FROM direction_proposals
                WHERE symbol=? AND decision_time=? AND model_version=?
                """,
                (symbol, decision, model_version),
            ).fetchone()
            if existing is not None:
                return "exists"
            scores = {layer.name: layer.score for layer in proposal.layers}
            conn.execute(
                """
                INSERT INTO direction_proposals (
                    symbol, decision_time, model_version, source, delay_seconds, status,
                    direction, strength, combined, disagreement, geopolitical, fundamental,
                    technical, candle, detail_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    symbol,
                    decision,
                    model_version,
                    proposal.source,
                    proposal.delay_seconds,
                    proposal.status,
                    proposal.direction,
                    _text(proposal.strength),
                    _text(proposal.combined),
                    1 if proposal.disagreement else 0,
                    _text(scores.get("geopolitical")),
                    _text(scores.get("fundamental")),
                    _text(scores.get("technical")),
                    _text(scores.get("candle")),
                    json.dumps(proposal.detail, ensure_ascii=False, sort_keys=True),
                    format_utc(datetime.now(timezone.utc)),
                ),
            )
        return "inserted"

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)


def _identity(draft: ForecastDraft) -> tuple:
    return (
        draft.symbol,
        draft.timeframe_seconds,
        format_utc(draft.decision_time),
        format(draft.horizon_hours, "f"),
        draft.model_name,
        draft.model_version,
        draft.definition_id,
    )


def _text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, "f")


def _opt(value: str | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(value)
