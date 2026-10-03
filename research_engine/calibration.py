"""Scores for published probabilities. Overlapping hourly forecasts are not independent."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

from research_engine.records import StoredForecast
from research_engine.targets import DOWN, FLAT, UP

_EPS = Decimal("1e-15")
_BINS = (
    (Decimal("0"), Decimal("0.2")),
    (Decimal("0.2"), Decimal("0.4")),
    (Decimal("0.4"), Decimal("0.6")),
    (Decimal("0.6"), Decimal("0.8")),
    (Decimal("0.8"), Decimal("1.0000001")),
)


@dataclass(frozen=True)
class ReliabilityBin:
    low: Decimal
    high: Decimal
    count: int
    up_rate: Decimal | None


@dataclass(frozen=True)
class CalibrationReport:
    n_published: int
    n_nonoverlapping: int
    brier: Decimal | None
    brier_nonoverlapping: Decimal | None
    log_loss: Decimal | None
    log_loss_nonoverlapping: Decimal | None
    reliability: tuple[ReliabilityBin, ...]


def calibration(rows: list[StoredForecast]) -> CalibrationReport:
    published = [
        row
        for row in rows
        if row.actual_status == "resolved"
        and row.draft.probability_status == "empirical"
        and row.actual_class is not None
    ]
    spaced = _nonoverlapping(published)
    return CalibrationReport(
        n_published=len(published),
        n_nonoverlapping=len(spaced),
        brier=_mean_score(published, _brier_one),
        brier_nonoverlapping=_mean_score(spaced, _brier_one),
        log_loss=_mean_score(published, _log_loss_one),
        log_loss_nonoverlapping=_mean_score(spaced, _log_loss_one),
        reliability=tuple(_reliability(published)),
    )


def _nonoverlapping(rows: list[StoredForecast]) -> list[StoredForecast]:
    kept: list[StoredForecast] = []
    next_allowed: dict[tuple[str, str], datetime] = {}
    for row in sorted(rows, key=lambda item: item.draft.decision_time):
        key = (row.draft.definition_id, format(row.draft.horizon_hours, "f"))
        if row.draft.decision_time < next_allowed.get(key, row.draft.decision_time):
            continue
        kept.append(row)
        horizon = timedelta(seconds=int(row.draft.horizon_hours * 3600))
        next_allowed[key] = row.draft.decision_time + horizon
    return kept


def _mean_score(rows: list[StoredForecast], score) -> Decimal | None:
    if not rows:
        return None
    total = sum((score(row) for row in rows), Decimal("0"))
    return total / Decimal(len(rows))


def _probabilities(row: StoredForecast) -> dict[str, Decimal]:
    draft = row.draft
    n = draft.n_up + draft.n_down + draft.n_flat
    return {
        UP: Decimal(draft.n_up) / Decimal(n),
        DOWN: Decimal(draft.n_down) / Decimal(n),
        FLAT: Decimal(draft.n_flat) / Decimal(n),
    }


def _brier_one(row: StoredForecast) -> Decimal:
    probabilities = _probabilities(row)
    total = Decimal("0")
    for klass in (UP, DOWN, FLAT):
        outcome = Decimal(1 if row.actual_class == klass else 0)
        total += (probabilities[klass] - outcome) ** 2
    return total


def _log_loss_one(row: StoredForecast) -> Decimal:
    probabilities = _probabilities(row)
    probability = probabilities[row.actual_class or UP]
    if probability < _EPS:
        probability = _EPS
    return -probability.ln()


def _reliability(rows: list[StoredForecast]) -> list[ReliabilityBin]:
    bins: list[ReliabilityBin] = []
    for low, high in _BINS:
        members = []
        for row in rows:
            probability = _probabilities(row)[UP]
            inclusive_last = high > 1 and probability <= Decimal(1)
            if low <= probability < high or inclusive_last:
                members.append(row)
        if not members:
            bins.append(ReliabilityBin(low, min(high, Decimal(1)), 0, None))
            continue
        ups = sum(1 for row in members if row.actual_class == UP)
        bins.append(
            ReliabilityBin(low, min(high, Decimal(1)), len(members), Decimal(ups) / Decimal(len(members)))
        )
    return bins
