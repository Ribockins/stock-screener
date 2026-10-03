"""Causal baseline.

The published rate is the historical frequency of UP/DOWN/FLAT inside one
session-and-trend bucket. Analogues are a separate block and are not blended
into that rate.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_CEILING
from statistics import median

from research_engine.clock import horizon_bars
from research_engine.config import DEFINITION_RULE, EngineConfig
from research_engine.features import analogue_vector, compute_features
from research_engine.fundamentals import signals_asof, visible_events
from research_engine.records import Bar, Event, ExternalSignal, ForecastDraft, Label
from research_engine.targets import DOWN, FLAT, UP, label_at


def eligible_indices(
    decision_index: int,
    horizon_bar_count: int,
    feature_ok: list[bool],
    label_ok: list[bool],
) -> list[int]:
    """Past rows whose outcome bar is already closed at the decision index."""
    chosen = []
    for index in range(decision_index):
        if index + horizon_bar_count <= decision_index and feature_ok[index] and label_ok[index]:
            chosen.append(index)
    return chosen


def nearest_indices(
    candidates: list[tuple[int, list[Decimal]]],
    current: list[Decimal],
    k: int,
) -> list[int]:
    if not candidates:
        return []
    width = len(current)
    means: list[Decimal] = []
    scales: list[Decimal] = []
    for dim in range(width):
        column = [vector[dim] for _, vector in candidates]
        center = sum(column, Decimal("0")) / Decimal(len(column))
        variance = sum((value - center) ** 2 for value in column) / Decimal(len(column))
        scale = variance.sqrt()
        means.append(center)
        scales.append(scale if scale != 0 else Decimal(1))
    ranked: list[tuple[Decimal, int]] = []
    for index, vector in candidates:
        distance = sum(
            (
                (vector[dim] - means[dim]) / scales[dim] - (current[dim] - means[dim]) / scales[dim]
            )
            ** 2
            for dim in range(width)
        )
        ranked.append((distance, index))
    ranked.sort(key=lambda item: (item[0], item[1]))
    return [index for _, index in ranked[:k]]


def nearest_rank(values: list[Decimal], quantile: Decimal) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = int((quantile * Decimal(len(ordered))).to_integral_value(rounding=ROUND_CEILING))
    rank = min(max(rank, 1), len(ordered))
    return ordered[rank - 1]


def walk_forward(
    bars: list[Bar],
    config: EngineConfig,
    trigger: str,
    events: list[Event] | None = None,
    signals: list[ExternalSignal] | None = None,
) -> list[ForecastDraft]:
    events = events or []
    signals = signals or []
    features = compute_features(bars, config)
    horizons: list[tuple[Decimal, int]] = []
    for hours in config.horizons_hours:
        count = horizon_bars(hours, config.timeframe_seconds)
        if count is not None:
            horizons.append((hours, count))
    labels: dict[Decimal, list[Label | None]] = {}
    for hours, count in horizons:
        labels[hours] = [
            label_at(bars, index, count, config) if features[index] is not None else None
            for index in range(len(bars))
        ]
    counts: dict[tuple[str, str], list[int]] = {}
    moves: dict[tuple[str, str], list[Decimal]] = {}
    drafts: list[ForecastDraft] = []
    vectors = [analogue_vector(feature) if feature is not None else None for feature in features]

    for index, feature in enumerate(features):
        for hours, count in horizons:
            origin = index - count
            if origin < 0 or features[origin] is None or labels[hours][origin] is None:
                continue
            key = (format(hours, "f"), features[origin].bucket)  # type: ignore[union-attr]
            bucket_counts = counts.setdefault(key, [0, 0, 0])
            label = labels[hours][origin]
            assert label is not None
            bucket_counts[_CLASS_INDEX[label.klass]] += 1
            moves.setdefault(key, []).append(label.gross_pips)
        if feature is None:
            continue
        context = {
            "features": feature.as_json(),
            "volume_kind": config.volume_kind,
            "rule": DEFINITION_RULE,
            "events": visible_events(events, feature.decision_time),
            "external_signals": signals_asof(signals, feature.bar_open),
        }
        for hours, count in horizons:
            key = (format(hours, "f"), feature.bucket)
            bucket_counts = counts.get(key, [0, 0, 0])
            sample_size = sum(bucket_counts)
            published = sample_size >= config.min_samples
            bucket_moves = moves.get(key, [])
            analogue_n, analogue_counts, analogue_median, analogue_status = _analogues(
                index=index,
                horizon_bar_count=count,
                vectors=vectors,
                labels=labels[hours],
                config=config,
            )
            drafts.append(
                ForecastDraft(
                    symbol=config.symbol,
                    timeframe_seconds=config.timeframe_seconds,
                    decision_time=feature.decision_time,
                    horizon_hours=hours,
                    model_name=config.model_name,
                    model_version=config.model_version,
                    definition_id=config.definition_id(),
                    trigger_reason=trigger,
                    bucket=feature.bucket,
                    probability_status="empirical" if published else "withheld",
                    n_samples=sample_size,
                    n_up=bucket_counts[0] if published else 0,
                    n_down=bucket_counts[1] if published else 0,
                    n_flat=bucket_counts[2] if published else 0,
                    q25_pips=nearest_rank(bucket_moves, Decimal("0.25")) if published else None,
                    q75_pips=nearest_rank(bucket_moves, Decimal("0.75")) if published else None,
                    analogue_status=analogue_status,
                    analogue_n=analogue_n,
                    analogue_n_up=analogue_counts[0],
                    analogue_n_down=analogue_counts[1],
                    analogue_n_flat=analogue_counts[2],
                    analogue_median_pips=analogue_median,
                    feature=context,
                    volume_kind=config.volume_kind,
                )
            )
    return drafts


def unsupported_horizons(config: EngineConfig) -> list[Decimal]:
    skipped = []
    for hours in config.horizons_hours:
        if horizon_bars(hours, config.timeframe_seconds) is None:
            skipped.append(hours)
    return skipped


_CLASS_INDEX = {UP: 0, DOWN: 1, FLAT: 2}


def _analogues(
    index: int,
    horizon_bar_count: int,
    vectors: list[list[Decimal] | None],
    labels: list[Label | None],
    config: EngineConfig,
) -> tuple[int, list[int], Decimal | None, str]:
    feature_ok = [vector is not None for vector in vectors]
    label_ok = [label is not None for label in labels]
    chosen = eligible_indices(index, horizon_bar_count, feature_ok, label_ok)
    current = vectors[index]
    if current is None:
        return 0, [0, 0, 0], None, "withheld"
    candidates = [(item, vectors[item]) for item in chosen if vectors[item] is not None]
    typed: list[tuple[int, list[Decimal]]] = [
        (item, vector) for item, vector in candidates if vector is not None
    ]
    neighbors = nearest_indices(typed, current, config.analogue_k)
    if len(neighbors) < config.min_samples:
        return len(neighbors), [0, 0, 0], None, "withheld"
    tally = [0, 0, 0]
    pips: list[Decimal] = []
    for neighbor in neighbors:
        label = labels[neighbor]
        assert label is not None
        tally[_CLASS_INDEX[label.klass]] += 1
        pips.append(label.gross_pips)
    return len(neighbors), tally, median(pips), "empirical"
