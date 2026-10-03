"""Two-hour direction strength.

The number is the average of the layers that actually have a reading.
A missing geopolitical or fundamental file is absent, not a silent zero.
This is not a probability.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from research_engine.config import EngineConfig
from research_engine.features import compute_features
from research_engine.instruments import instrument
from research_engine.records import Bar, Event, Feature

_LEAN = Decimal("0.1")
_WINDOW_HOURS = Decimal(48)
_STALE_SECONDS = 2 * 3600 + 15 * 60
_GEO_KINDS = {"geopolitical", "unexpected"}
_FUND_KINDS = {"scheduled", "fundamental"}


@dataclass(frozen=True)
class LayerScore:
    name: str
    score: Decimal | None
    note: str


@dataclass(frozen=True)
class DirectionProposal:
    symbol: str
    decision_time: datetime
    source: str
    delay_seconds: int
    status: str
    direction: str
    strength: Decimal | None
    combined: Decimal | None
    disagreement: bool
    layers: tuple[LayerScore, ...]
    detail: dict


def build_proposal(
    bars: list[Bar],
    config: EngineConfig,
    events: list[Event],
    fetched_at: datetime,
    source: str,
) -> DirectionProposal | None:
    features = compute_features(bars, config)
    chosen = _latest_two_hour_feature(features)
    if chosen is None:
        return None
    return proposal_for_feature(chosen, events, fetched_at, source, config.symbol)


def proposal_for_feature(
    feature: Feature,
    events: list[Event],
    fetched_at: datetime,
    source: str,
    symbol: str = "EURUSD",
) -> DirectionProposal:
    delay = int((fetched_at - feature.decision_time).total_seconds())
    status = "published" if 0 <= delay <= _STALE_SECONDS else "withheld"
    geopolitical = _event_layer(events, feature.decision_time, _GEO_KINDS, "geopolitical", "геополитика", symbol)
    fundamental = _event_layer(events, feature.decision_time, _FUND_KINDS, "fundamental", "фундамент", symbol)
    technical = LayerScore("technical", _technical_score(feature), _technical_note(feature))
    candle = LayerScore("candle", _candle_score(feature), _candle_note(feature))
    layers = (geopolitical, fundamental, technical, candle)
    scored = [layer for layer in layers if layer.score is not None]
    combined = None
    if scored:
        combined = sum((layer.score for layer in scored), Decimal("0")) / Decimal(len(scored))
    signs = [1 if layer.score > _LEAN else -1 for layer in scored if layer.score is not None and abs(layer.score) >= _LEAN]
    disagreement = 1 in signs and -1 in signs
    if combined is None or abs(combined) < _LEAN:
        raw_direction = "flat"
    elif combined > 0:
        raw_direction = "up"
    else:
        raw_direction = "down"
    if status != "published":
        direction = "flat"
        strength = None
    elif raw_direction == "flat":
        direction = "flat"
        strength = Decimal("0")
    else:
        direction = raw_direction
        strength = abs(combined)
    return DirectionProposal(
        symbol=symbol,
        decision_time=feature.decision_time,
        source=source,
        delay_seconds=delay,
        status=status,
        direction=direction,
        strength=strength,
        combined=combined,
        disagreement=disagreement,
        layers=layers,
        detail={
            "session": feature.session,
            "bucket": feature.bucket,
            "features": feature.as_json(),
            "rule": "equal weight of layers that have a reading; 2h UTC slot; strength is not a probability",
        },
    )


def render_proposal(proposal: DirectionProposal) -> str:
    lines = [
        f"{proposal.symbol}, слот 2ч: {proposal.decision_time.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"Источник котировок: {proposal.source}",
        _delay_line(proposal),
        "Сравнение слоёв, в этом порядке:",
    ]
    titles = {
        "geopolitical": "Геополитика",
        "fundamental": "Фундамент",
        "technical": "Техника",
        "candle": "Свечи",
    }
    for layer in proposal.layers:
        score = "нет чтения" if layer.score is None else _shown(layer.score)
        lines.append(f"- {titles[layer.name]}: {score}. {layer.note}")
    lines.append("Слои смотрят в разные стороны." if proposal.disagreement else "Знаки присутствующих слоёв не противоречат друг другу.")
    if proposal.status != "published":
        lines.append("Сила предложения не публикуется: данные этого слота уже не для текущего двухчасового цикла.")
    else:
        lines.append(f"Направление: {_direction_text(proposal.direction)}")
        lines.append(f"Сила предложения: {_shown(proposal.strength)}")
    spec = instrument(proposal.symbol)
    if spec is not None:
        lines.append(spec.contract_note)
    lines.append("Сила — это среднее чтение слоёв, не вероятность и не приказ.")
    return "\n".join(lines) + "\n"


def describe_sources() -> str:
    return "\n".join(
        [
            "Сейчас рабочий набор — NG и WTI. Задержка от минуты нормальна.",
            "- yfinance: NG=F (Henry Hub) и CL=F (WTI), часовые бары фронтального контракта.",
            "- sierra_csv: экспорт этих контрактов, если файл доступен локально.",
            "- events_csv: фундамент и геополитика. Знак отдельно: ng_sign и wti_sign (-1, 0, 1).",
            "Пока не входят в число силы:",
            "- TradingView из скринера: пакет и логин, и текущий загрузчик смотрит акции NASDAQ.",
            "- веб-поиск: у заголовка нет версии на момент решения, поэтому он не двигает силу.",
            "",
        ]
    )


def _latest_two_hour_feature(features: list[Feature | None]) -> Feature | None:
    chosen = None
    for feature in features:
        if feature is None:
            continue
        moment = feature.decision_time.astimezone(timezone.utc)
        if moment.minute == 0 and moment.second == 0 and moment.hour % 2 == 0:
            chosen = feature
    return chosen


def _technical_score(feature: Feature) -> Decimal:
    parts = [_clip(feature.h1_trend_score)]
    if feature.h4_score is not None:
        parts.append(_clip(feature.h4_score))
    if feature.momentum is not None:
        parts.append(_clip(feature.momentum))
    return sum(parts, Decimal("0")) / Decimal(len(parts))


def _candle_score(feature: Feature) -> Decimal:
    score = Decimal("0")
    if feature.bullish_engulfing:
        score += 1
    if feature.bearish_engulfing:
        score -= 1
    if feature.bullish_pin:
        score += Decimal("0.5")
    if feature.bearish_pin:
        score -= Decimal("0.5")
    return _clip(score)


def _event_layer(
    events: list[Event], decision: datetime, kinds: set[str], key: str, title: str, symbol: str
) -> LayerScore:
    names: list[str] = []
    contributions: list[Decimal] = []
    for event in events:
        if event.available_at > decision or event.kind not in kinds:
            continue
        age_hours = Decimal((decision - event.available_at).total_seconds()) / Decimal(3600)
        if age_hours > _WINDOW_HOURS:
            continue
        names.append(event.name)
        bias = event.sign_for(symbol)
        if bias is None or bias == 0:
            continue
        freshness = Decimal(1) - (age_hours / _WINDOW_HOURS)
        if freshness <= 0:
            continue
        magnitude = Decimal(event.impact) / Decimal(3) if event.impact else Decimal("0.5")
        magnitude = _clip(magnitude, Decimal(1))
        if magnitude < 0:
            magnitude = Decimal(0)
        contributions.append(Decimal(bias) * magnitude * freshness)
    if not names:
        return LayerScore(key, None, f"{title}: в последние 48 часов событий нет")
    if not contributions:
        return LayerScore(key, None, f"{title}: события без знака EURUSD: {', '.join(names)}")
    score = _clip(sum(contributions, Decimal("0")) / Decimal(len(contributions)))
    return LayerScore(key, score, f"{title}: {', '.join(names)}")


def _technical_note(feature: Feature) -> str:
    return (
        f"H1 (close-SMA)/ATR={_num(feature.h1_trend_score)}, "
        f"H4/ATR={_num(feature.h4_score)}, momentum/ATR={_num(feature.momentum)}"
    )


def _candle_note(feature: Feature) -> str:
    flags = []
    if feature.bullish_engulfing:
        flags.append("bullish engulfing")
    if feature.bearish_engulfing:
        flags.append("bearish engulfing")
    if feature.bullish_pin:
        flags.append("bullish pin")
    if feature.bearish_pin:
        flags.append("bearish pin")
    if feature.inside_bar:
        flags.append("inside bar")
    return "свечи: " + (", ".join(flags) if flags else "явной формации нет")


def _delay_line(proposal: DirectionProposal) -> str:
    minutes = proposal.delay_seconds / 60
    if proposal.delay_seconds < 0:
        return "Задержка отрицательная: часы источника и решения расходятся. Слот не предлагается."
    if proposal.status != "published":
        return (
            f"Задержка {minutes:.0f} мин. Для текущего цикла это уже следующий двухчасовой слот, "
            "сила не предлагается."
        )
    return f"Задержка {minutes:.0f} мин. Минута и больше для этого контура нормальны."


def _direction_text(direction: str) -> str:
    return {"up": "вверх по EURUSD", "down": "вниз по EURUSD", "flat": "без перевеса"}[direction]


def _clip(value: Decimal, limit: Decimal = Decimal("1")) -> Decimal:
    if value > limit:
        return limit
    if value < -limit:
        return -limit
    return value


def _shown(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.0001")), "f")


def _num(value: Decimal | None) -> str:
    return "n/a" if value is None else _shown(value)


def slot_is_current(decision_time: datetime, fetched_at: datetime) -> bool:
    delay = fetched_at - decision_time
    return timedelta(0) <= delay <= timedelta(seconds=_STALE_SECONDS)
