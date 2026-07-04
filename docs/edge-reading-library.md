# EDGE — библиотека из 100 книг (конспект по названиям)

Источник: список от пользователя (июнь 2026). Полные тексты **не** загружены — выжимки из публичных обзоров, интервью авторов и учебных материалов. Используем для развития **GEM My List** и правил EDGE, не как торговые рекомендации.

---

## Как это связано с проектом

| Уже в GEM / скане | Книги, которые усиливают |
|-------------------|---------------------------|
| RSI 28/72, дивергенции, Emerald/Ruby | Murphy, Pring, Miner, Elder |
| 4 TF (M15, H1, H4, D1) | Shannon (#15), Grimes |
| Сила сигнала WEAK→PREMIUM | Aronson, Kaufman, Davey |
| Чеклист 6 пунктов | Douglas, Tharp, Schwager |
| Свечи в GEM Logic | Nison, Coulling |
| S/R proximity | Grimes, Bulkowski |
| — (пока нет) | **Volume / VPA** (Coulling, Weis), **position sizing** (Tharp, Vince) |

---


## Книга 1 — Douglas (развёрнуто)

Полный конспект и внедрение: **`docs/books/01-trading-in-the-zone-douglas.md`**  
Протокол исполнения: **`docs/edge-discipline-protocol.md`**  
Журнал: **`data/signal_journal.csv`** (`python scripts/signal_journal.py`)

## Топ-15 для EDGE (приоритет пользователя)

### 1. Schwager — *A Complete Guide to the Futures Market*
- **Идея:** фьючерсы, спецификация контрактов, тестирование, TA + fundamental framework.
- **Для нас:** NG, WTI, Brent, Cocoa — корректные символы, сессии, не смешивать с акциями в одном риск-блоке.
- **Действие:** в чеклисте помечать **asset class** (energy / FX / index).

### 2. Murphy — *Technical Analysis of the Financial Markets*
- **Идея:** база TA — тренд, S/R, индикаторы, объём, межрыночный анализ.
- **Для нас:** язык отчётов (тренд / range), подтверждение сигнала объёмом (когда добавим VPA).

### 3. Grimes — *The Art and Science of Technical Analysis*
- **Идея:** edge = **дисбаланс** покупателей/продавцов; не паттерн ради паттерна; структура (swings) vs price action.
- **Для нас:** Ruby/Emerald только смыслены у **структуры** (у нас: near S/R + div + candle).
- **Действие:** не торговать «голый» RSI без S/R (уже в чеклисте location).

### 4. Aronson — *Evidence-Based Technical Analysis*
- **Идея:** data-mining bias; много правил → лучшее в бэктесте часто **удача**; нужны out-of-sample тесты и поправки.
- **Для нас:** не подкручивать RSI/lookback под последний месяц; логировать сигналы в JSON и считать hit-rate раз в квартал.
- **Действие (будущее):** `reports/signal_journal/` + простая статистика по Emerald/Ruby.

### 5. Kaufman — *Trading Systems and Methods*
- **Идея:** системы, адаптация, фильтры, режимы рынка.
- **Для нас:** MTF alignment = фильтр режима; combined score = ранжирование, не «всегда вход».

### 6. Davey — *Building Winning Algorithmic Trading Systems*
- **Идея:** walk-forward, робастность, не переоптимизировать.
- **Для нас:** один набор GEM-параметров (Pine 1.5 defaults) до явного A/B теста.

### 7. Chan — *Quantitative Trading*
- **Идея:** практичный quant, исполнение, простые альфы.
- **Для нас:** Python-скан как «альфа-радар», исполнение вручную у брокера (IG/CMC).

### 8. López de Prado — *Advances in Financial Machine Learning*
- **Идея:** overfitting, метки, purged CV, финансовые ML-ловушки.
- **Для нас:** если добавим ML — только после журнала сигналов; не обучать на тех же барах без purge.

### 9–10. Coulling — *Volume Price Analysis* / *Complete Guide to VPA*
- **Идея:** объём подтверждает цену; stopping volume; accumulation/distribution; «no demand» / «no supply».
- **Для нас:** **следующий большой модуль** — колонка Rel Volume в GEM My List; флаг «weak rally / weak decline».
- **Связь с GEM:** bearish div + **падающий объём на росте** = усилить Ruby score.

### 11–12. Schwager — *Market Wizards* / *Stock Market Wizards*
- **Идея:** разные edge (macro, discretionary, systematic); риск, дисциплина, адаптация.
- **Для нас:** не один «святой Грааль» — GEM My List = **скринер**, не автоторговля; размер позиции вне кода.


### Книги — конспекты

| # | Книга | Файл |
|---|--------|------|
| 1–3 | Douglas, Hougaard | `docs/books/01`…`03` |
| 15 | Shannon MTF | `docs/books/15-shannon-multiple-timeframes.md` |

### Психология — конспекты (пользователь)

| # | Книга | Файл |
|---|--------|------|
| 1 | Trading in the Zone | `docs/books/01-trading-in-the-zone-douglas.md` |
| 2 | The Disciplined Trader | `docs/books/02-the-disciplined-trader-douglas.md` |
| 3 | Best Loser Wins | `docs/books/03-best-loser-wins-hougaard.md` |

Два слоя EDGE: `docs/edge-two-layers.md` · Протокол: `docs/edge-discipline-protocol.md`

### 13–14. Douglas — Zone + Disciplined Trader (см. `docs/books/01`…`02`)
- **Идея:** вероятностное мышление; план; принятие серии исходов.
- **Для нас:** чеклист **Trade OK** = «разрешение смотреть сделку», не «обязан войти».

### 14. Hougaard — *Best Loser Wins*
- **Идея:** качество проигрышей; процесс > один трейд.
- **Для нас:** пункт risk в чеклисте; не повышать tier без ARMED/TRIGGERED.

### 15. Shannon — *Technical Analysis Using Multiple Timeframes*
- **Идея:** старший TF — контекст и тренд; младший — вход; **alignment** снижает ложные сигналы; 4 стадии рынка; стопы по структуре, не по $.
- **Для нас:** уже сделано — 4 таблицы M15/H1/H4/D1 + GEM My List; правило **2+ TF agree** в чеклисте = прямо из Shannon.
- **Уточнение:** торговать в сторону **D1/H4**, входить по **H1/M15** (для вас: energy/FX — H4+D1 фильтр, H1 trigger).

---

## 10 блоков × 10 книг (кратко — зачем категория)

### 1. Психология (1–10)
Процесс, эмоции, дисциплина. **EDGE:** чеклист и «Trade OK» снимают FOMO; Finviz gainers — отдельный список.

### 2. Market Wizards (11–20)
Модели мышления, риск. **EDGE:** не копировать чужой метод — брать принципы (size, stops, adapt).

### 3. Технический анализ (21–30)
База и паттерны. **EDGE:** Murphy/Pring = словарь; Bulkowski = ожидания по паттернам (осторожно с data mining).

### 4. Price action (31–40)
Брукс, Raschke, Dalton (market profile). **EDGE:** бары + контекст; позже — profile уровни рядом с S/R.

### 5. Systems / quant (41–50)
Тестирование и системы. **EDGE:** Aronson + Davey + Kaufman = как не врать себе бэктестом.

### 6. Risk / sizing (51–60)
Tharp, Vince, Grant. **EDGE:** следующий слой — % риска на инструмент в чеклисте (не только GEM).

### 7. Свечи (61–70)
Nison, Elder. **EDGE:** уже в GEM (bull/bear candle confluence).

### 8. Объём / flow (71–80)
VPA, Wyckoff, order flow. **EDGE:** высший приоритет после стабилизации MTF.

### 9. Акции / инвестиции (81–90)
Меньше приоритет для текущего watchlist (нет акций). Вернуться, если снова добавите NVDA и т.д.

### 10. История / макро / поведение (91–100)
Контекст пузырей, когнитивные искажения. **EDGE:** не торговать Ruby на индексе в день CPI/FOMC без пометки **event risk** (будущее).

---

## Правила EDGE (синтез топ-15 + GEM My List)

1. **Старший TF задаёт сторону** (H4 + D1); младший — тайминг (M15 + H1).
2. **Вход только если Trade OK** (≥4/6 и STRONG+), иначе watchlist.
3. **Один тематический риск** (не три нефти + три USD одновременно на полный размер).
4. **Сигнал ≠ edge**, пока не проверен журналом (Aronson).
5. **Объём** (когда добавим) должен **подтверждать** Ruby/Emerald, иначе понизить tier.
6. **Психология:** список Finviz / gainers не смешивать с «моими 12».

---

## Команды в cloud

| Фраза | Результат |
|-------|-----------|
| **GEM my list** | Trade board + 4 TF tables |
| **gemlist** | то же |
| **4 tables** | только M15 / H1 / H4 / D1 |

---

## Обновления кода (очередь по книгам)

| Приоритет | Фича | Книга |
|-----------|------|-------|
| P1 | Журнал сигналов + win rate | Aronson |
| P1 | Rel volume / VPA flag | Coulling |
| P2 | Event calendar flag (CPI, NFP, OPEC) | Schwager / macro |
| P2 | Position size hint (% risk) | Tharp |
| P3 | Regime filter (trend vs range) | Grimes, Kaufman |

---

*Документ обновлять при добавлении новых глав или цитат пользователя.*
