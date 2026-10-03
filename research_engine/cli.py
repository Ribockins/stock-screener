"""Command line for the research journal.

The process that can see the Sierra export should run this. A cloud agent
does not see C:\\SierraChart\\Data.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from research_engine.bars import closed_bars, parse_sierra_csv
from research_engine.clock import parse_timeframe, parse_utc
from research_engine.config import EngineConfig
from research_engine.fundamentals import load_events
from research_engine.pipeline import execute, refresh
from research_engine.sources import SourceError, fetch_yfinance_bars
from research_engine.store import Journal
from research_engine.strength import build_proposal, describe_sources, render_proposal

MODES = ("hourly", "london-open", "us-open", "macro", "daily")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="research_engine")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="ingest a CSV, journal the causal forecast, resolve matured rows")
    _add_config(run)
    run.add_argument("--csv", required=True)
    run.add_argument("--events")
    run.add_argument("--signals")
    run.add_argument("--mode", choices=MODES, default="hourly")
    run.add_argument("--backfill", action="store_true")
    run.add_argument("--resample", help="working timeframe, for example 1h, when the file is finer")
    run.add_argument("--now", help="UTC timestamp used to drop the still-forming bar")

    learn = sub.add_parser("learn", help="resolve matured journal rows and print calibration")
    _add_config(learn)

    report = sub.add_parser("report", help="print the journal without reading a CSV")
    _add_config(report)

    propose = sub.add_parser("propose", help="two-hour direction strength from the layers on hand")
    _add_config(propose)
    propose.add_argument("--csv")
    propose.add_argument("--source", choices=("csv", "yfinance"), default="csv")
    propose.add_argument("--events")
    propose.add_argument("--now")

    sub.add_parser("sources", help="list price and event sources this process can collect")

    args = parser.parse_args(argv)
    try:
        if args.command == "sources":
            print(describe_sources(), end="")
            return 0
        config = _config_from_args(args)
        if args.command == "propose":
            return _propose(args, config)
        if args.command == "run":
            source_seconds = config.timeframe_seconds
            if args.resample:
                config = replace(config, timeframe_seconds=parse_timeframe(args.resample))
            now = parse_utc(args.now) if args.now else datetime.now(timezone.utc)
            result = execute(
                Path(args.csv).read_text(encoding="utf-8-sig"),
                config,
                args.db,
                now,
                trigger=args.mode,
                backfill=args.backfill,
                source_seconds=source_seconds,
                events_text=Path(args.events).read_text(encoding="utf-8-sig") if args.events else None,
                signals_text=Path(args.signals).read_text(encoding="utf-8-sig") if args.signals else None,
            )
        else:
            result = refresh(config, args.db)
    except (OSError, ValueError, SourceError) as exc:
        print(f"Ошибка чтения: {exc}", file=sys.stderr)
        return 3
    print(result.report, end="")
    return result.exit_code


def _propose(args: argparse.Namespace, config: EngineConfig) -> int:
    now = parse_utc(args.now) if args.now else datetime.now(timezone.utc)
    events = []
    if args.events:
        events = load_events(Path(args.events).read_text(encoding="utf-8-sig"))
    if args.source == "yfinance":
        bars, source_name = fetch_yfinance_bars(config.symbol, now, 3600)
        config = replace(config, timeframe_seconds=3600, volume_kind="yfinance_fx_volume_unused")
    else:
        if not args.csv:
            raise ValueError("для --source csv нужен --csv")
        parsed, _issues = parse_sierra_csv(Path(args.csv).read_text(encoding="utf-8-sig"), config)
        bars, _dropped = closed_bars(parsed, config.timeframe_seconds, now)
        source_name = f"csv {args.csv}"
    proposal = build_proposal(bars, config, events, now, source_name)
    if proposal is None:
        print("Нет закрытого бара на чётной двухчасовой границе UTC.")
        return 2
    journal = Journal(args.db)
    state = journal.save_proposal(config.symbol, config.model_version, proposal)
    print(render_proposal(proposal), end="")
    print(f"Журнал: {state}")
    return 0 if proposal.status == "published" else 0


def _add_config(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db", default="data/research/eurusd.sqlite")
    parser.add_argument("--symbol", default="EURUSD")
    parser.add_argument("--timeframe", default="1h")
    parser.add_argument("--source-timezone", default="UTC")
    parser.add_argument("--pip-size", default="0.0001")
    parser.add_argument("--flat-band-pips", default="1")
    parser.add_argument("--min-samples", type=int, default=30)
    parser.add_argument("--atr-period", type=int, default=14)
    parser.add_argument("--sma-period", type=int, default=20)
    parser.add_argument("--volume-kind", default="unspecified")
    parser.add_argument("--model-version", default="0.1.0")


def _config_from_args(args: argparse.Namespace) -> EngineConfig:
    return EngineConfig(
        symbol=args.symbol,
        timeframe_seconds=parse_timeframe(args.timeframe),
        source_timezone=args.source_timezone,
        pip_size=Decimal(args.pip_size),
        flat_band_pips=Decimal(args.flat_band_pips),
        min_samples=args.min_samples,
        atr_period=args.atr_period,
        sma_period=args.sma_period,
        volume_kind=args.volume_kind,
        model_version=args.model_version,
    )


if __name__ == "__main__":
    raise SystemExit(main())
