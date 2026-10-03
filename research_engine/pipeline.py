"""Wire the collector, the causal model, the journal, and the report."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from research_engine.bars import closed_bars, parse_sierra_csv, quality_report, resample
from research_engine.config import EngineConfig
from research_engine.fundamentals import load_events, load_signals
from research_engine.model import unsupported_horizons, walk_forward
from research_engine.report import render
from research_engine.store import Journal


@dataclass(frozen=True)
class RunResult:
    exit_code: int
    report: str


def execute(
    csv_text: str,
    config: EngineConfig,
    db_path: str,
    now: datetime,
    *,
    trigger: str,
    backfill: bool,
    source_seconds: int | None = None,
    events_text: str | None = None,
    signals_text: str | None = None,
) -> RunResult:
    source_seconds = source_seconds or config.timeframe_seconds
    parsed, issues = parse_sierra_csv(csv_text, replace(config, timeframe_seconds=source_seconds))
    closed, forming = closed_bars(parsed, source_seconds, now)
    resample_dropped = 0
    working = closed
    if source_seconds != config.timeframe_seconds:
        working, resample_dropped = resample(closed, source_seconds, config.timeframe_seconds)
    journal = Journal(db_path)
    if not working and not journal.load_bars(config.symbol, config.timeframe_seconds):
        quality = quality_report(
            [],
            config.timeframe_seconds,
            n_rejected=len(issues),
            n_forming_dropped=forming,
        )
        report = render(config, quality, [], resample_dropped=resample_dropped)
        report += "В файле нет закрытых валидных баров. Прогноз не создан.\n"
        return RunResult(2, report)
    inserted, _duplicates, conflicts = journal.insert_bars(config.symbol, config.timeframe_seconds, working)
    del inserted
    bars = journal.load_bars(config.symbol, config.timeframe_seconds)
    events = load_events(events_text) if events_text else []
    signals = load_signals(signals_text) if signals_text else []
    drafts = walk_forward(bars, config, "backfill" if backfill else trigger, events, signals)
    if not backfill and drafts:
        latest = max(draft.decision_time for draft in drafts)
        drafts = [draft for draft in drafts if draft.decision_time == latest]
    for draft in drafts:
        journal.save_forecast(draft)
    journal.resolve(config)
    stored = journal.load_forecasts(config.symbol, config.timeframe_seconds)
    quality = quality_report(
        bars,
        config.timeframe_seconds,
        n_rejected=len(issues),
        n_conflicts=conflicts,
        n_forming_dropped=forming,
    )
    return RunResult(
        0,
        render(
            config,
            quality,
            stored,
            resample_dropped=resample_dropped,
            unsupported=unsupported_horizons(config),
        ),
    )


def refresh(config: EngineConfig, db_path: str) -> RunResult:
    """Resolve matured forecasts and report. Does not read a price file."""
    journal = Journal(db_path)
    journal.resolve(config)
    bars = journal.load_bars(config.symbol, config.timeframe_seconds)
    stored = journal.load_forecasts(config.symbol, config.timeframe_seconds)
    quality = quality_report(bars, config.timeframe_seconds)
    return RunResult(0, render(config, quality, stored, unsupported=unsupported_horizons(config)))
