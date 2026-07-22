# Technical Analysis Using Multiple Timeframes — Brian Shannon

| Поле | Данные |
|------|--------|
| **Название** | Technical Analysis Using Multiple Timeframes |
| **Автор** | Brian Shannon (CMT, AlphaTrends) |
| **Год** | 2008 (~184 стр.) |
| **Тема** | MTF, trend alignment, entry timing, risk, stops, short selling |
| **Полезность для EDGE** | **Очень высокая** — прямо под таблицы **M15 / H1 / H4 / D** |

---

## Главная идея

**Нельзя смотреть один timeframe изолированно.** У каждого TF своя роль:

| TF | Роль в EDGE |
|----|-------------|
| **D1** | Стратегический режим (фон рынка) |
| **H4** | Контекст силы / swing structure |
| **H1** | **Основной рабочий** сигнал (operational) |
| **M15** | Тактический warning, timing входа |

> Младший TF = **timing**. Старший TF = **смысл**.

Совпадает с: `docs/edge-mtf-propagation.md`, GEM My List, 4 таблицы scores.

---

## Как читать нашу таблицу (не «сигнал = вся картина»)

### Ошибка

Увидели Score 4 на одном TF → сразу «всё, вход».

### Правильно (Shannon + EDGE)

| Уровень | Правило |
|---------|---------|
| Score 4 на **одном** TF | **Candidate** (WARNING) |
| Score 4 **+** старший TF согласен | Сильнее |
| H1 + H4 одно направление | Серьёзный swing warning |
| D + H4 + H1 | Возможная **смена режима** |

---

## Роль каждого TF (для 12 инструментов)

### M15 — тактический warning

- Раннее обнаружение, точный вход, timing.
- **Минус:** шум, откат внутри H1/H4 тренда.
- **EDGE:** Propagation score; не полный размер без H1.

### H1 — главный operational layer

- Баланс шума и скорости; swing / intraday decisions.
- **GEM primary bar** для checklist и Exec tier.
- H1 STRONG/PREMIUM = серьёзный рабочий сигнал.

### H4 — контекст силы

- Структура swing; подтверждение H1.
- H1 SELL + H4 SELL → не «H1-шум», а ослабление крупнее.

### D1 — стратегический режим

- Большой фон; смена режима когда D + H4 + H1 сходятся.
- D warning + младшие подтверждают = premium swing / regime shift.

---

## Таблица интерпретации (Shannon-style)

| Ситуация | Интерпретация |
|----------|----------------|
| M15 SELL 4, H1/H4 bull | Краткосрочный откат / fade локально |
| H1 SELL 4, H4 neutral | Рабочий short **candidate** |
| H1 SELL 4, H4 SELL 3+ | Сильный bearish warning |
| H4 SELL 4, D у resistance | Premium swing candidate |
| D SELL 4, H4/H1 подтверждают | Возможная **крупная** смена режима |

Связь с **Exec:** CONFIRMED только при согласовании H1 + (H4 или D) + протокол Douglas.

---

## Основные тезисы для EDGE

### 1. Один TF обманывает

H1 bear div при D1 uptrend = часто откат, не разворот тренда.

### 2. Вход — минимальный риск

Shannon: вход в зоне высокой вероятности и **низкого** риска.

**EDGE:** S/R proximity, ARMED → TRIGGERED, stop по структуре (не $).

### 3. Trend alignment

Торговать **по** старшему TF или явно помечать **counter-trend** (половинный риск).

### 4. Четыре стадии рынка (упрощённо)

Accumulation → markup → distribution → decline — MTF помогает видеть фазу.

### 5. Объём и MA

Подтверждение сдвига; у нас — MFI/OBV в roadmap (Propagation).

### 6. Short selling / squeezes

Отдельная осторожность; для commodities и индексов — учитывать в notes.

---

## Score 0–4 на каждом TF (связь с таблицей пользователя)

На **каждом** TF отдельно (не смешивать):

| Фактор | Вес (черновик) |
|--------|----------------|
| RSI divergence | +1 |
| MFI divergence | +1 (или +2 в propagation) |
| Volume exhaust | +1 |
| ATR extreme / expansion | +1 |

**4 на M15** ≠ **4 на D** по силе: вес старшего TF выше в **MTF alignment score**.

---

## Внедрено / план в коде

| Элемент | Файл |
|---------|------|
| 4 TF tables | `cloud_gem_report`, GEM My List |
| Роли TF | этот документ + `config/mtf_roles.json` |
| Propagation M15→H4 | `docs/edge-mtf-propagation.md` |
| Alignment rules | `src/mtf_alignment.py` (Phase 2) |

### MTF Alignment (следующий шаг)

- `aligned_bear`: H1+H4 или H1+H4+D same direction STRONG+
- `counter_trend`: M15 vs H4/D → WARNING only
- Колонка в GEM My List: **MTF read** (одна строка из таблицы выше)

---

## Оценка для EDGE

| Критерий | Оценка |
|----------|--------|
| MTF architecture | 10/10 |
| Наши 4 таблицы | 10/10 |
| Entry / risk | 9/10 |
| Индикаторная формула | 7/10 (контекст важнее) |

**Вывод:** книга №15 — **обязательная** для чтения GEM My List и Propagation Layer. Продолжение Douglas (исполнение) + Shannon (структура TF).

---

*Конспект пользователя + публичные описания (Google Books, AlphaTrends).*
