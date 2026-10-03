"""Text report. Rates are labeled as historical frequencies, never as a trade."""

from __future__ import annotations

from decimal import Decimal

from research_engine import __version__
from research_engine.calibration import CalibrationReport, calibration
from research_engine.config import EngineConfig
from research_engine.records import QualityReport, StoredForecast

_DISCLAIMER = (
    "Это исследовательский журнал, не торговый сигнал. "
    "Опубликованная частота — доля прошлых close-to-close исходов в одной корзине. "
    "Она не является калиброванной вероятностью рынка."
)


def render(
    config: EngineConfig,
    quality: QualityReport,
    forecasts: list[StoredForecast],
    *,
    resample_dropped: int = 0,
    unsupported: list[Decimal] | None = None,
) -> str:
    lines = [
        f"{config.symbol} research engine {__version__}",
        _DISCLAIMER,
        "",
        f"Символ: {config.symbol}",
        f"Рабочий таймфрейм: {config.timeframe_seconds} с, сетка UTC",
        f"Сессии считаются по концу бара, часовой пояс {config.session_timezone}",
        f"Баров в базе: {quality.n_bars}",
        f"Пропуски между барами: {quality.n_gaps}",
        f"Отклонено строк файла: {quality.n_rejected}",
        f"Конфликты, исходный бар сохранён: {quality.n_conflicts}",
        f"Незакрытых баров отброшено: {quality.n_forming_dropped}",
        f"Неполных корзин ресемплинга отброшено: {resample_dropped}",
        "Фатальные проблемы: " + (", ".join(quality.fatal) if quality.fatal else "нет"),
        "",
        "Правило исхода: close-to-close.",
        (
            f"UP если изменение > {config.flat_band_pips} pips, "
            f"DOWN если < -{config.flat_band_pips} pips, иначе FLAT."
        ),
        "Нужен бар ровно через заданный горизонт. Пропуск не заполняется.",
        "Это изменение цены закрытия, не максимальное движение в сторону сделки.",
        f"Объём помечен как {config.volume_kind}. Смысл bid/ask зависит от поставщика данных.",
    ]
    if quality.gap_examples:
        lines.append("Примеры пропусков после: " + ", ".join(quality.gap_examples))
    if unsupported:
        lines.append("Горизонты не кратны бару и пропущены: " + ", ".join(format(item, "f") for item in unsupported))
    lines.extend(["", _scenario_block(forecasts, config), "", _calibration_block(forecasts)])
    return "\n".join(lines) + "\n"


def _scenario_block(forecasts: list[StoredForecast], config: EngineConfig) -> str:
    if not forecasts:
        return "Нет ни одного бара с полным окном признаков. Вероятность не публикуется."
    latest_time = max(row.draft.decision_time for row in forecasts)
    latest = [row for row in forecasts if row.draft.decision_time == latest_time]
    latest.sort(key=lambda row: row.draft.horizon_hours)
    head = latest[0]
    published = sum(row.draft.probability_status == "empirical" for row in forecasts)
    lines = [
        f"В журнале строк с опубликованной частотой: {published} из {len(forecasts)}.",
        "Ниже показано только последнее решение, а не лучший пример из истории.",
        f"Последнее решение: {head.draft.decision_time.strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"Триггер: {head.draft.trigger_reason}",
        f"Корзина: {head.draft.bucket}",
        _context_lines(head),
    ]
    for row in latest:
        lines.append(_horizon_line(row, config))
    return "\n".join(lines)


def _context_lines(row: StoredForecast) -> str:
    feature = row.draft.feature.get("features", {})
    events = row.draft.feature.get("events") or []
    signals = row.draft.feature.get("external_signals") or []
    parts = [
        f"Признаки H1 trend score={feature.get('h1_trend_score')}, H4/ATR={feature.get('h4_score')}, momentum/ATR={feature.get('momentum')}"
    ]
    if events:
        names = ", ".join(f"{event['name']} {event['currency']}" for event in events)
        parts.append("События, уже доступные на момент решения: " + names)
    else:
        parts.append("Фундаментальный блок не участвует: на момент решения нет размеченных событий.")
    if signals:
        rendered = ", ".join(f"{signal['name']}={signal['value']}" for signal in signals)
        parts.append("Внешние сигналы подключены как данные, не как вероятность: " + rendered)
    else:
        parts.append("ROTOR, GEM и VECTOR не перенесены и в вероятность не входят.")
    return "\n".join(parts)


