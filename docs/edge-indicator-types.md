# Типы индикаторов: подтверждение vs опережение

Краткая модель для EDGE (согласовано с пользователем + GEM Logic).

---

## Типы индикаторов (из списка ~100)

| Тип | Что показывает | Примеры |
|-----|----------------|---------|
| **Trend** | Направление | EMA, SMA, SuperTrend, Parabolic SAR |
| **Momentum** | Сила и скорость | RSI, MACD, Stochastic, CCI, ROC |
| **Volume / Money flow** | Деньги за движением | MFI, OBV, CMF, VWAP, Volume Profile |
| **Volatility** | Сжатие / расширение | ATR, Bollinger, Keltner, Squeeze |
| **Levels / Bands** | Зоны перегиба | BB, pivots, S/R, VP nodes |
| **Order flow** | Агрессивные buy/sell | CVD, delta, footprint |
| **Cycles** | Фазы рынка | Wyckoff-стадии, seasonal (реже в TA) |

Один индикатор может быть в нескольких ролях (например VWAP = level + volume).

---

## Главное уточнение (точнее, чем «все div = leading»)

| Режим сигнала | Обычно | Смысл |
|---------------|--------|--------|
| **Обычный сигнал** индикатора | **Подтверждающий** | Движение **уже** проявилось |
| **Дивергенция** того же индикатора | **Опережающий / warning** | Внутренняя сила **уже** слабеет, цена ещё «держит лицо» |

**Но:**

- Технически div можно искать на многих линиях (RSI, MFI, MACD hist, OBV, CVD…).
- **Качество** div разное: RSI/MFI/CVD сильнее; EMA/ATR/ADX как «линия div» — слабее или другое назначение.
- **Дивергенция ≠ entry** — это **предупреждение** (Douglas / Hougaard / GEM: WARNING tier).

---

## Примеры

### Подтверждающие (confirming)

| Сигнал | Сообщение |
|--------|-----------|
| RSI вышел из 30 вверх | momentum уже развернулся |
| MACD cross | импульс подтверждён |
| Цена выше EMA | тренд вверх |
| SuperTrend bullish | тренд переключился |
| ADX растёт | тренд усиливается (не направление!) |
| Пробой VWAP | институциональный сдвиг уже виден |

### Опережающие (leading / warning)

| Сигнал | Сообщение |
|--------|-----------|
| Цена HH, RSI LH | сила цены падает |
| Цена LL, MFI HL | продавцы слабеют |
| Цена ↑, OBV flat/down | объём не поддерживает |
| Цена HH, CVD не подтверждает | нет aggressive buyers |
| Цена ↑, MACD hist ↓ | двигатель слабеет |

---

## Качество дивергенции по индикатору

### Сильные для div

RSI, MFI, MACD histogram, OBV, CVD, CMF, CCI, Stoch RSI.

### Слабее / другая роль

EMA/SMA (сглаживание цены), ATR (диапазон), ADX (сила без направления div), BB (канал), SuperTrend/SAR (переключатели).

---

## Правильная цепочка сделки (4 шага)

```
1. Дивергенция     → раннее предупреждение (Layer 1)
2. Контекст       → где это (EMA, VWAP, BB, VP, S/R) (Layer 2)
3. Подтверждение  → свеча, пробой, cross, ST flip (Layer 3)
4. Entry          → только после 3 (CONFIRMED в протоколе)
```

GEM сегодня: **Layer 1** (RSI div) + часть **Layer 2** (S/R) + часть **Layer 3** (свечи, 3rd div, ARMED/TRIGGERED).

---

## Три слоя EDGE (архитектура продукта)

### Layer 1 — Leading (опережающий)

- RSI / MFI / MACD hist / OBV / CVD divergence  
- Dual div (RSI + MFI)  
- «Price makes HH without confirmation»

**В GEM:** raw div, setup count, Ruby/Emerald, **WARNING**.

### Layer 2 — Context (контекст)

- EMA regime (with/against trend)  
- VWAP distance  
- Bollinger stretch  
- Volume Profile / pivots  
- ATR distance (перегрев хода)

**В GEM:** `near_support` / `near_resistance`, MTF alignment.

### Layer 3 — Confirming (подтверждение)

- RSI exit extreme  
- MACD cross  
- Rejection candle  
- Structure break  
- SuperTrend flip  
- Close above/below EMA or VWAP  

**В GEM:** bull/bear candle, `buy_entry` / `sell_entry`, **CONFIRMED**, TRIGGERED.

---

## Короткий ответ на вопрос

**Да, мысль верная**, с формулировкой:

- Индикатор описывает **состояние** рынка.  
- **Обычный** сигнал чаще **подтверждает** уже идущее движение.  
- **Дивергенция** чаще **предупреждает**, что движение может сломаться — но **не** равна входу.

Не все 100 индикаторов одинаково полезны для div; для EDGE ядро div = **RSI + MFI**, контекст = **EMA / BB / VWAP**, подтверждение = **свечи + execution state**.

---

## Связанные файлы

- `docs/edge-indicator-combos.md` — TOP 10 пар  
- `docs/edge-two-layers.md` — analytical vs behavioural  
- `docs/edge-discipline-protocol.md` — WARNING vs CONFIRMED  
- `src/gem/analyzer.py` — Layer 1+3 сегодня  
- `src/edge_combos.py` — Layer 1 RSI+MFI (Phase 1)
