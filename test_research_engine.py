"""Causal journal tests. Synthetic prices only; nothing here is a market forecast."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from research_engine.bars import closed_bars, parse_sierra_csv, quality_report, resample
from research_engine.calibration import calibration
from research_engine.clock import parse_timeframe, session_label
from research_engine.config import EngineConfig
from research_engine.fundamentals import visible_events
from research_engine.model import eligible_indices, nearest_indices, nearest_rank, walk_forward
from research_engine.pipeline import execute
from research_engine.records import Bar, Event, ExternalSignal, Feature, ForecastDraft, StoredForecast
from research_engine.sources import bars_from_ohlc
from research_engine.strength import build_proposal, proposal_for_feature, render_proposal
from research_engine.store import Journal
from research_engine.targets import DOWN, FLAT, UP, classify, label_at

LONDON = ZoneInfo("Europe/London")


def _bar(open_time: datetime, close: str, spread: str = "0.0002") -> Bar:
    close_price = Decimal(close)
    open_price = close_price - Decimal(spread)
    return Bar(
        timestamp=open_time,
        open=open_price,
        high=close_price,
        low=open_price,
        close=close_price,
    )


def _asia_series(extra_hours: int = 3) -> list[Bar]:
    """Contiguous hourly bars starting at London 00:00 on 2 Jul 2026."""
    bars = []
    for hour in range(7 + extra_hours):
        end = datetime(2026, 7, 2, hour, 0, tzinfo=LONDON)
        open_time = (end - timedelta(hours=1)).astimezone(timezone.utc)
        close = Decimal("1.1000") + Decimal("0.0002") * hour
        bars.append(_bar(open_time, format(close, "f")))
    return bars


def _config(**overrides) -> EngineConfig:
    base = dict(
        timeframe_seconds=3600,
        horizons_hours=(Decimal("1"),),
        min_samples=5,
        atr_period=1,
        sma_period=1,
        analogue_k=5,
        flat_band_pips=Decimal("1"),
        pip_size=Decimal("0.0001"),
    )
    base.update(overrides)
    return EngineConfig(**base)


def _csv(bars: list[Bar]) -> str:
    lines = ["Date,Time,Open,High,Low,Close"]
    for bar in bars:
        moment = bar.timestamp.astimezone(timezone.utc)
        lines.append(
            f"{moment:%Y-%m-%d},{moment:%H:%M:%S},{bar.open},{bar.high},{bar.low},{bar.close}"
        )
    return "\n".join(lines) + "\n"


def _draft(decision: datetime, **overrides) -> ForecastDraft:
    payload = dict(
        symbol="EURUSD",
        timeframe_seconds=3600,
        decision_time=decision,
        horizon_hours=Decimal("1"),
        model_name="bucket_empirical",
        model_version="0.1.0",
        definition_id="test-definition",
        trigger_reason="hourly",
        bucket="asia|trend_flat",
        probability_status="empirical",
        n_samples=1,
        n_up=1,
        n_down=0,
        n_flat=0,
        q25_pips=Decimal("2"),
        q75_pips=Decimal("2"),
        analogue_status="withheld",
        analogue_n=0,
        analogue_n_up=0,
        analogue_n_down=0,
        analogue_n_flat=0,
        analogue_median_pips=None,
        feature={"features": {}, "events": [], "external_signals": []},
        volume_kind="unspecified",
    )
    payload.update(overrides)
    return ForecastDraft(**payload)


def _stored(draft: ForecastDraft, actual: str, when: datetime) -> StoredForecast:
    return StoredForecast(
        draft=draft,
        actual_status="resolved",
        actual_class=actual,
        actual_gross_pips=Decimal("2"),
        actual_time=when,
        created_at=when,
    )


class ResearchEngineTests(unittest.TestCase):
    def test_sessions_use_london_clock_including_summer_time(self):
        self.assertEqual(session_label(datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc), "Europe/London"), "overlap")
        self.assertEqual(session_label(datetime(2026, 1, 15, 12, 0, tzinfo=timezone.utc), "Europe/London"), "london")
        self.assertEqual(session_label(datetime(2026, 1, 15, 0, 30, tzinfo=timezone.utc), "Europe/London"), "asia")
        self.assertEqual(parse_timeframe("15m"), 900)
        self.assertEqual(parse_timeframe("4h"), 14400)

    def test_label_band_and_gap(self):
        self.assertEqual(classify(Decimal("1"), Decimal("1")), FLAT)
        self.assertEqual(classify(Decimal("1.000001"), Decimal("1")), UP)
        self.assertEqual(classify(Decimal("-1"), Decimal("1")), FLAT)
        self.assertEqual(classify(Decimal("-1.000001"), Decimal("1")), DOWN)
        bars = _asia_series(0)
        config = _config()
        self.assertEqual(label_at(bars, 1, 1, config).klass, UP)
        gapped = [bars[0], bars[2]]
        self.assertIsNone(label_at(gapped, 0, 1, config))

    def test_parser_rejects_partial_and_bad_ohlc(self):
        text = "\n".join(
            [
                "Date,Time,Open,High,Low,Last,Volume",
                "2026/01/05,08:00:00,1.17000,1.17040,1.16980,1.17020,100",
                "2026-01-05,09:00:00,1.17,1.16,1.18,1.17,10",
                "2026-01-05,10:00:00,1.17,1.18",
            ]
        )
        bars, issues = parse_sierra_csv(text, _config())
        self.assertEqual(len(bars), 1)
        self.assertEqual(bars[0].close, Decimal("1.17020"))
        self.assertEqual([issue.reason for issue in issues], ["invalid OHLC", "partial row"])

    def test_forming_bar_and_resample(self):
        start = datetime(2026, 1, 5, 8, 0, tzinfo=timezone.utc)
        bars = []
        for step in range(7):
            moment = start + timedelta(minutes=15 * step)
            bars.append(_bar(moment, format(Decimal("1.17000") + Decimal("0.0001") * step, "f"), "0.0001"))
        now = datetime(2026, 1, 5, 9, 30, tzinfo=timezone.utc)
        closed, dropped = closed_bars(bars, 900, now)
        self.assertEqual(dropped, 1)
        self.assertEqual(len(closed), 6)
        hourly, partial = resample(closed[:4], 900, 3600)
        self.assertEqual(len(hourly), 1)
        self.assertEqual(hourly[0].open, closed[0].open)
        self.assertEqual(hourly[0].close, closed[3].close)
        self.assertEqual(partial, 0)
        _, dropped_partial = resample(closed[:3], 900, 3600)
        self.assertEqual(dropped_partial, 1)

    def test_features_ignore_a_later_high_on_the_same_day(self):
        from research_engine.features import compute_features

        bars = _asia_series(3)
        config = _config()
        original = compute_features(bars, config)[3]
        spiked = list(bars)
        spiked[8] = replace(spiked[8], high=Decimal("9"))
        again = compute_features(spiked, config)[3]
        self.assertEqual(original.dist_day_high_pips, again.dist_day_high_pips)
        self.assertEqual(original.bucket, "asia|trend_flat")

    def test_walk_forward_rate_and_future_close_do_not_change_it(self):
        config = _config()
        bars = _asia_series(3)
        drafts = walk_forward(bars, config, "backfill")
        target = datetime(2026, 7, 2, 6, 0, tzinfo=LONDON).astimezone(timezone.utc)
        matched = [draft for draft in drafts if draft.decision_time == target]
        self.assertEqual(len(matched), 1)
        draft = matched[0]
        self.assertEqual(draft.probability_status, "empirical")
        self.assertEqual((draft.n_samples, draft.n_up, draft.n_down, draft.n_flat), (5, 5, 0, 0))
        earlier = [item for item in drafts if item.decision_time < target]
        self.assertTrue(all(item.probability_status == "withheld" for item in earlier))

        crashed = list(bars)
        crashed[7] = replace(crashed[7], close=Decimal("1.0000"), high=Decimal("1.1000"), low=Decimal("1.0000"), open=Decimal("1.0900"))
        again = [item for item in walk_forward(crashed, config, "backfill") if item.decision_time == target][0]
        self.assertEqual((again.n_up, again.n_samples, again.probability_status), (5, 5, "empirical"))
        prefix = [item for item in walk_forward(bars[:7], config, "backfill") if item.decision_time == target][0]
        self.assertEqual((prefix.n_up, prefix.q25_pips, prefix.analogue_n), (draft.n_up, draft.q25_pips, draft.analogue_n))

    def test_events_and_signals_do_not_change_the_rate(self):
        config = _config()
        bars = _asia_series(3)
        target = datetime(2026, 7, 2, 6, 0, tzinfo=LONDON).astimezone(timezone.utc)
        event = Event(target - timedelta(hours=1), "CPI", "USD", 3, Decimal("0.3"), Decimal("0.2"), Decimal("0.4"), "scheduled")
        future = Event(target + timedelta(hours=2), "NFP", "USD", 3, Decimal("200"), Decimal("180"), None, "scheduled")
        signal = ExternalSignal("ROTOR", bars[6].timestamp - timedelta(hours=1), Decimal("0.72"), "LONG")
        later_signal = ExternalSignal("ROTOR", bars[8].timestamp, Decimal("9"), "SHORT")
        plain = walk_forward(bars, config, "hourly")
        rich = walk_forward(bars, config, "hourly", [event, future], [signal, later_signal])
        plain_row = next(item for item in plain if item.decision_time == target)
        rich_row = next(item for item in rich if item.decision_time == target)
        self.assertEqual((plain_row.n_up, plain_row.n_samples), (rich_row.n_up, rich_row.n_samples))
        self.assertEqual(rich_row.feature["events"][0]["name"], "CPI")
        self.assertNotIn("NFP", [item["name"] for item in rich_row.feature["events"]])
        self.assertEqual(rich_row.feature["events"][0]["surprise"], "0.1")
        self.assertEqual(rich_row.feature["external_signals"][0]["value"], "0.72")
        self.assertEqual(len(visible_events([future], target)), 0)

    def test_analogues_cannot_see_an_unresolved_future(self):
        feature_ok = [True] * 12
        label_ok = [True] * 12
        chosen = eligible_indices(10, 3, feature_ok, label_ok)
        self.assertNotIn(8, chosen)
        self.assertIn(7, chosen)
        self.assertTrue(all(index + 3 <= 10 for index in chosen))
        current = [Decimal("0"), Decimal("1")]
        candidates = [(index, [Decimal(index), Decimal("0")]) for index in range(6)]
        candidates.append((6, [Decimal("0"), Decimal("1")]))
        neighbors = nearest_indices([(index, vector) for index, vector in candidates if index + 1 <= 5], current, 3)
        self.assertNotIn(6, neighbors)

    def test_journal_keeps_the_first_forecast_and_resolves_once(self):
        config = _config()
        bars = _asia_series(3)
        with tempfile.TemporaryDirectory() as tmp:
            result = execute(_csv(bars), config, str(Path(tmp) / "j.sqlite"), datetime(2026, 8, 1, tzinfo=timezone.utc), trigger="hourly", backfill=True)
            self.assertEqual(result.exit_code, 0)
            self.assertIn("не торговый сигнал", result.report)
            self.assertIn("close-to-close", result.report)
            self.assertIn("опубликованной частотой: 1 из", result.report)
            self.assertIn("вероятность не публикуется", result.report)
            journal = Journal(str(Path(tmp) / "j.sqlite"))
            stored = journal.load_forecasts("EURUSD", 3600)
            empirical = [row for row in stored if row.draft.probability_status == "empirical"]
            self.assertTrue(empirical)
            self.assertTrue(any(row.actual_status == "resolved" for row in empirical))
            again = journal.save_forecast(replace(empirical[0].draft, n_up=1, n_samples=99))
            self.assertEqual(again, "exists")
            reloaded = journal.load_forecasts("EURUSD", 3600)
            self.assertEqual(reloaded[stored.index(empirical[0])].draft.n_samples, empirical[0].draft.n_samples)
            resolved_before = sum(row.actual_status == "resolved" for row in reloaded)
            journal.resolve(config)
            resolved_after = sum(row.actual_status == "resolved" for row in journal.load_forecasts("EURUSD", 3600))
            self.assertEqual(resolved_before, resolved_after)

    def test_conflict_is_immutable_and_gap_becomes_unavailable(self):
        config = _config()
        with tempfile.TemporaryDirectory() as tmp:
            journal = Journal(str(Path(tmp) / "j.sqlite"))
            first = _bar(datetime(2026, 1, 5, 8, 0, tzinfo=timezone.utc), "1.1700")
            changed = replace(first, close=Decimal("1.1800"), high=Decimal("1.1800"))
            later = _bar(datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc), "1.1710")
            self.assertEqual(journal.insert_bars("EURUSD", 3600, [first])[0], 1)
            inserted, _duplicates, conflicts = journal.insert_bars("EURUSD", 3600, [changed, later])
            self.assertEqual((inserted, conflicts), (1, 1))
            self.assertEqual(journal.load_bars("EURUSD", 3600)[0].close, Decimal("1.1700"))
            decision = datetime(2026, 1, 5, 9, 0, tzinfo=timezone.utc)
            draft = _draft(decision, definition_id=config.definition_id(), model_name=config.model_name, model_version=config.model_version)
            self.assertEqual(journal.save_forecast(draft), "inserted")
            resolved, unavailable = journal.resolve(config)
            self.assertEqual((resolved, unavailable), (0, 1))
            self.assertEqual(journal.load_forecasts("EURUSD", 3600)[0].actual_status, "unavailable")

    def test_calibration_scores_only_published_rows(self):
        start = datetime(2026, 1, 5, 8, 0, tzinfo=timezone.utc)
        wrong = _stored(_draft(start, n_up=1, n_down=0, n_flat=0), DOWN, start)
        self.assertEqual(calibration([wrong]).brier, Decimal(2))
        withheld = _stored(
            _draft(start, probability_status="withheld", n_samples=4, n_up=0, n_down=0, n_flat=0),
            UP,
            start,
        )
        self.assertEqual(calibration([withheld]).n_published, 0)
        rows = []
        for offset, actual in ((0, UP), (1, DOWN), (2, UP)):
            moment = start + timedelta(hours=offset)
            rows.append(
                _stored(
                    _draft(moment, horizon_hours=Decimal("2"), n_samples=5, n_up=4, n_down=1, n_flat=0),
                    actual,
                    moment,
                )
            )
        report = calibration(rows)
        self.assertEqual(report.n_published, 3)
        self.assertEqual(report.n_nonoverlapping, 2)
        populated = [item for item in report.reliability if item.count]
        self.assertEqual(populated[0].count, 3)
        self.assertEqual(populated[0].up_rate, Decimal(2) / Decimal(3))
        self.assertEqual(nearest_rank([Decimal(index) for index in range(1, 5)], Decimal("0.25")), Decimal(1))
        self.assertEqual(nearest_rank([Decimal(index) for index in range(1, 5)], Decimal("0.75")), Decimal(3))

    def test_quality_flags_gaps_without_calling_them_fatal(self):
        bars = [
            _bar(datetime(2026, 1, 5, 8, 0, tzinfo=timezone.utc), "1.17"),
            _bar(datetime(2026, 1, 5, 11, 0, tzinfo=timezone.utc), "1.18"),
        ]
        report = quality_report(bars, 3600)
        self.assertTrue(report.ok)
        self.assertEqual(report.n_gaps, 1)

    def test_cli_sample_does_not_invent_a_probability(self):
        root = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory() as tmp:
            db = str(Path(tmp) / "j.sqlite")
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "research_engine",
                    "run",
                    "--csv",
                    str(root / "research_engine" / "examples" / "eurusd_sample.csv"),
                    "--db",
                    db,
                    "--now",
                    "2026-02-01T00:00:00Z",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("не торговый сигнал", completed.stdout)
            self.assertIn("Нет ни одного бара с полным окном признаков", completed.stdout)
            self.assertNotIn("эмпирическая частота прошлого", completed.stdout)

    def test_two_hour_strength_compares_layers_and_ignores_future_events(self):
        decision = datetime(2026, 7, 2, 10, 0, tzinfo=timezone.utc)
        feature = _feature(decision, Decimal("1"), Decimal("-1"))
        events = [
            Event(decision, "sanctions", "USD", 3, None, None, None, "geopolitical", eurusd_sign=-1),
            Event(decision - timedelta(minutes=30), "CPI", "USD", 3, Decimal("0.3"), Decimal("0.2"), None, "scheduled"),
            Event(decision + timedelta(hours=1), "NFP", "USD", 3, Decimal("1"), Decimal("1"), None, "scheduled", 1),
            Event(decision - timedelta(hours=49), "old shock", "EUR", 3, None, None, None, "geopolitical", 1),
        ]
        proposal = proposal_for_feature(feature, events, decision + timedelta(minutes=2), "csv test")
        self.assertEqual(proposal.status, "published")
        self.assertEqual(proposal.delay_seconds, 120)
        self.assertEqual(proposal.layers[0].score, Decimal("-1"))
        self.assertIsNone(proposal.layers[1].score)
        self.assertEqual(proposal.combined, Decimal("-1") / Decimal(3))
        self.assertEqual(proposal.direction, "down")
        self.assertEqual(proposal.strength, Decimal(1) / Decimal(3))
        self.assertTrue(proposal.disagreement)
        text = render_proposal(proposal)
        self.assertIn("sanctions", text)
        self.assertIn("CPI", text)
        self.assertNotIn("NFP", text)
        self.assertNotIn("old shock", text)
        self.assertIn("не вероятность", text)
        self.assertIn("Сила предложения", text)

    def test_stale_slot_does_not_publish_strength(self):
        decision = datetime(2026, 7, 2, 10, 0, tzinfo=timezone.utc)
        proposal = proposal_for_feature(_feature(decision, Decimal("1"), Decimal("1")), [], decision + timedelta(hours=3), "csv")
        self.assertEqual(proposal.status, "withheld")
        self.assertIsNone(proposal.strength)
        self.assertIn("не публикуется", render_proposal(proposal))

    def test_proposal_uses_the_latest_even_utc_hour_only(self):
        start = datetime(2026, 7, 2, 6, 0, tzinfo=timezone.utc)
        bars = [
            _bar(start + timedelta(hours=i), format(Decimal("1.1000") + Decimal("0.0002") * i, "f"))
            for i in range(5)
        ]
        now = datetime(2026, 7, 2, 11, 2, tzinfo=timezone.utc)
        proposal = build_proposal(bars, _config(), [], now, "csv")
        self.assertEqual(proposal.decision_time, datetime(2026, 7, 2, 10, 0, tzinfo=timezone.utc))
        kept = bars_from_ohlc(
            [
                (datetime(2026, 7, 2, 8, 0, tzinfo=timezone.utc), 1.1, 1.11, 1.09, 1.1),
                (datetime(2026, 7, 2, 11, 0, tzinfo=LONDON), 1.1, 1.11, 1.09, 1.1),
                (datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc), 1.1, 1.11, 1.09, 1.1),
            ],
            datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc),
            3600,
        )
        self.assertEqual(
            [bar.timestamp for bar in kept],
            [
                datetime(2026, 7, 2, 8, 0, tzinfo=timezone.utc),
                datetime(2026, 7, 2, 10, 0, tzinfo=timezone.utc),
            ],
        )

    def test_proposal_journal_keeps_the_first_reading(self):
        decision = datetime(2026, 7, 2, 10, 0, tzinfo=timezone.utc)
        proposal = proposal_for_feature(_feature(decision, Decimal("1"), Decimal("1")), [], decision + timedelta(minutes=2), "csv")
        with tempfile.TemporaryDirectory() as tmp:
            journal = Journal(str(Path(tmp) / "j.sqlite"))
            self.assertEqual(journal.save_proposal("EURUSD", "0.1.0", proposal), "inserted")
            self.assertEqual(journal.save_proposal("EURUSD", "0.1.0", proposal), "exists")


def _feature(decision: datetime, technical: Decimal, candle: Decimal) -> Feature:
    bullish = candle > 0
    bearish = candle < 0
    return Feature(
        bar_index=1,
        decision_time=decision,
        bar_open=decision - timedelta(hours=1),
        session="london",
        bucket="london|trend_up",
        h1_trend_score=technical,
        h4_score=technical,
        momentum=technical,
        acceleration=None,
        atr=Decimal("0.001"),
        atr_percentile=None,
        adr_completion=None,
        dist_day_high_pips=Decimal("1"),
        dist_day_low_pips=Decimal("1"),
        bullish_engulfing=bullish,
        bearish_engulfing=bearish,
        bullish_pin=False,
        bearish_pin=False,
        inside_bar=False,
        broke_london_high=False,
        broke_london_low=False,
        volume_imbalance=None,
    )


if __name__ == "__main__":
    unittest.main()