def _horizon_line(row: StoredForecast, config: EngineConfig) -> str:
    draft = row.draft
    hours = format(draft.horizon_hours, "f")
    outcome = f" факт: {row.actual_status}"
    if row.actual_status == "resolved":
        outcome += f" {row.actual_class} {row.actual_gross_pips} pips"
    if draft.probability_status != "empirical":
        analogue = _analogue_text(draft, config)
        return (
            f"{hours}h  вероятность не публикуется "
            f"(n={draft.n_samples}, нужно {config.min_samples}).{outcome}. {analogue}"
        )
    rates = (
        f"UP {_pct(draft.n_up, draft.n_samples)}%  "
        f"DOWN {_pct(draft.n_down, draft.n_samples)}%  "
        f"FLAT {_pct(draft.n_flat, draft.n_samples)}%"
    )
    quantiles = f"q25={draft.q25_pips} q75={draft.q75_pips} pips"
    return (
        f"{hours}h  эмпирическая частота прошлого, не калиброванная вероятность  "
        f"n={draft.n_samples}  {rates}. Ближайший ранг движений корзины: {quantiles}. "
        f"{_analogue_text(draft, config)}{outcome}."
    )


def _analogue_text(draft, config: EngineConfig) -> str:
    if draft.analogue_status != "empirical":
        return (
            f"Аналоги не публикуются (найдено {draft.analogue_n}, нужно {config.min_samples})."
        )
    return (
        "Аналоги, отдельно от корзины: "
        f"n={draft.analogue_n} "
        f"UP {_pct(draft.analogue_n_up, draft.analogue_n)}% "
        f"DOWN {_pct(draft.analogue_n_down, draft.analogue_n)}% "
        f"FLAT {_pct(draft.analogue_n_flat, draft.analogue_n)}%, "
        f"медиана {draft.analogue_median_pips} pips."
    )


def _calibration_block(forecasts: list[StoredForecast]) -> str:
    forward = [row for row in forecasts if row.draft.trigger_reason != "backfill"]
    reconstructed = [row for row in forecasts if row.draft.trigger_reason == "backfill"]
    lines = [
        "Калибровка считается только по строкам, где частота была опубликована до исхода и исход уже записан.",
        "Снятые с публикации строки (withheld) в счёт не входят.",
        "Соседние по времени прогнозы перекрываются и не являются независимыми наблюдениями.",
        _score_section("Forward-test", calibration(forward)),
        _score_section("Реконструкция backfill", calibration(reconstructed)),
        "Backfill показывает, что правило выдало бы на истории. Это не заменяет forward-test.",
        "Числа выше описывают журнал. Они не доказывают преимущество и не являются допуском к сделке.",
    ]
    return "\n".join(lines)


def _score_section(title: str, report: CalibrationReport) -> str:
    if report.n_published == 0:
        return f"{title}: опубликованных и уже разрешённых прогнозов нет."
    return (
        f"{title}: разрешено {report.n_published}, из них неперекрывающихся {report.n_nonoverlapping}. "
        f"Brier={_fmt(report.brier)}, Brier на неперекрывающихся={_fmt(report.brier_nonoverlapping)}, "
        f"log loss={_fmt(report.log_loss)}. Вывод о калибровке по этой выборке не делается."
    )


def _pct(part: int, whole: int) -> str:
    value = (Decimal(part) * Decimal(100) / Decimal(whole)).quantize(Decimal("0.1"))
    return format(value, "f")


def _fmt(value: Decimal | None) -> str:
    if value is None:
        return "n/a"
    return format(value.quantize(Decimal("0.0001")), "f")
