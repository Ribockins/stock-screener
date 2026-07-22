# TOP 10 комбинаций индикаторов для EDGE

Источник: пользователь (EDGE research).  
Текущий GEM Logic = **RSI + свечи + S/R** (Pine 1.5). План расширения ниже.

---

## Рейтинг для EDGE (2 индикатора)

| Место | Комбинация | Главная сила | Приоритет в коде |
|-------|------------|--------------|------------------|
| 1 | **RSI + MFI** | Дивергенция / exhaustion | **P0 — ядро** |
| 2 | RSI + EMA | Фильтр тренда | P1 |
| 3 | Bollinger + RSI | Растяжение / mean reversion | P1 |
| 4 | VWAP + RSI | Intraday reversal | P2 (M15) |
| 5 | MACD hist + MFI | Угасание импульса | P2 |
| 6 | ADX/DMI + RSI | Фильтр силы тренда | P1 filter |
| 7 | Squeeze + BB/KC | Pre-breakout | P3 модуль |
| 8 | Volume Profile + RSI | Div у уровня | P3 |
| 9 | CVD + RSI | Order flow | P3 (нужен feed) |
| 10 | SuperTrend + MFI | Trend + объём | P2 alerts |

---

## 1. RSI + MFI (главная пара)

**Тип:** price momentum + money flow  
**Назначение:** дивергенция, истощение, ранний разворот.

- RSI — сила **цены**.
- MFI — поддерживают ли движение **деньги/объём**.

**Идея:** цена вверх, RSI и MFI **не** подтверждают → сильный warning.

```
Цена ↑, сила цены ↓, сила денег ↓
```

**Лучше для:** акции, индексы, commodities, crypto.  
**Сигнал:** bearish/bullish divergence на **RSI + MFI одновременно**.

---

## 2. RSI + EMA

**Тип:** reversal + trend filter  
RSI в тренде долго в OB/OS → EMA даёт контекст.

**Пример sell:** RSI bear div + цена далеко выше EMA + EMA flatten + потеря импульса.  
**TF:** H1, H4, D1.

---

## 3. Bollinger Bands + RSI

**Тип:** volatility extreme + momentum  
Цена у верхней BB + RSI > 70 + rejection → exhaustion.  
**Минус:** ранние сигналы в сильном тренде.

---

## 4. MACD Histogram + MFI

Цена держится, histogram и MFI падают → двигатель слабеет.  
**Минус:** MACD запаздывает.

---

## 5. VWAP + RSI

Intraday: далеко от VWAP + RSI extreme → возврат к VWAP.  
**TF:** 5M–H1.

---

## 6. ADX/DMI + RSI

ADX растёт → не шортить «голый» RSI OB.  
ADX падает + RSI div → разворот сильнее.

---

## 7. Squeeze + Bollinger/Keltner

Сжатие → breakout. Отдельный модуль **Compression before expansion**.

---

## 8. Volume Profile + RSI

Div на HVN / POC / VAH/VAL — не в «пустом» месте.

---

## 9. CVD + RSI

Как RSI+MFI, глубже (aggressive buy/sell). Нужен quality feed.

---

## 10. SuperTrend + MFI

Trend + топливо: MFI падает при ещё bullish ST → предупреждение.

---

## Топ-3 для реализации в проекте

1. **RSI + MFI** — ядро дивергенции  
2. **RSI + EMA** — режим рынка (с/против тренда)  
3. **Bollinger + RSI** — растяжение + exhaustion  

---

## Формула EDGE (целевая)

| Слой | Роль |
|------|------|
| **RSI + MFI** | Ядро сигнала (div / exhaustion) |
| **EMA** | Фильтр режима |
| **BB / VWAP / VP** | *Где* сигнал опасен для толпы |

**Если строго 2 индикатора:** №1 **RSI + MFI**.

---

## Типы сигналов

См. `docs/edge-indicator-types.md` (confirming vs leading div).

## Связь с GEM My List (сейчас vs план)

| Сейчас (GEM 1.5) | План EDGE 2.0 |
|------------------|---------------|
| RSI 14, OB 72 / OS 28 | + MFI 14, те же зоны |
| Raw / 3rd div | + **dual div** (RSI ∧ MFI) |
| Emerald / Ruby | + tier **DUAL GEM** если оба |
| Strength PREMIUM | + `combo_flags`: mfi_confirm, ema_filter, bb_stretch |

См. `docs/edge-indicator-roadmap.md` и `src/edge_combos.py` (MFI + проверки).

---

## Оценка для вашего watchlist (12 инструментов)

| Класс | Лучшие комбо |
|-------|----------------|
| Energy (NG, WTI, Brent) | RSI+MFI, BB+RSI, ADX+RSI |
| Indices | RSI+MFI, RSI+EMA, VP+RSI (позже) |
| FX | RSI+MFI, VWAP+RSI (M15), ADX+RSI |
| Cocoa | RSI+MFI, BB+RSI |

---

*Не торговый совет — карта разработки EDGE.*
