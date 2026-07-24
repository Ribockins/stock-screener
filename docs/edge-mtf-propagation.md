# MTF Propagation Layer — перенос сигнала с младшего TF на старший

Ответ на вопрос: **не «есть ли сигнал на M15?»**, а **«может ли M15 вырасти в H1/H4/D1?»**

Согласовано с идеей пользователя + архитектурой EDGE (leading / context / confirming).

---

## Главный принцип

| Сигнал на M15 | Часто значит |
|---------------|--------------|
| RSI overbought 74 | «локально перегрели» — **не обязан** сломать H4 |
| MFI bear div на M15 | «деньги уже не тянут рост» — **чаще** видно на H1/H4 позже |
| CVD HH + price HH, CVD LH | агрессивные покупатели выдыхаются — **сильный** перенос |

**Да:** MFI (и объём/flow) **в среднем** переносится на старшие TF **лучше**, чем «голый» RSI OB/OS.

**Но:** не гарантия. Нужен **Propagation Score** + уровень старшего TF.

---

## Почему RSI слабее переносится

RSI ≈ скорость/величина **цены**. В тренде может долго быть 70+ на всех TF.

- M15 RSI 74 в H4 uptrend = часто **pullback**, не разворот.
- Перенос: **слабый–средний** для div; **средний** как фильтр экстремума.

---

## Почему MFI сильнее RSI (для переноса)

MFI = RSI **+ объём** (money flow).

| | RSI M15 | MFI M15 |
|--|---------|---------|
| Цена растёт | 74 | 58 и падает |
| Смысл | быстро выросли | **деньги не поддерживают** |

Это ближе к «ломается двигатель» → чаще проявится на H1/H4.

**Оценка переноса MFI:** ~8.8/10 (акции, индексы, commodities, FX, crypto с норм. volume).

---

## Классы индикаторов по силе переноса M15 → H1/H4

| Класс | Перенос | Примеры |
|-------|---------|---------|
| Order flow | **очень сильный** | CVD, delta, footprint |
| Volume / money flow | **сильный** | MFI, OBV, CMF |
| Market structure | **сильный** | Volume Profile, VWAP, HVN/POC |
| Volatility regime | **сильный** (направление?) | Squeeze, BB inside KC |
| Momentum oscillators | **слабый–средний** | RSI, Stoch (локальный перегрев) |
| Trend lines | **сверху вниз** | EMA, SuperTrend — не снизу вверх |

---

## TOP 10 — межтаймфреймовый перенос (M15 → H1/H4)

| # | Индикатор | Сила | Почему |
|---|-----------|------|--------|
| 1 | **CVD** | 9.5 | Реальное aggressive buy/sell pressure |
| 2 | **OBV** | 9.0 | Накопление/распределение раньше цены |
| 3 | **MFI** | 8.8 | Денежный поток + div; **ядро EDGE** |
| 4 | **Volume Profile** | 8.7 | M15 rejection у H4/D1 node |
| 5 | **VWAP** | 8.3 | Institutional anchor; mean reversion chain |
| 6 | **Squeeze (BB/KC)** | 8.2 | Сжатие → expansion на старшем TF |
| 7 | **Market breadth (A-D)** | 8.5 | Для **индексов** (US500, UK100, CAC40) |
| 8 | **OI + Funding** | 9.0 | Crypto/perpetuals; crowd positioning |
| 9 | **MACD histogram div** | 7.5 | Угасание momentum (lag) |
| 10 | **ADX/DMI weakening** | 7.8 | **Фильтр режима**, не главный entry |

### Для вашего watchlist (12 инструментов)

| Рынок | Топ переноса |
|-------|----------------|
| NG, WTI, Brent, Cocoa | CVD/MFI/OBV, VP, Squeeze |
| US30, US500, UK100, CAC40 | Breadth (если данные), MFI, OBV, VP |
| EURUSD, EURGBP, USDCAD, USDJPY | MFI, VWAP (M15), CVD (если feed) |

---

## RSI vs MFI — прямой ответ

| Утверждение | Вердикт |
|-------------|---------|
| M15 RSI OB → разворот до H4 | **Часто нет** — локальный или pullback |
| M15 MFI bear div → слабость на H1/H4 | **Чаще да**, чем RSI — **не всегда** |
| MFI сильнее одного RSI для переноса | **Да** в среднем |
| Лучше MFI alone | **Нет** — лучше **MFI + OBV** или **CVD + MFI** |

---

## MTF Propagation Score (черновик для EDGE)

Оценка на **M15** (или младшем TF сигнала): «потенциал развития на H1/H4».

| Условие | Вес |
|---------|-----|
| RSI divergence (M15) | +1 |
| MFI divergence (M15) | +2 |
| OBV divergence (M15) | +2 |
| CVD divergence (M15) | +3 |
| Цена у H1/H4 VP/S/R уровне | +2 |
| H1 RSI/MFI тоже слабеет | +2 |
| H4 trend overstretched (BB/ATR) | +2 |
| Squeeze / compression | +1 |
| Volume spike + rejection | +2 |

| Сумма | Интерпретация |
|-------|----------------|
| 0–3 | Локальный M15 шум |
| 4–6 | Watch — слабый перенос |
| **7–10** | **MTF expansion potential** |

Не entry — **усиление WARNING** и приоритет в GEM My List.

---

## Лучшие блоки (формулы)

**Универсально (ваш EDGE):**

```
MFI + OBV  (+ уровень H1/H4)
```

**Crypto / futures:**

```
CVD + Open Interest (+ Funding)
```

**Полный стек:**

```
CVD + MFI + OBV + H1/H4 Level (VP / S/R)
```

**Роли:**

- RSI = локальная усталость цены  
- MFI = усталость **без денег**  
- OBV = накопление/распределение  
- CVD = **реальное давление**  
- VP = **место битвы**

---

## Три слоя EDGE (обновление)

| Слой | Вопрос |
|------|--------|
| **1 Leading** | Есть ли слабость? (div) |
| **2 Propagation** | **Перенесётся ли на H1/H4?** ← этот документ |
| **3 Context** | Где? (VP, VWAP, S/R, EMA) |
| **4 Confirming** | Entry (свеча, TRIGGERED) |

GEM сегодня: 1 + 3 + 4. **Propagation = Phase 1b** после RSI+MFI в коде.

---

## Связанные файлы

- `docs/edge-indicator-types.md` — leading vs confirming  
- `docs/edge-indicator-combos.md` — пары индикаторов  
- `config/mtf_propagation.json` — веса score  
- `src/mtf_propagation.py` — расчёт (stub / Phase 1b)
