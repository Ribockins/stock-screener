# EDGE Discipline Protocol

Психологический «firewall» рядом с GEM My List.

| Книга | Вклад |
|-------|--------|
| **Trading in the Zone** (#1) | Вероятности, серия, CONFIRMED |
| **The Disciplined Trader** (#2) | Signal ≠ trade, риск до входа, объективность |
| **Best Loser Wins** (#3) | Good loss / Bad loss, не менять систему после 1–3 лоссов |

GEM = *есть ли edge?* · Protocol = *исполню ли без эмоций?*

---

## 10 шагов (каждая сделка)

| # | Шаг | Действие |
|---|-----|----------|
| 1 | Сигнал | GEM My List / scan |
| 2 | EDGE score | 0–4 из MTF strength (см. таблицу ниже) |
| 3 | Направление | Согласован с H4/D1 |
| 4 | Timeframe | 4 tables — не один TF в вакууме |
| 5 | **Свеча** | Действие на **закрытой** свече H1 (не мигающий live) |
| 6 | **Exec tier** | WARNING = watch; CONFIRMED = готовить вход |
| 7 | **Trigger** | ARMED → TRIGGERED / ваше правило |
| 8 | **Риск** | Entry, SL, TP, invalidation, % — **до** клика |
| 9 | **План** | Не переносить SL, не revenge size |
| 10 | **Журнал** | `signal_journal.py` + после сделки `result_r`, `loss_quality` |

Оценка системы — только на **серии** (≥20–50 записей), не на одной сделке.

---

## EDGE score 0–4 (из GEM strength)

| Score | GEM tier | Смысл |
|-------|----------|--------|
| 0 | NONE | Нет |
| 1 | WEAK | Слабый warning |
| 2 | MEDIUM | Кандидат |
| 3 | STRONG / VERY_STRONG | Сильный warning |
| 4 | PREMIUM | Premium candidate — вход **с trigger** |

Score **4** ≠ автоматический вход.

---

## Exec tier (Signal ≠ Trade)

| Tier | Действие |
|------|----------|
| **WAIT** | Нет сделки |
| **WARNING** | Наблюдение / половинный риск |
| **CONFIRMED** | План по полному риску |

---

## Hougaard: Loss Quality (после сделки)

| Значение | Когда |
|----------|--------|
| **good_loss** | Правило соблюдено, SL сработал |
| **bad_loss** | Ранний вход, widen SL, revenge, no stop |
| **win** | TP / цель по плану |
| **execution_error** | Закрыл рано из страха / держал убыток |

> Good loss is part of the system. Bad loss is violation of the system.

---

## Запрещено

- Вход на «красивую цифру» без trigger.
- Увеличение лота после убытка.
- Martingale / усреднение.
- Перенос stop «в надежде».
- Смена GEM после 1–3 лоссов.
- Finviz gainers в одном риске с «моими 12».

---

## Лимиты

`config/discipline.json`

---

## GEM My List

| Checklist | Protocol |
|-----------|----------|
| 6/6 ✅ + CONFIRMED | Полный план |
| 5/6 ⚠️ | WARNING |
| &lt;4/6 | WAIT |
