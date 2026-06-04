# EDGE — два слоя (из библиотеки Douglas + Hougaard)

## 1. Analytical EDGE (GEM Logic)

Что уже делает скан:

- RSI + дивергенции (Emerald / Ruby)
- Свечное подтверждение
- 4 TF: M15, H1, H4, D1
- Сила: WEAK → PREMIUM
- GEM My List + чеклист 6/6
- 4 таблицы scores по TF

## 2. Behavioural EDGE (дисциплина)

Что **не** заменяет индикатор:

| Правило | Источник |
|---------|----------|
| Signal ≠ Trade (WARNING / CONFIRMED) | Douglas #1–2 |
| Риск до входа (SL, TP, %) | Douglas #2 |
| Закрытая свеча / trigger | Disciplined Trader, Hougaard |
| Журнал + серия 20–50+ | Douglas, Aronson (позже) |
| Good loss / Bad loss | Hougaard #3 |
| Нет revenge, martingale, widen stop | Hougaard, `discipline.json` |
| Не менять GEM после 1–3 лоссов | Hougaard |

## Поток

```
Scan → GEM My List → Exec tier → Protocol 10 steps → Trade (you) → Journal → Review series
```

## Книги психологии (порядок)

1. *Trading in the Zone* — вероятности  
2. *The Disciplined Trader* — среда рынка, объективность  
3. *Best Loser Wins* — качество убытка  

Конспекты: `docs/books/01` … `03`.

## Indicator combos (TOP 10)

See `docs/edge-indicator-combos.md` — **RSI+MFI** = P0 core.
